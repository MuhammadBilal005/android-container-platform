#!/usr/bin/env python3
"""
Load Testing Suite for Android Container Platform
Tests system performance under various load conditions
"""

import asyncio
import json
import logging
import time
import psutil
import docker
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import subprocess
import threading
from dataclasses import dataclass, asdict
import concurrent.futures
import statistics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    load_average_1min: float
    active_containers: int

@dataclass
class ContainerMetrics:
    container_id: str
    container_name: str
    cpu_percent: float
    memory_usage_mb: float
    memory_limit_mb: float
    network_rx_bytes: int
    network_tx_bytes: int
    block_read_bytes: int
    block_write_bytes: int
    pids: int
    status: str
    uptime_seconds: float

@dataclass
class LoadTestResult:
    test_name: str
    test_type: str
    duration_seconds: int
    container_count: int
    success_rate: float
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    system_metrics: List[SystemMetrics]
    container_metrics: List[ContainerMetrics]
    errors: List[str]
    start_time: datetime
    end_time: datetime

class LoadTester:
    """Comprehensive load testing framework for Android containers"""
    
    def __init__(self, docker_client=None):
        self.docker_client = docker_client or docker.from_env()
        self.results: List[LoadTestResult] = []
        self.monitoring_active = False
        self.system_metrics: List[SystemMetrics] = []
        self.container_metrics: List[ContainerMetrics] = []
        
    def get_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            # Load average (Unix-like systems)
            load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
            
            # Active containers count
            containers = self.docker_client.containers.list()
            active_containers = len([c for c in containers if c.status == 'running'])
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_gb=memory.used / (1024**3),
                memory_available_gb=memory.available / (1024**3),
                disk_usage_percent=disk.percent,
                disk_free_gb=disk.free / (1024**3),
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                load_average_1min=load_avg,
                active_containers=active_containers
            )
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_gb=0.0,
                memory_available_gb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                network_bytes_sent=0,
                network_bytes_recv=0,
                load_average_1min=0.0,
                active_containers=0
            )
    
    def get_container_metrics(self, container_id: str) -> Optional[ContainerMetrics]:
        """Collect metrics for a specific container"""
        try:
            container = self.docker_client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Calculate CPU percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            
            cpu_percent = 0.0
            if system_delta > 0.0:
                cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
            
            # Memory usage
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            
            # Network stats
            network_stats = stats.get('networks', {})
            network_rx = sum(net['rx_bytes'] for net in network_stats.values())
            network_tx = sum(net['tx_bytes'] for net in network_stats.values())
            
            # Block I/O stats
            blkio_stats = stats.get('blkio_stats', {})
            block_read = sum(stat['value'] for stat in blkio_stats.get('io_service_bytes_recursive', []) 
                           if stat['op'] == 'Read')
            block_write = sum(stat['value'] for stat in blkio_stats.get('io_service_bytes_recursive', [])
                            if stat['op'] == 'Write')
            
            # PIDs count
            pids = stats.get('pids_stats', {}).get('current', 0)
            
            # Container info
            container.reload()
            uptime = (datetime.now() - datetime.fromisoformat(container.attrs['State']['StartedAt'].replace('Z', '+00:00').replace('T', ' '))).total_seconds()
            
            return ContainerMetrics(
                container_id=container_id,
                container_name=container.name,
                cpu_percent=cpu_percent,
                memory_usage_mb=memory_usage / (1024**2),
                memory_limit_mb=memory_limit / (1024**2),
                network_rx_bytes=network_rx,
                network_tx_bytes=network_tx,
                block_read_bytes=block_read,
                block_write_bytes=block_write,
                pids=pids,
                status=container.status,
                uptime_seconds=uptime
            )
            
        except Exception as e:
            logger.error(f"Failed to collect container metrics for {container_id}: {e}")
            return None
    
    def start_monitoring(self, interval: int = 5):
        """Start system and container monitoring"""
        self.monitoring_active = True
        self.system_metrics = []
        self.container_metrics = []
        
        def monitor():
            while self.monitoring_active:
                # Collect system metrics
                sys_metrics = self.get_system_metrics()
                self.system_metrics.append(sys_metrics)
                
                # Collect container metrics for all running containers
                containers = self.docker_client.containers.list()
                for container in containers:
                    if container.status == 'running':
                        container_metrics = self.get_container_metrics(container.id)
                        if container_metrics:
                            self.container_metrics.append(container_metrics)
                
                time.sleep(interval)
        
        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()
        logger.info(f"Started monitoring with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring_active = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=10)
        logger.info("Stopped monitoring")
    
    async def create_container(self, image: str, container_name: str) -> Optional[str]:
        """Create and start a new Android container"""
        try:
            container = self.docker_client.containers.run(
                image=image,
                name=container_name,
                detach=True,
                privileged=True,
                ports={'5555/tcp': None},  # Expose ADB port
                environment={
                    'DISPLAY': ':99',
                    'GPU': '1'
                },
                volumes={
                    '/tmp/.X11-unix': {'bind': '/tmp/.X11-unix', 'mode': 'rw'}
                }
            )
            
            # Wait for container to be ready
            await asyncio.sleep(10)
            
            logger.info(f"Created container: {container_name} ({container.id[:12]})")
            return container.id
            
        except Exception as e:
            logger.error(f"Failed to create container {container_name}: {e}")
            return None
    
    async def test_container_responsiveness(self, container_id: str) -> Tuple[bool, float]:
        """Test if container is responsive via ADB"""
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Get container port mapping
            port_info = container.ports.get('5555/tcp')
            if not port_info:
                return False, 0.0
            
            host_port = port_info[0]['HostPort']
            
            start_time = time.time()
            
            # Test ADB connection
            result = subprocess.run([
                'adb', 'connect', f'localhost:{host_port}'
            ], capture_output=True, text=True, timeout=10)
            
            response_time = time.time() - start_time
            
            success = 'connected' in result.stdout.lower()
            
            if success:
                # Test basic command
                test_result = subprocess.run([
                    'adb', '-s', f'localhost:{host_port}', 'shell', 'echo', 'test'
                ], capture_output=True, text=True, timeout=5)
                success = 'test' in test_result.stdout
            
            return success, response_time
            
        except Exception as e:
            logger.error(f"Responsiveness test failed for {container_id}: {e}")
            return False, 0.0
    
    async def stress_test_single_container(self, duration: int = 300) -> LoadTestResult:
        """Stress test a single container with intensive operations"""
        test_name = "Single Container Stress Test"
        logger.info(f"Starting {test_name}")
        
        start_time = datetime.now()
        self.start_monitoring()
        
        errors = []
        response_times = []
        
        # Create container
        container_id = await self.create_container(
            'android-platform:android-13-arm64', 
            f'stress_test_{int(time.time())}'
        )
        
        if not container_id:
            return LoadTestResult(
                test_name=test_name,
                test_type="stress",
                duration_seconds=0,
                container_count=0,
                success_rate=0.0,
                avg_response_time=0.0,
                max_response_time=0.0,
                min_response_time=0.0,
                system_metrics=[],
                container_metrics=[],
                errors=["Failed to create container"],
                start_time=start_time,
                end_time=datetime.now()
            )
        
        try:
            # Run stress test for specified duration
            end_time_target = time.time() + duration
            
            while time.time() < end_time_target:
                # Test container responsiveness
                success, response_time = await self.test_container_responsiveness(container_id)
                response_times.append(response_time)
                
                if not success:
                    errors.append(f"Container unresponsive at {datetime.now()}")
                
                # Simulate load on container
                try:
                    container = self.docker_client.containers.get(container_id)
                    container.exec_run('stress --cpu 2 --timeout 10s', detach=True)
                except:
                    pass
                
                await asyncio.sleep(5)
        
        finally:
            # Cleanup
            try:
                container = self.docker_client.containers.get(container_id)
                container.stop()
                container.remove()
            except:
                pass
            
            self.stop_monitoring()
        
        # Calculate results
        success_rate = (len([r for r in response_times if r > 0]) / len(response_times)) * 100 if response_times else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        
        result = LoadTestResult(
            test_name=test_name,
            test_type="stress",
            duration_seconds=duration,
            container_count=1,
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            max_response_time=max_response_time,
            min_response_time=min_response_time,
            system_metrics=self.system_metrics.copy(),
            container_metrics=self.container_metrics.copy(),
            errors=errors,
            start_time=start_time,
            end_time=datetime.now()
        )
        
        self.results.append(result)
        return result
    
    async def load_test_multiple_containers(self, container_count: int = 5, duration: int = 180) -> LoadTestResult:
        """Load test with multiple concurrent containers"""
        test_name = f"Multiple Container Load Test ({container_count} containers)"
        logger.info(f"Starting {test_name}")
        
        start_time = datetime.now()
        self.start_monitoring()
        
        errors = []
        response_times = []
        created_containers = []
        
        try:
            # Create multiple containers concurrently
            create_tasks = []
            for i in range(container_count):
                task = self.create_container(
                    'android-platform:android-13-arm64',
                    f'load_test_{int(time.time())}_{i}'
                )
                create_tasks.append(task)
            
            # Wait for all containers to be created
            container_ids = await asyncio.gather(*create_tasks, return_exceptions=True)
            created_containers = [cid for cid in container_ids if isinstance(cid, str)]
            
            logger.info(f"Successfully created {len(created_containers)} out of {container_count} containers")
            
            if not created_containers:
                raise Exception("Failed to create any containers")
            
            # Test all containers concurrently
            async def test_container_repeatedly(container_id: str):
                container_response_times = []
                test_end_time = time.time() + duration
                
                while time.time() < test_end_time:
                    try:
                        success, response_time = await self.test_container_responsiveness(container_id)
                        container_response_times.append(response_time)
                        
                        if not success:
                            errors.append(f"Container {container_id[:12]} unresponsive")
                        
                    except Exception as e:
                        errors.append(f"Test error for {container_id[:12]}: {e}")
                    
                    await asyncio.sleep(2)
                
                return container_response_times
            
            # Run tests on all containers concurrently
            test_tasks = [test_container_repeatedly(cid) for cid in created_containers]
            all_response_times = await asyncio.gather(*test_tasks, return_exceptions=True)
            
            # Flatten response times
            for times in all_response_times:
                if isinstance(times, list):
                    response_times.extend(times)
        
        finally:
            # Cleanup all containers
            for container_id in created_containers:
                try:
                    container = self.docker_client.containers.get(container_id)
                    container.stop()
                    container.remove()
                    logger.info(f"Cleaned up container {container_id[:12]}")
                except Exception as e:
                    logger.error(f"Failed to cleanup container {container_id[:12]}: {e}")
            
            self.stop_monitoring()
        
        # Calculate results
        success_rate = (len([r for r in response_times if r > 0]) / len(response_times)) * 100 if response_times else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        
        result = LoadTestResult(
            test_name=test_name,
            test_type="load",
            duration_seconds=duration,
            container_count=len(created_containers),
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            max_response_time=max_response_time,
            min_response_time=min_response_time,
            system_metrics=self.system_metrics.copy(),
            container_metrics=self.container_metrics.copy(),
            errors=errors,
            start_time=start_time,
            end_time=datetime.now()
        )
        
        self.results.append(result)
        return result
    
    async def scalability_test(self, max_containers: int = 10, step_size: int = 2) -> List[LoadTestResult]:
        """Test system scalability by gradually increasing container count"""
        logger.info(f"Starting scalability test: 0 to {max_containers} containers")
        
        scalability_results = []
        
        for container_count in range(step_size, max_containers + 1, step_size):
            logger.info(f"Testing with {container_count} containers")
            
            result = await self.load_test_multiple_containers(
                container_count=container_count,
                duration=120  # Shorter duration for scalability test
            )
            
            scalability_results.append(result)
            
            # Brief pause between scalability steps
            await asyncio.sleep(30)
        
        return scalability_results
    
    async def endurance_test(self, duration: int = 3600) -> LoadTestResult:
        """Long-duration endurance test"""
        test_name = f"Endurance Test ({duration}s)"
        logger.info(f"Starting {test_name}")
        
        return await self.load_test_multiple_containers(
            container_count=3,  # Moderate load for extended period
            duration=duration
        )
    
    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        if not self.results:
            return {"error": "No test results available"}
        
        report = {
            "test_timestamp": datetime.now().isoformat(),
            "total_tests_run": len(self.results),
            "test_results": [],
            "performance_summary": {},
            "recommendations": []
        }
        
        # Process each test result
        for result in self.results:
            test_data = {
                "test_name": result.test_name,
                "test_type": result.test_type,
                "duration_seconds": result.duration_seconds,
                "container_count": result.container_count,
                "success_rate": result.success_rate,
                "avg_response_time": result.avg_response_time,
                "max_response_time": result.max_response_time,
                "min_response_time": result.min_response_time,
                "error_count": len(result.errors),
                "system_performance": {},
                "container_performance": {}
            }
            
            # System performance analysis
            if result.system_metrics:
                cpu_values = [m.cpu_percent for m in result.system_metrics]
                memory_values = [m.memory_percent for m in result.system_metrics]
                
                test_data["system_performance"] = {
                    "avg_cpu_percent": statistics.mean(cpu_values),
                    "max_cpu_percent": max(cpu_values),
                    "avg_memory_percent": statistics.mean(memory_values),
                    "max_memory_percent": max(memory_values),
                    "peak_active_containers": max(m.active_containers for m in result.system_metrics)
                }
            
            # Container performance analysis
            if result.container_metrics:
                container_cpu_values = [m.cpu_percent for m in result.container_metrics]
                container_memory_values = [m.memory_usage_mb for m in result.container_metrics]
                
                test_data["container_performance"] = {
                    "avg_container_cpu_percent": statistics.mean(container_cpu_values),
                    "max_container_cpu_percent": max(container_cpu_values),
                    "avg_container_memory_mb": statistics.mean(container_memory_values),
                    "max_container_memory_mb": max(container_memory_values)
                }
            
            report["test_results"].append(test_data)
        
        # Generate performance summary
        all_success_rates = [r.success_rate for r in self.results]
        all_response_times = [r.avg_response_time for r in self.results]
        
        report["performance_summary"] = {
            "overall_avg_success_rate": statistics.mean(all_success_rates),
            "overall_avg_response_time": statistics.mean(all_response_times),
            "total_errors": sum(len(r.errors) for r in self.results),
            "test_types_coverage": list(set(r.test_type for r in self.results))
        }
        
        # Generate recommendations
        recommendations = []
        
        if report["performance_summary"]["overall_avg_success_rate"] < 95:
            recommendations.append("Success rate below 95% - consider optimizing container startup time or resource allocation")
        
        if report["performance_summary"]["overall_avg_response_time"] > 2.0:
            recommendations.append("Average response time above 2 seconds - consider performance tuning")
        
        if report["performance_summary"]["total_errors"] > 10:
            recommendations.append("High error count detected - investigate system stability")
        
        report["recommendations"] = recommendations
        
        return report

async def main():
    """Main test execution function"""
    import sys
    
    logger.info("Starting Android Container Platform Load Testing")
    
    tester = LoadTester()
    
    try:
        # Run different types of load tests
        
        # 1. Single container stress test
        logger.info("Running single container stress test...")
        await tester.stress_test_single_container(duration=300)
        
        # 2. Multiple container load test
        logger.info("Running multiple container load test...")
        await tester.load_test_multiple_containers(container_count=5, duration=180)
        
        # 3. Scalability test
        logger.info("Running scalability test...")
        scalability_results = await tester.scalability_test(max_containers=8, step_size=2)
        
        # Generate and save report
        report = tester.generate_performance_report()
        
        print(json.dumps(report, indent=2))
        
        # Save detailed report
        with open(f"/tmp/load_test_report_{int(time.time())}.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info("Load testing completed successfully")
        
    except Exception as e:
        logger.error(f"Load testing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())