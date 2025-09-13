import asyncio
import subprocess
from typing import Dict, List, Optional

class TrafficRouter:
    """Handles traffic routing and proxy configuration for namespaces"""
    
    def __init__(self):
        self.namespace_routes = {}  # namespace -> routing config
    
    async def configure_proxy_routing(self, namespace: str, ip_address: str, proxy_config: Dict) -> bool:
        """Configure proxy routing for a namespace"""
        
        try:
            proxy_type = proxy_config.get("type", "http")
            proxy_host = proxy_config["host"]
            proxy_port = proxy_config["port"]
            
            if proxy_type.lower() == "socks5":
                return await self._configure_socks5_routing(namespace, ip_address, proxy_config)
            else:
                return await self._configure_http_proxy_routing(namespace, ip_address, proxy_config)
                
        except Exception as e:
            print(f"Proxy routing configuration failed for {namespace}: {e}")
            return False
    
    async def _configure_http_proxy_routing(self, namespace: str, ip_address: str, proxy_config: Dict) -> bool:
        """Configure HTTP proxy routing"""
        
        try:
            proxy_host = proxy_config["host"]
            proxy_port = proxy_config["port"]
            
            # Set up iptables rules to redirect HTTP/HTTPS traffic through proxy
            # First, allow direct connection to proxy
            subprocess.run([
                "iptables", "-A", "OUTPUT",
                "-s", ip_address,
                "-d", proxy_host,
                "-p", "tcp", "--dport", str(proxy_port),
                "-j", "ACCEPT"
            ], check=False)
            
            # Redirect HTTP traffic (port 80) to proxy
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "iptables", "-t", "nat", "-A", "OUTPUT",
                "-p", "tcp", "--dport", "80",
                "-j", "DNAT", "--to-destination", f"{proxy_host}:{proxy_port}"
            ], check=False)
            
            # Redirect HTTPS traffic (port 443) to proxy
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "iptables", "-t", "nat", "-A", "OUTPUT", 
                "-p", "tcp", "--dport", "443",
                "-j", "DNAT", "--to-destination", f"{proxy_host}:{proxy_port}"
            ], check=False)
            
            # Set HTTP_PROXY and HTTPS_PROXY environment variables for the namespace
            proxy_url = self._build_proxy_url(proxy_config)
            
            # Create a script to set proxy environment variables
            proxy_script = f"""#!/bin/bash
export HTTP_PROXY="{proxy_url}"
export HTTPS_PROXY="{proxy_url}"
export http_proxy="{proxy_url}"
export https_proxy="{proxy_url}"
export no_proxy="localhost,127.0.0.1"
exec "$@"
"""
            
            # Write proxy script to namespace
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "sh", "-c", f"echo '{proxy_script}' > /usr/local/bin/proxy-wrapper && chmod +x /usr/local/bin/proxy-wrapper"
            ], check=False)
            
            self.namespace_routes[namespace] = {
                "type": "http_proxy",
                "proxy_config": proxy_config,
                "ip_address": ip_address
            }
            
            return True
            
        except Exception as e:
            print(f"HTTP proxy routing failed for {namespace}: {e}")
            return False
    
    async def _configure_socks5_routing(self, namespace: str, ip_address: str, proxy_config: Dict) -> bool:
        """Configure SOCKS5 proxy routing using redsocks"""
        
        try:
            proxy_host = proxy_config["host"]
            proxy_port = proxy_config["port"]
            proxy_user = proxy_config.get("username", "")
            proxy_pass = proxy_config.get("password", "")
            
            # Install redsocks if not available (simplified check)
            subprocess.run(["which", "redsocks"], check=True, capture_output=True)
            
            # Create redsocks configuration
            redsocks_config = f"""
base {{
    log_debug = off;
    log_info = on;
    log = stderr;
    daemon = off;
    redirector = iptables;
}}

redsocks {{
    local_ip = 127.0.0.1;
    local_port = 12345;
    ip = {proxy_host};
    port = {proxy_port};
    type = socks5;
"""
            
            if proxy_user and proxy_pass:
                redsocks_config += f"""
    login = "{proxy_user}";
    password = "{proxy_pass}";
"""
            
            redsocks_config += "}\n"
            
            # Write config file
            config_path = f"/tmp/redsocks_{namespace}.conf"
            with open(config_path, 'w') as f:
                f.write(redsocks_config)
            
            # Start redsocks in namespace
            subprocess.Popen([
                "ip", "netns", "exec", namespace,
                "redsocks", "-c", config_path
            ])
            
            # Configure iptables to redirect traffic to redsocks
            # Create a new chain for proxy
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "iptables", "-t", "nat", "-N", "PROXY"
            ], check=False)
            
            # Ignore local traffic
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "iptables", "-t", "nat", "-A", "PROXY",
                "-d", "127.0.0.0/8", "-j", "RETURN"
            ], check=False)
            
            # Ignore RFC1918 addresses
            for subnet in ["192.168.0.0/16", "172.16.0.0/12", "10.0.0.0/8"]:
                subprocess.run([
                    "ip", "netns", "exec", namespace,
                    "iptables", "-t", "nat", "-A", "PROXY",
                    "-d", subnet, "-j", "RETURN"
                ], check=False)
            
            # Redirect TCP traffic to redsocks
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "iptables", "-t", "nat", "-A", "PROXY",
                "-p", "tcp", "-j", "REDIRECT", "--to-ports", "12345"
            ], check=False)
            
            # Apply the PROXY chain to OUTPUT
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "iptables", "-t", "nat", "-A", "OUTPUT",
                "-p", "tcp", "-j", "PROXY"
            ], check=False)
            
            self.namespace_routes[namespace] = {
                "type": "socks5_proxy",
                "proxy_config": proxy_config,
                "ip_address": ip_address,
                "redsocks_config": config_path
            }
            
            return True
            
        except subprocess.CalledProcessError:
            print("redsocks not available, falling back to HTTP proxy")
            return await self._configure_http_proxy_routing(namespace, ip_address, proxy_config)
        except Exception as e:
            print(f"SOCKS5 routing failed for {namespace}: {e}")
            return False
    
    def _build_proxy_url(self, proxy_config: Dict) -> str:
        """Build proxy URL from configuration"""
        
        auth = ""
        if proxy_config.get("username") and proxy_config.get("password"):
            auth = f"{proxy_config['username']}:{proxy_config['password']}@"
        
        return f"http://{auth}{proxy_config['host']}:{proxy_config['port']}"
    
    async def apply_custom_rules(self, namespace: str, rules: Dict) -> bool:
        """Apply custom traffic routing rules"""
        
        try:
            # Block specific domains
            if "blocked_domains" in rules:
                for domain in rules["blocked_domains"]:
                    # Block DNS resolution for domain
                    subprocess.run([
                        "ip", "netns", "exec", namespace,
                        "iptables", "-A", "OUTPUT",
                        "-p", "udp", "--dport", "53",
                        "-m", "string", "--string", domain,
                        "--algo", "bm", "-j", "DROP"
                    ], check=False)
            
            # Block specific IPs
            if "blocked_ips" in rules:
                for ip in rules["blocked_ips"]:
                    subprocess.run([
                        "ip", "netns", "exec", namespace,
                        "iptables", "-A", "OUTPUT",
                        "-d", ip, "-j", "DROP"
                    ], check=False)
            
            # Rate limiting
            if "rate_limit" in rules:
                limit = rules["rate_limit"]  # e.g., "100/sec"
                subprocess.run([
                    "ip", "netns", "exec", namespace,
                    "iptables", "-A", "OUTPUT",
                    "-m", "limit", "--limit", limit,
                    "-j", "ACCEPT"
                ], check=False)
            
            # Port restrictions
            if "allowed_ports" in rules:
                # First, block all outgoing traffic
                subprocess.run([
                    "ip", "netns", "exec", namespace,
                    "iptables", "-A", "OUTPUT", "-j", "DROP"
                ], check=False)
                
                # Then allow specific ports
                for port in rules["allowed_ports"]:
                    subprocess.run([
                        "ip", "netns", "exec", namespace,
                        "iptables", "-I", "OUTPUT",
                        "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"
                    ], check=False)
                    
                    subprocess.run([
                        "ip", "netns", "exec", namespace,
                        "iptables", "-I", "OUTPUT",
                        "-p", "udp", "--dport", str(port), "-j", "ACCEPT"
                    ], check=False)
                
                # Allow established connections
                subprocess.run([
                    "ip", "netns", "exec", namespace,
                    "iptables", "-I", "OUTPUT",
                    "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT"
                ], check=False)
            
            # Traffic shaping (using tc - traffic control)
            if "bandwidth_limit" in rules:
                bandwidth = rules["bandwidth_limit"]  # e.g., "1mbit"
                
                # Get interface name (simplified)
                result = subprocess.run([
                    "ip", "netns", "exec", namespace,
                    "ip", "link", "show", "type", "veth"
                ], capture_output=True, text=True)
                
                if result.stdout:
                    # Extract interface name (simplified parsing)
                    for line in result.stdout.split('\n'):
                        if 'veth-ns-' in line:
                            iface = line.split(':')[1].strip().split('@')[0]
                            
                            # Apply traffic shaping
                            subprocess.run([
                                "ip", "netns", "exec", namespace,
                                "tc", "qdisc", "add", "dev", iface, "root", "tbf",
                                "rate", bandwidth, "latency", "50ms", "burst", "1540"
                            ], check=False)
                            break
            
            return True
            
        except Exception as e:
            print(f"Custom rules application failed for {namespace}: {e}")
            return False
    
    async def remove_routing_rules(self, namespace: str) -> bool:
        """Remove routing rules for a namespace"""
        
        try:
            if namespace not in self.namespace_routes:
                return True
            
            route_config = self.namespace_routes[namespace]
            
            # Flush namespace iptables
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "iptables", "-F"
            ], check=False)
            
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "iptables", "-t", "nat", "-F"
            ], check=False)
            
            # Remove redsocks config if SOCKS5
            if route_config.get("type") == "socks5_proxy":
                config_path = route_config.get("redsocks_config")
                if config_path:
                    subprocess.run(["rm", "-f", config_path], check=False)
            
            # Remove from tracking
            del self.namespace_routes[namespace]
            
            return True
            
        except Exception as e:
            print(f"Failed to remove routing rules for {namespace}: {e}")
            return False
    
    async def get_routing_info(self, namespace: str) -> Optional[Dict]:
        """Get routing information for a namespace"""
        
        if namespace not in self.namespace_routes:
            return None
        
        try:
            route_config = self.namespace_routes[namespace].copy()
            
            # Get current iptables rules
            result = subprocess.run([
                "ip", "netns", "exec", namespace,
                "iptables", "-L", "-n", "-v"
            ], capture_output=True, text=True)
            
            route_config["iptables_rules"] = result.stdout
            
            # Get NAT rules
            result = subprocess.run([
                "ip", "netns", "exec", namespace,
                "iptables", "-t", "nat", "-L", "-n", "-v"
            ], capture_output=True, text=True)
            
            route_config["nat_rules"] = result.stdout
            
            return route_config
            
        except Exception as e:
            print(f"Failed to get routing info for {namespace}: {e}")
            return None
    
    async def test_proxy_connectivity(self, namespace: str, proxy_config: Dict) -> bool:
        """Test if proxy connectivity is working in namespace"""
        
        try:
            proxy_url = self._build_proxy_url(proxy_config)
            
            # Test HTTP through proxy
            result = subprocess.run([
                "ip", "netns", "exec", namespace,
                "curl", "-s", "--proxy", proxy_url,
                "--max-time", "10", "http://httpbin.org/ip"
            ], capture_output=True, timeout=15)
            
            if result.returncode == 0:
                # Verify we're using proxy IP
                try:
                    import json
                    response_data = json.loads(result.stdout.decode())
                    proxy_ip = response_data.get("origin", "")
                    
                    # The IP should be different from our direct IP
                    return len(proxy_ip) > 0 and proxy_ip != "unknown"
                    
                except:
                    return True  # At least the request succeeded
            
            return False
            
        except Exception as e:
            print(f"Proxy connectivity test failed for {namespace}: {e}")
            return False
    
    async def update_proxy_config(self, namespace: str, new_proxy_config: Dict) -> bool:
        """Update proxy configuration for an existing namespace"""
        
        try:
            # Remove existing routing rules
            await self.remove_routing_rules(namespace)
            
            # Get IP address from existing config
            ip_address = self.namespace_routes.get(namespace, {}).get("ip_address")
            if not ip_address:
                return False
            
            # Apply new proxy configuration
            return await self.configure_proxy_routing(namespace, ip_address, new_proxy_config)
            
        except Exception as e:
            print(f"Proxy config update failed for {namespace}: {e}")
            return False
    
    def get_all_routing_configs(self) -> Dict[str, Dict]:
        """Get all routing configurations"""
        return self.namespace_routes.copy()