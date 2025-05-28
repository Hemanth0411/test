import os
import sys
from adb_controller import run_adb_command

def install_apk(apk_path):
    """
    Install an APK file on the connected device/emulator.
    
    Args:
        apk_path (str): Path to the APK file
        
    Returns:
        bool: True if installation was successful, False otherwise
    """
    if not os.path.exists(apk_path):
        print(f"Error: APK file not found at {apk_path}")
        return False
        
    print(f"Installing APK: {apk_path}")
    result = run_adb_command(f"install -r {apk_path}")
    
    if result and "Success" in result:
        print("APK installed successfully!")
        return True
    else:
        print("Failed to install APK")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python install_apk.py <path_to_apk>")
        sys.exit(1)
        
    apk_path = sys.argv[1]
    install_apk(apk_path)

if __name__ == "__main__":
    main() 