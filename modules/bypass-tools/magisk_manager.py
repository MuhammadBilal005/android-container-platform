#!/usr/bin/env python3

"""
Magisk Manager for Android Containers
Manages Magisk installation, modules, and root hiding
"""

import os
import json
import subprocess
import zipfile
import requests
import hashlib
from pathlib import Path

class MagiskManager:
    def __init__(self):
        self.magisk_path = "/data/adb/magisk"
        self.modules_path = "/data/adb/modules"
        self.magisk_binary = "/system/bin/magisk"
        self.busybox_path = "/data/adb/magisk/busybox"
        
    def is_magisk_installed(self):
        """Check if Magisk is installed"""
        return os.path.exists(self.magisk_binary) or os.path.exists(self.magisk_path)
    
    def get_magisk_version(self):
        """Get installed Magisk version"""
        try:
            result = subprocess.run([self.magisk_binary, "-v"], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "Unknown"
    
    def install_module(self, module_path, module_id=None):
        """Install a Magisk module from zip file"""
        if not self.is_magisk_installed():
            print("ERROR: Magisk not installed")
            return False
        
        try:
            # Create modules directory if it doesn't exist
            os.makedirs(self.modules_path, exist_ok=True)
            
            # Extract module
            with zipfile.ZipFile(module_path, 'r') as zip_file:
                # Read module.prop to get module ID
                try:
                    module_prop = zip_file.read('module.prop').decode('utf-8')
                    for line in module_prop.split('\n'):
                        if line.startswith('id='):
                            module_id = line.split('=', 1)[1].strip()
                            break
                except:
                    if not module_id:
                        print("ERROR: Cannot determine module ID")
                        return False
                
                # Create module directory
                module_dir = os.path.join(self.modules_path, module_id)
                os.makedirs(module_dir, exist_ok=True)
                
                # Extract all files
                zip_file.extractall(module_dir)
            
            # Set proper permissions
            self.set_module_permissions(module_dir)
            
            print(f"Module {module_id} installed successfully")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to install module: {e}")
            return False
    
    def set_module_permissions(self, module_dir):
        """Set proper permissions for module files"""
        try:
            # Set directory permissions
            os.chmod(module_dir, 0o755)
            
            # Set file permissions
            for root, dirs, files in os.walk(module_dir):
                for dir_name in dirs:
                    os.chmod(os.path.join(root, dir_name), 0o755)
                
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    if file_name in ['service.sh', 'post-fs-data.sh', 'uninstall.sh'] or file_name.endswith('.sh'):
                        os.chmod(file_path, 0o755)  # Executable
                    else:
                        os.chmod(file_path, 0o644)  # Regular file
                        
        except Exception as e:
            print(f"WARNING: Failed to set permissions: {e}")
    
    def create_module(self, module_id, module_name, module_version, module_author, description=""):
        """Create a new Magisk module"""
        module_dir = os.path.join(self.modules_path, module_id)
        
        try:
            os.makedirs(module_dir, exist_ok=True)
            
            # Create module.prop
            module_prop = f"""id={module_id}
name={module_name}
version={module_version}
versionCode={int(module_version.replace('.', ''))}
author={module_author}
description={description}
"""
            
            with open(os.path.join(module_dir, 'module.prop'), 'w') as f:
                f.write(module_prop)
            
            # Create empty service.sh
            service_sh = """#!/system/bin/sh

# This script will be executed in late_start service mode
"""
            
            with open(os.path.join(module_dir, 'service.sh'), 'w') as f:
                f.write(service_sh)
            
            self.set_module_permissions(module_dir)
            
            print(f"Module {module_id} created successfully")
            return module_dir
            
        except Exception as e:
            print(f"ERROR: Failed to create module: {e}")
            return None
    
    def enable_module(self, module_id):
        """Enable a Magisk module"""
        module_dir = os.path.join(self.modules_path, module_id)
        if not os.path.exists(module_dir):
            print(f"ERROR: Module {module_id} not found")
            return False
        
        # Remove disable flag if it exists
        disable_flag = os.path.join(module_dir, 'disable')
        if os.path.exists(disable_flag):
            os.remove(disable_flag)
        
        print(f"Module {module_id} enabled")
        return True
    
    def disable_module(self, module_id):
        """Disable a Magisk module"""
        module_dir = os.path.join(self.modules_path, module_id)
        if not os.path.exists(module_dir):
            print(f"ERROR: Module {module_id} not found")
            return False
        
        # Create disable flag
        disable_flag = os.path.join(module_dir, 'disable')
        with open(disable_flag, 'w') as f:
            f.write('')
        
        print(f"Module {module_id} disabled")
        return True
    
    def remove_module(self, module_id):
        """Remove a Magisk module"""
        module_dir = os.path.join(self.modules_path, module_id)
        if not os.path.exists(module_dir):
            print(f"ERROR: Module {module_id} not found")
            return False
        
        # Create remove flag (will be removed on next reboot)
        remove_flag = os.path.join(module_dir, 'remove')
        with open(remove_flag, 'w') as f:
            f.write('')
        
        print(f"Module {module_id} marked for removal")
        return True
    
    def list_modules(self):
        """List all installed modules"""
        if not os.path.exists(self.modules_path):
            print("No modules installed")
            return []
        
        modules = []
        for module_id in os.listdir(self.modules_path):
            module_dir = os.path.join(self.modules_path, module_id)
            if not os.path.isdir(module_dir):
                continue
            
            module_prop_file = os.path.join(module_dir, 'module.prop')
            if not os.path.exists(module_prop_file):
                continue
            
            # Parse module.prop
            module_info = {'id': module_id}
            try:
                with open(module_prop_file, 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            module_info[key] = value
            except:
                pass
            
            # Check status
            module_info['enabled'] = not os.path.exists(os.path.join(module_dir, 'disable'))
            module_info['remove_pending'] = os.path.exists(os.path.join(module_dir, 'remove'))
            
            modules.append(module_info)
        
        return modules
    
    def print_modules(self):
        """Print formatted list of modules"""
        modules = self.list_modules()
        
        if not modules:
            print("No modules installed")
            return
        
        print("Installed Magisk Modules:")
        print("-" * 80)
        print(f"{'ID':<20} {'Name':<25} {'Version':<10} {'Status':<10}")
        print("-" * 80)
        
        for module in modules:
            status = "Enabled" if module['enabled'] else "Disabled"
            if module['remove_pending']:
                status = "Removing"
            
            print(f"{module.get('id', 'Unknown'):<20} "
                  f"{module.get('name', 'Unknown'):<25} "
                  f"{module.get('version', 'Unknown'):<10} "
                  f"{status:<10}")
    
    def configure_denylist(self, packages=None):
        """Configure Magisk DenyList"""
        denylist_path = "/data/adb/magisk/.magisk/denylist"
        
        # Default packages to hide root from
        default_packages = [
            "com.google.android.gms",
            "com.google.android.gsf",
            "com.android.vending",
            "com.google.android.play.games",
            "com.chase.sig.android",
            "com.bankofamerica.android",
            "com.wellsfargo.mobile.android",
            "com.paypal.android.p2pmobile",
            "com.square.cash",
            "com.nianticlabs.pokemongo",
            "com.supercell.clashofclans",
            "com.king.candycrushsaga",
            "com.netflix.mediaclient",
            "com.disney.disneyplus"
        ]
        
        packages = packages or default_packages
        
        try:
            os.makedirs(os.path.dirname(denylist_path), exist_ok=True)
            
            with open(denylist_path, 'w') as f:
                for package in packages:
                    f.write(f"{package}\n")
            
            print(f"DenyList configured with {len(packages)} packages")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to configure DenyList: {e}")
            return False
    
    def hide_magisk_app(self, package_name="com.topjohnwu.magisk"):
        """Hide Magisk app with random package name"""
        try:
            import random
            import string
            
            # Generate random package name
            random_name = 'com.android.' + ''.join(random.choices(string.ascii_lowercase, k=8))
            
            # Use Magisk command to hide app
            result = subprocess.run([self.magisk_binary, "--hide", package_name, random_name],
                                  capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                print(f"Magisk app hidden as: {random_name}")
                return True
            else:
                print(f"Failed to hide Magisk app: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"ERROR: Failed to hide Magisk app: {e}")
            return False
    
    def create_integrity_bypass_module(self):
        """Create a comprehensive integrity bypass module"""
        module_id = "comprehensive_integrity_bypass"
        module_dir = self.create_module(
            module_id,
            "Comprehensive Integrity Bypass",
            "1.0",
            "Android Container Platform",
            "Advanced SafetyNet and Play Integrity bypass"
        )
        
        if not module_dir:
            return False
        
        # Create system.prop for build property modifications
        system_prop = """# Integrity Bypass Properties
ro.debuggable=0
ro.secure=1
ro.boot.verifiedbootstate=green
ro.boot.flash.locked=1
ro.boot.veritymode=enforcing
ro.boot.warranty_bit=0
ro.warranty_bit=0
ro.build.selinux.enforce=1
ro.build.type=user
ro.build.tags=release-keys

# Hide development settings
persist.sys.usb.config=none
ro.adb.secure=1
persist.sys.developer_options_enabled=0

# Additional security properties
ro.is_userdebug=0
ro.allow.mock.location=0
ro.kernel.android.checkjni=0
"""
        
        with open(os.path.join(module_dir, 'system.prop'), 'w') as f:
            f.write(system_prop)
        
        # Create service script for runtime modifications
        service_script = """#!/system/bin/sh

# Runtime integrity bypass modifications

# Reset properties that might be modified
resetprop ro.debuggable 0
resetprop ro.secure 1
resetprop ro.boot.verifiedbootstate green
resetprop ro.boot.flash.locked 1

# Hide Magisk traces
if [ -d "/data/adb/magisk" ]; then
    chmod 000 /data/adb/magisk/.magisk 2>/dev/null
fi

# Hide root binaries
for su_path in "/system/bin/su" "/system/xbin/su" "/sbin/su"; do
    if [ -f "$su_path" ]; then
        chmod 000 "$su_path" 2>/dev/null
    fi
done

# Create fake SafetyNet result cache
mkdir -p /data/data/com.google.android.gms/cache/safety_net
cat > /data/data/com.google.android.gms/cache/safety_net/result.json << 'EOF'
{
  "nonce": "R2Rra24fVm5xa2Mgd2XY",
  "timestampMs": 9860437986543,
  "apkPackageName": "com.google.android.gms",
  "ctsProfileMatch": true,
  "basicIntegrity": true,
  "evaluationType": "BASIC,HARDWARE_BACKED"
}
EOF

chown system:system /data/data/com.google.android.gms/cache/safety_net/result.json 2>/dev/null
chmod 600 /data/data/com.google.android.gms/cache/safety_net/result.json 2>/dev/null
"""
        
        with open(os.path.join(module_dir, 'service.sh'), 'w') as f:
            f.write(service_script)
        
        self.set_module_permissions(module_dir)
        
        print(f"Comprehensive integrity bypass module created")
        return True

def main():
    import sys
    
    manager = MagiskManager()
    
    if len(sys.argv) < 2:
        print("Magisk Manager Usage:")
        print("  magisk_manager.py status")
        print("  magisk_manager.py list")
        print("  magisk_manager.py enable <module_id>")
        print("  magisk_manager.py disable <module_id>")
        print("  magisk_manager.py remove <module_id>")
        print("  magisk_manager.py install <module_zip>")
        print("  magisk_manager.py create-bypass")
        print("  magisk_manager.py configure-denylist")
        print("  magisk_manager.py hide-app")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        print(f"Magisk installed: {manager.is_magisk_installed()}")
        if manager.is_magisk_installed():
            print(f"Magisk version: {manager.get_magisk_version()}")
    
    elif command == "list":
        manager.print_modules()
    
    elif command == "enable" and len(sys.argv) > 2:
        manager.enable_module(sys.argv[2])
    
    elif command == "disable" and len(sys.argv) > 2:
        manager.disable_module(sys.argv[2])
    
    elif command == "remove" and len(sys.argv) > 2:
        manager.remove_module(sys.argv[2])
    
    elif command == "install" and len(sys.argv) > 2:
        manager.install_module(sys.argv[2])
    
    elif command == "create-bypass":
        manager.create_integrity_bypass_module()
    
    elif command == "configure-denylist":
        manager.configure_denylist()
    
    elif command == "hide-app":
        manager.hide_magisk_app()
    
    else:
        print("Invalid command")
        sys.exit(1)

if __name__ == "__main__":
    main()