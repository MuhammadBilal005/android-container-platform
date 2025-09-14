#!/usr/bin/env python3
"""
GPS Injection Accuracy Testing Suite
Tests GPS location spoofing accuracy and performance
"""

import asyncio
import json
import logging
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, NamedTuple
import subprocess
import requests
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeoPoint(NamedTuple):
    latitude: float
    longitude: float
    altitude: float = 0.0
    accuracy: float = 5.0

@dataclass
class GPSTestResult:
    container_id: str
    test_name: str
    expected_location: GeoPoint
    actual_location: Optional[GeoPoint]
    distance_error_meters: float
    accuracy_percentage: float
    response_time_ms: float
    injection_success: bool
    app_detection_success: bool
    timestamp: datetime
    error: Optional[str] = None

@dataclass
class MovementTestResult:
    container_id: str
    path_name: str
    waypoints: List[GeoPoint]
    actual_path: List[GeoPoint]
    total_distance_expected_m: float
    total_distance_actual_m: float
    average_speed_kmh: float
    max_deviation_m: float
    path_accuracy_percentage: float
    timing_accuracy_percentage: float
    duration_seconds: float
    timestamp: datetime

class GPSAccuracyTester:
    """Comprehensive GPS injection accuracy testing framework"""
    
    def __init__(self, container_id: str, adb_port: int = 5555):
        self.container_id = container_id
        self.adb_port = adb_port
        self.results: List[GPSTestResult] = []
        self.movement_results: List[MovementTestResult] = []
        
        # Test locations around the world for accuracy testing
        self.test_locations = {
            "new_york": GeoPoint(40.7128, -74.0060, 10.0, 5.0),
            "london": GeoPoint(51.5074, -0.1278, 35.0, 3.0),
            "tokyo": GeoPoint(35.6762, 139.6503, 40.0, 4.0),
            "sydney": GeoPoint(-33.8688, 151.2093, 25.0, 5.0),
            "dubai": GeoPoint(25.2048, 55.2708, 5.0, 3.0),
            "san_francisco": GeoPoint(37.7749, -122.4194, 52.0, 4.0),
            "paris": GeoPoint(48.8566, 2.3522, 35.0, 3.0),
            "beijing": GeoPoint(39.9042, 116.4074, 44.0, 5.0),
            "mumbai": GeoPoint(19.0760, 72.8777, 8.0, 6.0),
            "sao_paulo": GeoPoint(-23.5505, -46.6333, 760.0, 5.0)
        }
        
        # Test movement paths
        self.test_paths = {
            "manhattan_walk": [
                GeoPoint(40.7614, -73.9776, 10.0),  # Times Square
                GeoPoint(40.7505, -73.9934, 15.0),  # Herald Square  
                GeoPoint(40.7489, -73.9857, 12.0),  # Empire State Building
                GeoPoint(40.7480, -73.9857, 12.0),  # Nearby
                GeoPoint(40.7358, -74.0036, 8.0),   # Chelsea Market
            ],
            "london_drive": [
                GeoPoint(51.5074, -0.1278, 35.0),   # London Eye area
                GeoPoint(51.5007, -0.1246, 30.0),   # Westminster
                GeoPoint(51.5033, -0.1195, 25.0),   # Big Ben
                GeoPoint(51.5081, -0.0759, 45.0),   # Tower Bridge
                GeoPoint(51.5155, -0.0922, 50.0),   # St Paul's Cathedral
            ],
            "tokyo_train": [
                GeoPoint(35.6762, 139.6503, 40.0),  # Tokyo Station
                GeoPoint(35.6586, 139.7454, 35.0),  # Shibuya
                GeoPoint(35.6695, 139.7018, 38.0),  # Ginza
                GeoPoint(35.7090, 139.7319, 42.0),  # Ueno
                GeoPoint(35.6284, 139.7387, 30.0),  # Roppongi
            ]
        }
    
    def calculate_distance(self, point1: GeoPoint, point2: GeoPoint) -> float:
        """Calculate distance between two GPS points in meters using Haversine formula"""
        
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(point1.latitude)
        lon1_rad = math.radians(point1.longitude)
        lat2_rad = math.radians(point2.latitude)
        lon2_rad = math.radians(point2.longitude)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of Earth in meters
        r = 6371000
        
        # Calculate the distance
        distance = r * c
        
        # Add altitude difference if significant
        altitude_diff = abs(point2.altitude - point1.altitude)
        if altitude_diff > 1.0:
            distance = math.sqrt(distance**2 + altitude_diff**2)
        
        return distance
    
    async def inject_gps_location(self, location: GeoPoint) -> bool:
        """Inject GPS location into Android container"""
        try:
            # Use ADB to inject location
            cmd = [
                'adb', '-s', f'localhost:{self.adb_port}',
                'shell', 'am', 'broadcast',
                '-a', 'android.location.GPS_ENABLED_CHANGE',
                '--ez', 'enabled', 'true'
            ]
            subprocess.run(cmd, capture_output=True, timeout=5)
            
            # Set mock location
            location_cmd = [
                'adb', '-s', f'localhost:{self.adb_port}',
                'shell', 'am', 'broadcast',
                '-a', 'android.location.providers.gps.SET_LOCATION',
                '--ef', 'latitude', str(location.latitude),
                '--ef', 'longitude', str(location.longitude),
                '--ef', 'altitude', str(location.altitude),
                '--ef', 'accuracy', str(location.accuracy)
            ]
            
            result = subprocess.run(location_cmd, capture_output=True, text=True, timeout=10)
            
            # Also try using location service directly
            location_service_cmd = [
                'adb', '-s', f'localhost:{self.adb_port}',
                'shell', 'service', 'call', 'location', '49',
                'i32', '0',  # provider ID
                'd', str(location.latitude),
                'd', str(location.longitude), 
                'f', str(location.altitude),
                'f', str(location.accuracy),
                'i64', str(int(time.time() * 1000))  # timestamp
            ]
            
            subprocess.run(location_service_cmd, capture_output=True, timeout=10)
            
            return "error" not in result.stderr.lower()
            
        except Exception as e:
            logger.error(f"Failed to inject GPS location: {e}")
            return False
    
    async def get_current_location(self) -> Optional[GeoPoint]:
        """Get current GPS location from Android container"""
        try:
            # Try multiple methods to get location
            methods = [
                # Method 1: Using location service
                [
                    'adb', '-s', f'localhost:{self.adb_port}',
                    'shell', 'dumpsys', 'location'
                ],
                # Method 2: Using location manager
                [
                    'adb', '-s', f'localhost:{self.adb_port}',
                    'shell', 'service', 'call', 'location', '1'
                ]
            ]
            
            for method in methods:
                try:
                    result = subprocess.run(method, capture_output=True, text=True, timeout=10)
                    
                    # Parse location from output
                    if "latitude" in result.stdout.lower() and "longitude" in result.stdout.lower():
                        lines = result.stdout.split('\n')
                        lat, lon, alt = None, None, 0.0
                        
                        for line in lines:
                            if 'latitude' in line.lower():
                                try:
                                    lat = float(line.split()[-1])
                                except:
                                    pass
                            elif 'longitude' in line.lower():
                                try:
                                    lon = float(line.split()[-1])
                                except:
                                    pass
                            elif 'altitude' in line.lower():
                                try:
                                    alt = float(line.split()[-1])
                                except:
                                    pass
                        
                        if lat is not None and lon is not None:
                            return GeoPoint(lat, lon, alt, 5.0)
                
                except:
                    continue
            
            # Fallback method: Try to read from location test app
            app_result = subprocess.run([
                'adb', '-s', f'localhost:{self.adb_port}',
                'shell', 'am', 'broadcast',
                '-a', 'com.locationtest.GET_CURRENT_LOCATION'
            ], capture_output=True, text=True, timeout=10)
            
            # This would need a custom location test app to respond
            return None
            
        except Exception as e:
            logger.error(f"Failed to get current location: {e}")
            return None
    
    async def install_location_test_app(self) -> bool:
        """Install GPS testing application"""
        try:
            apk_path = "/opt/testing/gps-tester.apk"
            result = subprocess.run([
                'adb', '-s', f'localhost:{self.adb_port}',
                'install', apk_path
            ], capture_output=True, text=True, timeout=60)
            
            if "Success" in result.stdout:
                # Grant location permissions
                permissions = [
                    "android.permission.ACCESS_FINE_LOCATION",
                    "android.permission.ACCESS_COARSE_LOCATION",
                    "android.permission.ACCESS_MOCK_LOCATION"
                ]
                
                for permission in permissions:
                    subprocess.run([
                        'adb', '-s', f'localhost:{self.adb_port}',
                        'shell', 'pm', 'grant', 'com.gpstest', permission
                    ], capture_output=True, timeout=5)
                
                logger.info("GPS test app installed successfully")
                return True
            else:
                logger.warning("GPS test app not available, using system methods")
                return False
                
        except Exception as e:
            logger.error(f"Failed to install GPS test app: {e}")
            return False
    
    async def test_location_accuracy(self, location_name: str, location: GeoPoint) -> GPSTestResult:
        """Test GPS injection accuracy for a single location"""
        logger.info(f"Testing GPS accuracy for {location_name}")
        
        start_time = time.time()
        
        # Inject the location
        injection_success = await self.inject_gps_location(location)
        
        if not injection_success:
            return GPSTestResult(
                container_id=self.container_id,
                test_name=f"GPS Accuracy - {location_name}",
                expected_location=location,
                actual_location=None,
                distance_error_meters=float('inf'),
                accuracy_percentage=0.0,
                response_time_ms=(time.time() - start_time) * 1000,
                injection_success=False,
                app_detection_success=False,
                timestamp=datetime.now(),
                error="GPS injection failed"
            )
        
        # Wait for location to be set
        await asyncio.sleep(3)
        
        # Get the current location
        actual_location = await self.get_current_location()
        
        response_time_ms = (time.time() - start_time) * 1000
        
        if actual_location is None:
            return GPSTestResult(
                container_id=self.container_id,
                test_name=f"GPS Accuracy - {location_name}",
                expected_location=location,
                actual_location=None,
                distance_error_meters=float('inf'),
                accuracy_percentage=0.0,
                response_time_ms=response_time_ms,
                injection_success=injection_success,
                app_detection_success=False,
                timestamp=datetime.now(),
                error="Could not retrieve location"
            )
        
        # Calculate accuracy
        distance_error = self.calculate_distance(location, actual_location)
        
        # Accuracy percentage (inverse of error, with expected accuracy as baseline)
        expected_accuracy_m = location.accuracy
        accuracy_percentage = max(0, 100 - (distance_error / expected_accuracy_m * 100))
        
        # Test if apps can detect the location
        app_detection_success = await self.test_app_location_detection(location)
        
        return GPSTestResult(
            container_id=self.container_id,
            test_name=f"GPS Accuracy - {location_name}",
            expected_location=location,
            actual_location=actual_location,
            distance_error_meters=distance_error,
            accuracy_percentage=accuracy_percentage,
            response_time_ms=response_time_ms,
            injection_success=injection_success,
            app_detection_success=app_detection_success,
            timestamp=datetime.now()
        )
    
    async def test_app_location_detection(self, location: GeoPoint) -> bool:
        """Test if apps can successfully detect the injected location"""
        try:
            # Launch a location-aware app (like Maps or a location test app)
            subprocess.run([
                'adb', '-s', f'localhost:{self.adb_port}',
                'shell', 'am', 'start',
                '-a', 'android.intent.action.VIEW',
                '-d', f'geo:{location.latitude},{location.longitude}'
            ], capture_output=True, timeout=10)
            
            await asyncio.sleep(5)
            
            # Check if the app shows the correct location
            # This is simplified - in practice, would need OCR or UI automation
            logcat_result = subprocess.run([
                'adb', '-s', f'localhost:{self.adb_port}',
                'shell', 'logcat', '-d', '-s', 'LocationManager:*'
            ], capture_output=True, text=True, timeout=5)
            
            # Look for location updates in logs
            return "location" in logcat_result.stdout.lower()
            
        except Exception as e:
            logger.error(f"App location detection test failed: {e}")
            return False
    
    async def test_movement_path(self, path_name: str, waypoints: List[GeoPoint], 
                                speed_kmh: float = 30.0) -> MovementTestResult:
        """Test GPS movement simulation along a path"""
        logger.info(f"Testing movement path: {path_name}")
        
        start_time = time.time()
        actual_path = []
        
        # Calculate expected total distance
        expected_distance = 0.0
        for i in range(len(waypoints) - 1):
            expected_distance += self.calculate_distance(waypoints[i], waypoints[i + 1])
        
        # Calculate time per segment based on speed
        time_per_meter = 1.0 / (speed_kmh * 1000 / 3600)  # seconds per meter
        
        try:
            for i, waypoint in enumerate(waypoints):
                logger.info(f"Moving to waypoint {i + 1}/{len(waypoints)}")
                
                # Inject location
                injection_success = await self.inject_gps_location(waypoint)
                if not injection_success:
                    logger.warning(f"Failed to inject waypoint {i + 1}")
                    continue
                
                # Wait for location to be set and get actual location
                await asyncio.sleep(2)
                actual_location = await self.get_current_location()
                
                if actual_location:
                    actual_path.append(actual_location)
                
                # Calculate delay to next waypoint based on distance and speed
                if i < len(waypoints) - 1:
                    segment_distance = self.calculate_distance(waypoints[i], waypoints[i + 1])
                    delay_time = segment_distance * time_per_meter
                    await asyncio.sleep(min(delay_time, 30))  # Cap at 30 seconds per segment
        
        except Exception as e:
            logger.error(f"Movement path test failed: {e}")
        
        # Calculate actual total distance
        actual_distance = 0.0
        for i in range(len(actual_path) - 1):
            actual_distance += self.calculate_distance(actual_path[i], actual_path[i + 1])
        
        # Calculate maximum deviation from expected path
        max_deviation = 0.0
        for i, expected_point in enumerate(waypoints):
            if i < len(actual_path):
                deviation = self.calculate_distance(expected_point, actual_path[i])
                max_deviation = max(max_deviation, deviation)
        
        # Calculate accuracy percentages
        distance_accuracy = 100.0
        if expected_distance > 0:
            distance_accuracy = max(0, 100 - abs(expected_distance - actual_distance) / expected_distance * 100)
        
        duration = time.time() - start_time
        expected_duration = expected_distance * time_per_meter
        timing_accuracy = max(0, 100 - abs(duration - expected_duration) / expected_duration * 100)
        
        path_accuracy = max(0, 100 - max_deviation / 50.0 * 100)  # 50m baseline for path accuracy
        
        return MovementTestResult(
            container_id=self.container_id,
            path_name=path_name,
            waypoints=waypoints,
            actual_path=actual_path,
            total_distance_expected_m=expected_distance,
            total_distance_actual_m=actual_distance,
            average_speed_kmh=(actual_distance / 1000) / (duration / 3600) if duration > 0 else 0,
            max_deviation_m=max_deviation,
            path_accuracy_percentage=path_accuracy,
            timing_accuracy_percentage=timing_accuracy,
            duration_seconds=duration,
            timestamp=datetime.now()
        )
    
    async def run_comprehensive_gps_test(self) -> Tuple[List[GPSTestResult], List[MovementTestResult]]:
        """Run comprehensive GPS accuracy testing"""
        logger.info(f"Starting comprehensive GPS testing for {self.container_id}")
        
        # Install location test app if available
        await self.install_location_test_app()
        
        # Test static location accuracy
        logger.info("Testing static location accuracy...")
        for location_name, location in self.test_locations.items():
            try:
                result = await self.test_location_accuracy(location_name, location)
                self.results.append(result)
                
                # Brief pause between tests
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Failed to test location {location_name}: {e}")
                error_result = GPSTestResult(
                    container_id=self.container_id,
                    test_name=f"GPS Accuracy - {location_name}",
                    expected_location=location,
                    actual_location=None,
                    distance_error_meters=float('inf'),
                    accuracy_percentage=0.0,
                    response_time_ms=0.0,
                    injection_success=False,
                    app_detection_success=False,
                    timestamp=datetime.now(),
                    error=str(e)
                )
                self.results.append(error_result)
        
        # Test movement paths
        logger.info("Testing movement path accuracy...")
        for path_name, waypoints in self.test_paths.items():
            try:
                result = await self.test_movement_path(path_name, waypoints)
                self.movement_results.append(result)
                
                # Pause between path tests
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Failed to test path {path_name}: {e}")
        
        return self.results, self.movement_results
    
    def generate_gps_report(self) -> Dict:
        """Generate comprehensive GPS accuracy report"""
        if not self.results and not self.movement_results:
            return {"error": "No GPS test results available"}
        
        report = {
            "container_id": self.container_id,
            "test_timestamp": datetime.now().isoformat(),
            "static_location_tests": {
                "total_tests": len(self.results),
                "successful_injections": sum(1 for r in self.results if r.injection_success),
                "successful_detections": sum(1 for r in self.results if r.app_detection_success),
                "average_accuracy_percentage": sum(r.accuracy_percentage for r in self.results) / len(self.results) if self.results else 0,
                "average_distance_error_m": sum(r.distance_error_meters for r in self.results if r.distance_error_meters != float('inf')) / len([r for r in self.results if r.distance_error_meters != float('inf')]) if self.results else 0,
                "average_response_time_ms": sum(r.response_time_ms for r in self.results) / len(self.results) if self.results else 0,
                "test_results": []
            },
            "movement_path_tests": {
                "total_tests": len(self.movement_results),
                "average_path_accuracy": sum(r.path_accuracy_percentage for r in self.movement_results) / len(self.movement_results) if self.movement_results else 0,
                "average_timing_accuracy": sum(r.timing_accuracy_percentage for r in self.movement_results) / len(self.movement_results) if self.movement_results else 0,
                "average_max_deviation_m": sum(r.max_deviation_m for r in self.movement_results) / len(self.movement_results) if self.movement_results else 0,
                "test_results": []
            }
        }
        
        # Add static location test details
        for result in self.results:
            report["static_location_tests"]["test_results"].append({
                "test_name": result.test_name,
                "expected_location": {
                    "latitude": result.expected_location.latitude,
                    "longitude": result.expected_location.longitude,
                    "altitude": result.expected_location.altitude
                },
                "actual_location": {
                    "latitude": result.actual_location.latitude,
                    "longitude": result.actual_location.longitude,
                    "altitude": result.actual_location.altitude
                } if result.actual_location else None,
                "distance_error_meters": result.distance_error_meters,
                "accuracy_percentage": result.accuracy_percentage,
                "response_time_ms": result.response_time_ms,
                "injection_success": result.injection_success,
                "app_detection_success": result.app_detection_success,
                "timestamp": result.timestamp.isoformat(),
                "error": result.error
            })
        
        # Add movement path test details
        for result in self.movement_results:
            report["movement_path_tests"]["test_results"].append({
                "path_name": result.path_name,
                "waypoint_count": len(result.waypoints),
                "actual_waypoint_count": len(result.actual_path),
                "expected_distance_m": result.total_distance_expected_m,
                "actual_distance_m": result.total_distance_actual_m,
                "average_speed_kmh": result.average_speed_kmh,
                "max_deviation_m": result.max_deviation_m,
                "path_accuracy_percentage": result.path_accuracy_percentage,
                "timing_accuracy_percentage": result.timing_accuracy_percentage,
                "duration_seconds": result.duration_seconds,
                "timestamp": result.timestamp.isoformat()
            })
        
        # Overall GPS system performance
        overall_accuracy = 0.0
        if self.results:
            static_accuracy = sum(r.accuracy_percentage for r in self.results) / len(self.results)
            movement_accuracy = sum(r.path_accuracy_percentage for r in self.movement_results) / len(self.movement_results) if self.movement_results else 0
            overall_accuracy = (static_accuracy + movement_accuracy) / 2 if self.movement_results else static_accuracy
        
        report["overall_gps_performance"] = {
            "overall_accuracy_percentage": overall_accuracy,
            "injection_success_rate": (sum(1 for r in self.results if r.injection_success) / len(self.results)) * 100 if self.results else 0,
            "detection_success_rate": (sum(1 for r in self.results if r.app_detection_success) / len(self.results)) * 100 if self.results else 0,
            "recommendation": "Excellent" if overall_accuracy > 90 else "Good" if overall_accuracy > 75 else "Needs Improvement"
        }
        
        return report

async def main():
    """Main test execution function"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python gps_accuracy_test.py <container_id>")
        sys.exit(1)
    
    container_id = sys.argv[1]
    tester = GPSAccuracyTester(container_id)
    
    static_results, movement_results = await tester.run_comprehensive_gps_test()
    report = tester.generate_gps_report()
    
    print(json.dumps(report, indent=2))
    
    # Save report to file
    with open(f"/tmp/gps_accuracy_report_{container_id}_{int(time.time())}.json", 'w') as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())