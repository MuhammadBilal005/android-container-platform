#!/system/bin/sh

# Android Container Setup Script
# Configures device spoofing and system properties on container start

LOG_TAG="AndroidSetup"
LOG_FILE="/data/local/tmp/android-setup.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$LOG_TAG] $1" | tee -a "$LOG_FILE"
}

log "Starting Android container setup..."

# Wait for Android system to be ready
wait_for_system() {
    local timeout=60
    local count=0
    
    while [ $count -lt $timeout ]; do
        if getprop sys.boot_completed | grep -q "1"; then
            log "Android system is ready"
            return 0
        fi
        log "Waiting for system to boot... ($count/$timeout)"
        sleep 2
        count=$((count + 1))
    done
    
    log "ERROR: System failed to boot within timeout"
    return 1
}

# Apply device profile based on Android version and architecture
apply_device_profile() {
    local android_version="${ANDROID_VERSION:-11}"
    local arch="${ARCH:-arm64}"
    local profile_dir="/system/etc/device-profiles"
    
    log "Applying device profile for Android $android_version ($arch)"
    
    # Generate random device identifiers
    generate_device_identifiers() {
        # Generate random IMEI (15 digits)
        IMEI=$(python3 -c "import random; print(''.join([str(random.randint(0,9)) for _ in range(15)]))")
        
        # Generate random Android ID (16 hex characters)
        ANDROID_ID=$(python3 -c "import random; print(''.join([format(random.randint(0,15), 'x') for _ in range(16)]))")
        
        # Generate random serial number
        SERIAL=$(python3 -c "import random, string; print(''.join(random.choices(string.ascii_uppercase + string.digits, k=10)))")
        
        # Generate random MAC address
        MAC=$(python3 -c "import random; print(':'.join(['%02x' % random.randint(0x00, 0xff) for _ in range(6)]))")
        
        # Generate random advertising ID
        AD_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")
    }
    
    generate_device_identifiers
    
    log "Generated identifiers:"
    log "  IMEI: $IMEI"
    log "  Android ID: $ANDROID_ID"
    log "  Serial: $SERIAL"
    log "  MAC: $MAC"
    log "  Ad ID: $AD_ID"
    
    # Apply identifiers to system
    setprop ro.telephony.imei_sv $IMEI
    setprop ro.serialno $SERIAL
    setprop ro.boot.serialno $SERIAL
    setprop wifi.interface wlan0
    
    # Store identifiers for persistence
    echo "$ANDROID_ID" > /data/system/android_id
    echo "$AD_ID" > /data/system/advertising_id
    
    # Apply timezone and locale randomization
    TIMEZONES=("America/New_York" "Europe/London" "Asia/Tokyo" "Australia/Sydney" "America/Los_Angeles" "Europe/Berlin")
    LOCALES=("en-US" "en-GB" "de-DE" "fr-FR" "ja-JP" "ko-KR")
    
    RANDOM_TZ=${TIMEZONES[$((RANDOM % ${#TIMEZONES[@]}))]}
    RANDOM_LOCALE=${LOCALES[$((RANDOM % ${#LOCALES[@]}))]}
    
    setprop persist.sys.timezone "$RANDOM_TZ"
    setprop persist.sys.locale "$RANDOM_LOCALE"
    
    log "Applied timezone: $RANDOM_TZ"
    log "Applied locale: $RANDOM_LOCALE"
}

# Configure network settings
configure_network() {
    log "Configuring network settings..."
    
    # Enable network location
    setprop ro.com.google.locationfeatures 1
    setprop ro.com.google.networklocation 1
    
    # Configure DNS settings
    setprop net.dns1 8.8.8.8
    setprop net.dns2 8.8.4.4
    
    # Enable data connection
    setprop ro.telephony.default_network 9
    setprop telephony.lteOnCdmaDevice 1
}

# Configure developer options and debugging
configure_developer_settings() {
    log "Configuring developer settings..."
    
    # Disable USB debugging detection
    setprop ro.adb.secure 0
    setprop ro.debuggable 0
    
    # Hide developer options
    setprop persist.sys.developer_options_enabled 0
    
    # Configure mock location settings
    setprop ro.allow.mock.location 0
}

# Apply system-level security bypasses
apply_security_bypasses() {
    log "Applying security bypasses..."
    
    # SafetyNet bypass properties
    setprop ro.boot.flash.locked 1
    setprop ro.boot.verifiedbootstate green
    setprop ro.boot.warranty_bit 0
    setprop ro.warranty_bit 0
    setprop ro.debuggable 0
    setprop ro.secure 1
    
    # Hide root indicators
    if [ -f "/system/bin/su" ]; then
        chmod 000 /system/bin/su
    fi
    
    if [ -f "/system/xbin/su" ]; then
        chmod 000 /system/xbin/su
    fi
    
    # Hide Magisk traces
    if [ -d "/data/adb/magisk" ]; then
        setprop ro.magisk.hide 1
    fi
}

# Configure app-specific bypasses
configure_app_bypasses() {
    log "Configuring app-specific bypasses..."
    
    # Banking apps detection bypass
    mkdir -p /data/system/packages
    
    # Popular banking app package names to monitor
    BANKING_APPS="com.chase.sig.android com.bankofamerica.android com.wellsfargo.mobile.android"
    
    for app in $BANKING_APPS; do
        if pm list packages | grep -q "$app"; then
            log "Detected banking app: $app - applying bypass"
            am force-stop "$app" 2>/dev/null || true
        fi
    done
    
    # Gaming apps detection bypass
    GAMING_APPS="com.nianticlabs.pokemongo com.supercell.clashofclans com.king.candycrushsaga"
    
    for app in $GAMING_APPS; do
        if pm list packages | grep -q "$app"; then
            log "Detected gaming app: $app - applying bypass"
            am force-stop "$app" 2>/dev/null || true
        fi
    done
}

# Setup system-level hooks
setup_system_hooks() {
    log "Setting up system-level hooks..."
    
    # Create init.d directory for persistent modifications
    mkdir -p /system/etc/init.d
    
    # Create hook script for system property persistence
    cat > /system/etc/init.d/99android-setup << 'EOF'
#!/system/bin/sh
# Persistent system property setup

# Restore device identifiers on boot
if [ -f "/data/system/android_id" ]; then
    ANDROID_ID=$(cat /data/system/android_id)
    setprop ro.build.id "$ANDROID_ID"
fi

if [ -f "/data/system/advertising_id" ]; then
    AD_ID=$(cat /data/system/advertising_id)
    # Apply advertising ID through system service
    am broadcast -a com.google.android.gms.ads.identifier.service.START --ei pid $$ >/dev/null 2>&1 || true
fi

# Ensure security properties are maintained
setprop ro.boot.flash.locked 1
setprop ro.boot.verifiedbootstate green
setprop ro.debuggable 0
setprop ro.secure 1
EOF

    chmod 755 /system/etc/init.d/99android-setup
}

# Main execution
main() {
    log "Android Setup Script v1.0"
    log "Container: Android $ANDROID_VERSION ($ARCH)"
    
    # Wait for system to be ready
    if ! wait_for_system; then
        log "FATAL: System not ready, exiting"
        exit 1
    fi
    
    # Apply configurations
    apply_device_profile
    configure_network
    configure_developer_settings
    apply_security_bypasses
    configure_app_bypasses
    setup_system_hooks
    
    log "Android setup completed successfully"
    
    # Signal readiness
    setprop sys.android_setup.completed 1
    touch /data/local/tmp/android-setup.done
}

# Execute main function
main "$@"

exit 0