# Android Container Platform - Base Redroid Image
# Contains common spoofing tools and bypass mechanisms

FROM ubuntu:22.04

# Install base dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    unzip \
    python3 \
    python3-pip \
    adb \
    fastboot \
    openjdk-11-jdk \
    git \
    build-essential \
    cmake \
    pkg-config \
    libssl-dev \
    libffi-dev \
    sqlite3 \
    xxd \
    binutils \
    && rm -rf /var/lib/apt/lists/*

# Install Android SDK tools
ENV ANDROID_HOME=/opt/android-sdk
ENV PATH=${PATH}:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools

RUN mkdir -p ${ANDROID_HOME} && \
    cd ${ANDROID_HOME} && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip && \
    unzip -q commandlinetools-linux-9477386_latest.zip && \
    mkdir -p cmdline-tools/latest && \
    mv cmdline-tools/* cmdline-tools/latest/ && \
    rm commandlinetools-linux-9477386_latest.zip

# Accept Android SDK licenses
RUN yes | sdkmanager --licenses && \
    sdkmanager "platform-tools" "platforms;android-33" "build-tools;33.0.0"

# Install Python dependencies for spoofing tools
RUN pip3 install \
    cryptography \
    pycryptodome \
    requests \
    lxml \
    beautifulsoup4 \
    faker

# Create spoofing tools directory
WORKDIR /opt/spoofing-tools

# Install Magisk Delta (latest version for bypass)
RUN wget -O magisk.apk https://github.com/HuskyDG/magisk-files/releases/latest/download/app-release.apk && \
    wget -O magisk.zip https://github.com/HuskyDG/magisk-files/releases/latest/download/Magisk-v26.1.zip

# Install Universal SafetyNet Fix
RUN wget -O safetynet-fix.zip https://github.com/kdrag0n/safetynet-fix/releases/latest/download/safetynet-fix-v2.4.0.zip

# Install Play Integrity Fix
RUN wget -O play-integrity-fix.zip https://github.com/chiteroman/PlayIntegrityFix/releases/latest/download/PlayIntegrityFix.zip

# Install Shamiko (hide Magisk)
RUN wget -O shamiko.zip https://github.com/LSPosed/LSPosed.github.io/releases/latest/download/shamiko-release.zip

# Install LSPosed (Xposed framework)
RUN wget -O lsposed.zip https://github.com/LSPosed/LSPosed/releases/latest/download/LSPosed-v1.9.2-7024-zygisk-release.zip

# Custom spoofing scripts
COPY scripts/device-spoofing/ /opt/spoofing-tools/device-spoofing/
COPY scripts/integrity-bypass/ /opt/spoofing-tools/integrity-bypass/
COPY scripts/gps-injection/ /opt/spoofing-tools/gps-injection/
COPY scripts/network-config/ /opt/spoofing-tools/network-config/

# Build property modification tool
RUN cat > /opt/spoofing-tools/buildprop-editor.py << 'EOF'
#!/usr/bin/env python3
import sys
import json
import os
import shutil
from datetime import datetime

class BuildPropEditor:
    def __init__(self, build_prop_path="/system/build.prop"):
        self.build_prop_path = build_prop_path
        self.backup_path = build_prop_path + ".backup"
        
    def backup(self):
        if os.path.exists(self.build_prop_path):
            shutil.copy2(self.build_prop_path, self.backup_path)
            return True
        return False
    
    def restore(self):
        if os.path.exists(self.backup_path):
            shutil.copy2(self.backup_path, self.build_prop_path)
            return True
        return False
    
    def modify_properties(self, properties_dict):
        if not os.path.exists(self.build_prop_path):
            return False
            
        # Read existing properties
        existing_props = {}
        with open(self.build_prop_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    existing_props[key.strip()] = value.strip()
        
        # Update with new properties
        existing_props.update(properties_dict)
        
        # Write modified properties
        with open(self.build_prop_path, 'w') as f:
            f.write(f"# Modified by Android Container Platform - {datetime.now()}\n")
            for key, value in sorted(existing_props.items()):
                f.write(f"{key}={value}\n")
        
        return True
    
    def get_property(self, key):
        if not os.path.exists(self.build_prop_path):
            return None
            
        with open(self.build_prop_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith(key + '='):
                    return line.split('=', 1)[1]
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: buildprop-editor.py <command> [args]")
        sys.exit(1)
    
    editor = BuildPropEditor()
    command = sys.argv[1]
    
    if command == "backup":
        success = editor.backup()
        print("Backup successful" if success else "Backup failed")
    elif command == "restore":
        success = editor.restore()
        print("Restore successful" if success else "Restore failed")
    elif command == "modify":
        if len(sys.argv) < 3:
            print("Usage: buildprop-editor.py modify <json_properties>")
            sys.exit(1)
        
        try:
            properties = json.loads(sys.argv[2])
            success = editor.modify_properties(properties)
            print("Modification successful" if success else "Modification failed")
        except json.JSONDecodeError:
            print("Invalid JSON format")
            sys.exit(1)
    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: buildprop-editor.py get <property_key>")
            sys.exit(1)
        
        value = editor.get_property(sys.argv[2])
        if value:
            print(value)
        else:
            print("Property not found")
    else:
        print("Unknown command:", command)
        sys.exit(1)
EOF

RUN chmod +x /opt/spoofing-tools/buildprop-editor.py

# IMEI modification tool
RUN cat > /opt/spoofing-tools/imei-changer.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import re
import struct
from datetime import datetime

class IMEIChanger:
    def __init__(self):
        self.nvram_paths = [
            "/data/nvram/APCFG/APRDEB/BT_Addr",
            "/data/nvram/APCFG/APRDCL/WIFI",
            "/efs/imei/mps_code.dat",
            "/persist/WCNSS_qcom_wlan_nv.bin",
            "/persist/bluetooth/.bdaddr",
            "/system/etc/bluetooth/bdaddr"
        ]
        
    def generate_luhn_checksum(self, imei_14):
        """Generate valid IMEI checksum using Luhn algorithm"""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(imei_14)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        
        return (10 - (checksum % 10)) % 10
    
    def generate_valid_imei(self, prefix="35"):
        """Generate a valid IMEI with proper checksum"""
        import random
        
        # TAC (Type Allocation Code) - first 8 digits
        if len(prefix) == 2:
            tac = prefix + ''.join([str(random.randint(0, 9)) for _ in range(6)])
        else:
            tac = '35' + ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Serial number - next 6 digits
        serial = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Calculate checksum digit
        imei_14 = tac + serial
        checksum = self.generate_luhn_checksum(int(imei_14))
        
        return imei_14 + str(checksum)
    
    def modify_imei_in_system(self, new_imei):
        """Modify IMEI in system files and properties"""
        success_count = 0
        
        # Set system property
        os.system(f'setprop gsm.device.imei0 {new_imei}')
        os.system(f'setprop gsm.device.imei {new_imei}')
        os.system(f'setprop ril.IMEI {new_imei}')
        os.system(f'setprop ro.ril.oem.imei {new_imei}')
        
        # Create IMEI file
        try:
            os.makedirs('/data/imei', exist_ok=True)
            with open('/data/imei/imei.txt', 'w') as f:
                f.write(new_imei)
            success_count += 1
        except:
            pass
        
        # Modify RIL database if it exists
        try:
            import sqlite3
            ril_db_path = '/data/user_de/0/com.android.providers.telephony/databases/telephony.db'
            if os.path.exists(ril_db_path):
                conn = sqlite3.connect(ril_db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE siminfo SET icc_id = ? WHERE _id = 1", (new_imei,))
                conn.commit()
                conn.close()
                success_count += 1
        except:
            pass
        
        return success_count > 0
    
    def get_current_imei(self):
        """Get current IMEI from system"""
        # Try different methods to get IMEI
        methods = [
            "getprop gsm.device.imei0",
            "getprop gsm.device.imei",
            "getprop ril.IMEI",
            "service call iphonesubinfo 1"
        ]
        
        for method in methods:
            try:
                result = os.popen(method).read().strip()
                if result and len(result) == 15 and result.isdigit():
                    return result
            except:
                continue
        
        return None

if __name__ == "__main__":
    changer = IMEIChanger()
    
    if len(sys.argv) < 2:
        print("Usage: imei-changer.py <command> [args]")
        print("Commands:")
        print("  generate - Generate a new valid IMEI")
        print("  set <imei> - Set IMEI to specific value")
        print("  get - Get current IMEI")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "generate":
        new_imei = changer.generate_valid_imei()
        print(f"Generated IMEI: {new_imei}")
        success = changer.modify_imei_in_system(new_imei)
        print("IMEI set successfully" if success else "Failed to set IMEI")
        
    elif command == "set":
        if len(sys.argv) < 3:
            print("Usage: imei-changer.py set <imei>")
            sys.exit(1)
        
        new_imei = sys.argv[2]
        if len(new_imei) != 15 or not new_imei.isdigit():
            print("Invalid IMEI format. Must be 15 digits.")
            sys.exit(1)
        
        success = changer.modify_imei_in_system(new_imei)
        print("IMEI set successfully" if success else "Failed to set IMEI")
        
    elif command == "get":
        current_imei = changer.get_current_imei()
        if current_imei:
            print(f"Current IMEI: {current_imei}")
        else:
            print("Could not retrieve IMEI")
    else:
        print("Unknown command:", command)
        sys.exit(1)
EOF

RUN chmod +x /opt/spoofing-tools/imei-changer.py

# Android ID modification tool
RUN cat > /opt/spoofing-tools/android-id-changer.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import sqlite3
import random
import string
from pathlib import Path

class AndroidIDChanger:
    def __init__(self):
        self.settings_db_path = '/data/system/users/0/settings_system.db'
        self.secure_db_path = '/data/system/users/0/settings_secure.db'
        
    def generate_android_id(self):
        """Generate a new Android ID (16 hex characters)"""
        return ''.join(random.choices(string.hexdigits.lower(), k=16))
    
    def modify_android_id_in_db(self, new_android_id, db_path):
        """Modify Android ID in SQLite database"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Update existing Android ID or insert new one
            cursor.execute("""
                INSERT OR REPLACE INTO secure (name, value) 
                VALUES ('android_id', ?)
            """, (new_android_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Database error: {e}")
            return False
    
    def set_android_id_property(self, android_id):
        """Set Android ID via system properties"""
        os.system(f'setprop android.device.id {android_id}')
        os.system(f'setprop sys.android_id {android_id}')
        
        # Create Android ID file
        try:
            os.makedirs('/data/android_id', exist_ok=True)
            with open('/data/android_id/android_id.txt', 'w') as f:
                f.write(android_id)
            return True
        except:
            return False
    
    def modify_android_id(self, new_android_id):
        """Modify Android ID using multiple methods"""
        success_count = 0
        
        # Method 1: Settings database
        if os.path.exists(self.secure_db_path):
            if self.modify_android_id_in_db(new_android_id, self.secure_db_path):
                success_count += 1
        
        # Method 2: System properties
        if self.set_android_id_property(new_android_id):
            success_count += 1
        
        # Method 3: Settings provider
        try:
            os.system(f'settings put secure android_id {new_android_id}')
            success_count += 1
        except:
            pass
        
        return success_count > 0
    
    def get_current_android_id(self):
        """Get current Android ID"""
        # Try different methods
        methods = [
            "settings get secure android_id",
            "getprop android.device.id",
            "getprop sys.android_id"
        ]
        
        for method in methods:
            try:
                result = os.popen(method).read().strip()
                if result and len(result) == 16:
                    return result
            except:
                continue
        
        return None

if __name__ == "__main__":
    changer = AndroidIDChanger()
    
    if len(sys.argv) < 2:
        print("Usage: android-id-changer.py <command> [args]")
        print("Commands:")
        print("  generate - Generate and set new Android ID")
        print("  set <id> - Set Android ID to specific value")
        print("  get - Get current Android ID")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "generate":
        new_id = changer.generate_android_id()
        print(f"Generated Android ID: {new_id}")
        success = changer.modify_android_id(new_id)
        print("Android ID set successfully" if success else "Failed to set Android ID")
        
    elif command == "set":
        if len(sys.argv) < 3:
            print("Usage: android-id-changer.py set <android_id>")
            sys.exit(1)
        
        new_id = sys.argv[2]
        if len(new_id) != 16:
            print("Invalid Android ID format. Must be 16 characters.")
            sys.exit(1)
        
        success = changer.modify_android_id(new_id)
        print("Android ID set successfully" if success else "Failed to set Android ID")
        
    elif command == "get":
        current_id = changer.get_current_android_id()
        if current_id:
            print(f"Current Android ID: {current_id}")
        else:
            print("Could not retrieve Android ID")
    else:
        print("Unknown command:", command)
        sys.exit(1)
EOF

RUN chmod +x /opt/spoofing-tools/android-id-changer.py

# Create entrypoint script
RUN cat > /opt/spoofing-tools/container-entrypoint.sh << 'EOF'
#!/bin/bash

# Android Container Platform - Container Entrypoint
# Applies device spoofing and integrity bypass on container start

set -e

echo "🔧 Starting Android Container Platform configuration..."

# Load device identity from environment or generate new one
if [ -n "$DEVICE_IDENTITY" ]; then
    echo "📱 Applying device identity configuration..."
    
    # Parse device identity JSON
    MANUFACTURER=$(echo "$DEVICE_IDENTITY" | jq -r '.device_profile.manufacturer // "Google"')
    MODEL=$(echo "$DEVICE_IDENTITY" | jq -r '.device_profile.model // "Pixel 7"')
    ANDROID_VERSION=$(echo "$DEVICE_IDENTITY" | jq -r '.device_profile.android_version // "13"')
    IMEI=$(echo "$DEVICE_IDENTITY" | jq -r '.imei // empty')
    ANDROID_ID=$(echo "$DEVICE_IDENTITY" | jq -r '.android_id // empty')
    SERIAL_NUMBER=$(echo "$DEVICE_IDENTITY" | jq -r '.serial_number // empty')
    
    echo "Device: $MANUFACTURER $MODEL (Android $ANDROID_VERSION)"
    
    # Apply device spoofing
    if [ -n "$IMEI" ]; then
        echo "🔧 Setting IMEI: $IMEI"
        python3 /opt/spoofing-tools/imei-changer.py set "$IMEI"
    fi
    
    if [ -n "$ANDROID_ID" ]; then
        echo "🔧 Setting Android ID: $ANDROID_ID"
        python3 /opt/spoofing-tools/android-id-changer.py set "$ANDROID_ID"
    fi
    
    # Apply system properties
    if echo "$DEVICE_IDENTITY" | jq -e '.system_properties' > /dev/null; then
        echo "🔧 Applying system properties..."
        SYSTEM_PROPS=$(echo "$DEVICE_IDENTITY" | jq -c '.system_properties')
        python3 /opt/spoofing-tools/buildprop-editor.py modify "$SYSTEM_PROPS"
    fi
fi

# Apply integrity bypass modules
if [ "$ENABLE_INTEGRITY_BYPASS" = "true" ]; then
    echo "🛡️ Installing integrity bypass modules..."
    
    # Install Magisk if not present
    if [ ! -f /system/bin/magisk ]; then
        echo "Installing Magisk..."
        cp /opt/spoofing-tools/magisk.zip /data/local/tmp/
        cd /data/local/tmp
        unzip -q magisk.zip
        ./magiskinit --magisk32 --magisk64 --selinux /data/local/tmp/magisk32 /data/local/tmp/magisk64
    fi
    
    # Install SafetyNet Fix
    if [ -f /opt/spoofing-tools/safetynet-fix.zip ]; then
        echo "Installing SafetyNet Fix..."
        mkdir -p /data/adb/modules/safetynet-fix
        cd /data/adb/modules/safetynet-fix
        unzip -q /opt/spoofing-tools/safetynet-fix.zip
        chmod 755 *.sh
    fi
    
    # Install Play Integrity Fix
    if [ -f /opt/spoofing-tools/play-integrity-fix.zip ]; then
        echo "Installing Play Integrity Fix..."
        mkdir -p /data/adb/modules/playintegrityfix
        cd /data/adb/modules/playintegrityfix
        unzip -q /opt/spoofing-tools/play-integrity-fix.zip
        chmod 755 *.sh
    fi
    
    # Install Shamiko (hide Magisk)
    if [ -f /opt/spoofing-tools/shamiko.zip ]; then
        echo "Installing Shamiko..."
        mkdir -p /data/adb/modules/shamiko
        cd /data/adb/modules/shamiko
        unzip -q /opt/spoofing-tools/shamiko.zip
        chmod 755 *.sh
    fi
fi

# Configure GPS injection if enabled
if [ "$ENABLE_GPS_INJECTION" = "true" ]; then
    echo "🌍 Setting up GPS injection..."
    
    # Create GPS provider replacement
    mkdir -p /data/gps
    
    # Set initial location if provided
    if [ -n "$INITIAL_LATITUDE" ] && [ -n "$INITIAL_LONGITUDE" ]; then
        echo "📍 Setting initial location: $INITIAL_LATITUDE, $INITIAL_LONGITUDE"
        python3 /opt/spoofing-tools/gps-injection/gps-injector.py set "$INITIAL_LATITUDE" "$INITIAL_LONGITUDE"
    fi
fi

# Configure network isolation if enabled
if [ "$ENABLE_NETWORK_ISOLATION" = "true" ]; then
    echo "🌐 Configuring network isolation..."
    
    # Setup proxy if provided
    if [ -n "$PROXY_HOST" ] && [ -n "$PROXY_PORT" ]; then
        echo "🔗 Configuring proxy: $PROXY_HOST:$PROXY_PORT"
        
        # Set global proxy
        settings put global http_proxy "$PROXY_HOST:$PROXY_PORT"
        settings put secure http_proxy "$PROXY_HOST:$PROXY_PORT"
        
        # Configure DNS if provided
        if [ -n "$DNS_SERVERS" ]; then
            echo "🔧 Setting DNS servers: $DNS_SERVERS"
            IFS=',' read -ra DNS_ARRAY <<< "$DNS_SERVERS"
            for i in "${!DNS_ARRAY[@]}"; do
                setprop "net.dns$((i+1))" "${DNS_ARRAY[i]}"
            done
        fi
    fi
fi

# Start Android services
echo "🚀 Starting Android system..."

# Ensure critical services are running
start adbd
start bootanim
start servicemanager
start vold
start netd

# Wait for Android to fully boot
echo "⏳ Waiting for Android boot completion..."
while [ "$(getprop sys.boot_completed)" != "1" ]; do
    sleep 2
done

echo "✅ Android Container Platform configuration complete!"
echo "📱 Device Identity Applied"
echo "🛡️ Integrity Bypass Active"
echo "🌍 GPS Injection Ready"
echo "🌐 Network Isolation Configured"

# Keep container running
exec "$@"
EOF

RUN chmod +x /opt/spoofing-tools/container-entrypoint.sh

# Install jq for JSON parsing
RUN apt-get update && apt-get install -y jq && rm -rf /var/lib/apt/lists/*

# Create default Android configuration
ENV ENABLE_DEVICE_SPOOFING=true
ENV ENABLE_INTEGRITY_BYPASS=true
ENV ENABLE_GPS_INJECTION=true
ENV ENABLE_NETWORK_ISOLATION=true

# Set entrypoint
ENTRYPOINT ["/opt/spoofing-tools/container-entrypoint.sh"]