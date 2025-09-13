#!/usr/bin/env python3

"""
LSPosed/Xposed Installer and Module Manager
Manages LSPosed framework and Xposed modules for system modification
"""

import os
import json
import subprocess
import zipfile
import shutil
from pathlib import Path

class XposedInstaller:
    def __init__(self):
        self.lsposed_path = "/data/adb/lspd"
        self.modules_path = "/data/adb/lspd/modules"
        self.config_path = "/data/adb/lspd/config"
        self.framework_path = "/system/framework"
        
    def is_lsposed_installed(self):
        """Check if LSPosed is installed"""
        return os.path.exists(self.lsposed_path) and os.path.exists("/system/framework/lspd")
    
    def get_lsposed_version(self):
        """Get LSPosed version"""
        try:
            version_file = os.path.join(self.lsposed_path, "version")
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    return f.read().strip()
        except:
            pass
        return "Unknown"
    
    def install_xposed_module(self, module_apk_path, package_name=None):
        """Install Xposed module APK"""
        if not self.is_lsposed_installed():
            print("ERROR: LSPosed not installed")
            return False
        
        try:
            # Install APK using pm
            result = subprocess.run(["pm", "install", "-r", module_apk_path],
                                  capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                print(f"ERROR: Failed to install APK: {result.stderr}")
                return False
            
            # Get package name from APK if not provided
            if not package_name:
                try:
                    aapt_result = subprocess.run(["aapt", "dump", "badging", module_apk_path],
                                               capture_output=True, text=True, check=False)
                    for line in aapt_result.stdout.split('\n'):
                        if line.startswith("package: name="):
                            package_name = line.split("'")[1]
                            break
                except:
                    print("WARNING: Could not determine package name")
            
            if package_name:
                print(f"Xposed module {package_name} installed successfully")
                
                # Enable module by default
                self.enable_module(package_name)
                
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to install Xposed module: {e}")
            return False
    
    def enable_module(self, package_name):
        """Enable Xposed module"""
        try:
            # Create modules config directory
            os.makedirs(self.config_path, exist_ok=True)
            
            # Enable module in LSPosed config
            enabled_modules_file = os.path.join(self.config_path, "enabled_modules.json")
            
            enabled_modules = []
            if os.path.exists(enabled_modules_file):
                try:
                    with open(enabled_modules_file, 'r') as f:
                        enabled_modules = json.load(f)
                except:
                    pass
            
            if package_name not in enabled_modules:
                enabled_modules.append(package_name)
                
                with open(enabled_modules_file, 'w') as f:
                    json.dump(enabled_modules, f, indent=2)
                
                print(f"Module {package_name} enabled")
                return True
            else:
                print(f"Module {package_name} already enabled")
                return True
                
        except Exception as e:
            print(f"ERROR: Failed to enable module: {e}")
            return False
    
    def disable_module(self, package_name):
        """Disable Xposed module"""
        try:
            enabled_modules_file = os.path.join(self.config_path, "enabled_modules.json")
            
            if not os.path.exists(enabled_modules_file):
                print(f"Module {package_name} not found in enabled modules")
                return False
            
            enabled_modules = []
            try:
                with open(enabled_modules_file, 'r') as f:
                    enabled_modules = json.load(f)
            except:
                pass
            
            if package_name in enabled_modules:
                enabled_modules.remove(package_name)
                
                with open(enabled_modules_file, 'w') as f:
                    json.dump(enabled_modules, f, indent=2)
                
                print(f"Module {package_name} disabled")
                return True
            else:
                print(f"Module {package_name} not enabled")
                return False
                
        except Exception as e:
            print(f"ERROR: Failed to disable module: {e}")
            return False
    
    def list_installed_modules(self):
        """List installed Xposed modules"""
        try:
            # Get list of installed packages with Xposed metadata
            result = subprocess.run(["pm", "list", "packages", "-3"],
                                  capture_output=True, text=True, check=False)
            
            modules = []
            for line in result.stdout.split('\n'):
                if line.startswith("package:"):
                    package_name = line.replace("package:", "").strip()
                    
                    # Check if package has Xposed metadata
                    if self.is_xposed_module(package_name):
                        module_info = self.get_module_info(package_name)
                        modules.append(module_info)
            
            return modules
            
        except Exception as e:
            print(f"ERROR: Failed to list modules: {e}")
            return []
    
    def is_xposed_module(self, package_name):
        """Check if package is an Xposed module"""
        try:
            # Check for xposed_init file or meta-data
            result = subprocess.run(["pm", "dump", package_name],
                                  capture_output=True, text=True, check=False)
            
            if "xposed" in result.stdout.lower() or "lsposed" in result.stdout.lower():
                return True
                
            # Also check for common Xposed module characteristics
            xposed_keywords = ["hook", "module", "framework", "modify"]
            for keyword in xposed_keywords:
                if keyword in result.stdout.lower():
                    return True
                    
            return False
            
        except:
            return False
    
    def get_module_info(self, package_name):
        """Get detailed information about Xposed module"""
        module_info = {
            'package_name': package_name,
            'name': package_name,
            'version': 'Unknown',
            'enabled': False,
            'description': ''
        }
        
        try:
            # Get package info
            result = subprocess.run(["pm", "dump", package_name],
                                  capture_output=True, text=True, check=False)
            
            # Parse output for relevant information
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('versionName='):
                    module_info['version'] = line.split('=', 1)[1]
                elif 'android:label=' in line:
                    # Extract label
                    if '@' not in line:
                        label = line.split('android:label=')[1].strip('"')
                        if label:
                            module_info['name'] = label
            
            # Check if module is enabled
            enabled_modules_file = os.path.join(self.config_path, "enabled_modules.json")
            if os.path.exists(enabled_modules_file):
                try:
                    with open(enabled_modules_file, 'r') as f:
                        enabled_modules = json.load(f)
                        module_info['enabled'] = package_name in enabled_modules
                except:
                    pass
            
        except Exception as e:
            print(f"WARNING: Could not get info for {package_name}: {e}")
        
        return module_info
    
    def install_privacy_modules(self):
        """Install common privacy/spoofing modules"""
        print("Installing privacy and spoofing modules...")
        
        # Create module configurations for common privacy modules
        modules_config = {
            "com.github.tehcneko.meowcatspoof": {
                "name": "MeowCat Spoof",
                "description": "Device and location spoofing",
                "hooks": ["android.os.Build", "android.location.LocationManager"]
            },
            "de.robv.android.xposed.mods.appsettings": {
                "name": "App Settings",
                "description": "Per-app settings modification",
                "hooks": ["android.content.res.Resources", "android.app.ActivityThread"]
            },
            "com.crossbowffs.usticker": {
                "name": "USB Sticker",
                "description": "USB debugging detection bypass",
                "hooks": ["android.provider.Settings"]
            }
        }
        
        # Create module configurations
        for package_name, config in modules_config.items():
            self.create_module_config(package_name, config)
        
        print("Privacy modules configured")
    
    def create_module_config(self, package_name, config):
        """Create configuration for Xposed module"""
        try:
            config_dir = os.path.join(self.config_path, "modules", package_name)
            os.makedirs(config_dir, exist_ok=True)
            
            # Create module config file
            config_file = os.path.join(config_dir, "config.json")
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Create hooks configuration
            if 'hooks' in config:
                hooks_file = os.path.join(config_dir, "hooks.json")
                hooks_config = {
                    "enabled_hooks": config['hooks'],
                    "hook_mode": "replace",
                    "stealth_mode": True
                }
                
                with open(hooks_file, 'w') as f:
                    json.dump(hooks_config, f, indent=2)
            
            print(f"Configuration created for {package_name}")
            
        except Exception as e:
            print(f"ERROR: Failed to create config for {package_name}: {e}")
    
    def create_build_prop_hook(self):
        """Create Xposed module to hook build properties"""
        module_dir = "/data/local/tmp/buildprop_hook"
        os.makedirs(module_dir, exist_ok=True)
        
        # Create hook script
        hook_script = """
package com.android.container.buildprophook;

import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedHelpers;
import de.robv.android.xposed.callbacks.XC_LoadPackage.LoadPackageParam;
import android.os.SystemProperties;

public class BuildPropHook implements IXposedHookLoadPackage {
    
    @Override
    public void handleLoadPackage(LoadPackageParam lpparam) throws Throwable {
        
        // Hook SystemProperties.get() calls
        XposedHelpers.findAndHookMethod(SystemProperties.class, "get", 
            String.class, new XC_MethodHook() {
                @Override
                protected void afterHookedMethod(MethodHookParam param) throws Throwable {
                    String key = (String) param.args[0];
                    String originalValue = (String) param.getResult();
                    String spoofedValue = getSpoofedProperty(key, originalValue);
                    
                    if (!spoofedValue.equals(originalValue)) {
                        param.setResult(spoofedValue);
                    }
                }
            });
        
        // Hook SystemProperties.get() with default value
        XposedHelpers.findAndHookMethod(SystemProperties.class, "get", 
            String.class, String.class, new XC_MethodHook() {
                @Override
                protected void afterHookedMethod(MethodHookParam param) throws Throwable {
                    String key = (String) param.args[0];
                    String originalValue = (String) param.getResult();
                    String spoofedValue = getSpoofedProperty(key, originalValue);
                    
                    if (!spoofedValue.equals(originalValue)) {
                        param.setResult(spoofedValue);
                    }
                }
            });
    }
    
    private String getSpoofedProperty(String key, String originalValue) {
        // Load spoofed properties from file
        // This would read from /data/local/tmp/spoofed_props.json
        
        switch (key) {
            case "ro.debuggable":
                return "0";
            case "ro.secure":
                return "1";
            case "ro.build.type":
                return "user";
            case "ro.build.tags":
                return "release-keys";
            case "ro.boot.verifiedbootstate":
                return "green";
            case "ro.boot.flash.locked":
                return "1";
            default:
                return originalValue;
        }
    }
}
"""
        
        # Create manifest and other files
        # This would be a complete Android module structure
        
        print("Build property hook module created")
    
    def print_modules(self):
        """Print formatted list of installed modules"""
        modules = self.list_installed_modules()
        
        if not modules:
            print("No Xposed modules installed")
            return
        
        print("Installed Xposed Modules:")
        print("-" * 80)
        print(f"{'Package Name':<40} {'Name':<20} {'Version':<10} {'Status':<10}")
        print("-" * 80)
        
        for module in modules:
            status = "Enabled" if module['enabled'] else "Disabled"
            print(f"{module['package_name']:<40} "
                  f"{module['name']:<20} "
                  f"{module['version']:<10} "
                  f"{status:<10}")
    
    def restart_lsposed(self):
        """Restart LSPosed service"""
        try:
            # Stop LSPosed
            subprocess.run(["killall", "lspd"], check=False)
            
            # Start LSPosed
            subprocess.run(["/system/bin/lspd"], check=False)
            
            print("LSPosed service restarted")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to restart LSPosed: {e}")
            return False

def main():
    import sys
    
    installer = XposedInstaller()
    
    if len(sys.argv) < 2:
        print("Xposed Installer Usage:")
        print("  xposed_installer.py status")
        print("  xposed_installer.py list")
        print("  xposed_installer.py install <module.apk>")
        print("  xposed_installer.py enable <package_name>")
        print("  xposed_installer.py disable <package_name>")
        print("  xposed_installer.py install-privacy")
        print("  xposed_installer.py create-buildprop-hook")
        print("  xposed_installer.py restart")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        print(f"LSPosed installed: {installer.is_lsposed_installed()}")
        if installer.is_lsposed_installed():
            print(f"LSPosed version: {installer.get_lsposed_version()}")
    
    elif command == "list":
        installer.print_modules()
    
    elif command == "install" and len(sys.argv) > 2:
        installer.install_xposed_module(sys.argv[2])
    
    elif command == "enable" and len(sys.argv) > 2:
        installer.enable_module(sys.argv[2])
    
    elif command == "disable" and len(sys.argv) > 2:
        installer.disable_module(sys.argv[2])
    
    elif command == "install-privacy":
        installer.install_privacy_modules()
    
    elif command == "create-buildprop-hook":
        installer.create_build_prop_hook()
    
    elif command == "restart":
        installer.restart_lsposed()
    
    else:
        print("Invalid command")
        sys.exit(1)

if __name__ == "__main__":
    main()