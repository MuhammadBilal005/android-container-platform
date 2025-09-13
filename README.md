# Android Container Platform

A comprehensive Redroid-based Android container platform with complete device spoofing integration for bypassing modern integrity checks and detection systems.

## 🚀 Features

### Core Capabilities
- **Multi-Version Support**: Android 11, 12, 13, and 14
- **Multi-Architecture**: ARM64 and x86_64 support
- **Device Spoofing**: Complete hardware fingerprint spoofing
- **Integrity Bypass**: SafetyNet and Play Integrity bypass
- **GPS Injection**: Real-time location spoofing with movement simulation
- **Root Detection Bypass**: Advanced hiding techniques
- **Container Orchestration**: Automated management and monitoring

### Security Features
- **Play Integrity Fix**: Latest bypass techniques for Google's integrity API
- **Tricky Store**: Advanced keystore attestation bypass
- **Shamiko**: Root hiding with comprehensive app targeting
- **Zygisk Next**: Enhanced process isolation and modification
- **Build.prop Spoofing**: Dynamic system property modification
- **Network Isolation**: Proxy-ready traffic routing

### Device Profiles
- **Samsung Galaxy S24**: Latest flagship Android 14 profile
- **Google Pixel 8**: Pure Android 14 experience
- **OnePlus 12**: Performance-focused Android 14
- **Custom Profiles**: Easy addition of new device configurations

## 📁 Project Structure

```
android-container-platform/
├── docker/                          # Docker configurations
│   ├── android-11/
│   │   ├── arm64/Dockerfile
│   │   └── x86_64/Dockerfile
│   ├── android-12/
│   │   ├── arm64/Dockerfile
│   │   └── x86_64/Dockerfile
│   ├── android-13/
│   │   ├── arm64/Dockerfile
│   │   └── x86_64/Dockerfile
│   └── android-14/
│       ├── arm64/Dockerfile
│       └── x86_64/Dockerfile
├── scripts/                         # Core system scripts
│   ├── android-setup.sh            # Device configuration script
│   ├── integrity-bypass.sh         # SafetyNet/Play Integrity bypass
│   ├── gps-injection.sh            # GPS spoofing and injection
│   └── container-orchestrator.py   # Container management
├── modules/                         # Spoofing and bypass modules
│   ├── device-profiles/            # Device hardware profiles
│   │   ├── samsung_galaxy_s24.json
│   │   ├── google_pixel_8.json
│   │   ├── oneplus_12.json
│   │   └── build_prop_generator.py
│   ├── bypass-tools/               # Root and integrity bypass tools
│   │   ├── magisk_manager.py
│   │   └── xposed_installer.py
│   └── gps-injection/              # Location spoofing components
├── health-checks/                   # Container health monitoring
│   └── android-health.sh
├── docker-compose.yml              # Multi-container orchestration
└── README.md                       # This file
```

## 🛠 Installation and Setup

### Prerequisites
- Docker and Docker Compose
- KVM support (for hardware acceleration)
- 16GB+ RAM recommended
- 50GB+ free disk space

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/android-container-platform.git
   cd android-container-platform
   ```

2. **Build all containers**:
   ```bash
   docker-compose build
   ```

3. **Start the platform**:
   ```bash
   docker-compose up -d
   ```

4. **Verify containers are running**:
   ```bash
   docker-compose ps
   ```

### Container Access

Once running, containers are accessible via ADB:
- **Android 14 ARM64**: `adb connect localhost:5555`
- **Android 14 x86_64**: `adb connect localhost:5556`
- **Android 13 ARM64**: `adb connect localhost:5557`
- **Android 12 Gaming**: `adb connect localhost:5558`

## 🎯 Usage Examples

### Basic Container Management

```bash
# Start specific container
docker-compose up -d android-14-arm64

# View container logs
docker-compose logs -f android-14-arm64

# Execute commands in container
docker-compose exec android-14-arm64 bash

# Stop all containers
docker-compose down
```

### Device Configuration

Containers automatically apply device spoofing on startup. To manually configure:

```bash
# Enter container
docker-compose exec android-14-arm64 bash

# Check spoofing status
/system/bin/android-setup.sh

# Verify integrity bypass
/system/bin/integrity-bypass.sh

# Set custom GPS location
set-location 37.7749 -122.4194 50.0 3.0

# Monitor GPS updates
gps-monitor
```

### Health Monitoring

```bash
# Check container health
docker-compose exec android-14-arm64 /usr/local/bin/health-check.sh

