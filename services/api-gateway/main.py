import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import httpx
from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib

from auth import AuthManager
from service_client import ServiceClient

app = FastAPI(
    title="Android Container Platform API Gateway",
    version="1.0.0",
    description="Central API Gateway for the Android Container Platform"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3001"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.local"]
)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://acp_user:acp_secure_password@localhost:5432/android_platform")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")
JWT_ALGORITHM = "HS256"

# Service URLs
IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL", "http://identity-manager:8001")
LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL", "http://location-manager:8002")
NETWORK_SERVICE_URL = os.getenv("NETWORK_SERVICE_URL", "http://network-manager:8003")
LIFECYCLE_SERVICE_URL = os.getenv("LIFECYCLE_SERVICE_URL", "http://lifecycle-manager:8004")

engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
Base = declarative_base()

# Redis client
redis_client = None

# Components
auth_manager = AuthManager(JWT_SECRET, JWT_ALGORITHM)
service_client = ServiceClient()

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class APIKey(Base):
    __tablename__ = "api_keys"
    
    key_id = Column(String, primary_key=True)
    key_hash = Column(String, unique=True, nullable=False)
    user_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    rate_limit = Column(Integer, default=1000)  # requests per hour
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)

class RateLimitLog(Base):
    __tablename__ = "rate_limit_logs"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Request/Response models
class LoginRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    is_admin: Optional[bool] = False

class CreateInstanceRequest(BaseModel):
    android_version: Optional[str] = "13"
    device_manufacturer: Optional[str] = None
    device_model: Optional[str] = None
    cpu_limit: Optional[float] = 2.0
    memory_limit: Optional[str] = "4G"
    storage_size: Optional[str] = "8G"
    network_config: Optional[Dict] = None
    location_config: Optional[Dict] = None
    custom_properties: Optional[Dict] = None

class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    altitude: Optional[float] = 0.0
    accuracy: Optional[float] = 10.0
    speed: Optional[float] = 0.0
    bearing: Optional[float] = 0.0

@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = redis.from_url(REDIS_URL)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize service client
    await service_client.initialize(
        identity_url=IDENTITY_SERVICE_URL,
        location_url=LOCATION_SERVICE_URL,
        network_url=NETWORK_SERVICE_URL,
        lifecycle_url=LIFECYCLE_SERVICE_URL
    )

@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Get user from database
        async with AsyncSession(engine) as session:
            user = await session.get(User, user_id)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            return user
            
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# Rate limiting dependency
async def check_rate_limit(user: User = Depends(get_current_user)):
    """Check API rate limits"""
    
    # Simple rate limiting - 1000 requests per hour per user
    current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    
    # Count requests in current hour
    cache_key = f"rate_limit:{user.id}:{current_hour.timestamp()}"
    current_count = await redis_client.get(cache_key)
    
    if current_count is None:
        current_count = 0
    else:
        current_count = int(current_count)
    
    if current_count >= 1000:  # Rate limit
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Increment counter
    await redis_client.setex(cache_key, 3600, current_count + 1)
    
    return user

