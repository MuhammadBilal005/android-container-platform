import asyncio
import json
import os
import subprocess
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import redis.asyncio as redis
from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import requests
import aiohttp

from proxy_manager import ProxyManager
from network_isolator import NetworkIsolator
from traffic_router import TrafficRouter

app = FastAPI(title="Network Manager Service", version="1.0.0")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://acp_user:acp_secure_password@localhost:5432/android_platform")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
Base = declarative_base()

# Redis client
redis_client = None

# Network components
proxy_manager = ProxyManager()
network_isolator = NetworkIsolator()
traffic_router = TrafficRouter()

class NetworkConfig(Base):
    __tablename__ = "network_configs"
    
    instance_id = Column(String, primary_key=True)
    ip_address = Column(String, nullable=False)
    proxy_config = Column(Text, nullable=True)  # JSON string
    dns_servers = Column(Text, nullable=True)   # JSON string
    network_namespace = Column(String, nullable=True)
    traffic_rules = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class ProxyConfig(Base):
    __tablename__ = "proxy_configs"
    
    id = Column(String, primary_key=True)
    proxy_type = Column(String, nullable=False)  # http, socks5, residential, etc.
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String, nullable=True)
    password = Column(String, nullable=True)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    is_working = Column(Boolean, default=True)
    response_time = Column(Integer, nullable=True)  # milliseconds
    last_checked = Column(DateTime, default=datetime.utcnow)

class NetworkRequest(BaseModel):
    proxy_type: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    dns_servers: Optional[List[str]] = None
    custom_rules: Optional[Dict] = None

class ProxyRequest(BaseModel):
    proxy_type: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None

class NetworkResponse(BaseModel):
    instance_id: str
    ip_address: str
    proxy_config: Optional[Dict]
    dns_servers: List[str]
    network_namespace: str
    external_ip: str
    geolocation: Dict

@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = redis.from_url(REDIS_URL)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize network components
    await proxy_manager.initialize()
    await network_isolator.initialize()

@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()

def generate_private_ip() -> str:
    """Generate a unique private IP address for container"""
    # Use 172.20.x.x range for container networking
    base_network = ipaddress.IPv4Network('172.20.0.0/16')
    
    # Generate random IP in range
    import random
    while True:
        host_part = random.randint(100, 65000)  # Avoid common IPs
        ip = base_network.network_address + host_part
        
        # Check if IP is not already assigned (simplified check)
        if str(ip) not in ['172.20.0.1', '172.20.0.2']:  # Reserve gateway IPs
            return str(ip)

