#!/usr/bin/env python3

"""
Build.prop Generator for Android Device Spoofing
Generates realistic build.prop files based on device profiles
"""

import json
import random
import string
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

class BuildPropGenerator:
    def __init__(self, profile_path=None):
        self.profile_path = profile_path
        self.profile_data = None
        if profile_path:
            self.load_profile(profile_path)
    
    def load_profile(self, profile_path):
        """Load device profile from JSON file"""
        try:
            with open(profile_path, 'r') as f:
                self.profile_data = json.load(f)
            print(f"Loaded profile: {self.profile_data.get('device_name', 'Unknown')}")
        except Exception as e:
            print(f"Error loading profile: {e}")
            return False
        return True
    
    def generate_imei(self, pattern=None):
        """Generate a realistic IMEI number"""
        if pattern:
            # Use pattern from profile (e.g., "35{13}" means 35 followed by 13 random digits)
            if '{' in pattern and '}' in pattern:
                prefix = pattern.split('{')[0]
                count = int(pattern.split('{')[1].split('}')[0])
                suffix = ''.join([str(random.randint(0, 9)) for _ in range(count)])
                return prefix + suffix
        
        # Default IMEI generation
        # Start with common TAC (Type Allocation Code)
        tacs = ['35404309', '35171005', '35328504', '35699302', '35917803']
        tac = random.choice(tacs)
        
        # Generate 6 random digits for serial number
        serial = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Calculate check digit using Luhn algorithm
        digits = tac + serial
        check_digit = self.calculate_luhn_check_digit(digits)
        
        return digits + str(check_digit)
    
    def calculate_luhn_check_digit(self, digits):
        """Calculate Luhn check digit for IMEI"""
        total = 0
        for i, digit in enumerate(reversed(digits)):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n = (n // 10) + (n % 10)
            total += n
        return (10 - (total % 10)) % 10
    
    def generate_serial_number(self, pattern=None):
        """Generate device serial number"""
        if pattern:
            # Use pattern from profile
            result = ""
            i = 0
            while i < len(pattern):
                char = pattern[i]
                if char == '{' and i + 2 < len(pattern) and pattern[i + 2] == '}':
                    count = int(pattern[i + 1])
                    result += ''.join([str(random.randint(0, 9)) for _ in range(count)])
                    i += 3
                else:
                    result += char
                    i += 1
            return result
        
        # Default serial number generation
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    
    def generate_android_id(self, length=16):
        """Generate Android ID (hexadecimal)"""
        return ''.join([format(random.randint(0, 15), 'x') for _ in range(length)])
    
    def generate_mac_address(self, oui=None):
        """Generate MAC address with optional OUI"""
        if oui:
            # Use OUI from profile
            oui_clean = oui.replace(':', '')
            suffix = ''.join([format(random.randint(0, 255), '02x') for _ in range(3)])
            mac = oui_clean + suffix
            return ':'.join([mac[i:i+2] for i in range(0, 12, 2)]).upper()
        
        # Generate random MAC
        return ':'.join([format(random.randint(0, 255), '02x') for _ in range(6)]).upper()
    
    def generate_build_timestamp(self):
        """Generate realistic build timestamp"""
        # Random timestamp within last 6 months
        now = int(time.time())
        six_months_ago = now - (6 * 30 * 24 * 60 * 60)
        build_time = random.randint(six_months_ago, now)
        return str(build_time)
    
    def generate_build_prop(self, output_path=None):
        """Generate complete build.prop file"""
        if not self.profile_data:
            print("No profile loaded")
            return None
        
        # Generate unique identifiers
        imei = self.generate_imei(self.profile_data.get('spoofing_config', {}).get('imei_pattern'))
        serial = self.generate_serial_number(self.profile_data.get('spoofing_config', {}).get('serial_pattern'))
        android_id = self.generate_android_id(self.profile_data.get('spoofing_config', {}).get('android_id_length', 16))
        mac_address = self.generate_mac_address(self.profile_data.get('spoofing_config', {}).get('mac_address_oui'))
        build_timestamp = self.generate_build_timestamp()
        
        # Start building the properties
        props = []
        
        # Header
        props.append("# Build properties generated by Android Container Platform")
        props.append(f"# Device: {self.profile_data.get('device_name', 'Unknown')}")
        props.append(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        props.append("")
        
        # Core device properties
        props.append("# Device identification")
        props.append(f"ro.product.model={self.profile_data.get('model')}")
        props.append(f"ro.product.brand={self.profile_data.get('brand')}")
        props.append(f"ro.product.name={self.profile_data.get('product')}")
        props.append(f"ro.product.device={self.profile_data.get('device')}")
        props.append(f"ro.product.manufacturer={self.profile_data.get('manufacturer')}")
        props.append("")
        
        # Build information
        props.append("# Build information")
        props.append(f"ro.build.id={self.profile_data.get('build_id')}")
        props.append(f"ro.build.display.id={self.profile_data.get('build_id')}")
        props.append(f"ro.build.version.release={self.profile_data.get('android_version')}")
        props.append(f"ro.build.version.sdk={self.profile_data.get('sdk_level')}")
        props.append(f"ro.build.type={self.profile_data.get('build_type')}")
        props.append(f"ro.build.tags={self.profile_data.get('build_tags')}")
        props.append(f"ro.build.fingerprint={self.profile_data.get('build_fingerprint')}")
        props.append(f"ro.build.description={self.profile_data.get('build_description')}")
        props.append(f"ro.build.date.utc={build_timestamp}")
        props.append("")
        
        # Hardware properties
        props.append("# Hardware properties")
        props.append(f"ro.hardware={self.profile_data.get('hardware')}")
        props.append(f"ro.product.board={self.profile_data.get('device')}")
        props.append(f"ro.product.cpu.abi={self.profile_data.get('cpu_abi')}")
        if self.profile_data.get('cpu_abi2'):
            props.append(f"ro.product.cpu.abi2={self.profile_data.get('cpu_abi2')}")
        props.append("")
        
        # Security properties
        props.append("# Security properties")
        props.append(f"ro.build.version.security_patch={self.profile_data.get('security_patch')}")
        props.append("ro.secure=1")
        props.append("ro.debuggable=0")
        props.append("ro.boot.verifiedbootstate=green")
        props.append("ro.boot.flash.locked=1")
        props.append("ro.boot.veritymode=enforcing")
        props.append("ro.boot.warranty_bit=0")
        props.append("ro.warranty_bit=0")
        props.append("")
        
        # Device identifiers
        props.append("# Device identifiers")
        props.append(f"ro.serialno={serial}")
        props.append(f"ro.boot.serialno={serial}")
        props.append("# Android ID will be set by runtime scripts")
        props.append("# IMEI will be set by runtime scripts")
        props.append("")
        
        # Display properties
        if 'display' in self.profile_data:
            display = self.profile_data['display']
            props.append("# Display properties")
            props.append(f"ro.sf.lcd_density={display.get('density', 320)}")
            props.append(f"ro.config.screen_width={display.get('width_px', 1080)}")
            props.append(f"ro.config.screen_height={display.get('height_px', 1920)}")
            props.append("")
        
        # Add system properties from profile
        if 'system_properties' in self.profile_data:
            props.append("# System properties from device profile")
            for key, value in self.profile_data['system_properties'].items():
                props.append(f"{key}={value}")
            props.append("")
        
        # Network properties
        props.append("# Network properties")
        props.append("ro.telephony.default_network=9")
        props.append("telephony.lteOnCdmaDevice=1")
        props.append("ro.com.google.locationfeatures=1")
        props.append("ro.com.google.networklocation=1")
        props.append("")
        
        # Additional spoofing properties
        props.append("# Additional spoofing properties")
        props.append("persist.sys.usb.config=none")
        props.append("ro.adb.secure=1")
        props.append("persist.sys.developer_options_enabled=0")
        props.append("ro.allow.mock.location=0")
        props.append("ro.kernel.android.checkjni=0")
        props.append("")
        
        # Join all properties
        build_prop_content = '\n'.join(props)
        
        # Save to file if output path provided
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    f.write(build_prop_content)
                print(f"Build.prop saved to: {output_path}")
            except Exception as e:
                print(f"Error saving build.prop: {e}")
        
        # Also save identifiers to separate file for runtime use
        identifiers = {
            'imei': imei,
            'serial': serial,
            'android_id': android_id,
            'mac_address': mac_address,
            'bluetooth_name': self.profile_data.get('spoofing_config', {}).get('bluetooth_name', 'Android Device'),
            'user_agent': self.profile_data.get('spoofing_config', {}).get('user_agent', 'Mozilla/5.0 (Linux; Android)')
        }
        
        if output_path:
            identifiers_path = output_path.replace('.prop', '_identifiers.json')
            try:
                with open(identifiers_path, 'w') as f:
                    json.dump(identifiers, f, indent=2)
                print(f"Device identifiers saved to: {identifiers_path}")
            except Exception as e:
                print(f"Error saving identifiers: {e}")
        
        return build_prop_content, identifiers
    
    def list_available_profiles(self, profiles_dir="/system/etc/device-profiles"):
        """List available device profiles"""
        try:
            profiles_path = Path(profiles_dir)
            profiles = list(profiles_path.glob("*.json"))
            
            print("Available device profiles:")
            for profile in profiles:
                try:
                    with open(profile, 'r') as f:
                        data = json.load(f)
                    device_name = data.get('device_name', 'Unknown')
                    android_version = data.get('android_version', 'Unknown')
                    print(f"  {profile.stem}: {device_name} (Android {android_version})")
                except:
                    print(f"  {profile.stem}: [Error reading profile]")
        except Exception as e:
            print(f"Error listing profiles: {e}")

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  build_prop_generator.py <profile_file> [output_file]")
        print("  build_prop_generator.py --list")
        sys.exit(1)
    
    generator = BuildPropGenerator()
    
    if sys.argv[1] == '--list':
        generator.list_available_profiles()
        return
    
    profile_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not generator.load_profile(profile_file):
        sys.exit(1)
    
    build_prop, identifiers = generator.generate_build_prop(output_file)
    
    if not output_file:
        print("\nGenerated build.prop content:")
        print("=" * 50)
        print(build_prop)
        print("=" * 50)
        print("\nGenerated identifiers:")
        for key, value in identifiers.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    main()