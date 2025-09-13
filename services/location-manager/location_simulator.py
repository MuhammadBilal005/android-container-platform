import asyncio
import math
import random
import time
import uuid
from typing import Dict, List, Optional, Tuple
import geopy.distance
import numpy as np

from gps_injector import GPSInjector

class LocationSimulator:
    """Advanced location simulation with realistic movement patterns"""
    
    def __init__(self, instance_id: str):
        self.instance_id = instance_id
        self.injector = GPSInjector(instance_id)
        self.is_running = False
        self.current_route = None
        self.simulation_task = None
    
    async def create_route(self, waypoints: List[Tuple[float, float]], 
                          speed_profile: Optional[Dict[str, float]] = None,
                          route_name: str = "default") -> str:
        """Create a route with waypoints and speed profile"""
        
        route_id = str(uuid.uuid4())
        
        # Default speed profile if none provided
        if not speed_profile:
            speed_profile = {
                "walking": 5.0,      # 5 km/h
                "cycling": 20.0,     # 20 km/h  
                "driving": 50.0,     # 50 km/h
                "highway": 100.0     # 100 km/h
            }
        
        # Calculate distances between waypoints
        route_segments = []
        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]
            distance = geopy.distance.distance(start, end).kilometers
            
            # Determine speed based on distance and area type
            if distance > 50:  # Long distance - highway
                speed = speed_profile.get("highway", 100.0)
            elif distance > 10:  # Medium distance - driving
                speed = speed_profile.get("driving", 50.0)
            elif distance > 2:   # Short distance - cycling
                speed = speed_profile.get("cycling", 20.0)
            else:                # Very short - walking
                speed = speed_profile.get("walking", 5.0)
            
            route_segments.append({
                "start": start,
                "end": end,
                "distance_km": distance,
                "speed_kmh": speed,
                "duration_hours": distance / speed if speed > 0 else 0
            })
        
        self.current_route = {
            "id": route_id,
            "name": route_name,
            "waypoints": waypoints,
            "segments": route_segments,
            "speed_profile": speed_profile,
            "total_distance": sum(seg["distance_km"] for seg in route_segments),
            "total_duration": sum(seg["duration_hours"] for seg in route_segments)
        }
        
        return route_id
    
    async def start_simulation(self, route_id: str, update_interval: float = 1.0):
        """Start route simulation with specified update interval"""
        
        if not self.current_route or self.current_route["id"] != route_id:
            raise ValueError("Route not found or not loaded")
        
        self.is_running = True
        self.simulation_task = asyncio.create_task(
            self._simulate_movement(update_interval)
        )
    
    async def stop(self):
        """Stop the current simulation"""
        self.is_running = False
        if self.simulation_task:
            self.simulation_task.cancel()
            try:
                await self.simulation_task
            except asyncio.CancelledError:
                pass
    
    async def _simulate_movement(self, update_interval: float):
        """Main simulation loop"""
        
        route = self.current_route
        start_time = time.time()
        
        try:
            for segment_idx, segment in enumerate(route["segments"]):
                if not self.is_running:
                    break
                
                await self._simulate_segment(segment, update_interval, segment_idx)
            
            # Simulation completed
            total_time = time.time() - start_time
            print(f"Route simulation completed in {total_time:.1f} seconds")
            
        except asyncio.CancelledError:
            print("Route simulation cancelled")
        except Exception as e:
            print(f"Route simulation error: {e}")
        finally:
            self.is_running = False
    
    async def _simulate_segment(self, segment: Dict, update_interval: float, segment_idx: int):
        """Simulate movement along a route segment"""
        
        start_lat, start_lng = segment["start"]
        end_lat, end_lng = segment["end"]
        distance_km = segment["distance_km"]
        speed_kmh = segment["speed_kmh"]
        
        # Calculate number of steps based on distance and update interval
        duration_seconds = (distance_km / speed_kmh) * 3600
        num_steps = max(int(duration_seconds / update_interval), 1)
        
        # Add realistic movement variations
        base_speed = speed_kmh
        
        for step in range(num_steps + 1):
            if not self.is_running:
                break
            
            # Calculate progress along segment (0 to 1)
            progress = step / num_steps
            
            # Add realistic speed variations
            speed_variation = self._get_speed_variation(base_speed, progress, segment_idx)
            current_speed = base_speed * speed_variation
            
            # Calculate current position with some randomness for realism
            current_lat, current_lng = self._interpolate_position(
                start_lat, start_lng, end_lat, end_lng, progress
            )
            
            # Add small random variations to simulate GPS noise
            current_lat += random.uniform(-0.0001, 0.0001)
            current_lng += random.uniform(-0.0001, 0.0001)
            
            # Calculate bearing
            bearing = self._calculate_bearing(start_lat, start_lng, end_lat, end_lng)
            
            # Add bearing variation for realistic movement
            bearing += random.uniform(-5, 5)
            bearing = bearing % 360
            
            # Calculate accuracy based on speed and environment
            accuracy = self._calculate_accuracy(current_speed, segment_idx)
            
            # Calculate altitude with realistic variations
            altitude = self._calculate_altitude(progress, segment_idx)
            
            # Inject location
            success = await self.injector.inject_location(
                latitude=current_lat,
                longitude=current_lng,
                altitude=altitude,
                accuracy=accuracy,
                speed=current_speed / 3.6,  # Convert km/h to m/s
                bearing=bearing,
                provider="gps"
            )
            
            if not success:
                print(f"Failed to inject location at step {step}")
            
            # Wait for next update
            await asyncio.sleep(update_interval)
    
    def _interpolate_position(self, start_lat: float, start_lng: float,
                            end_lat: float, end_lng: float, progress: float) -> Tuple[float, float]:
        """Interpolate position between two points with realistic path"""
        
        # Simple linear interpolation with small curve for realism
        lat_diff = end_lat - start_lat
        lng_diff = end_lng - start_lng
        
        # Add slight curve to make movement more realistic
        curve_factor = 0.0001 * math.sin(progress * math.pi)
        
        current_lat = start_lat + (lat_diff * progress) + curve_factor
        current_lng = start_lng + (lng_diff * progress) + curve_factor
        
        return current_lat, current_lng
    
    def _calculate_bearing(self, start_lat: float, start_lng: float,
                          end_lat: float, end_lng: float) -> float:
        """Calculate bearing between two points"""
        
        start_lat_rad = math.radians(start_lat)
        start_lng_rad = math.radians(start_lng)
        end_lat_rad = math.radians(end_lat)
        end_lng_rad = math.radians(end_lng)
        
        delta_lng = end_lng_rad - start_lng_rad
        
        y = math.sin(delta_lng) * math.cos(end_lat_rad)
        x = (math.cos(start_lat_rad) * math.sin(end_lat_rad) -
             math.sin(start_lat_rad) * math.cos(end_lat_rad) * math.cos(delta_lng))
        
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    def _get_speed_variation(self, base_speed: float, progress: float, segment_idx: int) -> float:
        """Get realistic speed variation based on conditions"""
        
        # Base variation for realistic movement
        variation = 1.0
        
        # Speed up/slow down at beginning and end of segments
        if progress < 0.1:  # Accelerating
            variation = 0.7 + (progress * 3.0)
        elif progress > 0.9:  # Decelerating
            variation = 0.7 + ((1.0 - progress) * 3.0)
        
        # Random variations for traffic, terrain, etc.
        if base_speed > 30:  # Driving speeds
            variation *= random.uniform(0.8, 1.2)  # Traffic variations
        elif base_speed > 10:  # Cycling speeds
            variation *= random.uniform(0.9, 1.1)  # Terrain variations
        else:  # Walking speeds
            variation *= random.uniform(0.95, 1.05)  # Small variations
        
        # Occasional stops or slow-downs
        if random.random() < 0.05:  # 5% chance
            variation *= 0.3  # Significant slowdown
        
        return max(0.1, min(2.0, variation))  # Clamp between 0.1x and 2.0x
    
    def _calculate_accuracy(self, speed: float, segment_idx: int) -> float:
        """Calculate GPS accuracy based on conditions"""
        
        base_accuracy = 10.0
        
        # Speed affects accuracy
        if speed > 50:  # High speed
            base_accuracy = 15.0
        elif speed > 20:  # Medium speed
            base_accuracy = 8.0
        else:  # Low speed
            base_accuracy = 5.0
        
        # Add random variation
        accuracy = base_accuracy * random.uniform(0.8, 1.5)
        
        # Occasional poor GPS conditions
        if random.random() < 0.1:  # 10% chance
            accuracy *= random.uniform(2.0, 5.0)
        
        return min(50.0, accuracy)  # Cap at 50m
    
    def _calculate_altitude(self, progress: float, segment_idx: int) -> float:
        """Calculate realistic altitude variations"""
        
        # Base altitude with terrain simulation
        base_altitude = 50.0 + (segment_idx * 10)  # Gradual elevation change
        
        # Add terrain variations
        terrain_variation = 20.0 * math.sin(progress * math.pi * 2)
        
        # Random small variations
        random_variation = random.uniform(-5.0, 5.0)
        
        altitude = base_altitude + terrain_variation + random_variation
        
        return max(0.0, altitude)  # Don't go below sea level
    
    async def create_realistic_route(self, start_location: Tuple[float, float],
                                   destination: Tuple[float, float],
                                   transport_mode: str = "driving") -> str:
        """Create a realistic route between two points"""
        
        start_lat, start_lng = start_location
        dest_lat, dest_lng = destination
        
        # Calculate direct distance
        direct_distance = geopy.distance.distance(start_location, destination).kilometers
        
        # Generate intermediate waypoints for realistic routing
        waypoints = [start_location]
        
        # Add waypoints based on distance and transport mode
        if direct_distance > 5:  # Add waypoints for longer routes
            num_waypoints = min(int(direct_distance / 5), 10)
            
            for i in range(1, num_waypoints):
                progress = i / num_waypoints
                
                # Base interpolation
                inter_lat = start_lat + (dest_lat - start_lat) * progress
                inter_lng = start_lng + (dest_lng - start_lng) * progress
                
                # Add road-like deviations
                deviation = 0.01 * math.sin(progress * math.pi * 3)
                inter_lat += deviation
                inter_lng += deviation
                
                waypoints.append((inter_lat, inter_lng))
        
        waypoints.append(destination)
        
        # Set speed profile based on transport mode
        speed_profiles = {
            "walking": {"walking": 5.0},
            "cycling": {"cycling": 20.0, "walking": 5.0},
            "driving": {"driving": 50.0, "highway": 80.0, "cycling": 20.0},
            "highway": {"highway": 120.0, "driving": 60.0}
        }
        
        speed_profile = speed_profiles.get(transport_mode, speed_profiles["driving"])
        
        return await self.create_route(waypoints, speed_profile, f"{transport_mode}_route")
    
    async def simulate_idle_movement(self, center: Tuple[float, float],
                                   radius_meters: float = 100,
                                   duration_minutes: float = 60):
        """Simulate small movements around a central location (like being in a building)"""
        
        center_lat, center_lng = center
        
        # Generate small random movements within radius
        waypoints = [center]
        
        # Create small movements every few minutes
        movements = int(duration_minutes / 5)  # Movement every 5 minutes
        
        for _ in range(movements):
            # Random angle and distance within radius
            angle = random.uniform(0, 2 * math.pi)
            distance_m = random.uniform(0, radius_meters)
            
            # Convert to coordinate offset
            lat_offset = (distance_m * math.cos(angle)) / 111000  # Rough conversion
            lng_offset = (distance_m * math.sin(angle)) / (111000 * math.cos(math.radians(center_lat)))
            
            new_lat = center_lat + lat_offset
            new_lng = center_lng + lng_offset
            waypoints.append((new_lat, new_lng))
        
        # Return to center
        waypoints.append(center)
        
        # Very slow movement (indoor movement)
        speed_profile = {"walking": 2.0}
        
        route_id = await self.create_route(waypoints, speed_profile, "idle_movement")
        await self.start_simulation(route_id, update_interval=30.0)  # Update every 30 seconds
        
        return route_id