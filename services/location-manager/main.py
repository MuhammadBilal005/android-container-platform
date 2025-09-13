import asyncio
import json
import math
import os
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel
import redis.asyncio as redis
from sqlalchemy import create_engine, Column, String, DateTime, Float, Boolean, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import geopy.distance
import numpy as np

from gps_injector import GPSInjector
from location_simulator import LocationSimulator

app = FastAPI(title="Location Manager Service", version="1.0.0")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://acp_user:acp_secure_password@localhost:5432/android_platform")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
Base = declarative_base()

# Redis client
redis_client = None

# Active location simulations
active_simulations: Dict[str, LocationSimulator] = {}

class LocationData(Base):
    __tablename__ = "location_data"
    
    id = Column(String, primary_key=True)
    instance_id = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, default=0.0)
    accuracy = Column(Float, default=10.0)
    speed = Column(Float, default=0.0)
    bearing = Column(Float, default=0.0)
    provider = Column(String, default="gps")
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_mock = Column(Boolean, default=False)

class LocationRoute(Base):
    __tablename__ = "location_routes"
    
    id = Column(String, primary_key=True)
    instance_id = Column(String, nullable=False)
    route_name = Column(String, nullable=False)
    waypoints = Column(Text, nullable=False)  # JSON string of coordinates
    speed_profile = Column(Text, nullable=True)  # JSON string of speed data
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=False)

class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    altitude: Optional[float] = 0.0
    accuracy: Optional[float] = 10.0
    speed: Optional[float] = 0.0
    bearing: Optional[float] = 0.0
    provider: Optional[str] = "gps"

class RouteRequest(BaseModel):
    waypoints: List[Tuple[float, float]]
    speed_profile: Optional[Dict[str, float]] = None
    route_name: Optional[str] = "default"

class LocationResponse(BaseModel):
    instance_id: str
    latitude: float
    longitude: float
    altitude: float
    accuracy: float
    speed: float
    bearing: float
    provider: str
    timestamp: datetime
    injection_method: str

@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = redis.from_url(REDIS_URL)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown") 
async def shutdown():
    if redis_client:
        await redis_client.close()
    
    # Stop all active simulations
    for sim in active_simulations.values():
        await sim.stop()

