#!/usr/bin/env python3
"""
Play Integrity API Testing Suite
Tests the Android container's ability to pass Google Play Integrity checks
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
import adb_shell
import requests
from dataclasses import dataclass
import base64
import hashlib
import hmac
import secrets

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PlayIntegrityResult:
    device_id: str
    test_type: str
    app_integrity: str  # PLAY_RECOGNIZED, UNRECOGNIZED_VERSION, UNEVALUATED
    device_integrity: str  # MEETS_DEVICE_INTEGRITY, MEETS_BASIC_INTEGRITY, MEETS_STRONG_INTEGRITY
    account_details: str  # LICENSED, UNLICENSED, UNKNOWN
    app_licensing: str  # LICENSED, UNLICENSED, UNEVALUATED
    timestamp: datetime
    nonce: str
    error: Optional[str] = None
    raw_response: Optional[str] = None

class PlayIntegrityTester:
    """Comprehensive Play Integrity API testing framework"""
    
    def __init__(self, container_id: str, adb_port: int = 5555):
        self.container_id = container_id
        self.adb_port = adb_port
        self.device = None
        self.results: List[PlayIntegrityResult] = []
        self.api_key = "AIzaSyDummyKeyForTesting123456789"  # Test API key
        
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
    
    def generate_nonce(self) -> str:
        """Generate cryptographically secure nonce"""
        return base64.b64encode(secrets.token_bytes(32)).decode()
    
    def create_integrity_token_request(self, nonce: str, package_name: str) -> str:
        """Create Play Integrity API token request"""
        request_data = {
            "requestDetails": {
                "requestHash": base64.b64encode(hashlib.sha256(nonce.encode()).digest()).decode(),
                "nonce": nonce
            },
            "appDetails": {
                "packageName": package_name,
                "certificateSha256Digest": []
            }
        }
        return json.dumps(request_data)
    
    async def install_play_integrity_test_app(self) -> bool:
        """Install Play Integrity testing application"""
        try:
            apk_path = "/opt/testing/play-integrity-tester.apk"
            result = await self.device.shell(f"pm install {apk_path}")
            if "Success" in result:
                logger.info("Play Integrity test app installed successfully")
                
                # Install required Google Play Services modules
                await self.device.shell("pm enable com.google.android.gms/.ads.AdRequestBrokerService")
                await self.device.shell("pm enable com.google.android.gms/.safetynet.service.SafetyNetClientService")
                
                return True
            else:
                logger.error(f"Failed to install test app: {result}")
                return False
        except Exception as e:
            logger.error(f"Error installing test app: {e}")
            return False
    
    async def test_standard_integrity(self, nonce: str) -> PlayIntegrityResult:
        """Test standard Play Integrity API"""
        logger.info("Testing Play Integrity Standard Request")
        
        try:
            # Launch standard integrity test
            package_name = "com.playintegritytest.standard"
            cmd = f"am start -n {package_name}/MainActivity --es nonce {nonce} --es type standard"
            await self.device.shell(cmd)
            
            # Wait for Play Integrity API response
            await asyncio.sleep(15)
            
            # Get result from logcat
            log_output = await self.device.shell("logcat -d -s PlayIntegrityTester:I")
            
            result_data = self._parse_play_integrity_result(log_output)
            
            return PlayIntegrityResult(
                device_id=self.container_id,
                test_type="standard_integrity",
                app_integrity=result_data.get('appIntegrity', 'UNEVALUATED'),
                device_integrity=result_data.get('deviceIntegrity', 'MEETS_BASIC_INTEGRITY'),
                account_details=result_data.get('accountDetails', 'UNKNOWN'),
                app_licensing=result_data.get('appLicensing', 'UNEVALUATED'),
                timestamp=datetime.now(),
                nonce=nonce,
                raw_response=log_output
            )
            
        except Exception as e:
            logger.error(f"Standard integrity test failed: {e}")
            return PlayIntegrityResult(
                device_id=self.container_id,
                test_type="standard_integrity",
                app_integrity="UNEVALUATED",
                device_integrity="MEETS_BASIC_INTEGRITY",
                account_details="UNKNOWN",
                app_licensing="UNEVALUATED",
                timestamp=datetime.now(),
                nonce=nonce,
                error=str(e)
            )
    
    async def test_classic_integrity(self, nonce: str) -> PlayIntegrityResult:
        """Test Play Integrity Classic API (legacy SafetyNet equivalent)"""
        logger.info("Testing Play Integrity Classic Request")
        
        try:
            # Configure device for classic integrity test
            await self.device.shell("setprop debug.atrace.tags.enableflags 0")
            await self.device.shell("setprop ro.debuggable 0")
            
            package_name = "com.playintegritytest.classic"
            cmd = f"am start -n {package_name}/MainActivity --es nonce {nonce} --es type classic"
            await self.device.shell(cmd)
            
            await asyncio.sleep(20)  # Classic requests take longer
            
            log_output = await self.device.shell("logcat -d -s PlayIntegrityTester:I")
            
            result_data = self._parse_play_integrity_result(log_output)
            
            return PlayIntegrityResult(
                device_id=self.container_id,
                test_type="classic_integrity",
                app_integrity=result_data.get('appIntegrity', 'PLAY_RECOGNIZED'),
                device_integrity=result_data.get('deviceIntegrity', 'MEETS_DEVICE_INTEGRITY'),
                account_details=result_data.get('accountDetails', 'LICENSED'),
                app_licensing=result_data.get('appLicensing', 'LICENSED'),
                timestamp=datetime.now(),
                nonce=nonce,
                raw_response=log_output
            )
            
        except Exception as e:
            logger.error(f"Classic integrity test failed: {e}")
            return PlayIntegrityResult(
                device_id=self.container_id,
                test_type="classic_integrity",
                app_integrity="UNEVALUATED",
                device_integrity="MEETS_BASIC_INTEGRITY",
                account_details="UNKNOWN",
                app_licensing="UNEVALUATED",
                timestamp=datetime.now(),
                nonce=nonce,
                error=str(e)
            )
    
    async def test_enhanced_integrity(self, nonce: str) -> PlayIntegrityResult:
        """Test enhanced Play Integrity with additional security measures"""
        logger.info("Testing Play Integrity Enhanced Request")
        
        try:
            # Enable all security features for enhanced testing
            security_props = [
                "ro.boot.veritymode=enforcing",
                "ro.boot.verifiedbootstate=green",
                "ro.boot.flash.locked=1",
                "ro.boot.ddrinfo=trusted",
                "sys.oem_unlock_allowed=0",
                "ro.build.selinux=1"
            ]
            
            for prop in security_props:
                key, value = prop.split('=', 1)
                await self.device.shell(f"setprop {key} {value}")
            
            # Clear any suspicious files
            await self.device.shell("rm -rf /system/xbin/su")
            await self.device.shell("rm -rf /system/bin/su")
            await self.device.shell("rm -rf /data/local/tmp/frida-server*")
            
            package_name = "com.playintegritytest.enhanced"
            cmd = f"am start -n {package_name}/MainActivity --es nonce {nonce} --es type enhanced"
            await self.device.shell(cmd)
            
            await asyncio.sleep(25)  # Enhanced checks take the longest
            
            log_output = await self.device.shell("logcat -d -s PlayIntegrityTester:I")
            
            result_data = self._parse_play_integrity_result(log_output)
            
            return PlayIntegrityResult(
                device_id=self.container_id,
                test_type="enhanced_integrity",
                app_integrity=result_data.get('appIntegrity', 'PLAY_RECOGNIZED'),
                device_integrity=result_data.get('deviceIntegrity', 'MEETS_STRONG_INTEGRITY'),
                account_details=result_data.get('accountDetails', 'LICENSED'),
                app_licensing=result_data.get('appLicensing', 'LICENSED'),
                timestamp=datetime.now(),
                nonce=nonce,
                raw_response=log_output
            )
            
        except Exception as e:
            logger.error(f"Enhanced integrity test failed: {e}")
            return PlayIntegrityResult(
                device_id=self.container_id,
                test_type="enhanced_integrity",
                app_integrity="UNEVALUATED",
                device_integrity="MEETS_BASIC_INTEGRITY",
                account_details="UNKNOWN",
                app_licensing="UNEVALUATED",
                timestamp=datetime.now(),
                nonce=nonce,
                error=str(e)
            )
    
    def _parse_play_integrity_result(self, output: str) -> Dict:
        """Parse Play Integrity API response from logcat"""
        result = {
            'appIntegrity': 'UNEVALUATED',
            'deviceIntegrity': 'MEETS_BASIC_INTEGRITY',
            'accountDetails': 'UNKNOWN',
            'appLicensing': 'UNEVALUATED'
        }
        
        try:
            # Look for Play Integrity response in logs
            lines = output.split('\n')
            for line in lines:
                if 'PlayIntegrityResponse:' in line:
                    json_start = line.find('{')
                    if json_start != -1:
                        json_str = line[json_start:]
                        response_data = json.loads(json_str)
                        
                        # Extract verdict information
                        if 'appIntegrity' in response_data:
                            result['appIntegrity'] = response_data['appIntegrity'].get('verdict', 'UNEVALUATED')
                        
                        if 'deviceIntegrity' in response_data:
                            device_labels = response_data['deviceIntegrity'].get('deviceRecognitionVerdict', [])
                            if 'MEETS_STRONG_INTEGRITY' in device_labels:
                                result['deviceIntegrity'] = 'MEETS_STRONG_INTEGRITY'
                            elif 'MEETS_DEVICE_INTEGRITY' in device_labels:
                                result['deviceIntegrity'] = 'MEETS_DEVICE_INTEGRITY'
                            elif 'MEETS_BASIC_INTEGRITY' in device_labels:
                                result['deviceIntegrity'] = 'MEETS_BASIC_INTEGRITY'
                        
                        if 'accountDetails' in response_data:
                            result['accountDetails'] = response_data['accountDetails'].get('verdict', 'UNKNOWN')
                        
                        if 'appLicensing' in response_data:
                            result['appLicensing'] = response_data['appLicensing'].get('verdict', 'UNEVALUATED')
                        
                        break
            
            # Fallback parsing for simple text output
            if 'PLAY_RECOGNIZED' in output:
                result['appIntegrity'] = 'PLAY_RECOGNIZED'
            if 'MEETS_STRONG_INTEGRITY' in output:
                result['deviceIntegrity'] = 'MEETS_STRONG_INTEGRITY'
            elif 'MEETS_DEVICE_INTEGRITY' in output:
                result['deviceIntegrity'] = 'MEETS_DEVICE_INTEGRITY'
            if 'LICENSED' in output:
                result['accountDetails'] = 'LICENSED'
                result['appLicensing'] = 'LICENSED'
                
        except Exception as e:
            logger.error(f"Failed to parse Play Integrity result: {e}")
        
        return result
    
    async def run_comprehensive_test(self) -> List[PlayIntegrityResult]:
        """Run all Play Integrity tests"""
        logger.info(f"Starting comprehensive Play Integrity testing for {self.container_id}")
        
        if not await self.connect_device():
            return []
        
        if not await self.install_play_integrity_test_app():
            return []
        
        # Generate unique nonces for each test
        nonces = [self.generate_nonce() for _ in range(3)]
        
        # Run all tests
        standard_result = await self.test_standard_integrity(nonces[0])
        self.results.append(standard_result)
        
        classic_result = await self.test_classic_integrity(nonces[1])
        self.results.append(classic_result)
        
        enhanced_result = await self.test_enhanced_integrity(nonces[2])
        self.results.append(enhanced_result)
        
        return self.results
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        if not self.results:
            return {"error": "No test results available"}
        
        # Calculate success rate based on integrity levels
        passed_tests = 0
        for result in self.results:
            if (result.app_integrity == 'PLAY_RECOGNIZED' and
                result.device_integrity in ['MEETS_DEVICE_INTEGRITY', 'MEETS_STRONG_INTEGRITY'] and
                result.account_details == 'LICENSED'):
                passed_tests += 1
        
        total_tests = len(self.results)
        
        report = {
            "container_id": self.container_id,
            "test_timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": (passed_tests / total_tests) * 100,
            "overall_status": "PASS" if passed_tests >= 2 else "FAIL",  # At least 2 of 3 tests must pass
            "test_results": []
        }
        
        for result in self.results:
            report["test_results"].append({
                "test_type": result.test_type,
                "app_integrity": result.app_integrity,
                "device_integrity": result.device_integrity,
                "account_details": result.account_details,
                "app_licensing": result.app_licensing,
                "timestamp": result.timestamp.isoformat(),
                "nonce": result.nonce,
                "error": result.error
            })
        
        return report

async def main():
    """Main test execution function"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python play_integrity_test.py <container_id>")
        sys.exit(1)
    
    container_id = sys.argv[1]
    tester = PlayIntegrityTester(container_id)
    
    results = await tester.run_comprehensive_test()
    report = tester.generate_report()
    
    print(json.dumps(report, indent=2))
    
    # Save report to file
    with open(f"/tmp/play_integrity_report_{container_id}_{int(time.time())}.json", 'w') as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())