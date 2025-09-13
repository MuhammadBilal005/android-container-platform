#!/bin/bash

# Android Container Health Check Script
# Verifies that all Android container services are running properly

LOG_TAG="AndroidHealth"
HEALTH_LOG="/var/log/android-health.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$LOG_TAG] $1" | tee -a "$HEALTH_LOG"
}

# Health check result codes
HEALTH_OK=0
HEALTH_WARNING=1
HEALTH_CRITICAL=2

# Overall health status
OVERALL_HEALTH=$HEALTH_OK

# Check if Android system is booted
check_android_boot() {
    log "Checking Android boot status..."
    
    # Check if system property indicates boot completion
    if ! getprop sys.boot_completed 2>/dev/null | grep -q "1"; then
        log "ERROR: Android system not fully booted"
        OVERALL_HEALTH=$HEALTH_CRITICAL
        return 1
    fi
    
    log "Android system boot: OK"
    return 0
}

# Check essential system services
check_system_services() {
    log "Checking essential system services..."
    
    local services=(
        "android.hardware.location.provider.LocationProviderService"
        "com.google.android.gms.location.internal.GoogleLocationManagerService"
        "android.app.ActivityManager"
        "android.content.pm.PackageManager"
        "android.telephony.TelephonyManager"
    )
    
    local failed_services=0
    
    for service in "${services[@]}"; do
        if ! dumpsys "$service" >/dev/null 2>&1; then
            log "WARNING: Service $service not responding"
            failed_services=$((failed_services + 1))
        fi
    done
    
    if [ $failed_services -gt 0 ]; then
        log "WARNING: $failed_services essential services not responding"
        if [ $failed_services -gt 2 ]; then
            OVERALL_HEALTH=$HEALTH_CRITICAL
        else
            OVERALL_HEALTH=$HEALTH_WARNING
        fi
        return 1
    fi
    
    log "Essential system services: OK"
    return 0
}

# Check ADB connectivity
check_adb_status() {
    log "Checking ADB connectivity..."
    
    # Check if ADB port is listening
    if ! netstat -ln 2>/dev/null | grep -q ":5555"; then
        log "WARNING: ADB port 5555 not listening"
        OVERALL_HEALTH=$HEALTH_WARNING
        return 1
    fi
    
    # Check ADB daemon status
    if ! getprop service.adb.tcp.port 2>/dev/null | grep -q "5555"; then
        log "WARNING: ADB TCP not enabled on port 5555"
        OVERALL_HEALTH=$HEALTH_WARNING
        return 1
    fi
    
    log "ADB connectivity: OK"
    return 0
}

# Check integrity bypass status
check_integrity_bypass() {
    log "Checking integrity bypass status..."
    
    # Check if bypass completion marker exists
    if [ ! -f "/data/local/tmp/integrity-bypass.done" ]; then
        log "WARNING: Integrity bypass not completed"
        OVERALL_HEALTH=$HEALTH_WARNING
        return 1
    fi
    
    # Check critical security properties
    local security_props=(
        "ro.boot.verifiedbootstate=green"
        "ro.boot.flash.locked=1"
        "ro.debuggable=0"
        "ro.secure=1"
    )
    
    for prop in "${security_props[@]}"; do
        key=$(echo "$prop" | cut -d= -f1)
        expected_value=$(echo "$prop" | cut -d= -f2)
        actual_value=$(getprop "$key" 2>/dev/null || echo "")
        
        if [ "$actual_value" != "$expected_value" ]; then
            log "WARNING: Security property $key = '$actual_value' (expected '$expected_value')"
            OVERALL_HEALTH=$HEALTH_WARNING
        fi
    done
    
    # Check if Magisk is properly hidden
    if [ -x "/system/bin/su" ] && [ "$(stat -c %a /system/bin/su)" != "000" ]; then
        log "WARNING: Root access not properly hidden"
        OVERALL_HEALTH=$HEALTH_WARNING
    fi
    
    log "Integrity bypass: OK"
    return 0
}

# Check GPS injection status
check_gps_injection() {
    log "Checking GPS injection status..."
    
    # Check if GPS injection completion marker exists
    if [ ! -f "/data/local/tmp/gps-injection.done" ]; then
        log "WARNING: GPS injection not completed"
        OVERALL_HEALTH=$HEALTH_WARNING
        return 1
    fi
    
    # Check if GPS service is running
    if [ ! -f "/data/local/tmp/gps_service.pid" ]; then
        log "WARNING: GPS service PID file not found"
        OVERALL_HEALTH=$HEALTH_WARNING
        return 1
    fi
    
    local gps_pid=$(cat /data/local/tmp/gps_service.pid 2>/dev/null)
    if [ -n "$gps_pid" ] && ! kill -0 "$gps_pid" 2>/dev/null; then
        log "WARNING: GPS service not running (PID: $gps_pid)"
        OVERALL_HEALTH=$HEALTH_WARNING
        return 1
    fi
    
    # Check if location data is being generated
    if [ ! -f "/data/local/tmp/current_location.json" ]; then
        log "WARNING: No current location data found"
        OVERALL_HEALTH=$HEALTH_WARNING
        return 1
    fi
    
    # Check if location data is recent (within last 5 minutes)
    local location_file="/data/local/tmp/current_location.json"
    local file_age=$(($(date +%s) - $(stat -c %Y "$location_file" 2>/dev/null || echo 0)))
    if [ $file_age -gt 300 ]; then
        log "WARNING: Location data is stale (${file_age}s old)"
        OVERALL_HEALTH=$HEALTH_WARNING
        return 1
    fi
    
    log "GPS injection: OK"
    return 0
}