# Auth endpoints
@app.post("/auth/login")
async def login(login_data: LoginRequest):
    """Authenticate user and return JWT token"""
    
    try:
        async with AsyncSession(engine) as session:
            # Find user by username
            result = await session.execute(
                session.query(User).filter(User.username == login_data.username)
            )
            user = result.scalar_one_or_none()
            
            if not user or not pwd_context.verify(login_data.password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password"
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is disabled"
                )
            
            # Update last login
            user.last_login = datetime.utcnow()
            await session.commit()
            
            # Create JWT token
            access_token = auth_manager.create_access_token(
                data={"sub": user.id, "username": user.username}
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user_id": user.id,
                "username": user.username,
                "is_admin": user.is_admin
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.post("/auth/register")
async def register(user_data: CreateUserRequest):
    """Register a new user"""
    
    try:
        async with AsyncSession(engine) as session:
            # Check if user already exists
            existing = await session.execute(
                session.query(User).filter(
                    (User.username == user_data.username) | 
                    (User.email == user_data.email)
                )
            )
            
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username or email already registered"
                )
            
            # Create new user
            user_id = f"user_{int(time.time())}_{hash(user_data.username) % 10000}"
            password_hash = pwd_context.hash(user_data.password)
            
            user = User(
                id=user_id,
                username=user_data.username,
                email=user_data.email,
                password_hash=password_hash,
                is_admin=user_data.is_admin
            )
            
            session.add(user)
            await session.commit()
            
            return {
                "user_id": user_id,
                "username": user_data.username,
                "email": user_data.email
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

# Android instance management
@app.post("/instances")
async def create_instance(request: CreateInstanceRequest, 
                         user: User = Depends(check_rate_limit)):
    """Create a new Android instance"""
    
    try:
        # Forward request to lifecycle manager
        response = await service_client.create_instance(request.dict())
        
        # Log the creation
        await redis_client.setex(
            f"instance_owner:{response['instance_id']}", 
            86400, 
            user.id
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Instance creation failed: {str(e)}")

@app.get("/instances")
async def list_instances(status: Optional[str] = None, 
                        user: User = Depends(check_rate_limit)):
    """List user's instances"""
    
    try:
        # Get all instances from lifecycle manager
        all_instances = await service_client.list_instances(status=status)
        
        # Filter to user's instances (in production, implement proper ownership)
        return all_instances
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list instances: {str(e)}")

@app.get("/instances/{instance_id}")
async def get_instance(instance_id: str, user: User = Depends(check_rate_limit)):
    """Get instance details"""
    
    try:
        return await service_client.get_instance(instance_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get instance: {str(e)}")

@app.post("/instances/{instance_id}/start")
async def start_instance(instance_id: str, user: User = Depends(check_rate_limit)):
    """Start an instance"""
    
    try:
        return await service_client.start_instance(instance_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start instance: {str(e)}")

@app.post("/instances/{instance_id}/stop")
async def stop_instance(instance_id: str, user: User = Depends(check_rate_limit)):
    """Stop an instance"""
    
    try:
        return await service_client.stop_instance(instance_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop instance: {str(e)}")

@app.delete("/instances/{instance_id}")
async def delete_instance(instance_id: str, user: User = Depends(check_rate_limit)):
    """Delete an instance"""
    
    try:
        response = await service_client.delete_instance(instance_id)
        
        # Clear ownership
        await redis_client.delete(f"instance_owner:{instance_id}")
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete instance: {str(e)}")

# Location management
@app.post("/instances/{instance_id}/location")
async def set_location(instance_id: str, location: LocationRequest, 
                      user: User = Depends(check_rate_limit)):
    """Set instance location"""
    
    try:
        return await service_client.set_location(instance_id, location.dict())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set location: {str(e)}")

@app.get("/instances/{instance_id}/location")
async def get_location(instance_id: str, user: User = Depends(check_rate_limit)):
    """Get current instance location"""
    
    try:
        return await service_client.get_location(instance_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get location: {str(e)}")

@app.post("/instances/{instance_id}/location/city")
async def set_city_location(instance_id: str, city: str, country: str = "US",
                           user: User = Depends(check_rate_limit)):
    """Set location to a specific city"""
    
    try:
        return await service_client.set_city_location(instance_id, city, country)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set city location: {str(e)}")

# Network management
@app.post("/instances/{instance_id}/network")
async def configure_network(instance_id: str, config: Dict,
                           user: User = Depends(check_rate_limit)):
    """Configure instance network"""
    
    try:
        return await service_client.configure_network(instance_id, config)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to configure network: {str(e)}")

@app.get("/instances/{instance_id}/network/status")
async def get_network_status(instance_id: str, user: User = Depends(check_rate_limit)):
    """Get network status"""
    
    try:
        return await service_client.get_network_status(instance_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get network status: {str(e)}")

# Device identity management
@app.post("/identity/generate")
async def generate_identity(config: Dict, user: User = Depends(check_rate_limit)):
    """Generate device identity"""
    
    try:
        return await service_client.generate_identity(config)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate identity: {str(e)}")

# Monitoring and stats
@app.get("/stats")
async def get_platform_stats(user: User = Depends(check_rate_limit)):
    """Get platform statistics"""
    
    try:
        return await service_client.get_platform_stats()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/instances/{instance_id}/stats")
async def get_instance_stats(instance_id: str, user: User = Depends(check_rate_limit)):
    """Get instance statistics"""
    
    try:
        return await service_client.get_instance_stats(instance_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get instance stats: {str(e)}")

@app.get("/instances/{instance_id}/logs")
async def get_instance_logs(instance_id: str, lines: int = 100,
                           user: User = Depends(check_rate_limit)):
    """Get instance logs"""
    
    try:
        return await service_client.get_instance_logs(instance_id, lines)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    try:
        # Check service connectivity
        services_health = {
            "identity": await service_client.check_service_health("identity"),
            "location": await service_client.check_service_health("location"),
            "network": await service_client.check_service_health("network"),
            "lifecycle": await service_client.check_service_health("lifecycle")
        }
        
        all_healthy = all(services_health.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.utcnow(),
            "services": services_health
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)