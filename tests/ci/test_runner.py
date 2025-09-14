#!/usr/bin/env python3
"""
Automated Test Runner for CI/CD Pipeline
Orchestrates all integrity and performance tests
"""

import asyncio
import json
import logging
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import yaml
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/test_runner.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TestRunner:
    """Automated test runner for CI/CD integration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "/tmp/test_config.yaml"
        self.config = self.load_config()
        self.test_results = {}
        self.start_time = datetime.now()
        
    def load_config(self) -> Dict:
        """Load test configuration"""
        default_config = {
            "containers": {
                "test_images": [
                    "android-platform:android-11-arm64",
                    "android-platform:android-12-arm64", 
                    "android-platform:android-13-arm64",
                    "android-platform:android-14-arm64"
                ],
                "parallel_limit": 3,
                "startup_timeout": 120
            },
            "integrity_tests": {
                "enabled": True,
                "safetynet": True,
                "play_integrity": True,
                "root_detection": True,
                "timeout_minutes": 30
            },
            "app_tests": {
                "enabled": True,
                "banking_apps": True,
                "social_media": True,
                "timeout_minutes": 45
            },
            "performance_tests": {
                "enabled": True,
                "load_testing": True,
                "gps_accuracy": True,
                "resource_monitoring": True,
                "timeout_minutes": 60
            },
            "reporting": {
                "generate_html": True,
                "generate_json": True,
                "generate_junit": True,
                "output_directory": "/tmp/test_reports"
            },
            "ci_integration": {
                "fail_on_integrity_failure": True,
                "fail_on_performance_threshold": False,
                "performance_threshold": 80.0,
                "required_success_rate": 90.0
            }
        }
        
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    user_config = yaml.safe_load(f)
                    # Merge user config with defaults
                    default_config.update(user_config)
        except Exception as e:
            logger.warning(f"Could not load config from {self.config_path}: {e}")
            logger.info("Using default configuration")
        
        return default_config
    
    async def setup_test_environment(self) -> bool:
        """Setup test environment"""
        try:
            logger.info("Setting up test environment...")
            
            # Create output directories
            output_dir = Path(self.config["reporting"]["output_directory"])
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            for subdir in ["integrity", "apps", "performance", "reports"]:
                (output_dir / subdir).mkdir(exist_ok=True)
            
            # Verify Docker is available
            result = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, text=True
            )
            if result.returncode != 0:
                logger.error("Docker is not available")
                return False
            
            # Verify ADB is available  
            result = subprocess.run(
                ["adb", "version"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                logger.error("ADB is not available")
                return False
            
            # Check if test images exist
            available_images = []
            for image in self.config["containers"]["test_images"]:
                result = subprocess.run(
                    ["docker", "inspect", image],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    available_images.append(image)
                else:
                    logger.warning(f"Test image not available: {image}")
            
            if not available_images:
                logger.error("No test images available")
                return False
            
            self.config["containers"]["test_images"] = available_images
            logger.info(f"Test environment ready with {len(available_images)} images")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup test environment: {e}")
            return False
    
    async def create_test_container(self, image: str, test_id: str) -> Optional[str]:
        """Create a test container"""
        try:
            container_name = f"test_{test_id}_{int(time.time())}"
            
            logger.info(f"Creating test container: {container_name}")
            
            # Create container
            cmd = [
                "docker", "run", "-d", "--name", container_name,
                "--privileged", 
                "-p", "0:5555",  # Dynamic port mapping
                "-e", "DISPLAY=:99",
                "-e", "GPU=1",
                image
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"Failed to create container: {result.stderr}")
                return None
            
            container_id = result.stdout.strip()
            
            # Wait for container to be ready
            await asyncio.sleep(self.config["containers"]["startup_timeout"])
            
            # Verify container is running
            inspect_result = subprocess.run(
                ["docker", "inspect", container_id],
                capture_output=True, text=True
            )
            
            if inspect_result.returncode == 0:
                inspect_data = json.loads(inspect_result.stdout)[0]
                if inspect_data["State"]["Running"]:
                    logger.info(f"Container ready: {container_name} ({container_id[:12]})")
                    return container_id
            
            logger.error(f"Container failed to start: {container_name}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to create test container: {e}")
            return None
    
    def get_container_adb_port(self, container_id: str) -> Optional[int]:
        """Get the ADB port for a container"""
        try:
            result = subprocess.run([
                "docker", "port", container_id, "5555"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                port_mapping = result.stdout.strip()
                # Format: 0.0.0.0:12345
                port = int(port_mapping.split(':')[-1])
                return port
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get ADB port for {container_id}: {e}")
            return None
    
    async def run_integrity_tests(self, container_id: str, adb_port: int) -> Dict:
        """Run integrity bypass tests"""
        logger.info(f"Running integrity tests on {container_id[:12]}")
        
        test_results = {
            "container_id": container_id,
            "adb_port": adb_port,
            "tests": {},
            "overall_success": False,
            "errors": []
        }
        
        test_scripts = []
        if self.config["integrity_tests"]["safetynet"]:
            test_scripts.append(("safetynet", "tests/integrity/safetynet_test.py"))
        if self.config["integrity_tests"]["play_integrity"]:
            test_scripts.append(("play_integrity", "tests/integrity/play_integrity_test.py"))
        if self.config["integrity_tests"]["root_detection"]:
            test_scripts.append(("root_detection", "tests/integrity/root_detection_test.py"))
        
        for test_name, script_path in test_scripts:
            try:
                logger.info(f"Running {test_name} test...")
                
                # Run test script
                result = subprocess.run([
                    sys.executable, script_path, container_id
                ], capture_output=True, text=True, 
                timeout=self.config["integrity_tests"]["timeout_minutes"] * 60)
                
                if result.returncode == 0:
                    # Parse test results
                    test_data = json.loads(result.stdout)
                    test_results["tests"][test_name] = test_data
                    logger.info(f"{test_name} test completed successfully")
                else:
                    error_msg = f"{test_name} test failed: {result.stderr}"
                    test_results["errors"].append(error_msg)
                    logger.error(error_msg)
                    
            except subprocess.TimeoutExpired:
                error_msg = f"{test_name} test timed out"
                test_results["errors"].append(error_msg)
                logger.error(error_msg)
            except Exception as e:
                error_msg = f"{test_name} test error: {e}"
                test_results["errors"].append(error_msg)
                logger.error(error_msg)
        
        # Determine overall success
        successful_tests = len([t for t in test_results["tests"].values() 
                              if t.get("overall_status") == "PASS"])
        total_tests = len(test_scripts)
        
        if total_tests > 0:
            success_rate = (successful_tests / total_tests) * 100
            test_results["success_rate"] = success_rate
            test_results["overall_success"] = success_rate >= self.config["ci_integration"]["required_success_rate"]
        
        return test_results
    
    async def run_app_tests(self, container_id: str, adb_port: int) -> Dict:
        """Run real app tests"""
        logger.info(f"Running app tests on {container_id[:12]}")
        
        test_results = {
            "container_id": container_id,
            "adb_port": adb_port,
            "tests": {},
            "overall_success": False,
            "errors": []
        }
        
        test_scripts = []
        if self.config["app_tests"]["banking_apps"]:
            test_scripts.append(("banking", "tests/apps/banking_app_test.py"))
        if self.config["app_tests"]["social_media"]:
            test_scripts.append(("social_media", "tests/apps/social_media_test.py"))
        
        for test_name, script_path in test_scripts:
            try:
                logger.info(f"Running {test_name} app test...")
                
                result = subprocess.run([
                    sys.executable, script_path, container_id
                ], capture_output=True, text=True,
                timeout=self.config["app_tests"]["timeout_minutes"] * 60)
                
                if result.returncode == 0:
                    test_data = json.loads(result.stdout)
                    test_results["tests"][test_name] = test_data
                    logger.info(f"{test_name} app test completed")
                else:
                    error_msg = f"{test_name} app test failed: {result.stderr}"
                    test_results["errors"].append(error_msg)
                    logger.error(error_msg)
                    
            except subprocess.TimeoutExpired:
                error_msg = f"{test_name} app test timed out"
                test_results["errors"].append(error_msg)
                logger.error(error_msg)
            except Exception as e:
                error_msg = f"{test_name} app test error: {e}"
                test_results["errors"].append(error_msg)
                logger.error(error_msg)
        
        # Calculate overall success
        total_success_rates = []
        for test_data in test_results["tests"].values():
            if "bypass_success_rate" in test_data:
                total_success_rates.append(test_data["bypass_success_rate"])
            elif "overall_compatibility_score" in test_data:
                total_success_rates.append(test_data["overall_compatibility_score"])
        
        if total_success_rates:
            avg_success_rate = sum(total_success_rates) / len(total_success_rates)
            test_results["success_rate"] = avg_success_rate
            test_results["overall_success"] = avg_success_rate >= self.config["ci_integration"]["required_success_rate"]
        
        return test_results
    
    async def run_performance_tests(self, container_id: str, adb_port: int) -> Dict:
        """Run performance tests"""
        logger.info(f"Running performance tests on {container_id[:12]}")
        
        test_results = {
            "container_id": container_id,
            "adb_port": adb_port,
            "tests": {},
            "overall_success": False,
            "errors": []
        }
        
        test_scripts = []
        if self.config["performance_tests"]["gps_accuracy"]:
            test_scripts.append(("gps_accuracy", "tests/performance/gps_accuracy_test.py"))
        
        for test_name, script_path in test_scripts:
            try:
                logger.info(f"Running {test_name} performance test...")
                
                result = subprocess.run([
                    sys.executable, script_path, container_id
                ], capture_output=True, text=True,
                timeout=self.config["performance_tests"]["timeout_minutes"] * 60)
                
                if result.returncode == 0:
                    test_data = json.loads(result.stdout)
                    test_results["tests"][test_name] = test_data
                    logger.info(f"{test_name} performance test completed")
                else:
                    error_msg = f"{test_name} performance test failed: {result.stderr}"
                    test_results["errors"].append(error_msg)
                    logger.error(error_msg)
                    
            except subprocess.TimeoutExpired:
                error_msg = f"{test_name} performance test timed out"
                test_results["errors"].append(error_msg)
                logger.error(error_msg)
            except Exception as e:
                error_msg = f"{test_name} performance test error: {e}"
                test_results["errors"].append(error_msg)
                logger.error(error_msg)
        
        # Run load testing separately if enabled
        if self.config["performance_tests"]["load_testing"]:
            try:
                logger.info("Running load performance test...")
                
                result = subprocess.run([
                    sys.executable, "tests/performance/load_test.py"
                ], capture_output=True, text=True,
                timeout=self.config["performance_tests"]["timeout_minutes"] * 60)
                
                if result.returncode == 0:
                    test_data = json.loads(result.stdout)
                    test_results["tests"]["load_testing"] = test_data
                    logger.info("Load testing completed")
                else:
                    error_msg = f"Load test failed: {result.stderr}"
                    test_results["errors"].append(error_msg)
                    logger.error(error_msg)
                    
            except Exception as e:
                error_msg = f"Load test error: {e}"
                test_results["errors"].append(error_msg)
                logger.error(error_msg)
        
        # Calculate performance score
        performance_scores = []
        for test_name, test_data in test_results["tests"].items():
            if test_name == "gps_accuracy" and "overall_gps_performance" in test_data:
                performance_scores.append(test_data["overall_gps_performance"]["overall_accuracy_percentage"])
            elif test_name == "load_testing" and "performance_summary" in test_data:
                performance_scores.append(test_data["performance_summary"]["overall_avg_success_rate"])
        
        if performance_scores:
            avg_performance = sum(performance_scores) / len(performance_scores)
            test_results["performance_score"] = avg_performance
            test_results["overall_success"] = avg_performance >= self.config["ci_integration"]["performance_threshold"]
        
        return test_results
    
    async def cleanup_container(self, container_id: str):
        """Clean up test container"""
        try:
            logger.info(f"Cleaning up container {container_id[:12]}")
            
            # Stop container
            subprocess.run(["docker", "stop", container_id], 
                         capture_output=True, timeout=30)
            
            # Remove container
            subprocess.run(["docker", "rm", container_id],
                         capture_output=True, timeout=30)
            
        except Exception as e:
            logger.error(f"Failed to cleanup container {container_id}: {e}")
    
    async def test_single_container(self, image: str, test_id: str) -> Dict:
        """Run all tests on a single container"""
        logger.info(f"Testing container image: {image}")
        
        container_results = {
            "image": image,
            "test_id": test_id,
            "container_id": None,
            "start_time": datetime.now().isoformat(),
            "integrity_tests": {},
            "app_tests": {},
            "performance_tests": {},
            "overall_success": False,
            "errors": []
        }
        
        container_id = None
        
        try:
            # Create test container
            container_id = await self.create_test_container(image, test_id)
            if not container_id:
                container_results["errors"].append("Failed to create container")
                return container_results
            
            container_results["container_id"] = container_id
            
            # Get ADB port
            adb_port = self.get_container_adb_port(container_id)
            if not adb_port:
                container_results["errors"].append("Failed to get ADB port")
                return container_results
            
            # Run integrity tests
            if self.config["integrity_tests"]["enabled"]:
                integrity_results = await self.run_integrity_tests(container_id, adb_port)
                container_results["integrity_tests"] = integrity_results
            
            # Run app tests
            if self.config["app_tests"]["enabled"]:
                app_results = await self.run_app_tests(container_id, adb_port)
                container_results["app_tests"] = app_results
            
            # Run performance tests
            if self.config["performance_tests"]["enabled"]:
                performance_results = await self.run_performance_tests(container_id, adb_port)
                container_results["performance_tests"] = performance_results
            
            # Determine overall success
            test_successes = []
            if container_results["integrity_tests"]:
                test_successes.append(container_results["integrity_tests"].get("overall_success", False))
            if container_results["app_tests"]:
                test_successes.append(container_results["app_tests"].get("overall_success", False))
            if container_results["performance_tests"]:
                test_successes.append(container_results["performance_tests"].get("overall_success", True))  # Performance tests are less critical
            
            container_results["overall_success"] = all(test_successes) if test_successes else False
            
        except Exception as e:
            error_msg = f"Container test failed: {e}\n{traceback.format_exc()}"
            container_results["errors"].append(error_msg)
            logger.error(error_msg)
            
        finally:
            # Cleanup
            if container_id:
                await self.cleanup_container(container_id)
        
        container_results["end_time"] = datetime.now().isoformat()
        return container_results
    
    async def run_all_tests(self) -> Dict:
        """Run all tests across all configured images"""
        logger.info("Starting comprehensive test execution")
        
        overall_results = {
            "test_run_id": f"run_{int(time.time())}",
            "start_time": self.start_time.isoformat(),
            "configuration": self.config,
            "container_results": [],
            "summary": {},
            "overall_success": False
        }
        
        try:
            # Setup environment
            if not await self.setup_test_environment():
                overall_results["summary"]["error"] = "Failed to setup test environment"
                return overall_results
            
            # Run tests on each image
            test_tasks = []
            for i, image in enumerate(self.config["containers"]["test_images"]):
                test_id = f"test_{i}"
                task = self.test_single_container(image, test_id)
                test_tasks.append(task)
                
                # Limit parallel execution
                if len(test_tasks) >= self.config["containers"]["parallel_limit"]:
                    results = await asyncio.gather(*test_tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, dict):
                            overall_results["container_results"].append(result)
                        else:
                            logger.error(f"Test task failed: {result}")
                    test_tasks = []
            
            # Run remaining tasks
            if test_tasks:
                results = await asyncio.gather(*test_tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, dict):
                        overall_results["container_results"].append(result)
                    else:
                        logger.error(f"Test task failed: {result}")
            
            # Calculate summary
            total_containers = len(overall_results["container_results"])
            successful_containers = len([r for r in overall_results["container_results"] 
                                       if r.get("overall_success", False)])
            
            overall_results["summary"] = {
                "total_containers_tested": total_containers,
                "successful_containers": successful_containers,
                "success_rate": (successful_containers / total_containers * 100) if total_containers > 0 else 0,
                "total_duration_minutes": (datetime.now() - self.start_time).total_seconds() / 60
            }
            
            # Determine overall success
            required_rate = self.config["ci_integration"]["required_success_rate"]
            overall_results["overall_success"] = overall_results["summary"]["success_rate"] >= required_rate
            
        except Exception as e:
            error_msg = f"Test execution failed: {e}\n{traceback.format_exc()}"
            overall_results["summary"]["error"] = error_msg
            logger.error(error_msg)
        
        overall_results["end_time"] = datetime.now().isoformat()
        return overall_results
    
    def generate_junit_report(self, results: Dict) -> str:
        """Generate JUnit XML report"""
        from xml.etree.ElementTree import Element, SubElement, tostring
        
        root = Element("testsuites")
        root.set("name", "AndroidContainerPlatformTests")
        root.set("tests", str(len(results["container_results"])))
        root.set("failures", str(len([r for r in results["container_results"] if not r.get("overall_success", False)])))
        root.set("time", str(results["summary"].get("total_duration_minutes", 0) * 60))
        
        for container_result in results["container_results"]:
            testsuite = SubElement(root, "testsuite")
            testsuite.set("name", f"Container_{container_result['image']}")
            testsuite.set("tests", "1")
            testsuite.set("failures", "0" if container_result.get("overall_success", False) else "1")
            
            testcase = SubElement(testsuite, "testcase")
            testcase.set("name", f"IntegrityAndCompatibility_{container_result['test_id']}")
            testcase.set("classname", container_result["image"])
            
            if not container_result.get("overall_success", False):
                failure = SubElement(testcase, "failure")
                failure.set("message", "Container tests failed")
                failure.text = "\n".join(container_result.get("errors", []))
        
        return tostring(root, encoding='unicode')
    
    def save_reports(self, results: Dict):
        """Save test reports in various formats"""
        output_dir = Path(self.config["reporting"]["output_directory"])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # JSON report
            if self.config["reporting"]["generate_json"]:
                json_path = output_dir / f"test_report_{timestamp}.json"
                with open(json_path, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                logger.info(f"JSON report saved: {json_path}")
            
            # JUnit XML report
            if self.config["reporting"]["generate_junit"]:
                junit_xml = self.generate_junit_report(results)
                junit_path = output_dir / f"junit_report_{timestamp}.xml"
                with open(junit_path, 'w') as f:
                    f.write(junit_xml)
                logger.info(f"JUnit report saved: {junit_path}")
            
            # Summary report
            summary_path = output_dir / f"summary_{timestamp}.txt"
            with open(summary_path, 'w') as f:
                f.write(f"Android Container Platform Test Summary\n")
                f.write(f"Test Run: {results['test_run_id']}\n")
                f.write(f"Start Time: {results['start_time']}\n")
                f.write(f"End Time: {results['end_time']}\n\n")
                f.write(f"Total Containers Tested: {results['summary']['total_containers_tested']}\n")
                f.write(f"Successful Containers: {results['summary']['successful_containers']}\n")
                f.write(f"Success Rate: {results['summary']['success_rate']:.2f}%\n")
                f.write(f"Total Duration: {results['summary']['total_duration_minutes']:.2f} minutes\n\n")
                f.write(f"Overall Result: {'PASS' if results['overall_success'] else 'FAIL'}\n")
            logger.info(f"Summary report saved: {summary_path}")
            
        except Exception as e:
            logger.error(f"Failed to save reports: {e}")

async def main():
    """Main test runner execution"""
    logger.info("Android Container Platform - Automated Test Runner")
    
    # Parse command line arguments
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # Create test runner
    runner = TestRunner(config_path)
    
    try:
        # Run all tests
        results = await runner.run_all_tests()
        
        # Save reports
        runner.save_reports(results)
        
        # Print summary
        print("\n" + "="*50)
        print("TEST EXECUTION SUMMARY")
        print("="*50)
        print(f"Overall Result: {'PASS' if results['overall_success'] else 'FAIL'}")
        print(f"Containers Tested: {results['summary'].get('total_containers_tested', 0)}")
        print(f"Success Rate: {results['summary'].get('success_rate', 0):.2f}%")
        print(f"Duration: {results['summary'].get('total_duration_minutes', 0):.2f} minutes")
        print("="*50)
        
        # Exit with appropriate code for CI/CD
        if results['overall_success']:
            print("All tests passed! ✅")
            sys.exit(0)
        else:
            print("Some tests failed! ❌")
            if runner.config["ci_integration"]["fail_on_integrity_failure"]:
                sys.exit(1)
            else:
                sys.exit(0)
                
    except Exception as e:
        logger.error(f"Test runner failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())