@app.post("/location/{instance_id}", response_model=LocationResponse)
async def set_location(instance_id: str, location: LocationRequest):
    """Set static location for an Android instance"""
    
    try:
        # Inject location into Android instance
        injector = GPSInjector(instance_id)
        success = await injector.inject_location(
            latitude=location.latitude,
            longitude=location.longitude,
            altitude=location.altitude,
            accuracy=location.accuracy,
            speed=location.speed,
            bearing=location.bearing,
            provider=location.provider
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to inject location")
        
        # Store in database
        location_id = f"{instance_id}_{int(time.time())}"
        async with AsyncSession(engine) as session:
            location_data = LocationData(
                id=location_id,
                instance_id=instance_id,
                latitude=location.latitude,
                longitude=location.longitude,
                altitude=location.altitude,
                accuracy=location.accuracy,
                speed=location.speed,
                bearing=location.bearing,
                provider=location.provider,
                is_mock=False  # System-level injection, not mock
            )
            session.add(location_data)
            await session.commit()
        
        # Cache current location
        await redis_client.setex(
            f"location:{instance_id}", 
            300,  # 5 minutes
            json.dumps({
                "latitude": location.latitude,
                "longitude": location.longitude,
                "altitude": location.altitude,
                "accuracy": location.accuracy,
                "speed": location.speed,
                "bearing": location.bearing,
                "provider": location.provider,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        
        return LocationResponse(
            instance_id=instance_id,
            latitude=location.latitude,
            longitude=location.longitude,
            altitude=location.altitude,
            accuracy=location.accuracy,
            speed=location.speed,
            bearing=location.bearing,
            provider=location.provider,
            timestamp=datetime.utcnow(),
            injection_method="system_level"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Location injection failed: {str(e)}")

@app.post("/route/{instance_id}")
async def start_route_simulation(instance_id: str, route: RouteRequest):
    """Start route-based location simulation"""
    
    try:
        # Stop any existing simulation
        if instance_id in active_simulations:
            await active_simulations[instance_id].stop()
            del active_simulations[instance_id]
        
        # Create new route simulation
        simulator = LocationSimulator(instance_id)
        route_id = await simulator.create_route(
            waypoints=route.waypoints,
            speed_profile=route.speed_profile,
            route_name=route.route_name
        )
        
        # Store route in database
        async with AsyncSession(engine) as session:
            location_route = LocationRoute(
                id=route_id,
                instance_id=instance_id,
                route_name=route.route_name,
                waypoints=json.dumps(route.waypoints),
                speed_profile=json.dumps(route.speed_profile) if route.speed_profile else None,
                is_active=True
            )
            session.add(location_route)
            await session.commit()
        
        # Start simulation
        await simulator.start_simulation(route_id)
        active_simulations[instance_id] = simulator
        
        return {
            "status": "started",
            "route_id": route_id,
            "instance_id": instance_id,
            "waypoints_count": len(route.waypoints)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route simulation failed: {str(e)}")

@app.post("/route/{instance_id}/stop")
async def stop_route_simulation(instance_id: str):
    """Stop active route simulation"""
    
    if instance_id not in active_simulations:
        raise HTTPException(status_code=404, detail="No active simulation found")
    
    try:
        await active_simulations[instance_id].stop()
        del active_simulations[instance_id]
        
        # Update database
        async with AsyncSession(engine) as session:
            # Mark all routes as inactive
            routes = await session.execute(
                session.query(LocationRoute)
                .filter(LocationRoute.instance_id == instance_id, LocationRoute.is_active == True)
            )
            for route in routes.scalars():
                route.is_active = False
            await session.commit()
        
        return {"status": "stopped", "instance_id": instance_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop simulation: {str(e)}")

@app.get("/location/{instance_id}")
async def get_current_location(instance_id: str):
    """Get current location of Android instance"""
    
    # Try cache first
    cached_location = await redis_client.get(f"location:{instance_id}")
    if cached_location:
        return json.loads(cached_location)
    
    # Fetch from database
    async with AsyncSession(engine) as session:
        location = await session.execute(
            session.query(LocationData)
            .filter(LocationData.instance_id == instance_id)
            .order_by(LocationData.timestamp.desc())
            .limit(1)
        )
        location = location.scalar_one_or_none()
        
        if not location:
            raise HTTPException(status_code=404, detail="No location data found")
        
        return {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "altitude": location.altitude,
            "accuracy": location.accuracy,
            "speed": location.speed,
            "bearing": location.bearing,
            "provider": location.provider,
            "timestamp": location.timestamp
        }

@app.get("/location/{instance_id}/history")
async def get_location_history(instance_id: str, limit: int = 100):
    """Get location history for Android instance"""
    
    async with AsyncSession(engine) as session:
        locations = await session.execute(
            session.query(LocationData)
            .filter(LocationData.instance_id == instance_id)
            .order_by(LocationData.timestamp.desc())
            .limit(limit)
        )
        
        return {
            "instance_id": instance_id,
            "locations": [
                {
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "altitude": loc.altitude,
                    "accuracy": loc.accuracy,
                    "speed": loc.speed,
                    "bearing": loc.bearing,
                    "provider": loc.provider,
                    "timestamp": loc.timestamp,
                    "is_mock": loc.is_mock
                }
                for loc in locations.scalars()
            ]
        }

@app.get("/routes/{instance_id}")
async def get_routes(instance_id: str):
    """Get all routes for an Android instance"""
    
    async with AsyncSession(engine) as session:
        routes = await session.execute(
            session.query(LocationRoute)
            .filter(LocationRoute.instance_id == instance_id)
            .order_by(LocationRoute.created_at.desc())
        )
        
        return {
            "instance_id": instance_id,
            "routes": [
                {
                    "id": route.id,
                    "route_name": route.route_name,
                    "waypoints": json.loads(route.waypoints),
                    "speed_profile": json.loads(route.speed_profile) if route.speed_profile else None,
                    "created_at": route.created_at,
                    "is_active": route.is_active
                }
                for route in routes.scalars()
            ]
        }

@app.websocket("/location/{instance_id}/stream")
async def location_stream(websocket: WebSocket, instance_id: str):
    """WebSocket endpoint for real-time location updates"""
    
    await websocket.accept()
    
    try:
        while True:
            # Get current location
            location_data = await redis_client.get(f"location:{instance_id}")
            if location_data:
                await websocket.send_text(location_data)
            
            # Wait for next update
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        pass

@app.post("/location/{instance_id}/random")
async def set_random_location(instance_id: str, 
                             center_lat: float = 40.7128, 
                             center_lng: float = -74.0060,
                             radius_km: float = 10.0):
    """Set random location within specified radius"""
    
    # Generate random location within radius
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, radius_km)
    
    # Calculate new coordinates
    origin = geopy.Point(center_lat, center_lng)
    destination = geopy.distance.distance(kilometers=distance).destination(origin, math.degrees(angle))
    
    location_request = LocationRequest(
        latitude=destination.latitude,
        longitude=destination.longitude,
        altitude=random.uniform(0, 100),
        accuracy=random.uniform(5, 15),
        speed=0.0,
        bearing=random.uniform(0, 360)
    )
    
    return await set_location(instance_id, location_request)

@app.post("/location/{instance_id}/city")
async def set_city_location(instance_id: str, city: str, country: str = "US"):
    """Set location to a specific city"""
    
    # City coordinates database (simplified)
    city_coords = {
        "new_york": (40.7128, -74.0060),
        "los_angeles": (34.0522, -118.2437),
        "chicago": (41.8781, -87.6298),
        "houston": (29.7604, -95.3698),
        "london": (51.5074, -0.1278),
        "paris": (48.8566, 2.3522),
        "tokyo": (35.6762, 139.6503),
        "sydney": (-33.8688, 151.2093),
        "dubai": (25.2048, 55.2708),
        "singapore": (1.3521, 103.8198)
    }
    
    city_key = city.lower().replace(" ", "_")
    if city_key not in city_coords:
        raise HTTPException(status_code=400, detail=f"City '{city}' not found")
    
    lat, lng = city_coords[city_key]
    
    # Add some randomness to avoid exact same coordinates
    lat += random.uniform(-0.01, 0.01)
    lng += random.uniform(-0.01, 0.01)
    
    location_request = LocationRequest(
        latitude=lat,
        longitude=lng,
        altitude=random.uniform(0, 50),
        accuracy=random.uniform(8, 12),
        speed=0.0,
        bearing=random.uniform(0, 360)
    )
    
    return await set_location(instance_id, location_request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)