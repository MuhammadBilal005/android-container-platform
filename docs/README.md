# Android Container Platform Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture) 
3. [Features](#features)
4. [Quick Start](#quick-start)
5. [API Reference](#api-reference)
6. [Deployment](#deployment)
7. [Security](#security)
8. [Troubleshooting](#troubleshooting)

## Overview

The Android Container Platform is a production-ready system for running Android instances in containerized environments using Redroid technology. It provides complete device spoofing, network isolation, location simulation, and integrity bypass capabilities.

### Key Benefits

- **Complete Identity Spoofing**: Bypass SafetyNet, Play Integrity, and other detection systems
- **System-Level GPS Injection**: Non-mock location simulation with realistic movement
- **Network Isolation**: Proxy integration with unique IP assignment per instance
- **Scalable Architecture**: Support for 50+ concurrent Android instances
- **Production Ready**: Monitoring, auto-scaling, and high availability

## Architecture

The platform consists of microservices orchestrating Android container instances:

```
┌─────────────────────────────────────┐
│           Web Dashboard             │
├─────────────────────────────────────┤
│              API Gateway            │  ← Port 3000
├─────────────────────────────────────┤
│  Identity │ Location │ Network      │
│  Manager  │ Manager  │ Manager      │  ← Ports 8001-8003
│   (8001)  │  (8002)  │  (8003)     │
├─────────────────────────────────────┤
│         Lifecycle Manager           │  ← Port 8004
├─────────────────────────────────────┤
│   PostgreSQL    │      Redis        │  ← Ports 5432, 6379
├─────────────────────────────────────┤
│      Android Container Layer        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐│
│  │Android  │ │Android  │ │Android  ││
│  │Instance │ │Instance │ │Instance ││
│  │(Redroid)│ │(Redroid)│ │(Redroid)││
│  └─────────┘ └─────────┘ └─────────┘│
└─────────────────────────────────────┘
```

### Service Components

1. **API Gateway** (Port 3000)
   - Central API endpoint
   - Authentication and authorization
   - Request routing and load balancing
   - Rate limiting

2. **Identity Manager** (Port 8001)
   - Device identity generation and spoofing
   - IMEI, Android ID, serial number management
   - System property configuration
   - Integrity bypass mechanisms

3. **Location Manager** (Port 8002)
   - System-level GPS injection
   - Route simulation and movement patterns
   - Location history and caching
   - Real-time coordinate updates

4. **Network Manager** (Port 8003)
   - Network namespace isolation
   - Proxy configuration and routing
   - DNS management
   - Traffic analysis and monitoring

5. **Lifecycle Manager** (Port 8004)
   - Redroid container orchestration
   - Instance creation, scaling, and management
   - Resource monitoring and optimization
   - Health checks and auto-recovery

## Features

### Complete Device Identity Spoofing

The platform generates realistic device identities that bypass detection:

- **IMEI Generation**: Valid Luhn checksum IMEIs
- **Android ID**: Cryptographically secure 16-character hex IDs
- **Serial Numbers**: Manufacturer-specific formats
- **Build Fingerprints**: Consistent with device profile
- **System Properties**: Complete ro.* and persist.* spoofing

### Advanced Location Simulation

System-level location injection without mock location APIs:

- **Non-Mock GPS**: Direct GPS provider replacement
- **Realistic Movement**: Speed variation and path deviation
- **Route Simulation**: Multi-waypoint path following
- **NMEA Injection**: Raw GPS data stream simulation
- **Provider Support**: GPS, Network, and Passive providers

### Network Isolation and Proxy Integration

Complete network traffic control and isolation:

- **Network Namespaces**: Isolated networking per instance
- **Proxy Support**: HTTP, SOCKS5, residential proxies
- **Geographic IP**: Country/city-specific IP assignment
- **DNS Control**: Custom DNS servers per instance
- **Traffic Rules**: Bandwidth limiting and filtering

### Integrity Bypass Mechanisms

Comprehensive bypass of Android security checks:

- **SafetyNet Bypass**: Hardware attestation spoofing
- **Play Integrity**: Device and app integrity passing
- **Root Detection**: Hide root access and modifications
- **Bootloader**: Spoof locked bootloader state
- **System Validation**: Pass CTS and security checks

## Quick Start

### Prerequisites

- Docker and Docker Compose
- 8GB+ RAM (16GB+ recommended for production)
- 50GB+ storage space
- Linux host (Ubuntu 20.04+ recommended)

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/android-container-platform.git
   cd android-container-platform
   ```

2. **Setup the platform:**
   ```bash
   make setup
   ```

3. **Start services:**
   ```bash
   make dev
   ```

4. **Verify installation:**
   ```bash
   curl http://localhost:3000/health
   ```

### First Android Instance

1. **Authenticate:**
   ```bash
   curl -X POST http://localhost:3000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin123"}'
   ```

2. **Create instance:**
   ```bash
   curl -X POST http://localhost:3000/instances \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "android_version": "13",
       "device_manufacturer": "Google", 
       "device_model": "Pixel 7",
       "cpu_limit": 2.0,
       "memory_limit": "4G"
     }'
   ```

3. **Monitor instance:**
   ```bash
   curl -X GET http://localhost:3000/instances/INSTANCE_ID \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

### Web Dashboard

Access the web dashboard at http://localhost:8080

- Username: `admin`
- Password: `admin123`

## API Reference

### Authentication

All API requests require authentication via JWT token:

```bash
# Login
POST /auth/login
{
  "username": "admin",
  "password": "admin123"
}

# Response
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

Include token in subsequent requests:
```bash
Authorization: Bearer YOUR_TOKEN
```

### Instance Management

#### Create Instance
```bash
POST /instances
{
  "android_version": "13",
  "device_manufacturer": "Google",
  "device_model": "Pixel 7", 
  "cpu_limit": 2.0,
  "memory_limit": "4G",
  "storage_size": "8G",
  "network_config": {
    "proxy_type": "residential",
    "country": "US"
  },
  "location_config": {
    "latitude": 40.7128,
    "longitude": -74.0060
  }
}
```

#### List Instances
```bash
GET /instances?status=running&limit=50
```

#### Instance Control
```bash
POST /instances/{instance_id}/start
POST /instances/{instance_id}/stop
POST /instances/{instance_id}/restart
DELETE /instances/{instance_id}
```

### Location Management

#### Set Location
```bash
POST /instances/{instance_id}/location
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "altitude": 10.0,
  "accuracy": 5.0,
  "speed": 0.0,
  "bearing": 0.0
}
```

#### Start Route Simulation
```bash
POST /instances/{instance_id}/route
{
  "waypoints": [
    [40.7128, -74.0060],
    [40.7589, -73.9851],
    [40.7614, -73.9776]
  ],
  "speed_profile": {
    "walking": 5.0,
    "driving": 50.0
  }
}
```

### Network Configuration

#### Configure Network
```bash
POST /instances/{instance_id}/network
{
  "proxy_type": "residential",
  "country": "US",
  "city": "New York",
  "dns_servers": ["8.8.8.8", "1.1.1.1"]
}
```

#### Test Network
```bash
POST /instances/{instance_id}/network/test
```

### Monitoring

#### Platform Stats
```bash
GET /stats
```

#### Instance Stats
```bash
GET /instances/{instance_id}/stats
```

#### Instance Logs
```bash
GET /instances/{instance_id}/logs?lines=100
```

## Deployment

### Production Deployment (Kubernetes)

1. **Setup cluster:**
   ```bash
   # Create namespace
   kubectl apply -f k8s/namespace.yaml
   
   # Deploy configuration
   kubectl apply -f k8s/configmap.yaml
   
   # Deploy databases
   kubectl apply -f k8s/postgres.yaml
   kubectl apply -f k8s/redis.yaml
   
   # Deploy services
   kubectl apply -f k8s/services.yaml
   
   # Deploy monitoring
   kubectl apply -f k8s/monitoring.yaml
   ```

2. **Verify deployment:**
   ```bash
   kubectl get pods -n android-platform
   kubectl get services -n android-platform
   ```

3. **Access services:**
   - API Gateway: `kubectl port-forward svc/api-gateway 3000:80 -n android-platform`
   - Grafana: `kubectl port-forward svc/grafana 3001:80 -n android-platform`

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379` |
| `JWT_SECRET` | JWT signing secret | Generated |
| `IDENTITY_SERVICE_URL` | Identity service URL | `http://identity-manager:8001` |
| `LOCATION_SERVICE_URL` | Location service URL | `http://location-manager:8002` |
| `NETWORK_SERVICE_URL` | Network service URL | `http://network-manager:8003` |
| `LIFECYCLE_SERVICE_URL` | Lifecycle service URL | `http://lifecycle-manager:8004` |

### Scaling Configuration

#### Horizontal Scaling
```yaml
# Increase replica count
spec:
  replicas: 5

# Auto-scaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

#### Resource Limits
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

## Security

### Authentication & Authorization

The platform uses JWT-based authentication with the following features:

- **Token expiration**: 24-hour token lifetime
- **Role-based access**: Admin and user roles
- **Rate limiting**: 1000 requests/hour per user
- **API key support**: For programmatic access

### Network Security

- **TLS encryption**: All inter-service communication encrypted
- **Network policies**: Kubernetes network segmentation
- **Firewall rules**: Restricted port access
- **Proxy validation**: Malicious proxy detection

### Container Security

- **Privilege dropping**: Containers run with minimal privileges
- **Resource limits**: CPU and memory constraints
- **Image scanning**: Vulnerability scanning on build
- **Secrets management**: Encrypted credential storage

### Data Protection

- **Database encryption**: Encrypted at rest
- **Backup encryption**: Encrypted backups
- **PII handling**: Minimal personal data storage
- **Audit logging**: Complete action logging

## Troubleshooting

### Common Issues

#### Service Not Starting

1. **Check logs:**
   ```bash
   docker-compose logs service-name
   kubectl logs -f deployment/service-name -n android-platform
   ```

2. **Verify connectivity:**
   ```bash
   curl http://localhost:3000/health
   ```

3. **Check dependencies:**
   ```bash
   # Database connectivity
   pg_isready -h localhost -p 5432
   
   # Redis connectivity
   redis-cli -h localhost -p 6379 ping
   ```

#### Android Instance Fails to Start

1. **Check system requirements:**
   ```bash
   # Verify KVM support
   kvm-ok
   
   # Check available memory
   free -h
   
   # Verify Docker resources
   docker system df
   ```

2. **Instance logs:**
   ```bash
   curl -X GET http://localhost:3000/instances/INSTANCE_ID/logs \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Container inspection:**
   ```bash
   docker inspect android-INSTANCE_ID
   docker logs android-INSTANCE_ID
   ```

#### Network Issues

1. **Check network namespace:**
   ```bash
   ip netns list
   ip netns exec netns-INSTANCE_ID ip addr show
   ```

2. **Test connectivity:**
   ```bash
   curl -X POST http://localhost:3000/instances/INSTANCE_ID/network/test \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Proxy validation:**
   ```bash
   curl -X GET http://localhost:3000/proxy/list \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

#### Performance Issues

1. **Resource monitoring:**
   ```bash
   # Check system resources
   htop
   iotop
   
   # Container resources
   docker stats
   
   # Platform metrics
   curl http://localhost:9090/metrics
   ```

2. **Database performance:**
   ```bash
   # Connection count
   psql -c "SELECT count(*) FROM pg_stat_activity;"
   
   # Slow queries
   psql -c "SELECT query FROM pg_stat_activity WHERE state = 'active';"
   ```

### Log Locations

- **Service logs**: `/var/log/android-platform/`
- **Container logs**: Docker/Kubernetes logs
- **Application logs**: Service-specific logging
- **Audit logs**: `/var/log/android-platform/audit/`

### Performance Tuning

#### Database Optimization
```sql
-- Increase connection pool
ALTER SYSTEM SET max_connections = 200;

-- Optimize memory
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
```

#### Container Resource Tuning
```yaml
# Increase resource limits for high-load instances
resources:
  limits:
    cpu: "4000m"
    memory: "8Gi"
```

#### Network Optimization
```bash
# Increase network buffer sizes
echo 'net.core.rmem_max = 134217728' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' >> /etc/sysctl.conf
sysctl -p
```

For additional support, check the [GitHub Issues](https://github.com/your-org/android-container-platform/issues) or consult the detailed service documentation in the respective service directories.