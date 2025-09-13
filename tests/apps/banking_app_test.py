#!/usr/bin/env python3
"""
Banking Apps Testing Suite
Tests real banking applications for integrity bypass effectiveness
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from dataclasses import dataclass
import subprocess
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BankingAppTest:
    app_name: str
    package_name: str
    apk_url: Optional[str]
    version: str
    test_scenarios: List[str]
    expected_behaviors: List[str]

@dataclass
class BankingAppResult:
    device_id: str
    app_name: str
    package_name: str
    version: str
    installation_success: bool
    launch_success: bool
    login_screen_accessible: bool
    root_detection_bypassed: bool
    integrity_checks_passed: bool
    functionality_tests: Dict[str, bool]
    crash_logs: List[str]
    timestamp: datetime
    error: Optional[str] = None

class BankingAppTester:
    """Comprehensive banking application testing framework"""
    
    def __init__(self, container_id: str, adb_port: int = 5555):
        self.container_id = container_id
        self.adb_port = adb_port
        self.device = None
        self.results: List[BankingAppResult] = []
        
        # Predefined banking apps for testing
        self.banking_apps = [
            BankingAppTest(
                app_name="Chase Mobile",
                package_name="com.chase.sig.android",
                apk_url="https://apk-storage.com/chase-mobile.apk",
                version="5.92",
                test_scenarios=[
                    "app_launch",
                    "login_screen_access", 
                    "biometric_prompt",
                    "account_balance_view",
                    "transaction_history"
                ],
                expected_behaviors=[
                    "no_root_detection_popup",
                    "no_integrity_failure_message",
                    "normal_ui_rendering",
                    "api_calls_successful"
                ]
            ),
            BankingAppTest(
                app_name="Bank of America Mobile",
                package_name="com.infonow.bofa",
                apk_url="https://apk-storage.com/bofa-mobile.apk", 
                version="10.5.1",
                test_scenarios=[
                    "app_launch",
                    "security_check_bypass",
                    "login_screen_access",
                    "account_overview"
                ],
                expected_behaviors=[
                    "no_security_warnings",
                    "normal_authentication_flow",
                    "api_connectivity"
                ]
            ),
            BankingAppTest(
                app_name="Wells Fargo Mobile",
                package_name="com.wf.wellsfargomobile",
                apk_url="https://apk-storage.com/wells-fargo-mobile.apk",
                version="8.3.0", 
                test_scenarios=[
                    "app_launch",
                    "device_registration",
                    "login_attempt",
                    "security_questions"
                ],
                expected_behaviors=[
                    "successful_device_fingerprinting",
                    "no_tampered_device_alerts",
                    "normal_security_flow"
                ]
            ),
            BankingAppTest(
                app_name="Capital One Mobile",
                package_name="com.konylabs.capitalone",
                apk_url="https://apk-storage.com/capital-one-mobile.apk",
                version="7.21.0",
                test_scenarios=[
                    "app_launch", 
                    "eno_virtual_card_access",
                    "credit_score_check",
                    "payment_scheduling"
                ],
                expected_behaviors=[
                    "no_jailbreak_detection",
                    "secure_api_communication",
                    "normal_feature_access"
                ]
            ),
            BankingAppTest(
                app_name="Citi Mobile",
                package_name="com.citi.citimobile",
                apk_url="https://apk-storage.com/citi-mobile.apk",
                version="9.15.0",
                test_scenarios=[
                    "app_launch",
                    "account_login",
                    "transaction_alerts",
                    "card_management"
                ],
                expected_behaviors=[
                    "bypass_device_integrity_checks",
                    "successful_biometric_authentication",
                    "normal_account_access"
                ]
            )
        ]
        
    async def connect_device(self) -> bool:
        """Connect to Android container via ADB"""
        try:
            # Use subprocess for ADB operations instead of adb_shell
            result = subprocess.run(
                ["adb", "connect", f"localhost:{self.adb_port}"], 
                capture_output=True, text=True, timeout=10
            )
            if "connected" in result.stdout.lower():
                logger.info(f"Connected to container {self.container_id}")
                return True
            else:
                logger.error(f"Failed to connect: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to device: {e}")
            return False
    
    async def download_apk(self, app: BankingAppTest) -> Optional[str]:
        """Download APK file for testing"""
        try:
            # Create APK cache directory
            apk_dir = Path("/tmp/banking_apks")
            apk_dir.mkdir(exist_ok=True)
            
            apk_path = apk_dir / f"{app.package_name}.apk"
            
            # Skip download if file already exists
            if apk_path.exists():
                logger.info(f"APK already cached: {app.app_name}")
                return str(apk_path)
            
            logger.info(f"Downloading APK for {app.app_name}")
            
            # For production use, implement actual APK download
            # This is a placeholder implementation
            logger.warning("APK download not implemented - using cached/manual APK placement")
            
            # Check if APK was manually placed
            if apk_path.exists():
                return str(apk_path)
            else:
                logger.error(f"APK not found for {app.app_name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to download APK for {app.app_name}: {e}")
            return None
    
    async def install_app(self, app: BankingAppTest) -> bool:
        """Install banking app on container"""
        try:
            apk_path = await self.download_apk(app)
            if not apk_path:
                return False
            
            logger.info(f"Installing {app.app_name}")
            
            # Install APK
            result = subprocess.run(
                ["adb", "-s", f"localhost:{self.adb_port}", "install", "-r", apk_path],
                capture_output=True, text=True, timeout=60
            )
            
            if "Success" in result.stdout:
                logger.info(f"Successfully installed {app.app_name}")
                return True
            else:
                logger.error(f"Failed to install {app.app_name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing {app.app_name}: {e}")
            return False
    
    async def launch_app(self, package_name: str) -> bool:
        """Launch banking application"""
        try:
            # Launch app
            result = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}", 
                "shell", "monkey", "-p", package_name, "-c", 
                "android.intent.category.LAUNCHER", "1"
            ], capture_output=True, text=True, timeout=30)
            
            if "Events injected: 1" in result.stdout:
                # Wait for app to load
                await asyncio.sleep(5)
                
                # Check if app is running
                check_result = subprocess.run([
                    "adb", "-s", f"localhost:{self.adb_port}", 
                    "shell", "pidof", package_name
                ], capture_output=True, text=True)
                
                return bool(check_result.stdout.strip())
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to launch app {package_name}: {e}")
            return False
    
    async def check_root_detection_popup(self, package_name: str) -> bool:
        """Check if root detection popup appears"""
        try:
            # Capture screen to analyze for root detection popups
            subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}", 
                "shell", "screencap", "/sdcard/screen.png"
            ], timeout=10)
            
            # Pull screenshot
            subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "pull", "/sdcard/screen.png", f"/tmp/screen_{package_name}.png"
            ], timeout=10)
            
            # Analyze screenshot for common root detection messages
            # This would typically use OCR or image analysis
            # For now, check logcat for root detection messages
            
            logcat_result = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "logcat", "-d", "-s", f"{package_name}:*"
            ], capture_output=True, text=True, timeout=10)
            
            root_keywords = [
                "root", "rooted", "jailbreak", "tampered", 
                "integrity", "security", "unauthorized"
            ]
            
            logcat_text = logcat_result.stdout.lower()
            return any(keyword in logcat_text for keyword in root_keywords)
            
        except Exception as e:
            logger.error(f"Failed to check root detection for {package_name}: {e}")
            return True  # Assume detection if check fails
    
    async def test_app_functionality(self, app: BankingAppTest) -> Dict[str, bool]:
        """Test specific banking app functionality"""
        functionality_results = {}
        
        try:
            # Test login screen accessibility
            await asyncio.sleep(3)  # Wait for app to fully load
            
            # Check if login screen is accessible (no crashes/blocks)
            ui_dump = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "uiautomator", "dump", "/sdcard/ui.xml"
            ], capture_output=True, text=True, timeout=10)
            
            functionality_results["login_screen_accessible"] = "error" not in ui_dump.stderr.lower()
            
            # Test for common banking UI elements
            subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "pull", "/sdcard/ui.xml", f"/tmp/ui_{app.package_name}.xml"
            ], timeout=10)
            
            # Check for typical banking app UI elements
            banking_ui_elements = [
                "username", "password", "login", "sign in", 
                "account", "balance", "transfer"
            ]
            
            try:
                with open(f"/tmp/ui_{app.package_name}.xml", 'r') as f:
                    ui_content = f.read().lower()
                    functionality_results["banking_ui_present"] = any(
                        element in ui_content for element in banking_ui_elements
                    )
            except:
                functionality_results["banking_ui_present"] = False
            
            # Test app stability (check for crashes)
            await asyncio.sleep(5)
            
            crash_check = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "pidof", app.package_name
            ], capture_output=True, text=True)
            
            functionality_results["app_stable"] = bool(crash_check.stdout.strip())
            
            # Test network connectivity within app
            network_test = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "netstat", "-an"
            ], capture_output=True, text=True, timeout=5)
            
            functionality_results["network_accessible"] = "ESTABLISHED" in network_test.stdout
            
        except Exception as e:
            logger.error(f"Functionality testing failed for {app.app_name}: {e}")
            functionality_results["error"] = True
        
        return functionality_results
    
    async def get_crash_logs(self, package_name: str) -> List[str]:
        """Retrieve crash logs for the application"""
        try:
            # Get crash logs from logcat
            crash_result = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "logcat", "-d", "-s", "AndroidRuntime:E", f"{package_name}:E"
            ], capture_output=True, text=True, timeout=10)
            
            crash_logs = []
            if crash_result.stdout:
                # Parse crash logs
                lines = crash_result.stdout.split('\n')
                current_crash = []
                
                for line in lines:
                    if "FATAL EXCEPTION" in line or "AndroidRuntime" in line:
                        if current_crash:
                            crash_logs.append('\n'.join(current_crash))
                            current_crash = []
                        current_crash.append(line)
                    elif current_crash and (line.startswith('\t') or line.startswith(' ')):
                        current_crash.append(line)
                    elif current_crash:
                        crash_logs.append('\n'.join(current_crash))
                        current_crash = []
                
                if current_crash:
                    crash_logs.append('\n'.join(current_crash))
            
            return crash_logs
            
        except Exception as e:
            logger.error(f"Failed to get crash logs for {package_name}: {e}")
            return [f"Error retrieving crash logs: {e}"]
    
    async def test_banking_app(self, app: BankingAppTest) -> BankingAppResult:
        """Test a single banking application comprehensively"""
        logger.info(f"Testing banking app: {app.app_name}")
        
        # Install app
        installation_success = await self.install_app(app)
        if not installation_success:
            return BankingAppResult(
                device_id=self.container_id,
                app_name=app.app_name,
                package_name=app.package_name,
                version=app.version,
                installation_success=False,
                launch_success=False,
                login_screen_accessible=False,
                root_detection_bypassed=False,
                integrity_checks_passed=False,
                functionality_tests={},
                crash_logs=[],
                timestamp=datetime.now(),
                error="Installation failed"
            )
        
        # Launch app
        launch_success = await self.launch_app(app.package_name)
        
        # Check for root detection
        root_detected = await self.check_root_detection_popup(app.package_name)
        root_detection_bypassed = not root_detected
        
        # Test functionality
        functionality_tests = await self.test_app_functionality(app)
        
        # Get crash logs
        crash_logs = await self.get_crash_logs(app.package_name)
        
        # Determine overall integrity check status
        integrity_checks_passed = (
            launch_success and 
            root_detection_bypassed and 
            functionality_tests.get("app_stable", False) and
            not crash_logs
        )
        
        result = BankingAppResult(
            device_id=self.container_id,
            app_name=app.app_name,
            package_name=app.package_name,
            version=app.version,
            installation_success=installation_success,
            launch_success=launch_success,
            login_screen_accessible=functionality_tests.get("login_screen_accessible", False),
            root_detection_bypassed=root_detection_bypassed,
            integrity_checks_passed=integrity_checks_passed,
            functionality_tests=functionality_tests,
            crash_logs=crash_logs,
            timestamp=datetime.now()
        )
        
        # Cleanup - uninstall app to free space
        subprocess.run([
            "adb", "-s", f"localhost:{self.adb_port}",
            "uninstall", app.package_name
        ], capture_output=True)
        
        return result
    
    async def run_comprehensive_test(self) -> List[BankingAppResult]:
        """Run tests on all banking applications"""
        logger.info(f"Starting comprehensive banking app testing for {self.container_id}")
        
        if not await self.connect_device():
            return []
        
        # Test each banking app
        for app in self.banking_apps:
            try:
                result = await self.test_banking_app(app)
                self.results.append(result)
                
                # Wait between tests to avoid resource conflicts
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Failed to test {app.app_name}: {e}")
                # Add error result
                error_result = BankingAppResult(
                    device_id=self.container_id,
                    app_name=app.app_name,
                    package_name=app.package_name,
                    version=app.version,
                    installation_success=False,
                    launch_success=False,
                    login_screen_accessible=False,
                    root_detection_bypassed=False,
                    integrity_checks_passed=False,
                    functionality_tests={},
                    crash_logs=[],
                    timestamp=datetime.now(),
                    error=str(e)
                )
                self.results.append(error_result)
        
        return self.results
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        if not self.results:
            return {"error": "No test results available"}
        
        # Calculate success metrics
        total_apps = len(self.results)
        successful_installs = sum(1 for r in self.results if r.installation_success)
        successful_launches = sum(1 for r in self.results if r.launch_success)
        bypassed_root_detection = sum(1 for r in self.results if r.root_detection_bypassed)
        passed_integrity_checks = sum(1 for r in self.results if r.integrity_checks_passed)
        
        report = {
            "container_id": self.container_id,
            "test_timestamp": datetime.now().isoformat(),
            "total_apps_tested": total_apps,
            "successful_installs": successful_installs,
            "successful_launches": successful_launches,
            "root_detection_bypasses": bypassed_root_detection,
            "integrity_check_passes": passed_integrity_checks,
            "install_success_rate": (successful_installs / total_apps) * 100,
            "launch_success_rate": (successful_launches / total_apps) * 100 if successful_installs > 0 else 0,
            "bypass_success_rate": (bypassed_root_detection / total_apps) * 100,
            "overall_compatibility": (passed_integrity_checks / total_apps) * 100,
            "test_results": []
        }
        
        for result in self.results:
            report["test_results"].append({
                "app_name": result.app_name,
                "package_name": result.package_name,
                "version": result.version,
                "installation_success": result.installation_success,
                "launch_success": result.launch_success,
                "login_screen_accessible": result.login_screen_accessible,
                "root_detection_bypassed": result.root_detection_bypassed,
                "integrity_checks_passed": result.integrity_checks_passed,
                "functionality_tests": result.functionality_tests,
                "crash_count": len(result.crash_logs),
                "timestamp": result.timestamp.isoformat(),
                "error": result.error
            })
        
        return report

async def main():
    """Main test execution function"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python banking_app_test.py <container_id>")
        sys.exit(1)
    
    container_id = sys.argv[1]
    tester = BankingAppTester(container_id)
    
    results = await tester.run_comprehensive_test()
    report = tester.generate_report()
    
    print(json.dumps(report, indent=2))
    
    # Save report to file
    with open(f"/tmp/banking_app_report_{container_id}_{int(time.time())}.json", 'w') as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())