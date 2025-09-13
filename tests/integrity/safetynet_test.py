#!/usr/bin/env python3
"""
SafetyNet API Testing Suite
Tests the Android container's ability to pass SafetyNet attestation checks
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import adb_shell
import requests
from dataclasses import dataclass
import base64
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SafetyNetResult:
    device_id: str
    test_type: str
    basic_integrity: bool
    cts_profile_match: bool
    evaluation_type: str
    nonce: str
    timestamp: datetime
    advice: str
    error: Optional[str] = None
    raw_response: Optional[str] = None

class SafetyNetTester:
    """Comprehensive SafetyNet API testing framework"""
    
    def __init__(self, container_id: str, adb_port: int = 5555):
        self.container_id = container_id
        self.adb_port = adb_port
        self.device = None
        self.results: List[SafetyNetResult] = []
        
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
        """Generate cryptographically secure nonce for SafetyNet request"""
        import secrets
        return base64.b64encode(secrets.token_bytes(32)).decode()
    
    async def install_safetynet_test_app(self) -> bool:
        """Install custom SafetyNet testing application"""
        try:
            # Install the test APK
            apk_path = "/opt/testing/safetynet-tester.apk"
            result = await self.device.shell(f"pm install {apk_path}")
            if "Success" in result:
                logger.info("SafetyNet test app installed successfully")
                return True
            else:
                logger.error(f"Failed to install test app: {result}")
                return False
        except Exception as e:
            logger.error(f"Error installing test app: {e}")
            return False
    
    async def test_basic_integrity(self, nonce: str) -> SafetyNetResult:
        """Test basic SafetyNet integrity"""
        logger.info("Testing SafetyNet Basic Integrity")
        
        try:
            # Launch SafetyNet test with basic integrity check
            cmd = f"am start -n com.safetynettest/MainActivity --es nonce {nonce} --es type basic"
            await self.device.shell(cmd)
            
            # Wait for result
            await asyncio.sleep(10)
            
            # Get result from test app
            result_cmd = "am broadcast -a com.safetynettest.RESULT"
            output = await self.device.shell(result_cmd)
            
            # Parse result
            result_data = self._parse_safetynet_result(output)
            
            return SafetyNetResult(
                device_id=self.container_id,
                test_type="basic_integrity",
                basic_integrity=result_data.get('basicIntegrity', False),
                cts_profile_match=result_data.get('ctsProfileMatch', False),
                evaluation_type=result_data.get('evaluationType', 'UNKNOWN'),
                nonce=nonce,
                timestamp=datetime.now(),
                advice=result_data.get('advice', ''),
                raw_response=output
            )
            
        except Exception as e:
            logger.error(f"Basic integrity test failed: {e}")
            return SafetyNetResult(
                device_id=self.container_id,
                test_type="basic_integrity",
                basic_integrity=False,
                cts_profile_match=False,
                evaluation_type="ERROR",
                nonce=nonce,
                timestamp=datetime.now(),
                advice="",
                error=str(e)
            )
    
    async def test_device_integrity(self, nonce: str) -> SafetyNetResult:
        """Test SafetyNet device integrity (hardware attestation)"""
        logger.info("Testing SafetyNet Device Integrity")
        
        try:
            # Test with hardware attestation
            cmd = f"am start -n com.safetynettest/MainActivity --es nonce {nonce} --es type device"
            await self.device.shell(cmd)
            
            await asyncio.sleep(15)  # Device integrity takes longer
            
            result_cmd = "am broadcast -a com.safetynettest.RESULT"
            output = await self.device.shell(result_cmd)
            
            result_data = self._parse_safetynet_result(output)
            
            return SafetyNetResult(
                device_id=self.container_id,
                test_type="device_integrity",
                basic_integrity=result_data.get('basicIntegrity', False),
                cts_profile_match=result_data.get('ctsProfileMatch', False),
                evaluation_type=result_data.get('evaluationType', 'UNKNOWN'),
                nonce=nonce,
                timestamp=datetime.now(),
                advice=result_data.get('advice', ''),
                raw_response=output
            )
            
        except Exception as e:
            logger.error(f"Device integrity test failed: {e}")
            return SafetyNetResult(
                device_id=self.container_id,
                test_type="device_integrity",
                basic_integrity=False,
                cts_profile_match=False,
                evaluation_type="ERROR",
                nonce=nonce,
                timestamp=datetime.now(),
                advice="",
                error=str(e)
            )
    
    async def test_strong_integrity(self, nonce: str) -> SafetyNetResult:
        """Test SafetyNet strong integrity with additional checks"""
        logger.info("Testing SafetyNet Strong Integrity")
        
        try:
            # Enable additional security features
            await self.device.shell("setprop security.perf_harden 1")
            await self.device.shell("setprop ro.boot.verifyboot green")
            await self.device.shell("setprop ro.boot.flash.locked 1")
            
            cmd = f"am start -n com.safetynettest/MainActivity --es nonce {nonce} --es type strong"
            await self.device.shell(cmd)
            
            await asyncio.sleep(20)  # Strong integrity takes the longest
            
            result_cmd = "am broadcast -a com.safetynettest.RESULT"
            output = await self.device.shell(result_cmd)
            
            result_data = self._parse_safetynet_result(output)
            
            return SafetyNetResult(
                device_id=self.container_id,
                test_type="strong_integrity",
                basic_integrity=result_data.get('basicIntegrity', False),
                cts_profile_match=result_data.get('ctsProfileMatch', False),
                evaluation_type=result_data.get('evaluationType', 'UNKNOWN'),
                nonce=nonce,
                timestamp=datetime.now(),
                advice=result_data.get('advice', ''),
                raw_response=output
            )
            
        except Exception as e:
            logger.error(f"Strong integrity test failed: {e}")
            return SafetyNetResult(
                device_id=self.container_id,
                test_type="strong_integrity",
                basic_integrity=False,
                cts_profile_match=False,
                evaluation_type="ERROR",
                nonce=nonce,
                timestamp=datetime.now(),
                advice="",
                error=str(e)
            )
    
    def _parse_safetynet_result(self, output: str) -> Dict:
        """Parse SafetyNet API response"""
        try:
            # Extract JSON from broadcast result
            start_idx = output.find('{')
            end_idx = output.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = output[start_idx:end_idx]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse SafetyNet result: {e}")
        
        # Fallback parsing for non-JSON output
        result = {
            'basicIntegrity': 'basicIntegrity: true' in output.lower(),
            'ctsProfileMatch': 'ctsprofilematch: true' in output.lower(),
            'evaluationType': 'BASIC' if 'basic' in output.lower() else 'UNKNOWN',
            'advice': ''
        }
        
        if 'advice:' in output.lower():
            advice_start = output.lower().find('advice:') + 7
            advice_end = output.find('\n', advice_start)
            if advice_end == -1:
                advice_end = len(output)
            result['advice'] = output[advice_start:advice_end].strip()
        
        return result
    
    async def run_comprehensive_test(self) -> List[SafetyNetResult]:
        """Run all SafetyNet integrity tests"""
        logger.info(f"Starting comprehensive SafetyNet testing for {self.container_id}")
        
        if not await self.connect_device():
            return []
        
        if not await self.install_safetynet_test_app():
            return []
        
        # Generate unique nonces for each test
        nonces = [self.generate_nonce() for _ in range(3)]
        
        # Run all tests
        basic_result = await self.test_basic_integrity(nonces[0])
        self.results.append(basic_result)
        
        device_result = await self.test_device_integrity(nonces[1])
        self.results.append(device_result)
        
        strong_result = await self.test_strong_integrity(nonces[2])
        self.results.append(strong_result)
        
        return self.results
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        if not self.results:
            return {"error": "No test results available"}
        
        passed_tests = sum(1 for r in self.results if r.basic_integrity and r.cts_profile_match)
        total_tests = len(self.results)
        
        report = {
            "container_id": self.container_id,
            "test_timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": (passed_tests / total_tests) * 100,
            "overall_status": "PASS" if passed_tests == total_tests else "FAIL",
            "test_results": []
        }
        
        for result in self.results:
            report["test_results"].append({
                "test_type": result.test_type,
                "basic_integrity": result.basic_integrity,
                "cts_profile_match": result.cts_profile_match,
                "evaluation_type": result.evaluation_type,
                "timestamp": result.timestamp.isoformat(),
                "advice": result.advice,
                "error": result.error
            })
        
        return report

async def main():
    """Main test execution function"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python safetynet_test.py <container_id>")
        sys.exit(1)
    
    container_id = sys.argv[1]
    tester = SafetyNetTester(container_id)
    
    results = await tester.run_comprehensive_test()
    report = tester.generate_report()
    
    print(json.dumps(report, indent=2))
    
    # Save report to file
    with open(f"/tmp/safetynet_report_{container_id}_{int(time.time())}.json", 'w') as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())