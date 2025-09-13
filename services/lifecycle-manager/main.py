import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import redis.asyncio as redis
from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import docker
import requests

from redroid_manager import RedroidManager
from container_orchestrator import ContainerOrchestrator
from android_configurator import AndroidConfigurator

app = FastAPI(title="Lifecycle Manager Service", version="1.0.0")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://acp_user:acp_secure_password@localhost:5432/android_platform")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Service URLs
IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL", "http://identity-manager:8001")
LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL", "http://location-manager:8002")
NETWORK_SERVICE_URL = os.getenv("NETWORK_SERVICE_URL", "http://network-manager:8003")

engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
Base = declarative_base()

# Redis client
redis_client = None

# Components
redroid_manager = RedroidManager()
container_orchestrator = ContainerOrchestrator()
android_configurator = AndroidConfigurator()

class AndroidInstance(Base):
    __tablename__ = "android_instances"
    
    instance_id = Column(String, primary_key=True)
    container_id = Column(String, unique=True, nullable=True)
    container_name = Column(String, unique=True, nullable=False)
    android_version = Column(String, nullable=False)
    device_profile = Column(Text, nullable=True)  # JSON string
    network_config = Column(Text, nullable=True)  # JSON string
    location_config = Column(Text, nullable=True)  # JSON string
    status = Column(String, default="creating")  # creating, running, stopped, failed
    cpu_limit = Column(Float, default=2.0)
    memory_limit = Column(String, default="4G")
    storage_size = Column(String, default="8G")
    vnc_port = Column(Integer, nullable=True)
    adb_port = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

class InstanceRequest(BaseModel):
    android_version: Optional[str] = "13"
    device_manufacturer: Optional[str] = None
    device_model: Optional[str] = None
    cpu_limit: Optional[float] = 2.0
    memory_limit: Optional[str] = "4G"
    storage_size: Optional[str] = "8G"
    network_config: Optional[Dict] = None
    location_config: Optional[Dict] = None
    custom_properties: Optional[Dict] = None

class InstanceResponse(BaseModel):
    instance_id: str
    container_name: str
    status: str
    android_version: str
    vnc_port: Optional[int]
    adb_port: Optional[int]
    device_profile: Optional[Dict]
    network_config: Optional[Dict]
    location_config: Optional[Dict]
    created_at: datetime

@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = redis.from_url(REDIS_URL)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize components
    await redroid_manager.initialize()
    await container_orchestrator.initialize()
    
    # Start background tasks
    asyncio.create_task(monitor_instances())

@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()

async def monitor_instances():
    """Background task to monitor instance health"""
    while True:
        try:
            await check_instance_health()
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            print(f"Instance monitoring error: {e}")
            await asyncio.sleep(60)

async def check_instance_health():
    """Check health of all running instances"""
    
    async with AsyncSession(engine) as session:
        # Get all running instances
        result = await session.execute(
            session.query(AndroidInstance)
            .filter(AndroidInstance.status == "running")
        )
        
        instances = result.scalars().all()
        
        for instance in instances:
            try:
                # Check if container is still running
                is_healthy = await container_orchestrator.check_container_health(instance.container_id)
                
                if is_healthy:
                    instance.last_heartbeat = datetime.utcnow()
                else:
                    instance.status = "failed"
                    instance.error_message = "Container health check failed"
                
            except Exception as e:
                instance.status = "failed"
                instance.error_message = str(e)
        
        await session.commit()

