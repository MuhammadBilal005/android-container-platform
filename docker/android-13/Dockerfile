# Android 13 (API 33) Container with Complete Device Spoofing
# Based on Redroid with integrated bypass mechanisms

FROM redroid/redroid:13.0.0-latest as redroid-base

# Copy base spoofing tools
COPY --from=android-platform/base-spoofing:latest /opt/spoofing-tools /opt/spoofing-tools

# Install additional Android 13 specific tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    jq \
    sqlite3 \
    curl \
    wget \
    unzip \
    adb \
    && rm -rf /var/lib/apt/lists/*

# Android 13 specific configuration
ENV ANDROID_VERSION=13
ENV API_LEVEL=33
ENV REDROID_GPU_MODE=guest
ENV REDROID_WIDTH=1080
ENV REDROID_HEIGHT=1920
ENV REDROID_DPI=480

# Create Android 13 specific spoofing configurations
RUN mkdir -p /opt/android13-config

# Android 13 build properties template
RUN cat > /opt/android13-config/build-props-template.json << 'EOF'
{
  "ro.build.version.release": "13",
  "ro.build.version.sdk": "33",
  "ro.build.version.codename": "REL",
  "ro.build.version.all_codenames": "REL",
  "ro.build.version.release_or_codename": "13",
  "ro.build.version.security_patch": "2024-01-01",
  "ro.build.version.base_os": "",
  "ro.build.version.min_supported_target_sdk": "23",
  "ro.build.type": "user",
  "ro.build.tags": "release-keys",
  "ro.build.flavor": "aosp_arm64-user",
  "ro.product.cpu.abi": "arm64-v8a",
  "ro.product.cpu.abilist": "arm64-v8a,armeabi-v7a,armeabi",
  "ro.product.cpu.abilist32": "armeabi-v7a,armeabi",
  "ro.product.cpu.abilist64": "arm64-v8a",
  "ro.product.locale": "en-US",
  "ro.wifi.channels": "",
  "ro.board.platform": "gs201",
  "ro.board.first_api_level": "33",
  "ro.vendor.build.version.release": "13",
  "ro.vendor.build.version.sdk": "33",
  "ro.system.build.version.release": "13",
  "ro.system.build.version.sdk": "33",
  "ro.system_ext.build.version.release": "13",
  "ro.system_ext.build.version.sdk": "33",
  "ro.odm.build.version.release": "13",
  "ro.odm.build.version.sdk": "33",
  "ro.vndk.version": "33",
  "ro.vndk.lite": "false",
  "ro.zygote": "zygote64_32",
  "ro.hardware.egl": "swiftshader",
  "ro.hardware.vulkan": "pastel",
  "ro.opengles.version": "196610",
  "ro.surface_flinger.max_frame_buffer_acquired_buffers": "3",
  "ro.surface_flinger.max_virtual_display_dimension": "2048",
  "ro.surface_flinger.protected_contents": "true",
  "ro.surface_flinger.use_color_management": "true",
  "ro.surface_flinger.wcg_composition_dataspace": "143261696",
  "ro.surface_flinger.default_composition_dataspace": "142671872",
  "ro.surface_flinger.force_hwc_copy_for_virtual_displays": "true",
  "ro.adb.secure": "0",
  "ro.allow.mock.location": "0",
  "ro.debuggable": "0",
  "ro.secure": "1",
  "ro.boot.verifiedbootstate": "green",
  "ro.boot.flash.locked": "1",
  "ro.boot.veritymode": "enforcing",
  "ro.boot.warranty_bit": "0",
  "ro.warranty_bit": "0",
  "ro.oem_unlock_supported": "0",
  "ro.boot.ddrinfo": "samsung_k4f8e164hb_hgcl_4gb",
  "ro.boot.hardware": "gs201",
  "ro.boot.revision": "MP1.0",
  "ro.boot.boottime": "1BLL:85,1BL:204,2BL:334,TZ:150,EL3:29,ABL:278,UEFI:2,LINUX:0,RCK:0,RCR:0,RCC:0,BUP:0,KDT:0,EDT:0,SW:79,KE:1,OATi:31,AVB:5,UFS:10,RTC:0,DEPOP:1,PON:1953",
  "ro.boot.dynamic_partitions": "true",
  "ro.boot.slot_suffix": "_a",
  "ro.product.first_api_level": "33",
  "ro.product.name": "aosp_arm64",
  "ro.product.device": "generic_arm64",
  "ro.product.brand": "Android",
  "ro.product.model": "AOSP on ARM64",
  "ro.product.manufacturer": "Android",
  "ro.treble.enabled": "true",
  "ro.actionable_compatible_property.enabled": "true",
  "ro.postinstall.fstab.prefix": "/system",
  "ro.config.notification_sound": "OnTheHunt.ogg",
  "ro.config.alarm_alert": "Alarm_Classic.ogg",
  "dalvik.vm.isa.arm64.variant": "generic",
  "dalvik.vm.isa.arm64.features": "default",
  "dalvik.vm.isa.arm.variant": "cortex-a15",
  "dalvik.vm.isa.arm.features": "default",
  "dalvik.vm.lockprof.threshold": "250",
  "dalvik.vm.image-dex2oat-Xms": "64m",
  "dalvik.vm.image-dex2oat-Xmx": "64m",
  "dalvik.vm.dex2oat-Xms": "64m",
  "dalvik.vm.dex2oat-Xmx": "512m",
  "dalvik.vm.usejit": "true",
  "dalvik.vm.usejitprofiles": "true",
  "dalvik.vm.dexopt.secondary": "true",
  "dalvik.vm.dexopt.thermal-cutoff": "2",
  "dalvik.vm.appimageformat": "lz4",
  "ro.dalvik.vm.native.bridge": "0",
  "pm.dexopt.first-boot": "extract",
  "pm.dexopt.boot-after-ota": "extract",
  "pm.dexopt.post-boot": "extract",
  "pm.dexopt.install": "speed-profile",
  "pm.dexopt.install-fast": "skip",
  "pm.dexopt.install-bulk": "speed-profile",
  "pm.dexopt.install-bulk-secondary": "extract",
  "pm.dexopt.install-bulk-downgraded": "extract",
  "pm.dexopt.install-bulk-secondary-downgraded": "extract",
  "pm.dexopt.bg-dexopt": "speed-profile",
  "pm.dexopt.ab-ota": "speed-profile",
  "pm.dexopt.inactive": "verify",
  "pm.dexopt.cmdline": "verify",
  "pm.dexopt.shared": "speed"
}
EOF

# Android 13 SafetyNet bypass configuration
RUN cat > /opt/android13-config/safetynet-bypass.sh << 'EOF'
#!/bin/bash

# Android 13 SafetyNet bypass implementation
echo "🛡️ Applying Android 13 SafetyNet bypass..."

# Set critical properties for Android 13
setprop ro.boot.vbmeta.device_state locked
setprop ro.boot.verifiedbootstate green
setprop ro.boot.flash.locked 1
setprop ro.boot.veritymode enforcing
setprop ro.boot.warranty_bit 0
setprop ro.warranty_bit 0
setprop ro.debuggable 0
setprop ro.secure 1
setprop ro.build.type user
setprop ro.build.tags release-keys
setprop ro.oem_unlock_supported 0
setprop sys.oem_unlock_allowed 0

# Android 13 specific properties
setprop ro.product.first_api_level 33
setprop ro.board.first_api_level 33
setprop ro.board.api_level 33
setprop ro.vendor.api_level 33

# Hide development settings
setprop ro.build.type user
setprop ro.adb.secure 1
settings put global development_settings_enabled 0
settings put global adb_enabled 0
settings put secure install_non_market_apps 0

# Remove debugging properties
resetprop --delete ro.debuggable
resetprop --delete ro.adb.secure
resetprop --delete persist.sys.usb.config
resetprop --delete persist.service.adb.enable
resetprop --delete persist.service.debuggerd.enable

# Android 13 Treble compliance
setprop ro.treble.enabled true
setprop ro.vndk.version 33
setprop ro.product.vndk.version 33

# Set hardware attestation properties
setprop ro.hardware.keystore_desede des
setprop ro.hardware.gatekeeper trusty
setprop ro.hardware.bootctrl gs201

# Configure verified boot
mkdir -p /data/misc/vold
echo "green" > /data/misc/vold/verified_boot_state
chmod 644 /data/misc/vold/verified_boot_state

echo "✅ Android 13 SafetyNet bypass applied"
EOF

RUN chmod +x /opt/android13-config/safetynet-bypass.sh

# Android 13 Play Integrity bypass
RUN cat > /opt/android13-config/play-integrity-bypass.sh << 'EOF'
#!/bin/bash

# Android 13 Play Integrity API bypass
echo "🛡️ Applying Android 13 Play Integrity bypass..."

# Key attestation spoofing for Android 13
setprop ro.hardware.keystore strongbox
setprop ro.hardware.keystore_desede des
setprop ro.hardware.gatekeeper trusty
setprop ro.security.keystore.keytype EC
setprop ro.security.keystore.keysize 256

# Set attestation challenge properties
mkdir -p /data/misc/keystore
mkdir -p /data/misc/keychain

# Create mock attestation data
cat > /data/misc/keystore/attestation_key << 'EOK'
-----BEGIN CERTIFICATE-----
MIICljCCAX4CAQAwDQYJKoZIhvcNAQELBQAwGTEXMBUGA1UEAwwOQW5kcm9pZCBQ
bGF0Zm9ybTAeFw0yNDAxMDEwMDAwMDBaFw0zNDAxMDEwMDAwMDBaMBkxFzAVBgNV
BAMMDkFuZHJvaWQgUGxhdGZvcm0wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
AoIBAQCvTkGQZ0QZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ
1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ
1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ
1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ
1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ
1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ
1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ1JQZ
wIDAQABMA0GCSqGSIb3DQEBCwUAA4IBAQB7QgGQZ0QZ1JQZ1JQZ1JQZ1JQZ1JQZ
-----END CERTIFICATE-----
EOK

chmod 644 /data/misc/keystore/attestation_key

# Configure hardware-backed keystore
setprop ro.hardware.keystore_desede true
setprop ro.hardware.vulkan pastel
setprop ro.opengles.version 196610

# Set device integrity properties
setprop ro.boot.vbmeta.device_state locked
setprop vendor.boot.vbmeta.device_state locked

echo "✅ Android 13 Play Integrity bypass applied"
EOF

RUN chmod +x /opt/android13-config/play-integrity-bypass.sh

# Android 13 GPS injection system
RUN cat > /opt/android13-config/gps-setup.sh << 'EOF'
#!/bin/bash

# Android 13 GPS injection setup
echo "🌍 Setting up Android 13 GPS injection..."

# Create GPS HAL configuration
mkdir -p /vendor/etc/gps
mkdir -p /data/vendor/gps

# Create GPS configuration file
cat > /vendor/etc/gps.conf << 'GPS_CONF'
# GPS Configuration for Android 13
NTP_SERVER=pool.ntp.org
XTRA_SERVER_1=https://xtrapath1.izatcloud.net/xtra3grc.bin
XTRA_SERVER_2=https://xtrapath2.izatcloud.net/xtra3grc.bin
XTRA_SERVER_3=https://xtrapath3.izatcloud.net/xtra3grc.bin

# Intermediate position report
INTERMEDIATE_POS=1
ACCURACY_THRES=3000
ENABLE_WIPER=1

# GPS_LOCK configuration
GPS_LOCK=0

# SUPL settings
SUPL_HOST=supl.google.com
SUPL_PORT=7275
SUPL_VER=0x20000
SUPL_MODE=1
GPS_CONF

# Create GPS HAL mock service
cat > /vendor/bin/hw/android.hardware.gnss@2.1-service-mock << 'GPS_SERVICE'
#!/system/bin/sh

# Mock GPS HAL service for Android 13
export GNSS_MOCK_ENABLED=1
export GNSS_MOCK_INTERVAL=1000

while true; do
    # Read location from injection file
    if [ -f /data/gps/current_location ]; then
        LOCATION=$(cat /data/gps/current_location)
        LAT=$(echo $LOCATION | cut -d',' -f1)
        LNG=$(echo $LOCATION | cut -d',' -f2)
        ALT=$(echo $LOCATION | cut -d',' -f3)
        ACC=$(echo $LOCATION | cut -d',' -f4)
        
        # Generate NMEA sentences
        TIME=$(date -u +%H%M%S.000)
        DATE=$(date -u +%d%m%y)
        
        # GPGGA sentence
        echo "\$GPGGA,$TIME,$LAT,N,$LNG,W,1,04,$ACC,M,$ALT,M,,*" > /dev/gnss0
        
        # GPRMC sentence  
        echo "\$GPRMC,$TIME,A,$LAT,N,$LNG,W,0.0,0.0,$DATE,,*" > /dev/gnss0
    fi
    
    sleep 1
done
GPS_SERVICE

chmod +x /vendor/bin/hw/android.hardware.gnss@2.1-service-mock

# Create GPS device node
mknod /dev/gnss0 c 10 200
chmod 666 /dev/gnss0

# Set GPS system properties for Android 13
setprop ro.hardware.gps qcom
setprop ro.gps.agps_provider 1
setprop persist.vendor.radio.enable_voicecall 1

echo "✅ Android 13 GPS injection setup complete"
EOF

RUN chmod +x /opt/android13-config/gps-setup.sh

# Android 13 root detection bypass
RUN cat > /opt/android13-config/root-bypass.sh << 'EOF'
#!/bin/bash

# Android 13 Root Detection Bypass
echo "🔐 Applying Android 13 root detection bypass..."

# Hide Magisk binary paths
MAGISK_PATHS=(
    "/sbin/magisk"
    "/sbin/magiskhide" 
    "/sbin/magiskpolicy"
    "/sbin/supolicy"
    "/system/bin/magisk"
    "/system/bin/su"
    "/system/xbin/su"
    "/vendor/bin/su"
    "/cache/magisk.log"
    "/data/adb/magisk"
    "/data/magisk.db"
)

for path in "${MAGISK_PATHS[@]}"; do
    if [ -e "$path" ]; then
        mount -o bind /dev/null "$path" 2>/dev/null || true
    fi
done

# Hide root apps
ROOT_APPS=(
    "com.topjohnwu.magisk"
    "com.koushikdutta.superuser"
    "com.noshufou.android.su"
    "com.thirdparty.superuser"
    "eu.chainfire.supersu"
    "com.zachspong.temprootremovejb"
    "com.ramdroid.appquarantine"
    "com.android.vending.billing.InAppBillingService.COIN"
    "com.chelpus.lackypatch"
    "com.dimonvideo.luckypatcher"
    "com.forpda.lp"
    "com.android.vending.billing.InAppBillingService.LUCK"
)

for app in "${ROOT_APPS[@]}"; do
    pm uninstall --user 0 "$app" 2>/dev/null || true
    pm hide "$app" 2>/dev/null || true
done

# Reset dangerous properties
resetprop --delete ro.debuggable
resetprop --delete ro.adb.secure
resetprop --delete persist.sys.usb.config
resetprop --delete persist.service.adb.enable
resetprop --delete persist.service.debuggerd.enable
resetprop --delete persist.sys.root_access

# Set safe properties  
setprop ro.debuggable 0
setprop ro.secure 1
setprop ro.build.type user
setprop ro.build.tags release-keys
setprop ro.adb.secure 1

# Hide SELinux status
resetprop --delete ro.boot.selinux
setprop ro.boot.selinux enforcing

# Hide bootloader unlock
setprop ro.boot.flash.locked 1
setprop ro.boot.warranty_bit 0

echo "✅ Android 13 root detection bypass applied"
EOF

RUN chmod +x /opt/android13-config/root-bypass.sh

# Create Android 13 startup script
RUN cat > /opt/android13-config/android13-startup.sh << 'EOF'
#!/bin/bash

echo "🚀 Starting Android 13 with complete device spoofing..."

# Apply device identity if provided
if [ -n "$DEVICE_IDENTITY" ]; then
    echo "📱 Applying device identity for Android 13..."
    
    # Parse and apply device properties
    DEVICE_PROPS=$(echo "$DEVICE_IDENTITY" | jq -c '.system_properties')
    if [ "$DEVICE_PROPS" != "null" ]; then
        # Merge with Android 13 template
        MERGED_PROPS=$(jq -s '.[0] * .[1]' /opt/android13-config/build-props-template.json <(echo "$DEVICE_PROPS"))
        echo "$MERGED_PROPS" > /tmp/final_props.json
        python3 /opt/spoofing-tools/buildprop-editor.py modify "$(cat /tmp/final_props.json)"
    fi
fi

# Apply Android 13 specific bypasses
/opt/android13-config/safetynet-bypass.sh
/opt/android13-config/play-integrity-bypass.sh
/opt/android13-config/root-bypass.sh
/opt/android13-config/gps-setup.sh

# Set Android 13 specific environment
export ANDROID_DATA=/data
export ANDROID_STORAGE=/storage
export EXTERNAL_STORAGE=/sdcard
export ANDROID_ROOT=/system
export BOOTCLASSPATH=/system/framework/core-oj.jar:/system/framework/core-libart.jar:/system/framework/framework.jar:/system/framework/ext.jar:/system/framework/apache-xml.jar:/system/framework/okhttp.jar:/system/framework/bouncycastle.jar:/system/framework/conscrypt.jar

# Start Android 13 system services
start servicemanager
start hwservicemanager  
start vndservicemanager
start surfaceflinger
start bootanim

# Wait for system to be ready
while [ "$(getprop sys.boot_completed)" != "1" ]; do
    sleep 1
done

echo "✅ Android 13 system ready with complete device spoofing"
EOF

RUN chmod +x /opt/android13-config/android13-startup.sh

# Update entrypoint to use Android 13 startup
RUN sed -i 's|exec "$@"|/opt/android13-config/android13-startup.sh \&\& exec "$@"|' /opt/spoofing-tools/container-entrypoint.sh

# Configure Android 13 defaults
ENV REDROID_MAGISK=true
ENV REDROID_ROOT=true

# Expose standard Android ports
EXPOSE 5555 5554 5900

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD adb connect localhost:5555 && adb shell getprop sys.boot_completed | grep -q "1"

# Labels
LABEL maintainer="Android Container Platform"
LABEL version="13.0.0-spoofed"
LABEL description="Android 13 container with complete device spoofing and integrity bypass"
LABEL android.version="13"
LABEL android.api="33"

ENTRYPOINT ["/opt/spoofing-tools/container-entrypoint.sh"]
CMD ["/init", "androidboot.redroid_gpu_mode=guest"]