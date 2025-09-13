import asyncio
import json
import time
from typing import Dict, List, Optional
import docker
import psutil

class ContainerOrchestrator:
    """Orchestrates container lifecycle and resource management"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.start_time = time.time()
        self.container_stats_cache = {}
    
    async def initialize(self):
        """Initialize the orchestrator"""
        print("Container Orchestrator initialized")
    
    async def start_container(self, container_id: str) -> bool:
        """Start a container with health monitoring"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            if container.status == "running":
                return True
            
            container.start()
            
            # Wait for container to be ready
            await self._wait_for_container_ready(container_id)
            
            return True
            
        except Exception as e:
            print(f"Failed to start container {container_id}: {e}")
            return False
    
    async def _wait_for_container_ready(self, container_id: str, timeout: int = 60):
        """Wait for container to be ready"""
        
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                container = self.docker_client.containers.get(container_id)
                
                if container.status == "running":
                    # Additional check - ensure container is responding
                    health_check = await self.check_container_health(container_id)
                    if health_check:
                        return True
                
            except Exception:
                pass
            
            await asyncio.sleep(2)
        
        raise Exception(f"Container {container_id} failed to become ready")
    
    async def stop_container(self, container_id: str) -> bool:
        """Stop a container gracefully"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            if container.status != "running":
                return True
            
            # Graceful stop with timeout
            container.stop(timeout=30)
            
            return True
            
        except Exception as e:
            print(f"Failed to stop container {container_id}: {e}")
            return False
    
    async def restart_container(self, container_id: str) -> bool:
        """Restart a container"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.restart(timeout=30)
            
            # Wait for restart to complete
            await self._wait_for_container_ready(container_id)
            
            return True
            
        except Exception as e:
            print(f"Failed to restart container {container_id}: {e}")
            return False
    
    async def remove_container(self, container_id: str, force: bool = False) -> bool:
        """Remove a container"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Stop first if running
            if container.status == "running":
                container.stop(timeout=10)
            
            # Remove container
            container.remove(force=force)
            
            # Clear from stats cache
            self.container_stats_cache.pop(container_id, None)
            
            return True
            
        except Exception as e:
            print(f"Failed to remove container {container_id}: {e}")
            return False
    
    async def check_container_health(self, container_id: str) -> bool:
        """Check if container is healthy"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Basic health checks
            if container.status != "running":
                return False
            
            # Check if container is responsive
            try:
                # Simple exec test
                result = container.exec_run("echo 'health_check'", timeout=5)
                return result.exit_code == 0
            except:
                return False
                
        except Exception:
            return False
    
    async def get_container_logs(self, container_id: str, lines: int = 100) -> str:
        """Get container logs"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            logs = container.logs(tail=lines, timestamps=True)
            return logs.decode('utf-8', errors='ignore')
            
        except Exception as e:
            return f"Failed to get logs: {str(e)}"
    
    async def get_container_stats(self, container_id: str) -> Dict:
        """Get detailed container statistics"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            if container.status != "running":
                return {"status": "not_running"}
            
            # Get stats (non-streaming)
            stats = container.stats(stream=False)
            
            # Parse CPU stats
            cpu_stats = self._parse_cpu_stats(stats)
            
            # Parse memory stats  
            memory_stats = self._parse_memory_stats(stats)
            
            # Parse network stats
            network_stats = self._parse_network_stats(stats)
            
            # Parse block I/O stats
            io_stats = self._parse_io_stats(stats)
            
            result = {
                "container_id": container_id,
                "name": container.name,
                "status": container.status,
                "cpu": cpu_stats,
                "memory": memory_stats,
                "network": network_stats,
                "io": io_stats,
                "timestamp": time.time()
            }
            
            # Cache stats
            self.container_stats_cache[container_id] = result
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_cpu_stats(self, stats: Dict) -> Dict:
        """Parse CPU statistics"""
        
        try:
            cpu_stats = stats["cpu_stats"]
            precpu_stats = stats["precpu_stats"]
            
            cpu_usage = cpu_stats["cpu_usage"]["total_usage"]
            precpu_usage = precpu_stats["cpu_usage"]["total_usage"]
            
            system_cpu_usage = cpu_stats["system_cpu_usage"]
            presystem_cpu_usage = precpu_stats["system_cpu_usage"]
            
            num_cpus = len(cpu_stats["cpu_usage"]["percpu_usage"])
            
            cpu_delta = cpu_usage - precpu_usage
            system_delta = system_cpu_usage - presystem_cpu_usage
            
            cpu_percent = 0.0
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
            
            return {
                "usage_percent": round(cpu_percent, 2),
                "system_cpu_usage": system_cpu_usage,
                "online_cpus": num_cpus,
                "throttled_periods": cpu_stats.get("throttling_data", {}).get("throttled_periods", 0),
                "throttled_time": cpu_stats.get("throttling_data", {}).get("throttled_time", 0)
            }
            
        except Exception:
            return {"error": "Failed to parse CPU stats"}
    
    def _parse_memory_stats(self, stats: Dict) -> Dict:
        """Parse memory statistics"""
        
        try:
            memory_stats = stats["memory_stats"]
            
            usage = memory_stats.get("usage", 0)
            limit = memory_stats.get("limit", 0)
            
            # Calculate cache if available
            cache = memory_stats.get("stats", {}).get("cache", 0)
            
            # Memory usage percentage
            usage_percent = 0.0
            if limit > 0:
                usage_percent = (usage / limit) * 100.0
            
            return {
                "usage_bytes": usage,
                "limit_bytes": limit,
                "usage_percent": round(usage_percent, 2),
                "cache_bytes": cache,
                "usage_mb": round(usage / (1024 * 1024), 2),
                "limit_mb": round(limit / (1024 * 1024), 2)
            }
            
        except Exception:
            return {"error": "Failed to parse memory stats"}
    
    def _parse_network_stats(self, stats: Dict) -> Dict:
        """Parse network statistics"""
        
        try:
            networks = stats["networks"]
            
            total_rx_bytes = 0
            total_tx_bytes = 0
            total_rx_packets = 0
            total_tx_packets = 0
            
            for interface, net_stats in networks.items():
                total_rx_bytes += net_stats.get("rx_bytes", 0)
                total_tx_bytes += net_stats.get("tx_bytes", 0)
                total_rx_packets += net_stats.get("rx_packets", 0)
                total_tx_packets += net_stats.get("tx_packets", 0)
            
            return {
                "rx_bytes": total_rx_bytes,
                "tx_bytes": total_tx_bytes,
                "rx_packets": total_rx_packets,
                "tx_packets": total_tx_packets,
                "rx_mb": round(total_rx_bytes / (1024 * 1024), 2),
                "tx_mb": round(total_tx_bytes / (1024 * 1024), 2)
            }
            
        except Exception:
            return {"error": "Failed to parse network stats"}
    
    def _parse_io_stats(self, stats: Dict) -> Dict:
        """Parse block I/O statistics"""
        
        try:
            blkio_stats = stats["blkio_stats"]
            
            read_bytes = 0
            write_bytes = 0
            
            # Parse I/O service bytes
            for stat in blkio_stats.get("io_service_bytes_recursive", []):
                if stat["op"] == "Read":
                    read_bytes += stat["value"]
                elif stat["op"] == "Write":
                    write_bytes += stat["value"]
            
            return {
                "read_bytes": read_bytes,
                "write_bytes": write_bytes,
                "read_mb": round(read_bytes / (1024 * 1024), 2),
                "write_mb": round(write_bytes / (1024 * 1024), 2)
            }
            
        except Exception:
            return {"error": "Failed to parse I/O stats"}
    
    async def execute_command(self, container_id: str, command: str) -> Dict:
        """Execute command in container"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            if container.status != "running":
                return {"error": "Container is not running"}
            
            # Execute command
            result = container.exec_run(command, timeout=30)
            
            return {
                "exit_code": result.exit_code,
                "output": result.output.decode('utf-8', errors='ignore'),
                "command": command
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_total_resource_usage(self) -> Dict:
        """Get total resource usage across all containers"""
        
        try:
            containers = self.docker_client.containers.list()
            android_containers = [c for c in containers if c.name.startswith("android-")]
            
            total_cpu = 0.0
            total_memory_usage = 0
            total_memory_limit = 0
            
            for container in android_containers:
                try:
                    stats = await self.get_container_stats(container.id)
                    
                    if "cpu" in stats and "usage_percent" in stats["cpu"]:
                        total_cpu += stats["cpu"]["usage_percent"]
                    
                    if "memory" in stats:
                        total_memory_usage += stats["memory"].get("usage_bytes", 0)
                        total_memory_limit += stats["memory"].get("limit_bytes", 0)
                        
                except Exception:
                    continue
            
            # Host system stats
            host_cpu_percent = psutil.cpu_percent()
            host_memory = psutil.virtual_memory()
            host_disk = psutil.disk_usage('/')
            
            return {
                "containers": {
                    "total_count": len(android_containers),
                    "total_cpu_percent": round(total_cpu, 2),
                    "total_memory_usage_mb": round(total_memory_usage / (1024 * 1024), 2),
                    "total_memory_limit_mb": round(total_memory_limit / (1024 * 1024), 2)
                },
                "host": {
                    "cpu_percent": host_cpu_percent,
                    "memory_total_gb": round(host_memory.total / (1024 * 1024 * 1024), 2),
                    "memory_used_gb": round(host_memory.used / (1024 * 1024 * 1024), 2),
                    "memory_percent": host_memory.percent,
                    "disk_total_gb": round(host_disk.total / (1024 * 1024 * 1024), 2),
                    "disk_used_gb": round(host_disk.used / (1024 * 1024 * 1024), 2),
                    "disk_percent": round((host_disk.used / host_disk.total) * 100, 2)
                }
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def cleanup_stopped_containers(self):
        """Cleanup stopped Android containers"""
        
        try:
            containers = self.docker_client.containers.list(all=True)
            
            cleaned_count = 0
            
            for container in containers:
                if (container.name.startswith("android-") and 
                    container.status in ["exited", "dead"]):
                    
                    try:
                        container.remove()
                        cleaned_count += 1
                        print(f"Cleaned up stopped container: {container.name}")
                    except Exception as e:
                        print(f"Failed to cleanup {container.name}: {e}")
            
            return cleaned_count
            
        except Exception as e:
            print(f"Container cleanup error: {e}")
            return 0
    
    async def scale_resources(self, container_id: str, cpu_limit: Optional[float] = None,
                            memory_limit: Optional[str] = None) -> bool:
        """Scale container resources dynamically"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Docker doesn't support runtime resource updates for running containers
            # This would require container restart
            
            update_config = {}
            
            if cpu_limit is not None:
                update_config["cpu_quota"] = int(cpu_limit * 100000)
                update_config["cpu_period"] = 100000
            
            if memory_limit is not None:
                # Parse memory limit (e.g., "4G" -> bytes)
                memory_bytes = self._parse_memory_limit(memory_limit)
                update_config["mem_limit"] = memory_bytes
            
            if update_config:
                container.update(**update_config)
                return True
            
            return False
            
        except Exception as e:
            print(f"Resource scaling failed for {container_id}: {e}")
            return False
    
    def _parse_memory_limit(self, limit_str: str) -> int:
        """Parse memory limit string to bytes"""
        
        limit_str = limit_str.upper()
        
        if limit_str.endswith('K'):
            return int(limit_str[:-1]) * 1024
        elif limit_str.endswith('M'):
            return int(limit_str[:-1]) * 1024 * 1024
        elif limit_str.endswith('G'):
            return int(limit_str[:-1]) * 1024 * 1024 * 1024
        else:
            return int(limit_str)
    
    async def get_container_events(self, container_id: str) -> List[Dict]:
        """Get container events"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Get events from Docker daemon
            events = self.docker_client.events(
                since=int(time.time()) - 3600,  # Last hour
                until=int(time.time()),
                filters={"container": container_id},
                decode=True
            )
            
            event_list = []
            for event in events:
                event_list.append({
                    "time": event.get("time"),
                    "action": event.get("Action"),
                    "status": event.get("status"),
                    "id": event.get("id", "")[:12]
                })
            
            return event_list
            
        except Exception as e:
            return [{"error": str(e)}]