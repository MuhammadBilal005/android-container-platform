import asyncio
import json
import subprocess
import tempfile
from typing import Dict, Optional

class AndroidConfigurator:
    """Configures Android system settings and applies device spoofing"""
    
    def __init__(self):
        self.adb_timeout = 30
    
    async def configure_instance(self, container_name: str, device_identity: Dict, 
                               network_config: Optional[Dict] = None):
        """Configure Android instance with device identity and settings"""
        
        try:
            print(f"Configuring Android instance: {container_name}")
            
            # Wait for Android to be fully booted
            await self._wait_for_android_ready(container_name)
            
            # Apply device identity spoofing
            await self._apply_device_spoofing(container_name, device_identity)
            
            # Configure system settings
            await self._configure_system_settings(container_name, device_identity)
            
            # Apply integrity bypass configurations
            await self._apply_integrity_bypass(container_name, device_identity)
            
            # Configure network settings if provided
            if network_config:
                await self._configure_network_settings(container_name, network_config)
            
            # Install essential apps and configurations
            await self._install_essential_apps(container_name)
            
            print(f"Android configuration complete for {container_name}")
            
        except Exception as e:
            print(f"Android configuration failed for {container_name}: {e}")
            raise
    
    async def _wait_for_android_ready(self, container_name: str, timeout: int = 180):
        """Wait for Android system to be fully ready"""
        
        print(f"Waiting for Android to be ready in {container_name}...")
        
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                # Check boot completed
                result = await self._adb_command(container_name, "getprop sys.boot_completed")
                if result.strip() == "1":
                    
                    # Check if package manager is ready
                    pm_result = await self._adb_command(container_name, "pm list packages android")
                    if "package:android" in pm_result:
                        
                        # Check if we can access settings
                        settings_result = await self._adb_command(container_name, "settings get global device_name")
                        if settings_result and "null" not in settings_result.lower():
                            print(f"Android is ready in {container_name}")
                            return
                
            except Exception:
                pass
            
            await asyncio.sleep(5)
        
        raise Exception(f"Android failed to become ready in {container_name}")
    
    async def _adb_command(self, container_name: str, command: str) -> str:
        """Execute ADB command in container"""
        
        try:
            result = subprocess.run([
                "docker", "exec", container_name,
                "adb", "shell", command
            ], capture_output=True, text=True, timeout=self.adb_timeout)
            
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            raise Exception(f"ADB command timeout: {command}")
        except Exception as e:
            raise Exception(f"ADB command failed: {command} - {str(e)}")
    
    async def _apply_device_spoofing(self, container_name: str, device_identity: Dict):
        """Apply device identity spoofing at system level"""
        
        print(f"Applying device spoofing for {container_name}")
        
        try:
            system_properties = device_identity.get("system_properties", {})
            
            # Create system properties override script
            props_script = "#!/system/bin/sh\n"
            
            for prop, value in system_properties.items():
                # Set system property
                props_script += f'setprop "{prop}" "{value}"\n'
            
            # Special handling for IMEI, Android ID, Serial Number
            if device_identity.get("imei"):
                props_script += f'setprop "ril.IMEI" "{device_identity["imei"]}"\n'
                props_script += f'setprop "ro.ril.oem.imei" "{device_identity["imei"]}"\n'
            
            if device_identity.get("android_id"):
                # Android ID is typically stored in settings database
                await self._adb_command(
                    container_name,
                    f'settings put secure android_id {device_identity["android_id"]}'
                )
            
            # Write and execute properties script
            await self._write_and_execute_script(container_name, props_script, "/system/bin/set_props.sh")
            
            # Override build.prop values
            await self._override_build_prop(container_name, system_properties)
            
        except Exception as e:
            print(f"Device spoofing failed: {e}")
            raise
    
    async def _override_build_prop(self, container_name: str, properties: Dict):
        """Override build.prop file with spoofed values"""
        
        try:
            # Read current build.prop
            current_props = await self._adb_command(container_name, "cat /system/build.prop")
            
            # Create new build.prop with overrides
            new_props_lines = []
            existing_props = set()
            
            for line in current_props.split('\n'):
                if '=' in line and not line.strip().startswith('#'):
                    prop_name = line.split('=')[0].strip()
                    
                    # Check if we need to override this property
                    override_value = None
                    for our_prop, our_value in properties.items():
                        if our_prop == prop_name or our_prop == prop_name.replace('ro.', ''):
                            override_value = our_value
                            existing_props.add(our_prop)
                            break
                    
                    if override_value:
                        new_props_lines.append(f"{prop_name}={override_value}")
                    else:
                        new_props_lines.append(line)
                else:
                    new_props_lines.append(line)
            
            # Add any new properties that weren't in the original file
            for prop, value in properties.items():
                if prop not in existing_props:
                    new_props_lines.append(f"ro.{prop}={value}")
            
            new_build_prop = '\n'.join(new_props_lines)
            
            # Write new build.prop
            await self._write_file_to_container(
                container_name, 
                new_build_prop, 
                "/system/build.prop.new"
            )
            
            # Replace original build.prop
            await self._adb_command(container_name, "mount -o rw,remount /system")
            await self._adb_command(container_name, "cp /system/build.prop.new /system/build.prop")
            await self._adb_command(container_name, "chmod 644 /system/build.prop")
            await self._adb_command(container_name, "mount -o ro,remount /system")
            
        except Exception as e:
            print(f"build.prop override failed: {e}")
    
    async def _configure_system_settings(self, container_name: str, device_identity: Dict):
        """Configure Android system settings"""
        
        print(f"Configuring system settings for {container_name}")
        
        try:
            device_profile = device_identity.get("device_profile", {})
            
            # Set device name
            device_name = f"{device_profile.get('manufacturer', 'Google')} {device_profile.get('model', 'Pixel 7')}"
            await self._adb_command(container_name, f'settings put global device_name "{device_name}"')
            
            # Configure display settings
            if device_profile.get("screen_density"):
                await self._adb_command(
                    container_name, 
                    f'wm density {device_profile["screen_density"]}'
                )
            
            # Disable developer options and debugging
            await self._adb_command(container_name, "settings put global development_settings_enabled 0")
            await self._adb_command(container_name, "settings put global adb_enabled 0")
            await self._adb_command(container_name, "settings put secure install_non_market_apps 0")
            
            # Configure location services
            await self._adb_command(container_name, "settings put secure location_mode 3")
            await self._adb_command(container_name, "settings put secure location_providers_allowed gps,network")
            
            # Configure timezone (based on location if available)
            await self._adb_command(container_name, "settings put global auto_time_zone 1")
            
            # Disable USB debugging indicator
            await self._adb_command(container_name, "settings put global adb_notify 0")
            
            # Configure other security settings
            await self._adb_command(container_name, "settings put secure lock_screen_lock_after_timeout 0")
            await self._adb_command(container_name, "settings put system screen_off_timeout 600000")
            
        except Exception as e:
            print(f"System settings configuration failed: {e}")
    
    async def _apply_integrity_bypass(self, container_name: str, device_identity: Dict):
        """Apply integrity bypass configurations"""
        
        print(f"Applying integrity bypass for {container_name}")
        
        try:
            bypass_config = device_identity.get("integrity_bypass_config", {})
            
            # SafetyNet bypass
            safetynet_config = bypass_config.get("safetynet", {})
            if safetynet_config.get("enabled"):
                await self._apply_safetynet_bypass(container_name, safetynet_config)
            
            # Root detection bypass
            root_config = bypass_config.get("root_detection", {})
            if root_config.get("enabled"):
                await self._apply_root_detection_bypass(container_name, root_config)
            
            # Bootloader bypass
            bootloader_config = bypass_config.get("bootloader_unlock", {})
            if bootloader_config.get("enabled"):
                await self._apply_bootloader_bypass(container_name, bootloader_config)
            
        except Exception as e:
            print(f"Integrity bypass application failed: {e}")
    
    async def _apply_safetynet_bypass(self, container_name: str, config: Dict):
        """Apply SafetyNet bypass configurations"""
        
        try:
            # Hide system modifications
            system_mods = config.get("system_modifications", {})
            for prop, value in system_mods.items():
                await self._adb_command(container_name, f'setprop "{prop}" "{value}"')
            
            # Install Universal SafetyNet Fix if available
            await self._install_safetynet_fix(container_name)
            
        except Exception as e:
            print(f"SafetyNet bypass failed: {e}")
    
    async def _apply_root_detection_bypass(self, container_name: str, config: Dict):
        """Apply root detection bypass"""
        
        try:
            # Hide root files and processes
            file_hiding = config.get("file_hiding", [])
            
            for file_path in file_hiding:
                # Remove or hide the file
                await self._adb_command(container_name, f"rm -f {file_path}")
            
            # Set anti-root system properties
            anti_detection = config.get("anti_detection_measures", {})
            if anti_detection.get("test_keys_bypass"):
                await self._adb_command(container_name, 'setprop "ro.build.tags" "release-keys"')
            
        except Exception as e:
            print(f"Root detection bypass failed: {e}")
    
    async def _apply_bootloader_bypass(self, container_name: str, config: Dict):
        """Apply bootloader unlock detection bypass"""
        
        try:
            spoofed_props = config.get("spoofed_properties", {})
            
            for prop, value in spoofed_props.items():
                await self._adb_command(container_name, f'setprop "{prop}" "{value}"')
            
        except Exception as e:
            print(f"Bootloader bypass failed: {e}")
    
    async def _configure_network_settings(self, container_name: str, network_config: Dict):
        """Configure network settings"""
        
        try:
            # Configure proxy if specified
            proxy_config = network_config.get("proxy_config")
            if proxy_config:
                await self._configure_proxy(container_name, proxy_config)
            
            # Configure DNS
            dns_servers = network_config.get("dns_servers", [])
            if dns_servers:
                await self._configure_dns(container_name, dns_servers)
            
        except Exception as e:
            print(f"Network configuration failed: {e}")
    
    async def _configure_proxy(self, container_name: str, proxy_config: Dict):
        """Configure HTTP proxy settings"""
        
        try:
            proxy_host = proxy_config["host"]
            proxy_port = proxy_config["port"]
            
            # Set global proxy
            await self._adb_command(
                container_name,
                f'settings put global http_proxy {proxy_host}:{proxy_port}'
            )
            
            # Set proxy for WiFi (if connected)
            await self._adb_command(
                container_name,
                f'settings put secure http_proxy {proxy_host}:{proxy_port}'
            )
            
        except Exception as e:
            print(f"Proxy configuration failed: {e}")
    
    async def _configure_dns(self, container_name: str, dns_servers: list):
        """Configure DNS settings"""
        
        try:
            # Set DNS servers (this is simplified - full implementation would
            # require modifying network configuration files)
            
            dns_list = ",".join(dns_servers)
            await self._adb_command(
                container_name,
                f'setprop "net.dns1" "{dns_servers[0]}"'
            )
            
            if len(dns_servers) > 1:
                await self._adb_command(
                    container_name,
                    f'setprop "net.dns2" "{dns_servers[1]}"'
                )
            
        except Exception as e:
            print(f"DNS configuration failed: {e}")
    
    async def _install_essential_apps(self, container_name: str):
        """Install essential apps and tools"""
        
        try:
            # This would typically install:
            # - Google Play Store (with spoofed device certification)
            # - Essential Google apps
            # - Security bypass modules
            
            print(f"Installing essential apps for {container_name}")
            
            # For now, just ensure basic Google services are configured
            await self._configure_google_services(container_name)
            
        except Exception as e:
            print(f"Essential apps installation failed: {e}")
    
    async def _configure_google_services(self, container_name: str):
        """Configure Google Play Services"""
        
        try:
            # Enable Google Play Services
            await self._adb_command(
                container_name,
                "pm enable com.google.android.gms"
            )
            
            # Configure device registration
            await self._adb_command(
                container_name,
                "am startservice com.google.android.gms/.checkin.CheckinService"
            )
            
        except Exception as e:
            print(f"Google services configuration failed: {e}")
    
    async def _install_safetynet_fix(self, container_name: str):
        """Install Universal SafetyNet Fix module"""
        
        try:
            # This would install the SafetyNet bypass module
            # Implementation depends on having the module file available
            print(f"Installing SafetyNet fix for {container_name}")
            
        except Exception as e:
            print(f"SafetyNet fix installation failed: {e}")
    
    async def _write_and_execute_script(self, container_name: str, script_content: str, 
                                      script_path: str):
        """Write and execute a script in the container"""
        
        try:
            # Write script to temporary location
            temp_path = f"/data/local/tmp/{script_path.split('/')[-1]}"
            
            await self._write_file_to_container(container_name, script_content, temp_path)
            
            # Make executable and run
            await self._adb_command(container_name, f"chmod 755 {temp_path}")
            await self._adb_command(container_name, f"sh {temp_path}")
            
        except Exception as e:
            print(f"Script execution failed: {e}")
    
    async def _write_file_to_container(self, container_name: str, content: str, 
                                     target_path: str):
        """Write file content to container"""
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Copy to container
                subprocess.run([
                    "docker", "cp", temp_file_path, 
                    f"{container_name}:{target_path}"
                ], check=True, timeout=30)
                
            finally:
                # Cleanup temp file
                subprocess.run(["rm", "-f", temp_file_path], check=False)
                
        except Exception as e:
            print(f"File write failed: {e}")
            raise