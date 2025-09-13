# Android Container Platform with Redroid

A production-ready containerized Android platform using Redroid that provides complete device spoofing, location simulation, and network isolation capabilities.

## Features

- **Redroid-based Android Containers**: Run multiple Android instances in isolated Docker containers
- **Complete Device Identity Spoofing**: Bypass SafetyNet, Play Integrity, and other detection systems  
- **System-Level GPS Injection**: Non-mock location injection with realistic movement patterns
- **Network Isolation**: Proxy integration with unique IP assignment per instance
- **Advanced Integrity Bypass**: Root detection bypass, hardware attestation spoofing
- **Application Management**: APK installation, app cloning, permission management
- **REST API & Web Dashboard**: Complete management interface
- **Production Ready**: Kubernetes deployment, auto-scaling, monitoring

## Quick Start

```bash
# Setup the platform
make setup

# Start development environment
make dev

# Deploy to production
make deploy
```

## Architecture

The platform consists of multiple services orchestrating Android container instances with complete identity and network isolation.

For detailed documentation, see the [docs](./docs) directory.