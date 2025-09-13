import asyncio
import subprocess
import ipaddress
from typing import Dict, List, Optional

class NetworkIsolator:
    """Handles network namespace creation and isolation"""
    
    def __init__(self):
        self.active_namespaces = set()
    
    async def initialize(self):
        """Initialize network isolation system"""
        # Ensure required kernel modules are loaded
        await self._load_kernel_modules()
        
        # Setup base networking
        await self._setup_base_networking()
    
    async def _load_kernel_modules(self):
        """Load required kernel modules"""
        modules = ["ip_tables", "iptable_nat", "ip_conntrack", "veth"]
        
        for module in modules:
            try:
                subprocess.run(["modprobe", module], check=False)
            except:
                pass  # Module might already be loaded
    
    async def _setup_base_networking(self):
        """Setup base networking configuration"""
        try:
            # Enable IP forwarding
            subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], check=False)
            subprocess.run(["sysctl", "-w", "net.ipv6.conf.all.forwarding=1"], check=False)
            
            # Setup default iptables rules
            await self._setup_default_iptables()
            
        except Exception as e:
            print(f"Base networking setup error: {e}")
    
    async def _setup_default_iptables(self):
        """Setup default iptables rules for NAT and forwarding"""
        
        commands = [
            # NAT table rules
            ["iptables", "-t", "nat", "-F"],  # Flush existing rules
            ["iptables", "-t", "nat", "-A", "POSTROUTING", "-s", "172.20.0.0/16", "-j", "MASQUERADE"],
            
            # Filter table rules
            ["iptables", "-A", "FORWARD", "-i", "docker0", "-o", "docker0", "-j", "ACCEPT"],
            ["iptables", "-A", "FORWARD", "-s", "172.20.0.0/16", "-j", "ACCEPT"],
            ["iptables", "-A", "FORWARD", "-d", "172.20.0.0/16", "-j", "ACCEPT"],
        ]
        
        for cmd in commands:
            try:
                subprocess.run(cmd, check=False, capture_output=True)
            except:
                pass  # Some rules might fail if they already exist
    
    async def create_namespace(self, namespace: str, ip_address: str) -> bool:
        """Create an isolated network namespace"""
        
        try:
            # Create network namespace
            subprocess.run(["ip", "netns", "add", namespace], check=True)
            
            # Create veth pair
            veth_host = f"veth-{namespace[:8]}"
            veth_ns = f"veth-ns-{namespace[:8]}"
            
            subprocess.run([
                "ip", "link", "add", veth_host, 
                "type", "veth", "peer", "name", veth_ns
            ], check=True)
            
            # Move one end to namespace
            subprocess.run([
                "ip", "link", "set", veth_ns, "netns", namespace
            ], check=True)
            
            # Configure host side
            subprocess.run(["ip", "link", "set", veth_host, "up"], check=True)
            subprocess.run([
                "ip", "addr", "add", "172.20.1.1/24", "dev", veth_host
            ], check=False)  # May already exist
            
            # Configure namespace side
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "ip", "link", "set", "lo", "up"
            ], check=True)
            
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "ip", "link", "set", veth_ns, "up"
            ], check=True)
            
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "ip", "addr", "add", f"{ip_address}/24", "dev", veth_ns
            ], check=True)
            
            # Add default route
            subprocess.run([
                "ip", "netns", "exec", namespace,
                "ip", "route", "add", "default", "via", "172.20.1.1"
            ], check=True)
            
            # Setup iptables rules for this namespace
            await self._setup_namespace_iptables(namespace, ip_address)
            
            self.active_namespaces.add(namespace)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to create namespace {namespace}: {e}")
            # Cleanup on failure
            await self.destroy_namespace(namespace)
            return False
    
    async def _setup_namespace_iptables(self, namespace: str, ip_address: str):
        """Setup iptables rules for namespace isolation"""
        
        # Allow traffic from this specific IP
        subprocess.run([
            "iptables", "-A", "FORWARD", 
            "-s", ip_address, "-j", "ACCEPT"
        ], check=False)
        
        subprocess.run([
            "iptables", "-A", "FORWARD",
            "-d", ip_address, "-j", "ACCEPT"
        ], check=False)
        
        # NAT rule for outgoing traffic
        subprocess.run([
            "iptables", "-t", "nat", "-A", "POSTROUTING",
            "-s", ip_address, "-j", "MASQUERADE"
        ], check=False)
    
    async def destroy_namespace(self, namespace: str) -> bool:
        """Destroy a network namespace and cleanup"""
        
        try:
            # Remove iptables rules
            await self._cleanup_namespace_iptables(namespace)
            
            # Get veth interface name
            veth_host = f"veth-{namespace[:8]}"
            
            # Delete veth pair (this also removes the namespace side)
            subprocess.run([
                "ip", "link", "delete", veth_host
            ], check=False)
            
            # Delete namespace
            subprocess.run([
                "ip", "netns", "delete", namespace
            ], check=False)
            
            self.active_namespaces.discard(namespace)
            return True
            
        except Exception as e:
            print(f"Failed to destroy namespace {namespace}: {e}")
            return False
    
    async def _cleanup_namespace_iptables(self, namespace: str):
        """Remove iptables rules for a namespace"""
        
        # This is simplified - in production you'd want to track
        # specific rules per namespace for precise cleanup
        try:
            subprocess.run(["iptables", "-F", "FORWARD"], check=False)
            subprocess.run(["iptables", "-t", "nat", "-F", "POSTROUTING"], check=False)
            
            # Re-setup default rules
            await self._setup_default_iptables()
            
        except:
            pass
    
    async def configure_dns(self, namespace: str, dns_servers: List[str]) -> bool:
        """Configure DNS for a namespace"""
        
        try:
            # Create resolv.conf content
            resolv_content = "\n".join([f"nameserver {dns}" for dns in dns_servers])
            resolv_content += "\noptions ndots:0\n"
            
            # Write to namespace resolv.conf
            proc = subprocess.Popen([
                "ip", "netns", "exec", namespace,
                "sh", "-c", f"echo '{resolv_content}' > /etc/resolv.conf"
            ])
            proc.wait()
            
            return proc.returncode == 0
            
        except Exception as e:
            print(f"DNS configuration failed for {namespace}: {e}")
            return False
    
    async def test_connectivity(self, namespace: str) -> Dict[str, bool]:
        """Test various connectivity aspects of a namespace"""
        
        results = {
            "namespace_exists": False,
            "interface_up": False,
            "ip_assigned": False,
            "default_route": False,
            "dns": False,
            "internet": False,
            "proxy": False
        }
        
        try:
            # Check if namespace exists
            result = subprocess.run([
                "ip", "netns", "list"
            ], capture_output=True, text=True)
            
            if namespace in result.stdout:
                results["namespace_exists"] = True
            else:
                return results
            
            # Check interface status
            result = subprocess.run([
                "ip", "netns", "exec", namespace,
                "ip", "link", "show"
            ], capture_output=True, text=True)
            
            if "state UP" in result.stdout:
                results["interface_up"] = True
            
            # Check IP assignment
            result = subprocess.run([
                "ip", "netns", "exec", namespace,
                "ip", "addr", "show"
            ], capture_output=True, text=True)
            
            if "172.20." in result.stdout:
                results["ip_assigned"] = True
            
            # Check default route
            result = subprocess.run([
                "ip", "netns", "exec", namespace,
                "ip", "route", "show", "default"
            ], capture_output=True, text=True)
            
            if "default" in result.stdout:
                results["default_route"] = True
            
            # Test DNS resolution
            result = subprocess.run([
                "ip", "netns", "exec", namespace,
                "nslookup", "google.com"
            ], capture_output=True, timeout=10)
            
            results["dns"] = result.returncode == 0
            
            # Test internet connectivity
            result = subprocess.run([
                "ip", "netns", "exec", namespace,
                "curl", "-s", "--max-time", "10", "http://httpbin.org/ip"
            ], capture_output=True, timeout=15)
            
            results["internet"] = result.returncode == 0
            
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            print(f"Connectivity test error for {namespace}: {e}")
        
        return results
    
    async def get_namespace_info(self, namespace: str) -> Optional[Dict]:
        """Get detailed information about a namespace"""
        
        if namespace not in self.active_namespaces:
            return None
        
        try:
            info = {
                "namespace": namespace,
                "interfaces": [],
                "routes": [],
                "dns_servers": []
            }
            
            # Get interfaces
            result = subprocess.run([
                "ip", "netns", "exec", namespace,
                "ip", "addr", "show"
            ], capture_output=True, text=True)
            
            # Parse interface information (simplified)
            for line in result.stdout.split('\n'):
                if 'inet ' in line:
                    parts = line.strip().split()
                    ip = parts[1] if len(parts) > 1 else ""
                    info["interfaces"].append(ip)
            
            # Get routes
            result = subprocess.run([
                "ip", "netns", "exec", namespace,
                "ip", "route", "show"
            ], capture_output=True, text=True)
            
            info["routes"] = result.stdout.strip().split('\n')
            
            # Get DNS servers
            try:
                result = subprocess.run([
                    "ip", "netns", "exec", namespace,
                    "cat", "/etc/resolv.conf"
                ], capture_output=True, text=True)
                
                for line in result.stdout.split('\n'):
                    if line.startswith('nameserver'):
                        dns = line.split()[1] if len(line.split()) > 1 else ""
                        if dns:
                            info["dns_servers"].append(dns)
            except:
                pass
            
            return info
            
        except Exception as e:
            print(f"Failed to get namespace info for {namespace}: {e}")
            return None
    
    async def execute_in_namespace(self, namespace: str, command: List[str]) -> subprocess.CompletedProcess:
        """Execute a command in a specific namespace"""
        
        if namespace not in self.active_namespaces:
            raise ValueError(f"Namespace {namespace} does not exist")
        
        full_command = ["ip", "netns", "exec", namespace] + command
        
        return subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=30
        )
    
    async def list_namespaces(self) -> List[str]:
        """List all active namespaces"""
        return list(self.active_namespaces)
    
    async def cleanup_all_namespaces(self):
        """Cleanup all namespaces (for shutdown)"""
        
        namespaces_to_cleanup = list(self.active_namespaces)
        
        for namespace in namespaces_to_cleanup:
            await self.destroy_namespace(namespace)
        
        print(f"Cleaned up {len(namespaces_to_cleanup)} namespaces")