# View health logs
docker-compose exec android-14-arm64 cat /var/log/android-health.log
```

## 🏗 Advanced Configuration

### Custom Device Profiles

Create new device profiles in `modules/device-profiles/`:

```json
{
  "device_name": "Custom Device",
  "manufacturer": "CustomOEM",
  "brand": "custombrand",
  "model": "CUSTOM-123",
  "android_version": "14",
  "build_fingerprint": "custom/fingerprint/here",
  "spoofing_config": {
    "imei_pattern": "35{13}",
    "serial_pattern": "CUST{8}"
  }
}
```

Generate build.prop file:
```bash
python3 modules/device-profiles/build_prop_generator.py custom_device.json custom.prop
```

### GPS Location Profiles

Configure dynamic location movement:
```bash
# Set walking pattern between locations
echo "SET_LOCATION 40.7128 -74.0060" | nc -U /data/local/tmp/gps_socket
sleep 30
echo "SET_LOCATION 40.7580 -73.9855" | nc -U /data/local/tmp/gps_socket
```

### Integrity Bypass Configuration

The platform includes multiple bypass layers:

1. **Play Integrity Fix**: Automatically configured for each Android version
2. **Tricky Store**: Hardware attestation bypass for advanced apps
3. **Shamiko**: Root hiding with comprehensive app denylist
4. **System Properties**: Build.prop modifications for security compliance

## 🔒 Security Features

### Automatic Bypasses
- ✅ SafetyNet Basic Integrity
- ✅ SafetyNet CTS Profile Match
- ✅ Play Integrity BASIC verdict
- ✅ Play Integrity DEVICE verdict
- ✅ Root detection (banking apps, games)
- ✅ Developer options detection
- ✅ USB debugging detection
- ✅ Mock location detection

### Supported App Categories
- 🏦 **Banking Apps**: Chase, Bank of America, Wells Fargo, PayPal
- 🎮 **Gaming Apps**: Pokemon GO, Clash of Clans, Candy Crush
- 📺 **Streaming**: Netflix, Disney+, Hulu, Amazon Prime
- 💼 **Enterprise**: Microsoft Office, Slack, Zoom, Citrix

## 📊 Monitoring and Management

### Container Health Checks
- System service status monitoring
- Integrity bypass verification
- GPS service monitoring
- Resource usage tracking
- Network connectivity checks

### Management Scripts
```bash
# Container orchestrator
python3 scripts/container-orchestrator.py create container1 config.json
python3 scripts/container-orchestrator.py list
python3 scripts/container-orchestrator.py monitor

# Magisk module management
python3 modules/bypass-tools/magisk_manager.py list
python3 modules/bypass-tools/magisk_manager.py create-bypass

# Xposed module management
python3 modules/bypass-tools/xposed_installer.py status
python3 modules/bypass-tools/xposed_installer.py install-privacy
```

## ⚠️ Important Notes

### Legal and Ethical Use
This platform is designed for:
- ✅ Security research and testing
- ✅ App compatibility testing
- ✅ Development and debugging
- ✅ Educational purposes
- ✅ Privacy protection research

### Performance Optimization
- Enable KVM acceleration for better performance
- Allocate sufficient RAM (4GB+ per container)
- Use SSD storage for better I/O performance
- Monitor resource usage with built-in health checks

### Troubleshooting

Common issues and solutions:

1. **Container won't start**:
   ```bash
   # Check Docker logs
   docker-compose logs android-14-arm64
   
   # Verify KVM support
   ls -la /dev/kvm
   ```

2. **ADB connection issues**:
   ```bash
   # Reset ADB
   adb kill-server
   adb start-server
   adb connect localhost:5555
   ```

3. **Integrity bypass failing**:
   ```bash
   # Check bypass status
   docker-compose exec android-14-arm64 /system/bin/integrity-bypass.sh
   
   # Restart integrity services
   docker-compose restart android-14-arm64
   ```

## 🔄 Updates and Maintenance

### Updating Bypass Modules
Bypass techniques are regularly updated. To get the latest versions:

```bash
# Pull latest container images
docker-compose pull

# Rebuild with latest bypasses
docker-compose build --no-cache

# Restart with updated configurations
docker-compose down && docker-compose up -d
```

### Adding New Android Versions
1. Create new Dockerfile in `docker/android-XX/`
2. Update device profiles for new version
3. Test integrity bypasses
4. Add to docker-compose.yml

## 🤝 Contributing

Contributions are welcome! Areas of interest:
- New device profiles
- Updated bypass techniques
- Performance improvements
- Additional monitoring features
- Documentation improvements

## 📄 License

This project is released under the MIT License. See LICENSE file for details.

---

**⚠️ Disclaimer**: This software is for educational and research purposes only. Users are responsible for complying with all applicable laws and terms of service. The authors are not responsible for any misuse of this software.