import asyncio
import json
import os
import random
import subprocess
from typing import Dict, List, Optional
import docker
import docker.errors

class RedroidManager:
    """Manages Redroid Android containers"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.redroid_images = {
            "11": "redroid/redroid:11.0.0-latest",
            "12": "redroid/redroid:12.0.0-latest", 
            "13": "redroid/redroid:13.0.0-latest",
            "14": "redroid/redroid:14.0.0-latest"
        }
        self.port_pool = {
            "vnc": set(range(5900, 6000)),
            "adb": set(range(5555, 5655))
        }
        self.used_ports = {
            "vnc": set(),
            "adb": set()
        }
    
    async def initialize(self):
        """Initialize Redroid manager"""
        await self._pull_redroid_images()
        await self._setup_port_pools()
    
    async def _pull_redroid_images(self):
        """Pull latest Redroid images"""
        
        print("Pulling Redroid images...")
        
        for version, image in self.redroid_images.items():
            try:
                print(f"Pulling {image}...")
                self.docker_client.images.pull(image)
                print(f"✓ {image} pulled successfully")
            except Exception as e:
                print(f"✗ Failed to pull {image}: {e}")
        
        print("Redroid image pull complete")
    
    async def _setup_port_pools(self):
        """Setup available port pools"""
        
        # Get currently used ports from existing containers
        try:
            containers = self.docker_client.containers.list(all=True)
            
            for container in containers:
                if container.name.startswith("android-"):
                    # Check port bindings
                    for port_binding in container.attrs.get("NetworkSettings", {}).get("Ports", {}):
                        if port_binding:
                            for binding in container.attrs["NetworkSettings"]["Ports"].get(port_binding, []):
                                if binding:
                                    host_port = int(binding["HostPort"])
                                    
                                    if 5900 <= host_port < 6000:  # VNC ports
                                        self.used_ports["vnc"].add(host_port)
                                    elif 5555 <= host_port < 5655:  # ADB ports
                                        self.used_ports["adb"].add(host_port)
                                        
        except Exception as e:
            print(f"Port pool setup error: {e}")
    
    def _allocate_port(self, port_type: str) -> int:
        """Allocate an available port"""
        
        available_ports = self.port_pool[port_type] - self.used_ports[port_type]
        
        if not available_ports:
            raise Exception(f"No available {port_type} ports")
        
        port = random.choice(list(available_ports))
        self.used_ports[port_type].add(port)
        
        return port
    
    def _release_port(self, port: int, port_type: str):
        """Release a port back to the pool"""
        self.used_ports[port_type].discard(port)
    
    async def create_container(self, container_name: str, android_version: str,
                             device_identity: Dict, cpu_limit: float = 2.0,
                             memory_limit: str = "4G", storage_size: str = "8G",
                             network_config: Optional[Dict] = None) -> Dict:
        """Create a new Redroid container"""
        
        try:
            # Get Redroid image
            if android_version not in self.redroid_images:
                raise ValueError(f"Unsupported Android version: {android_version}")
            
            image = self.redroid_images[android_version]
            
            # Allocate ports
            vnc_port = self._allocate_port("vnc")
            adb_port = self._allocate_port("adb")
            
            # Build system properties from device identity
            sys_props = self._build_system_properties(device_identity)
            
            # Container environment variables
            environment = {
                "REDROID_WIDTH": "1080",
                "REDROID_HEIGHT": "1920", 
                "REDROID_DPI": "320",
                "REDROID_FPS": "30",
                "REDROID_GPU_MODE": "guest",
                
                # System properties
                **{f"ro.{key}": value for key, value in sys_props.items()},
                
                # Device identity
                "ANDROID_ID": device_identity.get("android_id", ""),
                "IMEI": device_identity.get("imei", ""),
                "SERIAL_NUMBER": device_identity.get("serial_number", ""),
            }
            
            # Port bindings
            ports = {
                '5555/tcp': adb_port,  # ADB
                '5900/tcp': vnc_port,  # VNC
            }
            
            # Volume mounts for persistence
            volumes = {
                f"/data/android-instances/{container_name}": {
                    "bind": "/data",
                    "mode": "rw"
                }
            }
            
            # Create data directory
            os.makedirs(f"/data/android-instances/{container_name}", exist_ok=True)
            
            # Container configuration
            container_config = {
                "image": image,
                "name": container_name,
                "environment": environment,
                "ports": ports,
                "volumes": volumes,
                "privileged": True,  # Required for Android containers
                "devices": ["/dev/kvm", "/dev/dri"],  # Hardware acceleration
                "cap_add": ["SYS_ADMIN", "NET_ADMIN"],
                "security_opt": ["seccomp:unconfined"],
                "mem_limit": memory_limit,
                "cpu_quota": int(cpu_limit * 100000),
                "cpu_period": 100000,
                "detach": True,
                "remove": False,
                "restart_policy": {"Name": "unless-stopped"}
            }
            
            # Network configuration
            if network_config:
                container_config["network_mode"] = "none"  # We'll configure networking manually
            
            # Create container
            container = self.docker_client.containers.create(**container_config)
            
            # Configure network namespace if needed
            if network_config:
                await self._configure_container_network(container.id, network_config)
            
            return {
                "container_id": container.id,
                "container_name": container_name,
                "vnc_port": vnc_port,
                "adb_port": adb_port,
                "android_version": android_version,
                "image": image
            }
            
        except Exception as e:
            # Cleanup on failure
            self._release_port(vnc_port, "vnc")
            self._release_port(adb_port, "adb")
            raise Exception(f"Container creation failed: {str(e)}")
    
    def _build_system_properties(self, device_identity: Dict) -> Dict[str, str]:
        """Build system properties from device identity"""
        
        device_profile = device_identity.get("device_profile", {})
        system_properties = device_identity.get("system_properties", {})
        
        # Core system properties
        props = {
            "build.fingerprint": device_identity.get("build_fingerprint", ""),
            "product.manufacturer": device_profile.get("manufacturer", "Google"),
            "product.model": device_profile.get("model", "Pixel 7"),
            "product.brand": device_profile.get("manufacturer", "Google").lower(),
            "product.device": device_profile.get("model", "Pixel 7").lower().replace(" ", "_"),
            "build.version.release": device_profile.get("android_version", "13"),
            "build.version.sdk": str(device_profile.get("api_level", 33)),
            "serialno": device_identity.get("serial_number", ""),
            
            # Hardware properties
            "hardware": device_profile.get("hardware", "slider"),
            "board.platform": device_profile.get("platform", "gs201"),
            
            # Security properties (important for integrity checks)
            "secure": "1",
            "debuggable": "0",
            "build.type": "user",
            "build.tags": "release-keys",
            "boot.veritymode": "enforcing",
            "boot.flash.locked": "1",
            "boot.verifiedbootstate": "green",
            "oem_unlock_supported": "0",
        }
        
        # Merge with custom system properties
        props.update(system_properties)
        
        return props
    
    async def _configure_container_network(self, container_id: str, network_config: Dict):
        """Configure container networking"""
        
        try:
            namespace = network_config.get("network_namespace")
            if namespace:
                # Move container to network namespace
                subprocess.run([
                    "docker", "exec", container_id,
                    "ip", "link", "set", "dev", "eth0", "netns", namespace
                ], check=True)
                
        except Exception as e:
            print(f"Network configuration failed for {container_id}: {e}")
    
    async def start_container(self, container_id: str) -> bool:
        """Start a Redroid container"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.start()
            
            # Wait for Android to boot
            await self._wait_for_android_boot(container_id)
            
            return True
            
        except Exception as e:
            print(f"Failed to start container {container_id}: {e}")
            return False
    
    async def _wait_for_android_boot(self, container_id: str, timeout: int = 120):
        """Wait for Android system to complete booting"""
        
        print(f"Waiting for Android boot in {container_id}...")
        
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                # Check if Android is fully booted
                result = subprocess.run([
                    "docker", "exec", container_id,
                    "getprop", "sys.boot_completed"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout.strip() == "1":
                    print(f"Android boot completed in {container_id}")
                    return True
                    
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass
            
            await asyncio.sleep(5)
        
        raise Exception(f"Android boot timeout in {container_id}")
    
    async def stop_container(self, container_id: str) -> bool:
        """Stop a container"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop(timeout=30)
            return True
            
        except Exception as e:
            print(f"Failed to stop container {container_id}: {e}")
            return False
    
    async def remove_container(self, container_id: str) -> bool:
        """Remove a container and cleanup resources"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Get port information before removal
            port_bindings = container.attrs.get("HostConfig", {}).get("PortBindings", {})
            
            # Stop and remove container
            container.stop(timeout=10)
            container.remove(force=True)
            
            # Release ports
            for port_mapping, bindings in port_bindings.items():
                if bindings:
                    for binding in bindings:
                        host_port = int(binding["HostPort"])
                        
                        if 5900 <= host_port < 6000:
                            self._release_port(host_port, "vnc")
                        elif 5555 <= host_port < 5655:
                            self._release_port(host_port, "adb")
            
            # Cleanup data directory
            data_dir = f"/data/android-instances/{container.name}"
            subprocess.run(["rm", "-rf", data_dir], check=False)
            
            return True
            
        except Exception as e:
            print(f"Failed to remove container {container_id}: {e}")
            return False
    
    async def get_container_info(self, container_id: str) -> Optional[Dict]:
        """Get detailed container information"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Get port mappings
            port_bindings = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            
            vnc_port = None
            adb_port = None
            
            for port, bindings in port_bindings.items():
                if bindings:
                    host_port = int(bindings[0]["HostPort"])
                    
                    if "5900" in port:
                        vnc_port = host_port
                    elif "5555" in port:
                        adb_port = host_port
            
            return {
                "container_id": container.id,
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs["Created"],
                "started_at": container.attrs["State"].get("StartedAt"),
                "vnc_port": vnc_port,
                "adb_port": adb_port,
                "cpu_usage": await self._get_cpu_usage(container_id),
                "memory_usage": await self._get_memory_usage(container_id)
            }
            
        except Exception as e:
            print(f"Failed to get container info for {container_id}: {e}")
            return None
    
    async def _get_cpu_usage(self, container_id: str) -> float:
        """Get container CPU usage percentage"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            cpu_stats = stats["cpu_stats"]
            precpu_stats = stats["precpu_stats"]
            
            cpu_usage = cpu_stats["cpu_usage"]["total_usage"]
            precpu_usage = precpu_stats["cpu_usage"]["total_usage"]
            
            system_cpu_usage = cpu_stats["system_cpu_usage"]
            presystem_cpu_usage = precpu_stats["system_cpu_usage"]
            
            num_cpus = len(cpu_stats["cpu_usage"]["percpu_usage"])
            
            cpu_delta = cpu_usage - precpu_usage
            system_delta = system_cpu_usage - presystem_cpu_usage
            
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
                return round(cpu_percent, 2)
            
        except:
            pass
        
        return 0.0
    
    async def _get_memory_usage(self, container_id: str) -> Dict[str, int]:
        """Get container memory usage"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            memory_stats = stats["memory_stats"]
            
            return {
                "usage": memory_stats.get("usage", 0),
                "limit": memory_stats.get("limit", 0),
                "percentage": round((memory_stats.get("usage", 0) / memory_stats.get("limit", 1)) * 100, 2)
            }
            
        except:
            pass
        
        return {"usage": 0, "limit": 0, "percentage": 0}
    
    async def list_containers(self, all_containers: bool = False) -> List[Dict]:
        """List Redroid containers"""
        
        try:
            containers = self.docker_client.containers.list(all=all_containers)
            
            redroid_containers = []
            
            for container in containers:
                if container.name.startswith("android-"):
                    info = await self.get_container_info(container.id)
                    if info:
                        redroid_containers.append(info)
            
            return redroid_containers
            
        except Exception as e:
            print(f"Failed to list containers: {e}")
            return []
    
    async def execute_adb_command(self, container_id: str, command: str) -> str:
        """Execute ADB command in container"""
        
        try:
            result = subprocess.run([
                "docker", "exec", container_id,
                "adb", "shell", command
            ], capture_output=True, text=True, timeout=30)
            
            return result.stdout
            
        except Exception as e:
            return f"ADB command failed: {str(e)}"
    
    async def install_apk(self, container_id: str, apk_path: str) -> bool:
        """Install APK in container"""
        
        try:
            # Copy APK to container
            subprocess.run([
                "docker", "cp", apk_path, f"{container_id}:/tmp/app.apk"
            ], check=True)
            
            # Install APK
            result = subprocess.run([
                "docker", "exec", container_id,
                "adb", "install", "/tmp/app.apk"
            ], capture_output=True, text=True)
            
            return "Success" in result.stdout
            
        except Exception as e:
            print(f"APK installation failed: {e}")
            return False
    
    async def get_installed_packages(self, container_id: str) -> List[str]:
        """Get list of installed packages"""
        
        try:
            result = subprocess.run([
                "docker", "exec", container_id,
                "adb", "shell", "pm", "list", "packages"
            ], capture_output=True, text=True)
            
            packages = []
            for line in result.stdout.split('\n'):
                if line.startswith('package:'):
                    packages.append(line.replace('package:', '').strip())
            
            return packages
            
        except Exception as e:
            print(f"Failed to get installed packages: {e}")
            return []