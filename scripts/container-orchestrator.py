#!/usr/bin/env python3

"""
Android Container Orchestrator
Manages multiple Android container instances with device spoofing
"""

import os
import json
import time
import threading
import subprocess
import signal
import sys
from datetime import datetime
from pathlib import Path

class AndroidContainerOrchestrator:
    def __init__(self, config_file="/etc/android-containers/orchestrator.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.containers = {}
        self.running = False
        self.monitor_thread = None
        
    def load_config(self):
        """Load orchestrator configuration"""
        default_config = {
            "max_containers": 10,
            "base_port": 5555,
            "health_check_interval": 30,
            "restart_policy": "always",
            "container_timeout": 300,
            "device_profiles_dir": "/system/etc/device-profiles",
            "default_android_version": "13",
            "default_architecture": "arm64",
            "networking": {
                "bridge": "android-bridge",
                "subnet": "172.20.0.0/16"
            },
            "resources": {
                "memory_limit": "2g",
                "cpu_limit": "2",
                "disk_limit": "10g"
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
        except Exception as e:
            print(f"WARNING: Failed to load config: {e}")
        
        return default_config
    
    def save_config(self):
        """Save orchestrator configuration"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"ERROR: Failed to save config: {e}")
    
    def get_available_device_profiles(self):
        """Get list of available device profiles"""
        profiles_dir = Path(self.config["device_profiles_dir"])
        profiles = []
        
        try:
            for profile_file in profiles_dir.glob("*.json"):
                try:
                    with open(profile_file, 'r') as f:
                        profile_data = json.load(f)
                        profiles.append({
                            'id': profile_file.stem,
                            'name': profile_data.get('device_name', 'Unknown'),
                            'android_version': profile_data.get('android_version', 'Unknown'),
                            'manufacturer': profile_data.get('manufacturer', 'Unknown')
                        })
                except Exception as e:
                    print(f"WARNING: Failed to load profile {profile_file}: {e}")
        except Exception as e:
            print(f"ERROR: Failed to read profiles directory: {e}")
        
        return profiles
    
    def create_container(self, container_id, config):
        """Create and start a new Android container"""
        try:
            # Generate unique identifiers
            container_name = f"android-{container_id}"
            adb_port = self.config["base_port"] + int(container_id)
            
            # Select device profile
            device_profile = config.get("device_profile", "samsung_galaxy_s24")
            android_version = config.get("android_version", self.config["default_android_version"])
            architecture = config.get("architecture", self.config["default_architecture"])
            
            # Docker image selection
            docker_image = f"android-container-platform:android-{android_version}-{architecture}"
            
            # Environment variables
            env_vars = {
                "ANDROID_VERSION": android_version,
                "ARCH": architecture,
                "GPS_LATITUDE": str(config.get("latitude", 40.7128)),
                "GPS_LONGITUDE": str(config.get("longitude", -74.0060)),
                "GPS_ALTITUDE": str(config.get("altitude", 10.0)),
                "DEVICE_PROFILE": device_profile,
                "CONTAINER_ID": container_id
            }
            
            # Build docker run command
            docker_cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "--privileged",
                "--tmpfs", "/tmp",
                "-p", f"{adb_port}:5555",
                "--memory", self.config["resources"]["memory_limit"],
                "--cpus", self.config["resources"]["cpu_limit"]
            ]
            
            # Add environment variables
            for key, value in env_vars.items():
                docker_cmd.extend(["-e", f"{key}={value}"])
            
            # Add volumes
            docker_cmd.extend([
                "-v", "/dev/kvm:/dev/kvm",
                "-v", f"{self.config['device_profiles_dir']}:/system/etc/device-profiles:ro"
            ])
            
            # Add network configuration
            if "networking" in self.config:
                docker_cmd.extend(["--network", self.config["networking"]["bridge"]])
            
            # Add image name
            docker_cmd.append(docker_image)
            
            print(f"Creating container {container_name}...")
            print(f"Command: {' '.join(docker_cmd)}")
            
            # Execute docker run
            result = subprocess.run(docker_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"ERROR: Failed to create container {container_name}: {result.stderr}")
                return False
            
            # Get container ID from docker
            docker_container_id = result.stdout.strip()
            
            # Store container information
            container_info = {
                'id': container_id,
                'name': container_name,
                'docker_id': docker_container_id,
                'adb_port': adb_port,
                'device_profile': device_profile,
                'android_version': android_version,
                'architecture': architecture,
                'config': config,
                'created_at': datetime.now().isoformat(),
                'status': 'starting'
            }
            
            self.containers[container_id] = container_info
            
            print(f"Container {container_name} created successfully")
            print(f"ADB port: {adb_port}")
            print(f"Docker ID: {docker_container_id}")
            
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to create container {container_id}: {e}")
            return False
    
    def stop_container(self, container_id):
        """Stop and remove a container"""
        if container_id not in self.containers:
            print(f"ERROR: Container {container_id} not found")
            return False
        
        container_info = self.containers[container_id]
        
        try:
            # Stop container
            subprocess.run(["docker", "stop", container_info['docker_id']], 
                         capture_output=True, check=False)
            
            # Remove container
            subprocess.run(["docker", "rm", container_info['docker_id']], 
                         capture_output=True, check=False)
            
            # Remove from tracking
            del self.containers[container_id]
            
            print(f"Container {container_info['name']} stopped and removed")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to stop container {container_id}: {e}")
            return False
    
    def get_container_status(self, container_id):
        """Get detailed status of a container"""
        if container_id not in self.containers:
            return None
        
        container_info = self.containers[container_id]
        
        try:
            # Get container status from Docker
            result = subprocess.run(
                ["docker", "inspect", container_info['docker_id']], 
                capture_output=True, text=True, check=False
            )
            
            if result.returncode == 0:
                docker_info = json.loads(result.stdout)[0]
                status = docker_info['State']['Status']
                
                # Update container status
                container_info['status'] = status
                container_info['docker_info'] = {
                    'status': status,
                    'running': docker_info['State']['Running'],
                    'started_at': docker_info['State']['StartedAt'],
                    'finished_at': docker_info['State']['FinishedAt']
                }
                
                # Check health if container is running
                if status == 'running':
                    health_status = self.check_container_health(container_id)
                    container_info['health'] = health_status
                
                return container_info
            else:
                container_info['status'] = 'not_found'
                return container_info
                
        except Exception as e:
            print(f"WARNING: Failed to get status for container {container_id}: {e}")
            container_info['status'] = 'unknown'
            return container_info
    
    def check_container_health(self, container_id):
        """Check health of a specific container"""
        if container_id not in self.containers:
            return {'status': 'not_found'}
        
        container_info = self.containers[container_id]
        
        try:
            # Execute health check script inside container
            result = subprocess.run([
                "docker", "exec", container_info['docker_id'],
                "/usr/local/bin/health-check.sh"
            ], capture_output=True, text=True, check=False, timeout=30)
            
            health_status = {
                'timestamp': datetime.now().isoformat(),
                'exit_code': result.returncode,
                'output': result.stdout,
                'error': result.stderr
            }
            
            if result.returncode == 0:
                health_status['status'] = 'healthy'
            elif result.returncode == 1:
                health_status['status'] = 'warning'
            else:
                health_status['status'] = 'critical'
            
            return health_status
            
        except subprocess.TimeoutExpired:
            return {
                'status': 'timeout',
                'timestamp': datetime.now().isoformat(),
                'error': 'Health check timed out'
            }
        except Exception as e:
            return {
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def list_containers(self):
        """List all managed containers with status"""
        containers_list = []
        
        for container_id, container_info in self.containers.items():
            status_info = self.get_container_status(container_id)
            containers_list.append(status_info)
        
        return containers_list
    
    def monitor_containers(self):
        """Monitor containers and restart if needed"""
        while self.running:
            try:
                for container_id in list(self.containers.keys()):
                    status_info = self.get_container_status(container_id)
                    
                    if status_info and status_info['status'] != 'running':
                        if self.config["restart_policy"] == "always":
                            print(f"Container {container_id} is {status_info['status']}, restarting...")
                            self.restart_container(container_id)
                    
                    elif status_info and 'health' in status_info:
                        health = status_info['health']
                        if health['status'] == 'critical':
                            print(f"Container {container_id} is critically unhealthy, restarting...")
                            self.restart_container(container_id)
                
                time.sleep(self.config["health_check_interval"])
                
            except Exception as e:
                print(f"ERROR in monitor loop: {e}")
                time.sleep(10)
    
    def restart_container(self, container_id):
        """Restart a container"""
        if container_id not in self.containers:
            print(f"ERROR: Container {container_id} not found")
            return False
        
        container_info = self.containers[container_id]
        config = container_info['config']
        
        print(f"Restarting container {container_id}...")
        
        # Stop the container
        self.stop_container(container_id)
        
        # Wait a moment
        time.sleep(5)
        
        # Create new container with same config
        return self.create_container(container_id, config)
    
    def start_monitoring(self):
        """Start container monitoring in background"""
        if self.running:
            print("Monitoring already started")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_containers, daemon=True)
        self.monitor_thread.start()
        print("Container monitoring started")
    
    def stop_monitoring(self):
        """Stop container monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("Container monitoring stopped")
    
    def cleanup_all(self):
        """Stop all containers and cleanup"""
        print("Cleaning up all containers...")
        
        for container_id in list(self.containers.keys()):
            self.stop_container(container_id)
        
        self.stop_monitoring()
        print("Cleanup completed")
    
    def print_status(self):
        """Print formatted status of all containers"""
        containers = self.list_containers()
        
        if not containers:
            print("No containers running")
            return
        
        print("\nAndroid Container Status:")
        print("-" * 100)
        print(f"{'ID':<8} {'Name':<20} {'Status':<12} {'Health':<10} {'ADB Port':<8} {'Profile':<20}")
        print("-" * 100)
        
        for container in containers:
            health_status = "Unknown"
            if 'health' in container:
                health_status = container['health']['status'].title()
            
            print(f"{container['id']:<8} "
                  f"{container['name']:<20} "
                  f"{container['status'].title():<12} "
                  f"{health_status:<10} "
                  f"{container['adb_port']:<8} "
                  f"{container['device_profile']:<20}")

def signal_handler(sig, frame, orchestrator):
    """Handle shutdown signals"""
    print("\nReceived shutdown signal, cleaning up...")
    orchestrator.cleanup_all()
    sys.exit(0)

def main():
    orchestrator = AndroidContainerOrchestrator()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, orchestrator))
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, orchestrator))
    
    if len(sys.argv) < 2:
        print("Android Container Orchestrator Usage:")
        print("  container-orchestrator.py create <id> <config.json>")
        print("  container-orchestrator.py stop <id>")
        print("  container-orchestrator.py restart <id>")
        print("  container-orchestrator.py status [id]")
        print("  container-orchestrator.py list")
        print("  container-orchestrator.py profiles")
        print("  container-orchestrator.py monitor")
        print("  container-orchestrator.py cleanup")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create" and len(sys.argv) >= 4:
        container_id = sys.argv[2]
        config_file = sys.argv[3]
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            orchestrator.create_container(container_id, config)
        except Exception as e:
            print(f"ERROR: Failed to load config: {e}")
    
    elif command == "stop" and len(sys.argv) >= 3:
        container_id = sys.argv[2]
        orchestrator.stop_container(container_id)
    
    elif command == "restart" and len(sys.argv) >= 3:
        container_id = sys.argv[2]
        orchestrator.restart_container(container_id)
    
    elif command == "status":
        if len(sys.argv) >= 3:
            container_id = sys.argv[2]
            status = orchestrator.get_container_status(container_id)
            if status:
                print(json.dumps(status, indent=2))
            else:
                print(f"Container {container_id} not found")
        else:
            orchestrator.print_status()
    
    elif command == "list":
        orchestrator.print_status()
    
    elif command == "profiles":
        profiles = orchestrator.get_available_device_profiles()
        print("Available Device Profiles:")
        print("-" * 60)
        for profile in profiles:
            print(f"  {profile['id']:<20} {profile['name']:<25} Android {profile['android_version']}")
    
    elif command == "monitor":
        print("Starting container monitoring (Ctrl+C to stop)...")
        orchestrator.start_monitoring()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    elif command == "cleanup":
        orchestrator.cleanup_all()
    
    else:
        print("Invalid command")
        sys.exit(1)

if __name__ == "__main__":
    main()