@app.post("/instance/create", response_model=InstanceResponse)
async def create_instance(request: InstanceRequest, background_tasks: BackgroundTasks):
    """Create a new Android instance"""
    
    try:
        instance_id = str(uuid.uuid4())
        container_name = f"android-{instance_id[:8]}"
        
        # Generate device identity
        identity_response = requests.post(
            f"{IDENTITY_SERVICE_URL}/generate-identity",
            json={
                "manufacturer": request.device_manufacturer,
                "model": request.device_model,
                "android_version": request.android_version,
                "custom_properties": request.custom_properties
            }
        )
        
        if identity_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to generate device identity")
        
        device_identity = identity_response.json()
        
        # Configure network if requested
        network_config = None
        if request.network_config:
            network_response = requests.post(
                f"{NETWORK_SERVICE_URL}/network/{instance_id}",
                json=request.network_config
            )
            
            if network_response.status_code == 200:
                network_config = network_response.json()
        
        # Store instance in database
        async with AsyncSession(engine) as session:
            instance = AndroidInstance(
                instance_id=instance_id,
                container_name=container_name,
                android_version=request.android_version,
                device_profile=json.dumps(device_identity),
                network_config=json.dumps(network_config) if network_config else None,
                location_config=json.dumps(request.location_config) if request.location_config else None,
                cpu_limit=request.cpu_limit,
                memory_limit=request.memory_limit,
                storage_size=request.storage_size,
                status="creating"
            )
            session.add(instance)
            await session.commit()
        
        # Start container creation in background
        background_tasks.add_task(
            create_container_async, 
            instance_id, 
            container_name, 
            request, 
            device_identity, 
            network_config
        )
        
        return InstanceResponse(
            instance_id=instance_id,
            container_name=container_name,
            status="creating",
            android_version=request.android_version,
            vnc_port=None,
            adb_port=None,
            device_profile=device_identity,
            network_config=network_config,
            location_config=request.location_config,
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Instance creation failed: {str(e)}")

async def create_container_async(instance_id: str, container_name: str, 
                               request: InstanceRequest, device_identity: Dict, 
                               network_config: Optional[Dict]):
    """Async task to create and configure container"""
    
    try:
        # Update status to configuring
        async with AsyncSession(engine) as session:
            instance = await session.get(AndroidInstance, instance_id)
            instance.status = "configuring"
            await session.commit()
        
        # Create Redroid container
        container_info = await redroid_manager.create_container(
            container_name=container_name,
            android_version=request.android_version,
            device_identity=device_identity,
            cpu_limit=request.cpu_limit,
            memory_limit=request.memory_limit,
            storage_size=request.storage_size,
            network_config=network_config
        )
        
        # Configure Android system
        await android_configurator.configure_instance(
            container_name, device_identity, network_config
        )
        
        # Start container
        await container_orchestrator.start_container(container_info["container_id"])
        
        # Wait for container to be ready
        await asyncio.sleep(10)
        
        # Configure location if requested
        if request.location_config:
            location_response = requests.post(
                f"{LOCATION_SERVICE_URL}/location/{instance_id}",
                json=request.location_config
            )
        
        # Update instance with success
        async with AsyncSession(engine) as session:
            instance = await session.get(AndroidInstance, instance_id)
            instance.container_id = container_info["container_id"]
            instance.vnc_port = container_info.get("vnc_port")
            instance.adb_port = container_info.get("adb_port")
            instance.status = "running"
            instance.started_at = datetime.utcnow()
            instance.last_heartbeat = datetime.utcnow()
            await session.commit()
        
    except Exception as e:
        # Update instance with failure
        async with AsyncSession(engine) as session:
            instance = await session.get(AndroidInstance, instance_id)
            instance.status = "failed"
            instance.error_message = str(e)
            await session.commit()

@app.get("/instance/{instance_id}", response_model=InstanceResponse)
async def get_instance(instance_id: str):
    """Get instance information"""
    
    async with AsyncSession(engine) as session:
        instance = await session.get(AndroidInstance, instance_id)
        
        if not instance:
            raise HTTPException(status_code=404, detail="Instance not found")
        
        return InstanceResponse(
            instance_id=instance.instance_id,
            container_name=instance.container_name,
            status=instance.status,
            android_version=instance.android_version,
            vnc_port=instance.vnc_port,
            adb_port=instance.adb_port,
            device_profile=json.loads(instance.device_profile) if instance.device_profile else None,
            network_config=json.loads(instance.network_config) if instance.network_config else None,
            location_config=json.loads(instance.location_config) if instance.location_config else None,
            created_at=instance.created_at
        )

@app.post("/instance/{instance_id}/start")
async def start_instance(instance_id: str):
    """Start a stopped instance"""
    
    try:
        async with AsyncSession(engine) as session:
            instance = await session.get(AndroidInstance, instance_id)
            
            if not instance:
                raise HTTPException(status_code=404, detail="Instance not found")
            
            if instance.status == "running":
                return {"status": "already_running"}
            
            # Start container
            await container_orchestrator.start_container(instance.container_id)
            
            # Update status
            instance.status = "running"
            instance.started_at = datetime.utcnow()
            instance.last_heartbeat = datetime.utcnow()
            await session.commit()
        
        return {"status": "started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start instance: {str(e)}")

@app.post("/instance/{instance_id}/stop")
async def stop_instance(instance_id: str):
    """Stop a running instance"""
    
    try:
        async with AsyncSession(engine) as session:
            instance = await session.get(AndroidInstance, instance_id)
            
            if not instance:
                raise HTTPException(status_code=404, detail="Instance not found")
            
            # Stop container
            await container_orchestrator.stop_container(instance.container_id)
            
            # Update status
            instance.status = "stopped"
            instance.stopped_at = datetime.utcnow()
            await session.commit()
        
        return {"status": "stopped"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop instance: {str(e)}")

@app.post("/instance/{instance_id}/restart")
async def restart_instance(instance_id: str):
    """Restart an instance"""
    
    try:
        await stop_instance(instance_id)
        await asyncio.sleep(2)
        await start_instance(instance_id)
        
        return {"status": "restarted"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart instance: {str(e)}")

@app.delete("/instance/{instance_id}")
async def delete_instance(instance_id: str):
    """Delete an instance and cleanup resources"""
    
    try:
        async with AsyncSession(engine) as session:
            instance = await session.get(AndroidInstance, instance_id)
            
            if not instance:
                raise HTTPException(status_code=404, detail="Instance not found")
            
            # Stop and remove container
            if instance.container_id:
                await container_orchestrator.remove_container(instance.container_id)
            
            # Cleanup network configuration
            try:
                requests.delete(f"{NETWORK_SERVICE_URL}/network/{instance_id}")
            except:
                pass  # Network might not be configured
            
            # Remove from database
            await session.delete(instance)
            await session.commit()
        
        # Clear cache
        await redis_client.delete(f"instance:{instance_id}")
        
        return {"status": "deleted"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete instance: {str(e)}")

@app.get("/instances")
async def list_instances(status: Optional[str] = None, limit: int = 100, offset: int = 0):
    """List all instances"""
    
    async with AsyncSession(engine) as session:
        query = session.query(AndroidInstance)
        
        if status:
            query = query.filter(AndroidInstance.status == status)
        
        query = query.offset(offset).limit(limit).order_by(AndroidInstance.created_at.desc())
        
        result = await session.execute(query)
        instances = result.scalars().all()
        
        return {
            "instances": [
                {
                    "instance_id": instance.instance_id,
                    "container_name": instance.container_name,
                    "status": instance.status,
                    "android_version": instance.android_version,
                    "vnc_port": instance.vnc_port,
                    "adb_port": instance.adb_port,
                    "created_at": instance.created_at,
                    "last_heartbeat": instance.last_heartbeat
                }
                for instance in instances
            ]
        }

@app.get("/instance/{instance_id}/logs")
async def get_instance_logs(instance_id: str, lines: int = 100):
    """Get container logs for instance"""
    
    try:
        async with AsyncSession(engine) as session:
            instance = await session.get(AndroidInstance, instance_id)
            
            if not instance or not instance.container_id:
                raise HTTPException(status_code=404, detail="Instance not found")
            
            logs = await container_orchestrator.get_container_logs(
                instance.container_id, lines=lines
            )
            
            return {"logs": logs}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

@app.get("/instance/{instance_id}/stats")
async def get_instance_stats(instance_id: str):
    """Get container stats for instance"""
    
    try:
        async with AsyncSession(engine) as session:
            instance = await session.get(AndroidInstance, instance_id)
            
            if not instance or not instance.container_id:
                raise HTTPException(status_code=404, detail="Instance not found")
            
            stats = await container_orchestrator.get_container_stats(
                instance.container_id
            )
            
            return stats
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.post("/instance/{instance_id}/exec")
async def execute_command(instance_id: str, command: str):
    """Execute command in instance"""
    
    try:
        async with AsyncSession(engine) as session:
            instance = await session.get(AndroidInstance, instance_id)
            
            if not instance or not instance.container_id:
                raise HTTPException(status_code=404, detail="Instance not found")
            
            result = await container_orchestrator.execute_command(
                instance.container_id, command
            )
            
            return result
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")

@app.get("/stats")
async def get_platform_stats():
    """Get overall platform statistics"""
    
    try:
        async with AsyncSession(engine) as session:
            # Count instances by status
            total_result = await session.execute("SELECT COUNT(*) FROM android_instances")
            total_instances = total_result.scalar()
            
            running_result = await session.execute("SELECT COUNT(*) FROM android_instances WHERE status = 'running'")
            running_instances = running_result.scalar()
            
            failed_result = await session.execute("SELECT COUNT(*) FROM android_instances WHERE status = 'failed'")
            failed_instances = failed_result.scalar()
            
            # Get resource usage
            resource_usage = await container_orchestrator.get_total_resource_usage()
            
            return {
                "total_instances": total_instances,
                "running_instances": running_instances,
                "failed_instances": failed_instances,
                "stopped_instances": total_instances - running_instances - failed_instances,
                "resource_usage": resource_usage,
                "uptime": time.time() - container_orchestrator.start_time
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)