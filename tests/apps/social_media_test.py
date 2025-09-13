#!/usr/bin/env python3
"""
Social Media Apps Testing Suite
Tests popular social media applications for integrity bypass effectiveness
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
import subprocess
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SocialMediaApp:
    app_name: str
    package_name: str
    version: str
    test_scenarios: List[str]
    integrity_checks: List[str]

@dataclass
class SocialMediaResult:
    device_id: str
    app_name: str
    package_name: str
    version: str
    installation_success: bool
    launch_success: bool
    login_available: bool
    root_detection_bypassed: bool
    api_functionality: bool
    media_upload_works: bool
    push_notifications: bool
    location_services: bool
    camera_access: bool
    integrity_score: float
    performance_metrics: Dict[str, float]
    timestamp: datetime
    error: Optional[str] = None

class SocialMediaTester:
    """Comprehensive social media application testing framework"""
    
    def __init__(self, container_id: str, adb_port: int = 5555):
        self.container_id = container_id
        self.adb_port = adb_port
        self.device = None
        self.results: List[SocialMediaResult] = []
        
        # Popular social media apps for testing
        self.social_apps = [
            SocialMediaApp(
                app_name="Instagram",
                package_name="com.instagram.android",
                version="302.0.0.23.114",
                test_scenarios=[
                    "app_launch",
                    "camera_access",
                    "story_creation",
                    "media_upload",
                    "api_connectivity"
                ],
                integrity_checks=[
                    "device_fingerprinting",
                    "api_signature_validation", 
                    "media_processing_integrity"
                ]
            ),
            SocialMediaApp(
                app_name="TikTok",
                package_name="com.zhiliaoapp.musically",
                version="32.5.4",
                test_scenarios=[
                    "app_launch",
                    "video_recording",
                    "effects_processing",
                    "upload_functionality",
                    "recommendation_feed"
                ],
                integrity_checks=[
                    "bytedance_security_check",
                    "device_attestation",
                    "content_validation"
                ]
            ),
            SocialMediaApp(
                app_name="Snapchat", 
                package_name="com.snapchat.android",
                version="12.72.0.38",
                test_scenarios=[
                    "app_launch",
                    "camera_filters",
                    "location_services",
                    "snap_sending",
                    "story_posting"
                ],
                integrity_checks=[
                    "snapchat_security_framework",
                    "camera_integrity_check",
                    "location_verification"
                ]
            ),
            SocialMediaApp(
                app_name="WhatsApp",
                package_name="com.whatsapp",
                version="2.23.24.84",
                test_scenarios=[
                    "app_launch",
                    "phone_verification", 
                    "message_encryption",
                    "media_sharing",
                    "backup_functionality"
                ],
                integrity_checks=[
                    "signal_protocol_validation",
                    "phone_number_verification",
                    "message_integrity"
                ]
            ),
            SocialMediaApp(
                app_name="Twitter/X",
                package_name="com.twitter.android",
                version="10.23.0",
                test_scenarios=[
                    "app_launch",
                    "tweet_posting",
                    "media_upload",
                    "live_streaming",
                    "notification_handling"
                ],
                integrity_checks=[
                    "twitter_api_validation",
                    "content_authenticity",
                    "account_verification"
                ]
            ),
            SocialMediaApp(
                app_name="Facebook",
                package_name="com.facebook.katana", 
                version="441.0.0.33.113",
                test_scenarios=[
                    "app_launch",
                    "news_feed_loading",
                    "post_creation",
                    "messenger_integration",
                    "video_calling"
                ],
                integrity_checks=[
                    "facebook_app_integrity",
                    "graph_api_validation",
                    "privacy_compliance"
                ]
            ),
            SocialMediaApp(
                app_name="YouTube",
                package_name="com.google.android.youtube",
                version="18.48.39",
                test_scenarios=[
                    "app_launch",
                    "video_playback",
                    "subscription_sync",
                    "comment_posting",
                    "upload_functionality"
                ],
                integrity_checks=[
                    "google_play_services_check",
                    "drm_validation",
                    "content_policy_enforcement"
                ]
            )
        ]
    
    async def connect_device(self) -> bool:
        """Connect to Android container via ADB"""
        try:
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
    
    async def install_app(self, app: SocialMediaApp) -> bool:
        """Install social media app"""
        try:
            # Check for cached APK
            apk_path = f"/tmp/social_apks/{app.package_name}.apk"
            
            if not Path(apk_path).exists():
                logger.warning(f"APK not found for {app.app_name} at {apk_path}")
                return False
            
            logger.info(f"Installing {app.app_name}")
            
            result = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "install", "-r", apk_path
            ], capture_output=True, text=True, timeout=120)
            
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
        """Launch social media application"""
        try:
            # Launch app using monkey
            result = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "monkey", "-p", package_name, "-c",
                "android.intent.category.LAUNCHER", "1"
            ], capture_output=True, text=True, timeout=30)
            
            if "Events injected: 1" in result.stdout:
                # Wait for app to load
                await asyncio.sleep(8)
                
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
    
    async def test_camera_access(self, package_name: str) -> bool:
        """Test camera functionality"""
        try:
            # Grant camera permissions
            subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "pm", "grant", package_name, "android.permission.CAMERA"
            ], capture_output=True, timeout=5)
            
            # Check if camera can be accessed
            camera_test = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "dumpsys", "camera"
            ], capture_output=True, text=True, timeout=10)
            
            return "Camera service" in camera_test.stdout and "ERROR" not in camera_test.stdout
            
        except Exception as e:
            logger.error(f"Camera test failed: {e}")
            return False
    
    async def test_network_connectivity(self, package_name: str) -> bool:
        """Test network API connectivity"""
        try:
            # Monitor network usage for the app
            before_stats = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "cat", "/proc/net/dev"
            ], capture_output=True, text=True, timeout=5)
            
            # Wait for app to make network requests
            await asyncio.sleep(10)
            
            after_stats = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "cat", "/proc/net/dev"
            ], capture_output=True, text=True, timeout=5)
            
            # Simple check for network activity (not perfect but indicative)
            return len(after_stats.stdout) > len(before_stats.stdout)
            
        except Exception as e:
            logger.error(f"Network test failed: {e}")
            return False
    
    async def test_location_services(self, package_name: str) -> bool:
        """Test location services functionality"""
        try:
            # Grant location permissions
            permissions = [
                "android.permission.ACCESS_FINE_LOCATION",
                "android.permission.ACCESS_COARSE_LOCATION"
            ]
            
            for permission in permissions:
                subprocess.run([
                    "adb", "-s", f"localhost:{self.adb_port}",
                    "shell", "pm", "grant", package_name, permission
                ], capture_output=True, timeout=5)
            
            # Check location service status
            location_check = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "dumpsys", "location"
            ], capture_output=True, text=True, timeout=10)
            
            return "LocationManagerService" in location_check.stdout
            
        except Exception as e:
            logger.error(f"Location test failed: {e}")
            return False
    
    async def test_push_notifications(self, package_name: str) -> bool:
        """Test push notification functionality"""
        try:
            # Check if Google Play Services is available for FCM
            gps_check = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "pm", "list", "packages", "com.google.android.gms"
            ], capture_output=True, text=True, timeout=5)
            
            if "com.google.android.gms" not in gps_check.stdout:
                return False
            
            # Check notification settings for the app
            notification_check = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "dumpsys", "notification", "--noredact"
            ], capture_output=True, text=True, timeout=10)
            
            return package_name in notification_check.stdout
            
        except Exception as e:
            logger.error(f"Push notification test failed: {e}")
            return False
    
    async def check_integrity_bypass(self, app: SocialMediaApp) -> float:
        """Check integrity bypass effectiveness for social media apps"""
        try:
            integrity_score = 0.0
            total_checks = len(app.integrity_checks)
            
            # Check logcat for integrity-related messages
            logcat_result = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "logcat", "-d", "-s", f"{app.package_name}:*"
            ], capture_output=True, text=True, timeout=10)
            
            logcat_text = logcat_result.stdout.lower()
            
            # Common integrity failure keywords
            integrity_failure_keywords = [
                "integrity", "tampered", "rooted", "modified", 
                "unauthorized", "security", "verification failed",
                "device not supported", "untrusted"
            ]
            
            # If no integrity failure messages found, score increases
            if not any(keyword in logcat_text for keyword in integrity_failure_keywords):
                integrity_score += 0.4
            
            # Check for successful API calls (indicates bypassed checks)
            api_success_indicators = [
                "http 200", "success", "authenticated", "connected", "synced"
            ]
            
            if any(indicator in logcat_text for indicator in api_success_indicators):
                integrity_score += 0.3
            
            # Check app stability (no crashes)
            crash_indicators = ["fatal exception", "anr", "crash", "force close"]
            if not any(indicator in logcat_text for indicator in crash_indicators):
                integrity_score += 0.3
            
            return min(integrity_score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"Integrity check failed for {app.app_name}: {e}")
            return 0.0
    
    async def measure_performance(self, package_name: str) -> Dict[str, float]:
        """Measure app performance metrics"""
        try:
            performance_metrics = {}
            
            # CPU usage
            cpu_result = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "dumpsys", "cpuinfo", "|", "grep", package_name
            ], capture_output=True, text=True, timeout=10, shell=True)
            
            if cpu_result.stdout:
                try:
                    cpu_line = cpu_result.stdout.strip().split()
                    if len(cpu_line) > 0:
                        cpu_usage = float(cpu_line[0].replace('%', ''))
                        performance_metrics['cpu_usage_percent'] = cpu_usage
                except:
                    performance_metrics['cpu_usage_percent'] = 0.0
            else:
                performance_metrics['cpu_usage_percent'] = 0.0
            
            # Memory usage
            mem_result = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "dumpsys", "meminfo", package_name
            ], capture_output=True, text=True, timeout=10)
            
            if "TOTAL" in mem_result.stdout:
                try:
                    lines = mem_result.stdout.split('\n')
                    for line in lines:
                        if "TOTAL" in line:
                            parts = line.split()
                            if len(parts) > 1:
                                # Memory in KB, convert to MB
                                memory_kb = int(parts[1])
                                performance_metrics['memory_usage_mb'] = memory_kb / 1024
                                break
                except:
                    performance_metrics['memory_usage_mb'] = 0.0
            else:
                performance_metrics['memory_usage_mb'] = 0.0
            
            # App launch time (approximate)
            launch_start = time.time()
            await self.launch_app(package_name)
            launch_time = time.time() - launch_start
            performance_metrics['launch_time_seconds'] = launch_time
            
            return performance_metrics
            
        except Exception as e:
            logger.error(f"Performance measurement failed for {package_name}: {e}")
            return {'cpu_usage_percent': 0.0, 'memory_usage_mb': 0.0, 'launch_time_seconds': 0.0}
    
    async def test_social_media_app(self, app: SocialMediaApp) -> SocialMediaResult:
        """Test a single social media application comprehensively"""
        logger.info(f"Testing social media app: {app.app_name}")
        
        # Install app
        installation_success = await self.install_app(app)
        if not installation_success:
            return SocialMediaResult(
                device_id=self.container_id,
                app_name=app.app_name,
                package_name=app.package_name,
                version=app.version,
                installation_success=False,
                launch_success=False,
                login_available=False,
                root_detection_bypassed=False,
                api_functionality=False,
                media_upload_works=False,
                push_notifications=False,
                location_services=False,
                camera_access=False,
                integrity_score=0.0,
                performance_metrics={},
                timestamp=datetime.now(),
                error="Installation failed"
            )
        
        # Launch app
        launch_success = await self.launch_app(app.package_name)
        
        # Test various functionalities
        camera_access = await self.test_camera_access(app.package_name)
        api_functionality = await self.test_network_connectivity(app.package_name)
        location_services = await self.test_location_services(app.package_name)
        push_notifications = await self.test_push_notifications(app.package_name)
        
        # Measure integrity bypass effectiveness
        integrity_score = await self.check_integrity_bypass(app)
        
        # Measure performance
        performance_metrics = await self.measure_performance(app.package_name)
        
        # Check if login/main screen is available (basic UI test)
        ui_available = False
        try:
            ui_dump = subprocess.run([
                "adb", "-s", f"localhost:{self.adb_port}",
                "shell", "uiautomator", "dump", "/sdcard/ui.xml"
            ], capture_output=True, text=True, timeout=10)
            ui_available = "error" not in ui_dump.stderr.lower()
        except:
            ui_available = False
        
        result = SocialMediaResult(
            device_id=self.container_id,
            app_name=app.app_name,
            package_name=app.package_name,
            version=app.version,
            installation_success=installation_success,
            launch_success=launch_success,
            login_available=ui_available,
            root_detection_bypassed=integrity_score > 0.5,  # Threshold for bypass success
            api_functionality=api_functionality,
            media_upload_works=camera_access,  # Simplified assumption
            push_notifications=push_notifications,
            location_services=location_services,
            camera_access=camera_access,
            integrity_score=integrity_score,
            performance_metrics=performance_metrics,
            timestamp=datetime.now()
        )
        
        # Cleanup - uninstall app
        subprocess.run([
            "adb", "-s", f"localhost:{self.adb_port}",
            "uninstall", app.package_name
        ], capture_output=True)
        
        return result
    
    async def run_comprehensive_test(self) -> List[SocialMediaResult]:
        """Run tests on all social media applications"""
        logger.info(f"Starting comprehensive social media app testing for {self.container_id}")
        
        if not await self.connect_device():
            return []
        
        # Ensure APK directory exists
        Path("/tmp/social_apks").mkdir(exist_ok=True)
        
        # Test each social media app
        for app in self.social_apps:
            try:
                result = await self.test_social_media_app(app)
                self.results.append(result)
                
                # Wait between tests
                await asyncio.sleep(15)
                
            except Exception as e:
                logger.error(f"Failed to test {app.app_name}: {e}")
                # Add error result
                error_result = SocialMediaResult(
                    device_id=self.container_id,
                    app_name=app.app_name,
                    package_name=app.package_name,
                    version=app.version,
                    installation_success=False,
                    launch_success=False,
                    login_available=False,
                    root_detection_bypassed=False,
                    api_functionality=False,
                    media_upload_works=False,
                    push_notifications=False,
                    location_services=False,
                    camera_access=False,
                    integrity_score=0.0,
                    performance_metrics={},
                    timestamp=datetime.now(),
                    error=str(e)
                )
                self.results.append(error_result)
        
        return self.results
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        if not self.results:
            return {"error": "No test results available"}
        
        # Calculate metrics
        total_apps = len(self.results)
        successful_installs = sum(1 for r in self.results if r.installation_success)
        successful_launches = sum(1 for r in self.results if r.launch_success)
        bypassed_detections = sum(1 for r in self.results if r.root_detection_bypassed)
        working_apis = sum(1 for r in self.results if r.api_functionality)
        working_cameras = sum(1 for r in self.results if r.camera_access)
        
        avg_integrity_score = sum(r.integrity_score for r in self.results) / total_apps if total_apps > 0 else 0
        
        report = {
            "container_id": self.container_id,
            "test_timestamp": datetime.now().isoformat(),
            "total_apps_tested": total_apps,
            "successful_installs": successful_installs,
            "successful_launches": successful_launches,
            "bypass_successes": bypassed_detections,
            "api_functional_apps": working_apis,
            "camera_functional_apps": working_cameras,
            "install_success_rate": (successful_installs / total_apps) * 100,
            "launch_success_rate": (successful_launches / successful_installs) * 100 if successful_installs > 0 else 0,
            "bypass_success_rate": (bypassed_detections / total_apps) * 100,
            "api_success_rate": (working_apis / total_apps) * 100,
            "average_integrity_score": avg_integrity_score,
            "overall_compatibility_score": (avg_integrity_score * 100),
            "test_results": []
        }
        
        for result in self.results:
            report["test_results"].append({
                "app_name": result.app_name,
                "package_name": result.package_name,
                "version": result.version,
                "installation_success": result.installation_success,
                "launch_success": result.launch_success,
                "login_available": result.login_available,
                "root_detection_bypassed": result.root_detection_bypassed,
                "api_functionality": result.api_functionality,
                "media_upload_works": result.media_upload_works,
                "push_notifications": result.push_notifications,
                "location_services": result.location_services,
                "camera_access": result.camera_access,
                "integrity_score": result.integrity_score,
                "performance_metrics": result.performance_metrics,
                "timestamp": result.timestamp.isoformat(),
                "error": result.error
            })
        
        return report

async def main():
    """Main test execution function"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python social_media_test.py <container_id>")
        sys.exit(1)
    
    container_id = sys.argv[1]
    tester = SocialMediaTester(container_id)
    
    results = await tester.run_comprehensive_test()
    report = tester.generate_report()
    
    print(json.dumps(report, indent=2))
    
    # Save report to file
    with open(f"/tmp/social_media_report_{container_id}_{int(time.time())}.json", 'w') as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())