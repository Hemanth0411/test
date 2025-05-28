#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# Default values (can be overridden by environment variables if needed, but we'll primarily use CMD args)
AVD_NAME="agent_avd"
EMULATOR_PORT="5554" # Default emulator port for ADB
ADB_DEVICE_SERIAL="emulator-${EMULATOR_PORT}"
AGENT_ROOT_DIR="/agent" # Default agent root dir inside the container

echo "Starting Android Emulator: ${AVD_NAME}"
# Start the emulator in the background, headless, with a specific port
# -no-audio: Disables audio, often not needed for automation
# -no-snapshot: Starts from a clean state (optional, remove if you want to use snapshots)
# -port: Specifies the console port for the emulator, adb will be on port+1
# -gpu swiftshader_indirect (or host, auto, off): Try different GPU modes if 'auto' has issues in Docker.
#   'swiftshader_indirect' is a software renderer, slower but more compatible in restricted environments.
#   For better performance on Linux with KVM, you might try 'host' if KVM is enabled for the container.
emulator -avd "${AVD_NAME}" -no-window -no-audio -no-snapshot -port "${EMULATOR_PORT}" -gpu swiftshader_indirect &

# Wait for the emulator to boot
echo "Waiting for emulator to boot completely..."
# Use adb wait-for-device, then check sys.boot_completed property
# Redirect stdout/stderr of initial wait to /dev/null to avoid clutter if device not immediately up
adb wait-for-device > /dev/null 2>&1
# Once device is online, wait for boot complete
while [ "$(adb -s "${ADB_DEVICE_SERIAL}" shell getprop sys.boot_completed | tr -d '\r')" != "1" ]; do
  echo "Still waiting for boot..."
  sleep 5
done
echo "Emulator booted and ADB device (${ADB_DEVICE_SERIAL}) is ready."

# (Optional) Unlock screen if it's lockeda
# adb -s "${ADB_DEVICE_SERIAL}" shell input keyevent 82 # KEYCODE_MENU to wake up
# adb -s "${ADB_DEVICE_SERIAL}" shell input keyevent 4  # KEYCODE_BACK to dismiss lock screen if simple

echo "Starting workflow manager..."

# Arguments for workflow_manager.py:
# 1. APK Path (passed as $1 to this script)
# 2. Task Description (passed as $2 to this script)
# Optional:
# 3. Model Choice (passed as $3 to this script, if provided)
# 4. API Key (passed as $4 to this script, if provided)

# Build the command for workflow_manager.py
WORKFLOW_CMD="python workflow_manager.py \"$1\" \"$2\" --agent_root_dir \"${AGENT_ROOT_DIR}\""

if [ -n "$3" ] && [ "$3" != "None" ]; then # Check if Model Choice is provided and not "None"
    WORKFLOW_CMD="${WORKFLOW_CMD} --agent_model_choice \"$3\""
fi

if [ -n "$4" ] && [ "$4" != "None" ]; then # Check if API Key is provided and not "None"
    WORKFLOW_CMD="${WORKFLOW_CMD} --agent_api_key \"$4\""
fi

echo "Executing: ${WORKFLOW_CMD}"
# Use exec to replace the shell process with the Python process
eval exec "${WORKFLOW_CMD}"