# Check device spoofing
check_device_spoofing() {
    log "Checking device spoofing status..."
    
    # Check if android setup completion marker exists
    if [ ! -f "/data/local/tmp/android-setup.done" ]; then
        log "WARNING: Android setup not completed"
        OVERALL_HEALTH=$HEALTH_WARNING
        return 1
    fi
    
    # Verify core device properties are set
    local device_props=(
        "ro.product.model"
        "ro.product.brand"
        "ro.product.manufacturer"
        "ro.build.fingerprint"
    )
    
    for prop in "${device_props[@]}"; do
        if ! getprop "$prop" 2>/dev/null | grep -q "."; then
            log "WARNING: Device property $prop not set"
            OVERALL_HEALTH=$HEALTH_WARNING
        fi
    done
    
    # Check if device identifiers are generated
    if [ ! -f "/data/system/android_id" ]; then
        log "WARNING: Android ID not generated"
        OVERALL_HEALTH=$HEALTH_WARNING
    fi
    
    log "Device spoofing: OK"
    return 0
}

# Check system resources
check_system_resources() {
    log "Checking system resources..."
    
    # Check memory usage
    local mem_info=$(cat /proc/meminfo)
    local mem_total=$(echo "$mem_info" | grep MemTotal | awk '{print $2}')
    local mem_available=$(echo "$mem_info" | grep MemAvailable | awk '{print $2}')
    local mem_used_percent=$(( (mem_total - mem_available) * 100 / mem_total ))
    
    if [ $mem_used_percent -gt 90 ]; then
        log "WARNING: High memory usage: ${mem_used_percent}%"
        OVERALL_HEALTH=$HEALTH_WARNING
    elif [ $mem_used_percent -gt 95 ]; then
        log "CRITICAL: Very high memory usage: ${mem_used_percent}%"
        OVERALL_HEALTH=$HEALTH_CRITICAL
    fi
    
    # Check disk usage for critical partitions
    local partitions=("/data" "/system" "/tmp")
    
    for partition in "${partitions[@]}"; do
        if mountpoint -q "$partition" 2>/dev/null; then
            local disk_usage=$(df "$partition" | tail -1 | awk '{print $5}' | sed 's/%//')
            if [ "$disk_usage" -gt 85 ]; then
                log "WARNING: High disk usage on $partition: ${disk_usage}%"
                OVERALL_HEALTH=$HEALTH_WARNING
            elif [ "$disk_usage" -gt 95 ]; then
                log "CRITICAL: Very high disk usage on $partition: ${disk_usage}%"
                OVERALL_HEALTH=$HEALTH_CRITICAL
            fi
        fi
    done
    
    # Check CPU load
    local load_avg=$(cat /proc/loadavg | awk '{print $1}')
    local cpu_count=$(nproc)
    local load_percent=$(echo "$load_avg $cpu_count" | awk '{printf "%.0f", ($1/$2)*100}')
    
    if [ "$load_percent" -gt 80 ]; then
        log "WARNING: High CPU load: ${load_percent}%"
        OVERALL_HEALTH=$HEALTH_WARNING
    fi
    
    log "System resources: OK (Memory: ${mem_used_percent}%, Load: ${load_percent}%)"
    return 0
}

# Check network connectivity
check_network_connectivity() {
    log "Checking network connectivity..."
    
    # Check if network interfaces are up
    if ! ip link show | grep -q "state UP"; then
        log "WARNING: No network interfaces are up"
        OVERALL_HEALTH=$HEALTH_WARNING
        return 1
    fi
    
    # Check DNS resolution
    if ! nslookup google.com >/dev/null 2>&1; then
        log "WARNING: DNS resolution not working"
        OVERALL_HEALTH=$HEALTH_WARNING
        return 1
    fi
    
    # Check internet connectivity
    if ! ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1; then
        log "WARNING: No internet connectivity"
        OVERALL_HEALTH=$HEALTH_WARNING
        return 1
    fi
    
    log "Network connectivity: OK"
    return 0
}

# Generate health summary
generate_health_summary() {
    local health_status=""
    case $OVERALL_HEALTH in
        $HEALTH_OK)
            health_status="HEALTHY"
            ;;
        $HEALTH_WARNING)
            health_status="WARNING"
            ;;
        $HEALTH_CRITICAL)
            health_status="CRITICAL"
            ;;
    esac
    
    log "=== HEALTH CHECK SUMMARY ==="
    log "Overall Status: $health_status"
    log "Timestamp: $(date)"
    log "Container ID: ${HOSTNAME:-unknown}"
    log "Android Version: $(getprop ro.build.version.release 2>/dev/null || echo 'unknown')"
    log "============================"
    
    # Write status to health status file
    echo "$health_status" > /tmp/health_status
    echo "$(date +%s)" > /tmp/health_timestamp
}

# Main health check execution
main() {
    log "Starting Android container health check..."
    
    # Ensure log directory exists
    mkdir -p "$(dirname "$HEALTH_LOG")"
    
    # Run all health checks
    check_android_boot
    check_system_services
    check_adb_status
    check_integrity_bypass
    check_gps_injection
    check_device_spoofing
    check_system_resources
    check_network_connectivity
    
    # Generate summary
    generate_health_summary
    
    # Exit with appropriate code for Docker health check
    exit $OVERALL_HEALTH
}

# Run main function
main "$@"