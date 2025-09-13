#!/usr/bin/env python3
"""
Root Detection Bypass Testing Suite
Tests various root detection mechanisms and validates bypass effectiveness
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import adb_shell
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RootDetectionResult:
    device_id: str
    detection_method: str
    detected: bool
    bypass_status: str  # SUCCESS, FAILED, PARTIAL
    details: str
    timestamp: datetime
    error: Optional[str] = None

class RootDetectionTester:
    """Comprehensive root detection bypass testing framework"""
    
    def __init__(self, container_id: str, adb_port: int = 5555):
        self.container_id = container_id
        self.adb_port = adb_port
        self.device = None
        self.results: List[RootDetectionResult] = []
        
    async def connect_device(self) -> bool:
        """Connect to Android container via ADB"""
        try:
            from adb_shell.adb_device import AdbDeviceTcp
            self.device = AdbDeviceTcp(host='localhost', port=self.adb_port)
            await self.device.connect()
            logger.info(f"Connected to container {self.container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to device: {e}")
            return False
    
    async def test_su_binary_detection(self) -> RootDetectionResult:
        """Test detection of su binary files"""
        logger.info("Testing SU binary detection")
        
        try:
            # Check common su binary locations
            su_locations = [
                "/system/bin/su",
                "/system/xbin/su", 
                "/system/sbin/su",
                "/vendor/bin/su",
                "/sbin/su",
                "/data/local/tmp/su",
                "/data/local/bin/su"
            ]
            
            detected_binaries = []
            for location in su_locations:
                result = await self.device.shell(f"ls {location} 2>/dev/null")
                if location in result and "No such file" not in result:
                    detected_binaries.append(location)
            
            detected = len(detected_binaries) > 0
            bypass_status = "FAILED" if detected else "SUCCESS"
            
            details = f"SU binaries found: {detected_binaries}" if detected else "No SU binaries detected"
            
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="su_binary",
                detected=detected,
                bypass_status=bypass_status,
                details=details,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"SU binary test failed: {e}")
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="su_binary",
                detected=True,
                bypass_status="FAILED",
                details="Test execution failed",
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def test_build_tags_detection(self) -> RootDetectionResult:
        """Test detection via build tags"""
        logger.info("Testing build tags detection")
        
        try:
            # Check build tags for root indicators
            build_tags = await self.device.shell("getprop ro.build.tags")
            build_type = await self.device.shell("getprop ro.build.type")
            debuggable = await self.device.shell("getprop ro.debuggable")
            secure = await self.device.shell("getprop ro.secure")
            
            # Root indicators in build properties
            root_indicators = [
                ("test-keys" in build_tags.lower(), "test-keys in ro.build.tags"),
                (build_type.strip() != "user", f"ro.build.type is '{build_type.strip()}' (should be 'user')"),
                (debuggable.strip() == "1", "ro.debuggable is enabled"),
                (secure.strip() == "0", "ro.secure is disabled")
            ]
            
            detected_issues = [issue for detected, issue in root_indicators if detected]
            detected = len(detected_issues) > 0
            bypass_status = "FAILED" if detected else "SUCCESS"
            
            details = f"Build issues: {detected_issues}" if detected else "Build properties appear legitimate"
            
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="build_tags",
                detected=detected,
                bypass_status=bypass_status,
                details=details,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Build tags test failed: {e}")
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="build_tags",
                detected=True,
                bypass_status="FAILED",
                details="Test execution failed",
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def test_root_management_apps(self) -> RootDetectionResult:
        """Test detection of root management applications"""
        logger.info("Testing root management app detection")
        
        try:
            # Common root management apps
            root_apps = [
                "com.noshufou.android.su",
                "com.noshufou.android.su.elite", 
                "eu.chainfire.supersu",
                "com.koushikdutta.superuser",
                "com.thirdparty.superuser",
                "com.yellowes.su",
                "com.topjohnwu.magisk",
                "com.kingroot.kinguser",
                "com.kingo.root",
                "com.smedialink.oneclickroot",
                "com.zhiqupk.root.global",
                "com.alephzain.framaroot"
            ]
            
            detected_apps = []
            for app in root_apps:
                result = await self.device.shell(f"pm list packages {app}")
                if app in result:
                    detected_apps.append(app)
            
            detected = len(detected_apps) > 0
            bypass_status = "FAILED" if detected else "SUCCESS"
            
            details = f"Root apps found: {detected_apps}" if detected else "No root management apps detected"
            
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="root_apps",
                detected=detected,
                bypass_status=bypass_status,
                details=details,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Root apps test failed: {e}")
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="root_apps",
                detected=True,
                bypass_status="FAILED",
                details="Test execution failed",
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def test_dangerous_properties(self) -> RootDetectionResult:
        """Test detection of dangerous system properties"""
        logger.info("Testing dangerous properties detection")
        
        try:
            # Dangerous properties that indicate root
            dangerous_props = [
                ("service.adb.root", "1"),
                ("ro.debuggable", "1"), 
                ("ro.secure", "0"),
                ("ro.boot.veritymode", "disabled"),
                ("ro.boot.verifiedbootstate", "orange"),
                ("ro.boot.flash.locked", "0")
            ]
            
            detected_props = []
            for prop, dangerous_value in dangerous_props:
                result = await self.device.shell(f"getprop {prop}")
                if result.strip() == dangerous_value:
                    detected_props.append(f"{prop}={dangerous_value}")
            
            detected = len(detected_props) > 0
            bypass_status = "FAILED" if detected else "SUCCESS"
            
            details = f"Dangerous properties: {detected_props}" if detected else "No dangerous properties detected"
            
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="dangerous_properties",
                detected=detected,
                bypass_status=bypass_status,
                details=details,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Dangerous properties test failed: {e}")
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="dangerous_properties",
                detected=True,
                bypass_status="FAILED",
                details="Test execution failed",
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def test_rw_paths_detection(self) -> RootDetectionResult:
        """Test detection of read-write access to system paths"""
        logger.info("Testing RW paths detection")
        
        try:
            # System paths that should not be writable
            system_paths = [
                "/system",
                "/system/bin",
                "/system/sbin",
                "/system/xbin", 
                "/vendor/bin",
                "/sbin"
            ]
            
            writable_paths = []
            for path in system_paths:
                # Try to create a test file
                test_file = f"{path}/.root_test_{int(time.time())}"
                result = await self.device.shell(f"touch {test_file} 2>/dev/null && echo 'writable' && rm {test_file}")
                if "writable" in result:
                    writable_paths.append(path)
            
            detected = len(writable_paths) > 0
            bypass_status = "FAILED" if detected else "SUCCESS"
            
            details = f"Writable system paths: {writable_paths}" if detected else "System paths properly protected"
            
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="rw_paths",
                detected=detected,
                bypass_status=bypass_status,
                details=details,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"RW paths test failed: {e}")
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="rw_paths",
                detected=True,
                bypass_status="FAILED",
                details="Test execution failed",
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def test_selinux_status(self) -> RootDetectionResult:
        """Test SELinux enforcement status"""
        logger.info("Testing SELinux status")
        
        try:
            selinux_status = await self.device.shell("getenforce")
            selinux_status = selinux_status.strip().lower()
            
            # SELinux should be enforcing for non-rooted devices
            detected = selinux_status != "enforcing"
            bypass_status = "FAILED" if detected else "SUCCESS"
            
            details = f"SELinux status: {selinux_status}" + (" (should be 'Enforcing')" if detected else " (correct)")
            
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="selinux_status",
                detected=detected,
                bypass_status=bypass_status,
                details=details,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"SELinux test failed: {e}")
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="selinux_status",
                detected=True,
                bypass_status="FAILED",
                details="Test execution failed",
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def test_magisk_detection(self) -> RootDetectionResult:
        """Test Magisk-specific detection methods"""
        logger.info("Testing Magisk detection")
        
        try:
            # Magisk-specific indicators
            magisk_indicators = []
            
            # Check for Magisk files
            magisk_files = [
                "/data/adb/magisk",
                "/data/adb/modules", 
                "/sbin/.magisk",
                "/dev/.magisk",
                "/cache/.magisk",
                "/data/user_de/0/com.topjohnwu.magisk"
            ]
            
            for file_path in magisk_files:
                result = await self.device.shell(f"ls {file_path} 2>/dev/null")
                if file_path in result and "No such file" not in result:
                    magisk_indicators.append(f"File: {file_path}")
            
            # Check for Magisk processes
            processes = await self.device.shell("ps -A | grep magisk")
            if "magisk" in processes:
                magisk_indicators.append("Magisk processes detected")
            
            # Check for Magisk properties
            magisk_props = await self.device.shell("getprop | grep magisk")
            if "magisk" in magisk_props.lower():
                magisk_indicators.append("Magisk properties found")
            
            detected = len(magisk_indicators) > 0
            bypass_status = "FAILED" if detected else "SUCCESS"
            
            details = f"Magisk indicators: {magisk_indicators}" if detected else "No Magisk traces detected"
            
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="magisk_detection",
                detected=detected,
                bypass_status=bypass_status,
                details=details,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Magisk test failed: {e}")
            return RootDetectionResult(
                device_id=self.container_id,
                detection_method="magisk_detection",
                detected=True,
                bypass_status="FAILED",
                details="Test execution failed",
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def run_comprehensive_test(self) -> List[RootDetectionResult]:
        """Run all root detection tests"""
        logger.info(f"Starting comprehensive root detection testing for {self.container_id}")
        
        if not await self.connect_device():
            return []
        
        # Run all tests
        tests = [
            self.test_su_binary_detection(),
            self.test_build_tags_detection(), 
            self.test_root_management_apps(),
            self.test_dangerous_properties(),
            self.test_rw_paths_detection(),
            self.test_selinux_status(),
            self.test_magisk_detection()
        ]
        
        self.results = await asyncio.gather(*tests)
        return self.results
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        if not self.results:
            return {"error": "No test results available"}
        
        # Calculate bypass success rate
        successful_bypasses = sum(1 for r in self.results if r.bypass_status == "SUCCESS")
        total_tests = len(self.results)
        
        report = {
            "container_id": self.container_id,
            "test_timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "successful_bypasses": successful_bypasses,
            "bypass_rate": (successful_bypasses / total_tests) * 100,
            "overall_status": "PASS" if successful_bypasses == total_tests else "FAIL",
            "test_results": []
        }
        
        for result in self.results:
            report["test_results"].append({
                "detection_method": result.detection_method,
                "detected": result.detected,
                "bypass_status": result.bypass_status,
                "details": result.details,
                "timestamp": result.timestamp.isoformat(),
                "error": result.error
            })
        
        return report

async def main():
    """Main test execution function"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python root_detection_test.py <container_id>")
        sys.exit(1)
    
    container_id = sys.argv[1]
    tester = RootDetectionTester(container_id)
    
    results = await tester.run_comprehensive_test()
    report = tester.generate_report()
    
    print(json.dumps(report, indent=2))
    
    # Save report to file
    with open(f"/tmp/root_detection_report_{container_id}_{int(time.time())}.json", 'w') as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())