@app.post("/network/{instance_id}", response_model=NetworkResponse)
async def configure_network(instance_id: str, config: NetworkRequest):
    """Configure network isolation and proxy for Android instance"""
    
    try:
        # Generate unique IP address
        ip_address = generate_private_ip()
        
        # Select proxy based on requirements
        proxy_config = None
        if config.proxy_type or config.country:
            proxy_config = await proxy_manager.get_proxy(
                proxy_type=config.proxy_type,
                country=config.country,
                city=config.city
            )
            
            if not proxy_config:
                raise HTTPException(status_code=400, detail="No suitable proxy available")
        
        # Set up DNS servers
        dns_servers = config.dns_servers or ["8.8.8.8", "1.1.1.1"]
        if proxy_config and proxy_config.get("dns_servers"):
            dns_servers = proxy_config["dns_servers"]
        
        # Create network namespace
        namespace = f"netns-{instance_id}"
        await network_isolator.create_namespace(namespace, ip_address)
        
        # Configure proxy routing if proxy is specified
        if proxy_config:
            await traffic_router.configure_proxy_routing(
                namespace, ip_address, proxy_config
            )
        
        # Configure DNS
        await network_isolator.configure_dns(namespace, dns_servers)
        
        # Apply custom traffic rules
        if config.custom_rules:
            await traffic_router.apply_custom_rules(namespace, config.custom_rules)
        
        # Get external IP and geolocation
        external_ip, geolocation = await _get_external_info(proxy_config)
        
        # Store configuration in database
        async with AsyncSession(engine) as session:
            network_config = NetworkConfig(
                instance_id=instance_id,
                ip_address=ip_address,
                proxy_config=json.dumps(proxy_config) if proxy_config else None,
                dns_servers=json.dumps(dns_servers),
                network_namespace=namespace,
                traffic_rules=json.dumps(config.custom_rules) if config.custom_rules else None
            )
            session.add(network_config)
            await session.commit()
        
        # Cache configuration
        await redis_client.setex(
            f"network:{instance_id}",
            3600,
            json.dumps({
                "ip_address": ip_address,
                "proxy_config": proxy_config,
                "dns_servers": dns_servers,
                "namespace": namespace,
                "external_ip": external_ip,
                "geolocation": geolocation
            })
        )
        
        return NetworkResponse(
            instance_id=instance_id,
            ip_address=ip_address,
            proxy_config=proxy_config,
            dns_servers=dns_servers,
            network_namespace=namespace,
            external_ip=external_ip,
            geolocation=geolocation
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Network configuration failed: {str(e)}")

@app.get("/network/{instance_id}")
async def get_network_config(instance_id: str):
    """Get current network configuration for instance"""
    
    # Try cache first
    cached_config = await redis_client.get(f"network:{instance_id}")
    if cached_config:
        return json.loads(cached_config)
    
    # Fetch from database
    async with AsyncSession(engine) as session:
        config = await session.get(NetworkConfig, instance_id)
        if not config:
            raise HTTPException(status_code=404, detail="Network configuration not found")
        
        return {
            "instance_id": config.instance_id,
            "ip_address": config.ip_address,
            "proxy_config": json.loads(config.proxy_config) if config.proxy_config else None,
            "dns_servers": json.loads(config.dns_servers) if config.dns_servers else [],
            "network_namespace": config.network_namespace,
            "is_active": config.is_active
        }

@app.put("/network/{instance_id}/proxy")
async def update_proxy(instance_id: str, proxy_config: Dict):
    """Update proxy configuration for instance"""
    
    try:
        # Get current network config
        async with AsyncSession(engine) as session:
            config = await session.get(NetworkConfig, instance_id)
            if not config:
                raise HTTPException(status_code=404, detail="Network configuration not found")
            
            # Update proxy routing
            namespace = config.network_namespace
            await traffic_router.configure_proxy_routing(
                namespace, config.ip_address, proxy_config
            )
            
            # Update database
            config.proxy_config = json.dumps(proxy_config)
            config.updated_at = datetime.utcnow()
            await session.commit()
            
            # Update cache
            await redis_client.delete(f"network:{instance_id}")
        
        return {"status": "updated", "proxy_config": proxy_config}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy update failed: {str(e)}")

@app.post("/proxy/add")
async def add_proxy(proxy: ProxyRequest):
    """Add a new proxy to the pool"""
    
    try:
        proxy_id = str(uuid.uuid4())
        
        # Test proxy before adding
        is_working, response_time = await proxy_manager.test_proxy({
            "host": proxy.host,
            "port": proxy.port,
            "username": proxy.username,
            "password": proxy.password,
            "type": proxy.proxy_type
        })
        
        # Store in database
        async with AsyncSession(engine) as session:
            proxy_config = ProxyConfig(
                id=proxy_id,
                proxy_type=proxy.proxy_type,
                host=proxy.host,
                port=proxy.port,
                username=proxy.username,
                password=proxy.password,
                country=proxy.country,
                city=proxy.city,
                is_working=is_working,
                response_time=response_time
            )
            session.add(proxy_config)
            await session.commit()
        
        return {
            "proxy_id": proxy_id,
            "status": "working" if is_working else "failed",
            "response_time": response_time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add proxy: {str(e)}")

@app.get("/proxy/list")
async def list_proxies(proxy_type: Optional[str] = None, 
                      country: Optional[str] = None,
                      working_only: bool = True):
    """List available proxies"""
    
    async with AsyncSession(engine) as session:
        query = session.query(ProxyConfig)
        
        if proxy_type:
            query = query.filter(ProxyConfig.proxy_type == proxy_type)
        if country:
            query = query.filter(ProxyConfig.country == country)
        if working_only:
            query = query.filter(ProxyConfig.is_working == True)
        
        proxies = await session.execute(query)
        
        return {
            "proxies": [
                {
                    "id": proxy.id,
                    "type": proxy.proxy_type,
                    "host": proxy.host,
                    "port": proxy.port,
                    "country": proxy.country,
                    "city": proxy.city,
                    "is_working": proxy.is_working,
                    "response_time": proxy.response_time,
                    "last_checked": proxy.last_checked
                }
                for proxy in proxies.scalars()
            ]
        }

@app.delete("/network/{instance_id}")
async def cleanup_network(instance_id: str):
    """Clean up network configuration and isolation"""
    
    try:
        # Get network configuration
        async with AsyncSession(engine) as session:
            config = await session.get(NetworkConfig, instance_id)
            if not config:
                raise HTTPException(status_code=404, detail="Network configuration not found")
            
            # Clean up network namespace
            if config.network_namespace:
                await network_isolator.destroy_namespace(config.network_namespace)
            
            # Remove configuration
            await session.delete(config)
            await session.commit()
        
        # Clear cache
        await redis_client.delete(f"network:{instance_id}")
        
        return {"status": "cleaned_up", "instance_id": instance_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Network cleanup failed: {str(e)}")

@app.get("/network/{instance_id}/status")
async def get_network_status(instance_id: str):
    """Get network connectivity status"""
    
    try:
        # Get network configuration
        config_data = await redis_client.get(f"network:{instance_id}")
        if not config_data:
            raise HTTPException(status_code=404, detail="Network configuration not found")
        
        config = json.loads(config_data)
        namespace = config.get("network_namespace")
        
        # Test connectivity
        connectivity = await network_isolator.test_connectivity(namespace)
        
        # Get current external IP
        external_ip = await _get_current_external_ip(config.get("proxy_config"))
        
        return {
            "instance_id": instance_id,
            "connectivity": connectivity,
            "external_ip": external_ip,
            "dns_working": connectivity.get("dns", False),
            "internet_access": connectivity.get("internet", False),
            "proxy_working": connectivity.get("proxy", False)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

async def _get_external_info(proxy_config: Optional[Dict]) -> tuple:
    """Get external IP and geolocation"""
    
    try:
        if proxy_config:
            # Use proxy to get external info
            proxy_url = f"http://{proxy_config['host']}:{proxy_config['port']}"
            if proxy_config.get('username'):
                proxy_url = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get('http://httpbin.org/ip', 
                                     proxy=proxy_url, 
                                     timeout=aiohttp.ClientTimeout(total=10)) as response:
                    data = await response.json()
                    external_ip = data['origin']
        else:
            # Direct connection
            async with aiohttp.ClientSession() as session:
                async with session.get('http://httpbin.org/ip',
                                     timeout=aiohttp.ClientTimeout(total=10)) as response:
                    data = await response.json()
                    external_ip = data['origin']
        
        # Get geolocation
        async with aiohttp.ClientSession() as session:
            async with session.get(f'http://ip-api.com/json/{external_ip}',
                                 timeout=aiohttp.ClientTimeout(total=10)) as response:
                geolocation = await response.json()
        
        return external_ip, geolocation
        
    except Exception as e:
        return "unknown", {"error": str(e)}

async def _get_current_external_ip(proxy_config: Optional[Dict]) -> str:
    """Get current external IP"""
    
    try:
        external_ip, _ = await _get_external_info(proxy_config)
        return external_ip
    except:
        return "unknown"

@app.post("/network/{instance_id}/test")
async def test_network(instance_id: str):
    """Test network configuration and connectivity"""
    
    try:
        config_data = await redis_client.get(f"network:{instance_id}")
        if not config_data:
            raise HTTPException(status_code=404, detail="Network configuration not found")
        
        config = json.loads(config_data)
        namespace = config.get("network_namespace")
        
        # Run comprehensive network tests
        test_results = {
            "dns_resolution": await _test_dns(namespace),
            "internet_connectivity": await _test_internet(namespace),
            "proxy_functionality": await _test_proxy(namespace, config.get("proxy_config")),
            "ip_leak_test": await _test_ip_leak(namespace, config.get("proxy_config")),
            "speed_test": await _test_speed(namespace, config.get("proxy_config"))
        }
        
        return {
            "instance_id": instance_id,
            "test_results": test_results,
            "overall_status": "pass" if all(test_results.values()) else "fail"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Network test failed: {str(e)}")

async def _test_dns(namespace: str) -> bool:
    """Test DNS resolution"""
    try:
        result = subprocess.run([
            "ip", "netns", "exec", namespace,
            "nslookup", "google.com"
        ], capture_output=True, timeout=10)
        return result.returncode == 0
    except:
        return False

async def _test_internet(namespace: str) -> bool:
    """Test internet connectivity"""
    try:
        result = subprocess.run([
            "ip", "netns", "exec", namespace,
            "curl", "-s", "--max-time", "10", "http://httpbin.org/ip"
        ], capture_output=True, timeout=15)
        return result.returncode == 0
    except:
        return False

async def _test_proxy(namespace: str, proxy_config: Optional[Dict]) -> bool:
    """Test proxy functionality"""
    if not proxy_config:
        return True  # No proxy configured
    
    try:
        proxy_url = f"http://{proxy_config['host']}:{proxy_config['port']}"
        result = subprocess.run([
            "ip", "netns", "exec", namespace,
            "curl", "-s", "--proxy", proxy_url, "--max-time", "10",
            "http://httpbin.org/ip"
        ], capture_output=True, timeout=15)
        return result.returncode == 0
    except:
        return False

async def _test_ip_leak(namespace: str, proxy_config: Optional[Dict]) -> bool:
    """Test for IP leaks"""
    if not proxy_config:
        return True  # No proxy to leak from
    
    try:
        # Test multiple IP detection services
        services = [
            "http://httpbin.org/ip",
            "http://icanhazip.com",
            "http://ipinfo.io/ip"
        ]
        
        ips = []
        for service in services:
            try:
                proxy_url = f"http://{proxy_config['host']}:{proxy_config['port']}"
                result = subprocess.run([
                    "ip", "netns", "exec", namespace,
                    "curl", "-s", "--proxy", proxy_url, "--max-time", "5", service
                ], capture_output=True, timeout=10)
                
                if result.returncode == 0:
                    ip = result.stdout.decode().strip()
                    ips.append(ip)
            except:
                continue
        
        # All IPs should be the same (proxy IP)
        return len(set(ips)) <= 1 if ips else False
        
    except:
        return False

async def _test_speed(namespace: str, proxy_config: Optional[Dict]) -> Dict:
    """Test connection speed"""
    try:
        # Simple speed test using curl
        import time
        
        start_time = time.time()
        if proxy_config:
            proxy_url = f"http://{proxy_config['host']}:{proxy_config['port']}"
            result = subprocess.run([
                "ip", "netns", "exec", namespace,
                "curl", "-s", "--proxy", proxy_url, "--max-time", "30",
                "http://httpbin.org/bytes/1048576"  # 1MB test
            ], capture_output=True, timeout=35)
        else:
            result = subprocess.run([
                "ip", "netns", "exec", namespace,
                "curl", "-s", "--max-time", "30",
                "http://httpbin.org/bytes/1048576"  # 1MB test
            ], capture_output=True, timeout=35)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            speed_mbps = (1.0 / duration) * 8  # Convert to Mbps
            return {
                "success": True,
                "duration_seconds": duration,
                "speed_mbps": round(speed_mbps, 2)
            }
        
        return {"success": False, "error": "Speed test failed"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)