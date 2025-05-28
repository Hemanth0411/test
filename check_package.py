import sys
from adb_controller import run_adb_command

def is_package_installed(package_name):
    """
    Check if a package is installed on the connected device/emulator.
    
    Args:
        package_name (str): The package name to check
        
    Returns:
        bool: True if package is installed, False otherwise
    """
    print(f"Checking if package '{package_name}' is installed...")
    result = run_adb_command(f"shell pm list packages | grep {package_name}")
    
    if result and package_name in result:
        print(f"Package '{package_name}' is installed")
        return True
    else:
        print(f"Package '{package_name}' is not installed")
        return False

def get_package_version(package_name):
    """
    Get the version of an installed package.
    
    Args:
        package_name (str): The package name to check
        
    Returns:
        str: Version string if found, None otherwise
    """
    result = run_adb_command(f"shell dumpsys package {package_name} | grep versionName")
    if result:
        try:
            version = result.split("versionName=")[1].strip()
            return version
        except:
            return None
    return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python check_package.py <package_name>")
        sys.exit(1)
        
    package_name = sys.argv[1]
    if is_package_installed(package_name):
        version = get_package_version(package_name)
        if version:
            print(f"Package version: {version}")

if __name__ == "__main__":
    main() 