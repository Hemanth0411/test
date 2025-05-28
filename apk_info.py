import subprocess
import os
import sys
from typing import Tuple, Optional

def get_aapt_path() -> Optional[str]:
    """
    Try to find the aapt executable in common Android SDK locations
    Returns the path to aapt if found, None otherwise
    """
    # Common Android SDK locations
    sdk_locations = [
        os.path.expanduser("~/Android/Sdk/build-tools"),
        os.path.expanduser("~/AppData/Local/Android/Sdk/build-tools"),
        "C:/Users/Administrator/AppData/Local/Android/Sdk/build-tools",
        "/usr/local/android-sdk/build-tools",
        "/opt/android-sdk/build-tools"
    ]
    
    # Look for aapt in build-tools subdirectories
    for sdk_path in sdk_locations:
        if os.path.exists(sdk_path):
            # Get all build-tools versions
            versions = [d for d in os.listdir(sdk_path) if os.path.isdir(os.path.join(sdk_path, d))]
            if versions:
                # Use the latest version
                latest_version = sorted(versions)[-1]
                aapt_path = os.path.join(sdk_path, latest_version, "aapt")
                if os.name == 'nt':  # Windows
                    aapt_path += '.exe'
                if os.path.exists(aapt_path):
                    return aapt_path
    
    return None

def clean_app_name(app_name: str) -> str:
    """
    Clean the app name by removing any additional information after the actual name
    """
    # Remove anything after a single quote or special character
    if "'" in app_name:
        app_name = app_name.split("'")[0]
    if " icon=" in app_name:
        app_name = app_name.split(" icon=")[0]
    if " label=" in app_name:
        app_name = app_name.split(" label=")[0]
    
    return app_name.strip()

def get_apk_info(apk_path: str) -> Tuple[str, str]:
    """
    Extract package name and app name from an APK file using aapt
    
    Args:
        apk_path (str): Path to the APK file
        
    Returns:
        Tuple[str, str]: (package_name, app_name)
        
    Raises:
        FileNotFoundError: If APK file doesn't exist
        ValueError: If aapt tool is not found or APK info cannot be extracted
    """
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK file not found: {apk_path}")
    
    # Get aapt path
    aapt_path = get_aapt_path()
    if not aapt_path:
        raise ValueError("aapt tool not found. Please ensure Android SDK is installed and aapt is in PATH")
    
    try:
        # Run aapt dump badging command with proper encoding handling
        result = subprocess.run(
            [aapt_path, "dump", "badging", apk_path],
            capture_output=True,
            encoding='utf-8',
            errors='replace',  # Replace invalid characters instead of raising error
            check=True
        )
        
        if not result.stdout:
            raise ValueError("No output from aapt command")
        
        # Parse the output
        package_name = None
        app_name = None
        
        for line in result.stdout.split('\n'):
            if line.startswith('package: name='):
                # Extract package name
                try:
                    package_name = line.split('name=')[1].split(' ')[0].strip("'")
                except IndexError:
                    continue
            elif line.startswith('application: label='):
                # Extract app name
                try:
                    app_name = line.split('label=')[1].strip("'")
                    app_name = clean_app_name(app_name)  # Clean the app name
                except IndexError:
                    continue
            elif line.startswith('application-label:'):
                # Alternative way to get app name
                try:
                    app_name = line.split(':')[1].strip()
                    app_name = clean_app_name(app_name)  # Clean the app name
                except IndexError:
                    continue
        
        if not package_name:
            raise ValueError("Could not extract package name from APK")
        
        # If app name is not found, use the last part of package name
        if not app_name:
            app_name = package_name.split('.')[-1].capitalize()
        
        return package_name, app_name
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
        raise ValueError(f"Error running aapt: {error_msg}")
    except Exception as e:
        raise ValueError(f"Error processing APK: {str(e)}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python apk_info.py <path_to_apk>")
        sys.exit(1)
    
    apk_path = sys.argv[1]
    
    try:
        package_name, app_name = get_apk_info(apk_path)
        print(f"\nAPK Information:")
        print(f"Package Name: {package_name}")
        print(f"App Name: {app_name}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 