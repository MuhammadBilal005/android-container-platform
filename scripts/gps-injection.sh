#!/system/bin/sh

# GPS Location Injection and Spoofing Script
# Provides comprehensive GPS location management for Android containers

LOG_TAG="GPSInjection"
LOG_FILE="/data/local/tmp/gps-injection.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$LOG_TAG] $1" | tee -a "$LOG_FILE"
}

# Default coordinates (can be overridden by environment variables)
DEFAULT_LAT="${GPS_LATITUDE:-40.7128}"
DEFAULT_LON="${GPS_LONGITUDE:--74.0060}"
DEFAULT_ALT="${GPS_ALTITUDE:-10.0}"
DEFAULT_ACCURACY="${GPS_ACCURACY:-5.0}"

# GPS provider types
GPS_PROVIDER="gps"
NETWORK_PROVIDER="network"
PASSIVE_PROVIDER="passive"
FUSED_PROVIDER="fused"

# Create mock location provider service
create_mock_provider_service() {
    log "Creating mock location provider service..."
    
    # Create service directory
    local service_dir="/system/etc/gps-injection"
    mkdir -p "$service_dir"
    
    # Create GPS provider replacement script
    cat > "$service_dir/mock_gps_provider.py" << 'EOF'
#!/usr/bin/env python3

import time
import json
import socket
import threading
import subprocess
from datetime import datetime, timezone

class MockGPSProvider:
    def __init__(self, lat=40.7128, lon=-74.0060, alt=10.0, accuracy=5.0):
        self.latitude = lat
        self.longitude = lon
        self.altitude = alt
        self.accuracy = accuracy
        self.speed = 0.0
        self.bearing = 0.0
        self.running = False
        self.socket_path = "/data/local/tmp/gps_socket"
        
    def set_location(self, lat, lon, alt=None, accuracy=None):
        """Update current location coordinates"""
        self.latitude = lat
        self.longitude = lon
        if alt is not None:
            self.altitude = alt
        if accuracy is not None:
            self.accuracy = accuracy
        print(f"Location updated: {lat}, {lon}")
    
    def generate_nmea_sentence(self):
        """Generate NMEA GPS sentence"""
        timestamp = datetime.now(timezone.utc)
        time_str = timestamp.strftime("%H%M%S.%f")[:-3]  # HHMMSS.sss
        date_str = timestamp.strftime("%d%m%y")  # DDMMYY
        
        # Convert decimal degrees to degrees/minutes format
        lat_deg = int(abs(self.latitude))
        lat_min = (abs(self.latitude) - lat_deg) * 60
        lat_dir = 'N' if self.latitude >= 0 else 'S'
        
        lon_deg = int(abs(self.longitude))
        lon_min = (abs(self.longitude) - lon_deg) * 60
        lon_dir = 'E' if self.longitude >= 0 else 'W'
        
        # Create GPGGA sentence (Global Positioning System Fix Data)
        gpgga = f"GPGGA,{time_str},{lat_deg:02d}{lat_min:07.4f},{lat_dir},{lon_deg:03d}{lon_min:07.4f},{lon_dir},1,04,{self.accuracy:.1f},{self.altitude:.1f},M,0.0,M,,*"
        
        # Calculate checksum
        checksum = 0
        for char in gpgga.split('*')[0].split('$')[-1]:
            checksum ^= ord(char)
        
        gpgga += f"{checksum:02X}"
        
        return f"${gpgga}"
    
    def inject_location_system(self):
        """Inject location directly into Android location system"""
        try:
            # Use Android's location manager to inject test location
            cmd = [
                "am", "broadcast",
                "-a", "android.location.GPS_ENABLED_CHANGE",
                "--ez", "enabled", "true"
            ]
            subprocess.run(cmd, check=False, capture_output=True)
            
            # Set mock location via settings
            subprocess.run([
                "settings", "put", "secure", "mock_location", "1"
            ], check=False, capture_output=True)
            
            # Enable location services
            subprocess.run([
                "settings", "put", "secure", "location_providers_allowed", 
                "+gps,+network"
            ], check=False, capture_output=True)
            
            return True
        except Exception as e:
            print(f"Error injecting system location: {e}")
            return False
    
    def start_gps_service(self):
        """Start GPS service thread"""
        self.running = True
        
        def gps_loop():
            while self.running:
                try:
                    # Generate NMEA sentence
                    nmea = self.generate_nmea_sentence()
                    
                    # Write to GPS device (if available)
                    try:
                        with open("/dev/ttyGPS0", "w") as gps_dev:
                            gps_dev.write(nmea + "\n")
                    except:
                        pass  # GPS device not available
                    
                    # Inject into system location services
                    self.inject_location_system()
                    
                    # Write location to shared file for other processes
                    location_data = {
                        "latitude": self.latitude,
                        "longitude": self.longitude,
                        "altitude": self.altitude,
                        "accuracy": self.accuracy,
                        "speed": self.speed,
                        "bearing": self.bearing,
                        "timestamp": int(time.time() * 1000),
                        "provider": "gps"
                    }
                    
                    with open("/data/local/tmp/current_location.json", "w") as f:
                        json.dump(location_data, f)
                    
                    time.sleep(1)  # Update every second
                    
                except Exception as e:
                    print(f"GPS service error: {e}")
                    time.sleep(5)  # Wait before retrying
        
        threading.Thread(target=gps_loop, daemon=True).start()
    
    def create_socket_server(self):
        """Create socket server for external control"""
        def socket_handler():
            try:
                # Remove existing socket
                try:
                    import os
                    os.unlink(self.socket_path)
                except:
                    pass
                
                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                server.bind(self.socket_path)
                server.listen(1)
                
                while self.running:
                    try:
                        client, addr = server.accept()
                        data = client.recv(1024).decode()
                        
                        if data.startswith("SET_LOCATION"):
                            parts = data.strip().split()
                            if len(parts) >= 3:
                                lat = float(parts[1])
                                lon = float(parts[2])
                                alt = float(parts[3]) if len(parts) > 3 else self.altitude
                                self.set_location(lat, lon, alt)
                                client.send(b"OK\n")
                            else:
                                client.send(b"ERROR: Invalid format\n")
                        elif data.startswith("GET_LOCATION"):
                            response = f"{self.latitude},{self.longitude},{self.altitude}\n"
                            client.send(response.encode())
                        
                        client.close()
                    except Exception as e:
                        print(f"Socket error: {e}")
                        
            except Exception as e:
                print(f"Socket server error: {e}")
        
        threading.Thread(target=socket_handler, daemon=True).start()
    
    def run(self):
        """Start the mock GPS provider"""
        print(f"Starting Mock GPS Provider at {self.latitude}, {self.longitude}")
        
        self.start_gps_service()
        self.create_socket_server()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the GPS provider"""
        self.running = False
        print("Mock GPS Provider stopped")

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    lat = float(sys.argv[1]) if len(sys.argv) > 1 else 40.7128
    lon = float(sys.argv[2]) if len(sys.argv) > 2 else -74.0060
    alt = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    accuracy = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
    
    provider = MockGPSProvider(lat, lon, alt, accuracy)
    provider.run()
EOF
    
    chmod 755 "$service_dir/mock_gps_provider.py"
    
    log "Mock GPS provider service created"
}

# Create GPS control utilities
create_gps_utilities() {
    log "Creating GPS control utilities..."
    
    # Create location setter script
    cat > /system/bin/set-location << 'EOF'
#!/system/bin/sh

if [ $# -lt 2 ]; then
    echo "Usage: set-location <latitude> <longitude> [altitude] [accuracy]"
    echo "Example: set-location 40.7128 -74.0060 10.0 5.0"
    exit 1
fi

LAT="$1"
LON="$2"
ALT="${3:-10.0}"
ACC="${4:-5.0}"

# Send location to mock GPS provider
echo "SET_LOCATION $LAT $LON $ALT" | nc -U /data/local/tmp/gps_socket

# Also update system properties
setprop ro.kernel.android.gps.lat "$LAT"
setprop ro.kernel.android.gps.lon "$LON"
setprop ro.kernel.android.gps.alt "$ALT"

echo "Location set to: $LAT, $LON (altitude: $ALT, accuracy: $ACC)"
EOF
    
    chmod 755 /system/bin/set-location
    
    # Create location getter script
    cat > /system/bin/get-location << 'EOF'
#!/system/bin/sh

# Get current location from mock GPS provider
echo "GET_LOCATION" | nc -U /data/local/tmp/gps_socket 2>/dev/null || echo "GPS service not running"
EOF
    
    chmod 755 /system/bin/get-location
    
    # Create location monitoring script
    cat > /system/bin/gps-monitor << 'EOF'
#!/system/bin/sh

echo "GPS Location Monitor - Press Ctrl+C to stop"
echo "Time                | Latitude  | Longitude | Altitude | Accuracy"
echo "-------------------|-----------|-----------|----------|----------"

while true; do
    if [ -f "/data/local/tmp/current_location.json" ]; then
        LOCATION=$(cat /data/local/tmp/current_location.json)
        TIME=$(date '+%H:%M:%S')
        
        # Extract values using basic text processing
        LAT=$(echo "$LOCATION" | grep -o '"latitude": [^,]*' | cut -d: -f2 | tr -d ' ')
        LON=$(echo "$LOCATION" | grep -o '"longitude": [^,]*' | cut -d: -f2 | tr -d ' ')
        ALT=$(echo "$LOCATION" | grep -o '"altitude": [^,]*' | cut -d: -f2 | tr -d ' ')
        ACC=$(echo "$LOCATION" | grep -o '"accuracy": [^,]*' | cut -d: -f2 | tr -d ' ')
        
        printf "%8s | %9s | %9s | %8s | %8s\n" "$TIME" "$LAT" "$LON" "$ALT" "$ACC"
    else
        echo "No GPS data available"
    fi
    
    sleep 2
done
EOF
    
    chmod 755 /system/bin/gps-monitor
    
    log "GPS utilities created: set-location, get-location, gps-monitor"
}

# Setup system-level GPS hooks
setup_gps_hooks() {
    log "Setting up system-level GPS hooks..."
    
    # Create GPS provider hook for LocationManager
    local hooks_dir="/system/etc/gps-injection"
    
    cat > "$hooks_dir/location_manager_hook.py" << 'EOF'
#!/usr/bin/env python3

import json
import os
import time
from typing import Dict, Any

class LocationManagerHook:
    def __init__(self):
        self.location_file = "/data/local/tmp/current_location.json"
        self.providers = ["gps", "network", "passive", "fused"]
    
    def get_mock_location(self) -> Dict[str, Any]:
        """Get current mock location data"""
        try:
            if os.path.exists(self.location_file):
                with open(self.location_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading location file: {e}")
        
        # Return default location if file doesn't exist
        return {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "altitude": 10.0,
            "accuracy": 5.0,
            "speed": 0.0,
            "bearing": 0.0,
            "timestamp": int(time.time() * 1000),
            "provider": "gps"
        }
    
    def hook_getLastKnownLocation(self, provider: str) -> Dict[str, Any]:
        """Hook for getLastKnownLocation calls"""
        location = self.get_mock_location()
        location["provider"] = provider
        return location
    
    def hook_getCurrentLocation(self, provider: str) -> Dict[str, Any]:
        """Hook for getCurrentLocation calls"""
        location = self.get_mock_location()
        location["provider"] = provider
        return location
    
    def hook_requestLocationUpdates(self, provider: str, minTime: int, minDistance: float) -> bool:
        """Hook for requestLocationUpdates calls"""
        # Always return success
        return True
    
    def is_provider_enabled(self, provider: str) -> bool:
        """Check if location provider is enabled"""
        return provider in self.providers

# Global hook instance
location_hook = LocationManagerHook()

def getLastKnownLocation(provider):
    return location_hook.hook_getLastKnownLocation(provider)

def getCurrentLocation(provider):
    return location_hook.hook_getCurrentLocation(provider)

def requestLocationUpdates(provider, minTime, minDistance):
    return location_hook.hook_requestLocationUpdates(provider, minTime, minDistance)

def isProviderEnabled(provider):
    return location_hook.is_provider_enabled(provider)
EOF
    
    chmod 644 "$hooks_dir/location_manager_hook.py"
    
    log "GPS hooks configured for LocationManager interception"
}

# Configure location spoofing for specific apps
configure_app_location_spoofing() {
    log "Configuring app-specific location spoofing..."
    
    # Create app-specific location profiles
    local profiles_dir="/system/etc/gps-injection/app_profiles"
    mkdir -p "$profiles_dir"
    
    # Pokemon GO profile (random locations to avoid detection)
    cat > "$profiles_dir/com.nianticlabs.pokemongo.json" << 'EOF'
{
  "app_package": "com.nianticlabs.pokemongo",
  "spoofing_mode": "dynamic",
  "movement_pattern": "walking",
  "speed_limit": 10.0,
  "locations": [
    {"lat": 40.7829, "lon": -73.9654, "name": "Central Park, NY"},
    {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
    {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL"},
    {"lat": 29.7604, "lon": -95.3698, "name": "Houston, TX"}
  ],
  "update_interval": 30,
  "accuracy_variation": true
}
EOF
    
    # Banking apps profile (consistent location)
    cat > "$profiles_dir/banking_apps.json" << 'EOF'
{
  "apps": [
    "com.chase.sig.android",
    "com.bankofamerica.android",
    "com.wellsfargo.mobile.android",
    "com.paypal.android.p2pmobile"
  ],
  "spoofing_mode": "static",
  "location": {"lat": 40.7128, "lon": -74.0060, "name": "New York, NY"},
  "accuracy": 5.0,
  "consistent_location": true
}
EOF
    
    # Dating apps profile (realistic movement)
    cat > "$profiles_dir/dating_apps.json" << 'EOF'
{
  "apps": [
    "com.tinder",
    "com.bumble.app",
    "com.match.android.matchmobile"
  ],
  "spoofing_mode": "realistic",
  "movement_pattern": "urban",
  "home_location": {"lat": 40.7128, "lon": -74.0060},
  "work_location": {"lat": 40.7589, "lon": -73.9851},
  "movement_schedule": {
    "weekday": ["home", "work", "home"],
    "weekend": ["home", "social", "home"]
  }
}
EOF
    
    chmod 644 "$profiles_dir"/*.json
    
    log "App-specific location profiles configured"
}

# Start GPS injection service
start_gps_service() {
    log "Starting GPS injection service..."
    
    # Parse environment variables for initial location
    local lat="$DEFAULT_LAT"
    local lon="$DEFAULT_LON"
    local alt="$DEFAULT_ALT"
    local acc="$DEFAULT_ACCURACY"
    
    log "Initial location: $lat, $lon (altitude: $alt, accuracy: $acc)"
    
    # Start mock GPS provider in background
    python3 /system/etc/gps-injection/mock_gps_provider.py "$lat" "$lon" "$alt" "$acc" &
    
    local gps_pid=$!
    echo $gps_pid > /data/local/tmp/gps_service.pid
    
    log "GPS service started with PID: $gps_pid"
    
    # Wait for service to initialize
    sleep 3
    
    # Verify service is running
    if kill -0 $gps_pid 2>/dev/null; then
        log "GPS service is running successfully"
        return 0
    else
        log "ERROR: Failed to start GPS service"
        return 1
    fi
}

# Setup GPS service monitoring
setup_gps_monitoring() {
    log "Setting up GPS service monitoring..."
    
    # Create monitoring script
    cat > /system/bin/gps-service-monitor.sh << 'EOF'
#!/system/bin/sh

LOG_TAG="GPSMonitor"
LOG_FILE="/data/local/tmp/gps-monitor.log"
PID_FILE="/data/local/tmp/gps_service.pid"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$LOG_TAG] $1" >> "$LOG_FILE"
}

# Check if GPS service is running
check_gps_service() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # Service is running
        else
            log "GPS service not running (PID: $pid)"
            return 1  # Service is dead
        fi
    else
        log "GPS service PID file not found"
        return 1
    fi
}

# Restart GPS service if needed
restart_gps_service() {
    log "Restarting GPS service..."
    
    # Kill existing service
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        kill "$pid" 2>/dev/null || true
        rm -f "$PID_FILE"
    fi
    
    # Start new service
    /system/bin/gps-injection.sh
}

# Main monitoring loop
while true; do
    if ! check_gps_service; then
        log "GPS service check failed - restarting"
        restart_gps_service
    fi
    
    sleep 60  # Check every minute
done
EOF
    
    chmod 755 /system/bin/gps-service-monitor.sh
    
    # Start monitoring in background
    /system/bin/gps-service-monitor.sh &
    
    log "GPS service monitoring started"
}

# Main execution function
main() {
    log "GPS Injection Script v1.0"
    log "Default Location: $DEFAULT_LAT, $DEFAULT_LON"
    
    # Create required directories
    mkdir -p /data/local/tmp
    mkdir -p /system/etc/gps-injection
    
    # Setup GPS injection components
    create_mock_provider_service
    create_gps_utilities
    setup_gps_hooks
    configure_app_location_spoofing
    
    # Start GPS services
    if start_gps_service; then
        setup_gps_monitoring
        log "GPS injection setup completed successfully"
    else
        log "ERROR: Failed to setup GPS injection"
        return 1
    fi
    
    # Signal completion
    setprop sys.gps_injection.completed 1
    touch /data/local/tmp/gps-injection.done
}

# Execute main function
main "$@"

exit 0