import json
import random
from typing import Dict, Optional
from datetime import datetime, timedelta

class DeviceProfileGenerator:
    """Generates realistic device profiles for major Android manufacturers"""
    
    def __init__(self):
        self.device_profiles = {
            "Samsung": {
                "Galaxy S23": {
                    "android_versions": ["13", "14"],
                    "api_levels": {"13": 33, "14": 34},
                    "hardware": "qcom",
                    "platform": "taro",
                    "chipset": "sm8550",
                    "board": "dm1q",
                    "screen_density": 480,
                    "screen_resolution": "1080x2340",
                    "ram": "8GB",
                    "storage": "128GB"
                },
                "Galaxy S23 Ultra": {
                    "android_versions": ["13", "14"],
                    "api_levels": {"13": 33, "14": 34},
                    "hardware": "qcom",
                    "platform": "taro",
                    "chipset": "sm8550",
                    "board": "dm3q",
                    "screen_density": 480,
                    "screen_resolution": "1440x3088",
                    "ram": "12GB",
                    "storage": "256GB"
                },
                "Galaxy A54": {
                    "android_versions": ["13", "14"],
                    "api_levels": {"13": 33, "14": 34},
                    "hardware": "exynos1380",
                    "platform": "s5e8835",
                    "chipset": "exynos1380",
                    "board": "a54x",
                    "screen_density": 480,
                    "screen_resolution": "1080x2340",
                    "ram": "6GB",
                    "storage": "128GB"
                }
            },
            "Google": {
                "Pixel 7": {
                    "android_versions": ["13", "14"],
                    "api_levels": {"13": 33, "14": 34},
                    "hardware": "slider",
                    "platform": "gs201",
                    "chipset": "tensor",
                    "board": "slider",
                    "screen_density": 420,
                    "screen_resolution": "1080x2400",
                    "ram": "8GB",
                    "storage": "128GB"
                },
                "Pixel 7 Pro": {
                    "android_versions": ["13", "14"],
                    "api_levels": {"13": 33, "14": 34},
                    "hardware": "cheetah",
                    "platform": "gs201",
                    "chipset": "tensor",
                    "board": "cheetah",
                    "screen_density": 480,
                    "screen_resolution": "1440x3120",
                    "ram": "12GB",
                    "storage": "128GB"
                },
                "Pixel 8": {
                    "android_versions": ["14"],
                    "api_levels": {"14": 34},
                    "hardware": "shiba",
                    "platform": "zuma",
                    "chipset": "tensor_g3",
                    "board": "shiba",
                    "screen_density": 420,
                    "screen_resolution": "1080x2400",
                    "ram": "8GB",
                    "storage": "128GB"
                }
            },
            "OnePlus": {
                "OnePlus 11": {
                    "android_versions": ["13", "14"],
                    "api_levels": {"13": 33, "14": 34},
                    "hardware": "qcom",
                    "platform": "taro",
                    "chipset": "sm8550",
                    "board": "phoenix",
                    "screen_density": 480,
                    "screen_resolution": "1440x3216",
                    "ram": "8GB",
                    "storage": "128GB"
                },
                "OnePlus Nord 3": {
                    "android_versions": ["13", "14"],
                    "api_levels": {"13": 33, "14": 34},
                    "hardware": "mt6893",
                    "platform": "mt6893",
                    "chipset": "dimensity_9000",
                    "board": "larry",
                    "screen_density": 480,
                    "screen_resolution": "1080x2412",
                    "ram": "8GB",
                    "storage": "128GB"
                }
            },
            "Xiaomi": {
                "Mi 13": {
                    "android_versions": ["13", "14"],
                    "api_levels": {"13": 33, "14": 34},
                    "hardware": "qcom",
                    "platform": "taro",
                    "chipset": "sm8550",
                    "board": "fuxi",
                    "screen_density": 480,
                    "screen_resolution": "1080x2400",
                    "ram": "8GB",
                    "storage": "256GB"
                },
                "Redmi Note 12": {
                    "android_versions": ["12", "13"],
                    "api_levels": {"12": 31, "13": 33},
                    "hardware": "qcom",
                    "platform": "holi",
                    "chipset": "sm6225",
                    "board": "sweet",
                    "screen_density": 480,
                    "screen_resolution": "1080x2400",
                    "ram": "6GB",
                    "storage": "128GB"
                }
            },
            "Oppo": {
                "Find X6": {
                    "android_versions": ["13", "14"],
                    "api_levels": {"13": 33, "14": 34},
                    "hardware": "qcom",
                    "platform": "taro",
                    "chipset": "sm8550",
                    "board": "phoenix",
                    "screen_density": 480,
                    "screen_resolution": "1440x3216",
                    "ram": "12GB",
                    "storage": "256GB"
                }
            }
        }

    async def generate_profile(self, manufacturer: Optional[str] = None, 
                              model: Optional[str] = None, 
                              android_version: Optional[str] = None) -> Dict:
        """Generate a realistic device profile"""
        
        # Select manufacturer
        if not manufacturer:
            manufacturer = random.choice(list(self.device_profiles.keys()))
        elif manufacturer not in self.device_profiles:
            raise ValueError(f"Unsupported manufacturer: {manufacturer}")
        
        # Select model
        manufacturer_devices = self.device_profiles[manufacturer]
        if not model:
            model = random.choice(list(manufacturer_devices.keys()))
        elif model not in manufacturer_devices:
            raise ValueError(f"Unsupported model for {manufacturer}: {model}")
        
        device_spec = manufacturer_devices[model]
        
        # Select Android version
        if not android_version:
            android_version = random.choice(device_spec["android_versions"])
        elif android_version not in device_spec["android_versions"]:
            raise ValueError(f"Unsupported Android version for {manufacturer} {model}: {android_version}")
        
        # Build complete profile
        profile = {
            "manufacturer": manufacturer,
            "model": model,
            "android_version": android_version,
            "api_level": device_spec["api_levels"][android_version],
            "hardware": device_spec["hardware"],
            "platform": device_spec["platform"],
            "chipset": device_spec["chipset"],
            "board": device_spec["board"],
            "screen_density": device_spec["screen_density"],
            "screen_resolution": device_spec["screen_resolution"],
            "ram": device_spec["ram"],
            "storage": device_spec["storage"],
            
            # Additional realistic properties
            "build_user": "android-build",
            "build_host": f"abfarm-{random.randint(10000, 99999)}",
            "bootloader": self._generate_bootloader_version(manufacturer, model),
            "radio_version": self._generate_radio_version(manufacturer),
            "kernel_version": self._generate_kernel_version(android_version),
            "opengl_version": "OpenGL ES 3.2",
            "vulkan_version": "1.1.0" if int(android_version) >= 11 else None,
            
            # Security features
            "security_patch_level": self._get_realistic_security_patch(android_version),
            "verified_boot": True,
            "device_encryption": True,
            
            # Telephony capabilities
            "telephony_capable": True,
            "dual_sim": random.choice([True, False]),
            "nfc_capable": True,
            "bluetooth_version": "5.2" if int(android_version) >= 12 else "5.0",
            "wifi_capabilities": ["802.11a", "802.11b", "802.11g", "802.11n", "802.11ac", "802.11ax"],
            
            # Camera capabilities
            "camera_count": random.choice([2, 3, 4]),
            "front_camera": True,
            
            # Sensors
            "sensors": [
                "accelerometer", "gyroscope", "magnetometer", "proximity",
                "ambient_light", "fingerprint", "barometer"
            ]
        }
        
        return profile

    def _generate_bootloader_version(self, manufacturer: str, model: str) -> str:
        """Generate realistic bootloader version"""
        if manufacturer.lower() == "samsung":
            return f"{model.replace(' ', '').upper()}{random.randint(100, 999)}"
        elif manufacturer.lower() == "google":
            return f"slider-{random.randint(10000000, 99999999)}"
        else:
            return f"{manufacturer.lower()}-{random.randint(1000, 9999)}"

    def _generate_radio_version(self, manufacturer: str) -> str:
        """Generate realistic radio version"""
        if manufacturer.lower() == "samsung":
            return f"G99{random.randint(10, 99)}BXXU{random.randint(1, 9)}AVJ{random.randint(1, 9)}"
        elif manufacturer.lower() == "google":
            return f"g5123b-{random.randint(100000, 999999)}-{random.randint(220101, 241231)}"
        else:
            return f"{random.randint(1, 9)}.{random.randint(0, 99)}.{random.randint(0, 999)}"

    def _generate_kernel_version(self, android_version: str) -> str:
        """Generate realistic kernel version based on Android version"""
        kernel_mapping = {
            "11": ["4.19", "5.4"],
            "12": ["5.4", "5.10"],
            "13": ["5.10", "5.15"],
            "14": ["5.15", "6.1"]
        }
        
        kernel_base = random.choice(kernel_mapping.get(android_version, ["5.4"]))
        patch_level = random.randint(1, 200)
        
        return f"{kernel_base}.{patch_level}-android{random.randint(11, 14)}-{random.randint(100000, 999999)}"

    def _get_realistic_security_patch(self, android_version: str) -> str:
        """Get realistic security patch date within the last 6 months"""
        base_date = datetime.now()
        
        # Security patches are typically 1-6 months behind current date
        days_behind = random.randint(30, 180)
        patch_date = base_date - timedelta(days=days_behind)
        
        # Ensure it's the first of the month (Android security patches are monthly)
        patch_date = patch_date.replace(day=1)
        
        return patch_date.strftime("%Y-%m-%d")

    def get_available_profiles(self) -> Dict:
        """Get list of all available device profiles"""
        return {
            manufacturer: list(models.keys()) 
            for manufacturer, models in self.device_profiles.items()
        }