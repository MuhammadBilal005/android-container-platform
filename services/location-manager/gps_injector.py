import asyncio
import json
import os
import subprocess
import tempfile
from typing import Optional
import docker

class GPSInjector:
    """System-level GPS injection for Android containers"""
    
    def __init__(self, instance_id: str):
        self.instance_id = instance_id
        self.container_name = f"android-{instance_id}"
        self.docker_client = docker.from_env()
    
    async def inject_location(self, 
                            latitude: float, 
                            longitude: float,
                            altitude: float = 0.0,
                            accuracy: float = 10.0,
                            speed: float = 0.0,
                            bearing: float = 0.0,
                            provider: str = "gps") -> bool:
        """Inject location at system level (non-mock)"""
        
        try:
            container = self.docker_client.containers.get(self.container_name)
            
            # Method 1: Direct GPS provider injection via Android framework
            success = await self._inject_via_framework(
                container, latitude, longitude, altitude, accuracy, speed, bearing, provider
            )
            
            if success:
                return True
            
            # Method 2: Kernel-level GPS device simulation
            success = await self._inject_via_kernel_device(
                container, latitude, longitude, altitude, accuracy, speed, bearing
            )
            
            if success:
                return True
            
            # Method 3: HAL layer injection
            success = await self._inject_via_hal_layer(
                container, latitude, longitude, altitude, accuracy, speed, bearing
            )
            
            return success
            
        except Exception as e:
            print(f"GPS injection failed: {e}")
            return False
    
    async def _inject_via_framework(self, container, lat: float, lng: float, 
                                  alt: float, acc: float, speed: float, 
                                  bearing: float, provider: str) -> bool:
        """Inject location via Android LocationManager framework"""
        
        try:
            # Create location injection script
            injection_script = f"""
import android.location.Location;
import android.location.LocationManager;
import android.content.Context;
import java.lang.reflect.Method;

public class LocationInjector {{
    public static void injectLocation(Context context) {{
        try {{
            LocationManager lm = (LocationManager) context.getSystemService(Context.LOCATION_SERVICE);
            
            // Create location object
            Location location = new Location("{provider}");
            location.setLatitude({lat});
            location.setLongitude({lng});
            location.setAltitude({alt});
            location.setAccuracy({acc}f);
            location.setSpeed({speed}f);
            location.setBearing({bearing}f);
            location.setTime(System.currentTimeMillis());
            location.setElapsedRealtimeNanos(android.os.SystemClock.elapsedRealtimeNanos());
            
            // Get hidden method to set location
            Method method = LocationManager.class.getDeclaredMethod(
                "setTestProviderLocation", String.class, Location.class);
            method.setAccessible(true);
            
            // Enable test provider first
            Method addTestProvider = LocationManager.class.getDeclaredMethod(
                "addTestProvider", String.class, boolean.class, boolean.class, 
                boolean.class, boolean.class, boolean.class, boolean.class, 
                boolean.class, int.class, int.class);
            addTestProvider.setAccessible(true);
            addTestProvider.invoke(lm, "{provider}", false, false, false, false, 
                                 true, true, true, 1, 1);
            
            Method setTestProviderEnabled = LocationManager.class.getDeclaredMethod(
                "setTestProviderEnabled", String.class, boolean.class);
            setTestProviderEnabled.setAccessible(true);
            setTestProviderEnabled.invoke(lm, "{provider}", true);
            
            // Inject location
            method.invoke(lm, "{provider}", location);
            
            System.out.println("Location injected successfully");
        }} catch (Exception e) {{
            e.printStackTrace();
        }}
    }}
}}
"""
            
            # Write script to container
            with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
                f.write(injection_script)
                script_path = f.name
            
            # Copy to container
            container.exec_run(f"mkdir -p /data/local/tmp/location_injection")
            with open(script_path, 'rb') as f:
                container.put_archive("/data/local/tmp/location_injection", f.read())
            
            # Compile and execute
            result = container.exec_run([
                "sh", "-c", 
                f"cd /data/local/tmp/location_injection && "
                f"export CLASSPATH=/system/framework/framework.jar && "
                f"dalvikvm -cp . LocationInjector"
            ])
            
            os.unlink(script_path)
            return result.exit_code == 0
            
        except Exception as e:
            print(f"Framework injection failed: {e}")
            return False
    
    async def _inject_via_kernel_device(self, container, lat: float, lng: float,
                                      alt: float, acc: float, speed: float, bearing: float) -> bool:
        """Inject location via kernel-level GPS device simulation"""
        
        try:
            # Create NMEA sentences for GPS data
            nmea_sentences = self._generate_nmea_sentences(lat, lng, alt, speed, bearing)
            
            # Create virtual GPS device
            device_script = f"""#!/system/bin/sh
# Create virtual GPS device
echo '{nmea_sentences}' > /dev/ttyUSB0 2>/dev/null || true
echo '{nmea_sentences}' > /dev/tttyS0 2>/dev/null || true

# Inject into GPS HAL
setprop gps.current.latitude {lat}
setprop gps.current.longitude {lng}
setprop gps.current.altitude {alt}
setprop gps.current.accuracy {acc}
setprop gps.current.speed {speed}
setprop gps.current.bearing {bearing}
setprop gps.current.time $(date +%s)

# Notify location services
am broadcast -a android.location.GPS_ENABLED_CHANGE
am broadcast -a android.location.PROVIDERS_CHANGED
"""
            
            # Execute in container
            result = container.exec_run(["sh", "-c", device_script])
            return result.exit_code == 0
            
        except Exception as e:
            print(f"Kernel device injection failed: {e}")
            return False
    
    async def _inject_via_hal_layer(self, container, lat: float, lng: float,
                                  alt: float, acc: float, speed: float, bearing: float) -> bool:
        """Inject location via Hardware Abstraction Layer"""
        
        try:
            # Create HAL injection script
            hal_script = f"""
# GPS HAL injection
# Set location properties directly in system properties
setprop ro.hardware.gps true
setprop gps.lge.sv_policy 0
setprop gps.hal.current.latitude {lat}
setprop gps.hal.current.longitude {lng}
setprop gps.hal.current.altitude {alt}
setprop gps.hal.current.accuracy {acc}
setprop gps.hal.current.speed {speed}
setprop gps.hal.current.bearing {bearing}
setprop gps.hal.current.timestamp $(date +%s)000

# Update location manager
am broadcast -a android.intent.action.LOCATION_CHANGED \\
  --ef latitude {lat} --ef longitude {lng} --ef altitude {alt} \\
  --ef accuracy {acc} --ef speed {speed} --ef bearing {bearing}

# Force location update
am start-service -a android.location.LocationManager.GPS_LOCATION_UPDATE
"""
            
            result = container.exec_run(["sh", "-c", hal_script])
            return result.exit_code == 0
            
        except Exception as e:
            print(f"HAL injection failed: {e}")
            return False
    
    def _generate_nmea_sentences(self, lat: float, lng: float, alt: float, 
                                speed: float, bearing: float) -> str:
        """Generate NMEA sentences for GPS data"""
        
        import datetime
        
        # Convert coordinates to NMEA format
        lat_deg = int(abs(lat))
        lat_min = (abs(lat) - lat_deg) * 60
        lat_dir = 'N' if lat >= 0 else 'S'
        
        lng_deg = int(abs(lng))
        lng_min = (abs(lng) - lng_deg) * 60
        lng_dir = 'E' if lng >= 0 else 'W'
        
        # Current time
        now = datetime.datetime.utcnow()
        time_str = now.strftime("%H%M%S.000")
        date_str = now.strftime("%d%m%y")
        
        # GPGGA sentence (Global Positioning System Fix Data)
        gpgga = f"$GPGGA,{time_str},{lat_deg:02d}{lat_min:07.4f},{lat_dir},{lng_deg:03d}{lng_min:07.4f},{lng_dir},1,04,{alt:.1f},M,0.0,M,,*"
        
        # GPRMC sentence (Recommended Minimum Navigation Information)
        gprmc = f"$GPRMC,{time_str},A,{lat_deg:02d}{lat_min:07.4f},{lat_dir},{lng_deg:03d}{lng_min:07.4f},{lng_dir},{speed:.1f},{bearing:.1f},{date_str},,*"
        
        # Calculate checksums
        gpgga_checksum = self._calculate_nmea_checksum(gpgga)
        gprmc_checksum = self._calculate_nmea_checksum(gprmc)
        
        gpgga += f"{gpgga_checksum:02X}"
        gprmc += f"{gprmc_checksum:02X}"
        
        return f"{gpgga}\\n{gprmc}\\n"
    
    def _calculate_nmea_checksum(self, sentence: str) -> int:
        """Calculate NMEA sentence checksum"""
        checksum = 0
        for char in sentence[1:sentence.rfind('*')]:
            checksum ^= ord(char)
        return checksum
    
    async def inject_nmea_stream(self, nmea_data: str) -> bool:
        """Inject raw NMEA data stream"""
        
        try:
            container = self.docker_client.containers.get(self.container_name)
            
            # Write NMEA data to GPS device
            result = container.exec_run([
                "sh", "-c", 
                f"echo '{nmea_data}' > /dev/gps0 2>/dev/null || "
                f"echo '{nmea_data}' > /dev/ttyUSB0 2>/dev/null || "
                f"echo '{nmea_data}' | nc -u localhost 1234"
            ])
            
            return result.exit_code == 0
            
        except Exception as e:
            print(f"NMEA stream injection failed: {e}")
            return False
    
    async def enable_gps_provider(self, provider: str = "gps") -> bool:
        """Enable GPS provider in Android"""
        
        try:
            container = self.docker_client.containers.get(self.container_name)
            
            # Enable location services
            enable_script = f"""
# Enable location services
settings put secure location_providers_allowed +{provider}
settings put secure location_mode 3
am broadcast -a android.location.PROVIDERS_CHANGED
"""
            
            result = container.exec_run(["sh", "-c", enable_script])
            return result.exit_code == 0
            
        except Exception as e:
            print(f"Failed to enable GPS provider: {e}")
            return False