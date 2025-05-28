import argparse
import os
import sys
import time

try:
    from apk_info import get_apk_info
    from install_apk import install_apk
    from check_package import is_package_installed, get_package_version
    from scripts.utils import print_with_color
except ImportError as e:
    print(f"Error importing helper modules or scripts.utils: {e}")
    print("Please ensure apk_info.py, install_apk.py, check_package.py, and the 'scripts' package (with utils.py) are accessible.")
    sys.exit(1)

def main_workflow(apk_file_path, 
                  task_description, 
                  root_dir_for_agent=".", 
                  agent_model_choice=None, # New parameter
                  agent_api_key=None,      # New parameter
                  max_install_retries=2, 
                  install_wait_time=5):
    """
    Manages the workflow:
    1. Gets APK info (package name, app name).
    2. Installs the APK on the device.
    3. Verifies installation.
    4. Passes info (including optional model/key) to the agent and runs it.
    """
    print_with_color("--- Starting APK Processing, Installation, and Agent Workflow ---", "blue")

    # --- Step 1: Get APK Info ---
    if not os.path.exists(apk_file_path):
        print_with_color(f"Error: APK file not found at '{apk_file_path}'", "red")
        return

    print_with_color(f"\n[INFO] Getting information for APK: {apk_file_path}", "yellow")
    package_name = None
    app_name_from_apk = None
    try:
        package_name, app_name_from_apk = get_apk_info(apk_file_path)
        if not package_name or not app_name_from_apk:
            print_with_color("[ERROR] Failed to retrieve valid package name or app name from APK.", "red")
            return
        print_with_color(f"[SUCCESS] APK Info Retrieved:", "green")
        print_with_color(f"  App Name (from APK): {app_name_from_apk}", "green")
        print_with_color(f"  Package Name: {package_name}", "green")
    except Exception as e:
        print_with_color(f"[ERROR] Could not get APK info: {e}", "red")
        return

    # --- Step 2: Install APK and Verify ---
    print_with_color(f"\n[INFO] Attempting to install '{app_name_from_apk}' ({package_name})...", "yellow")
    installed_successfully = False
    for attempt in range(max_install_retries):
        print_with_color(f"  Installation attempt {attempt + 1}/{max_install_retries}...", "cyan")
        if install_apk(apk_file_path): 
            print_with_color(f"  Waiting {install_wait_time} seconds for installation to settle...", "cyan")
            time.sleep(install_wait_time)
            if is_package_installed(package_name):
                installed_version = get_package_version(package_name)
                version_str = f" (Version: {installed_version})" if installed_version else ""
                print_with_color(f"[SUCCESS] '{app_name_from_apk}'{version_str} is installed and verified.", "green")
                installed_successfully = True
                break
            else:
                print_with_color(f"  [WARNING] Installation reported success by 'install_apk', but package '{package_name}' not found after waiting.", "orange")
        else:
            print_with_color(f"  [INFO] Installation attempt {attempt + 1} failed (as reported by 'install_apk').", "orange")

        if attempt < max_install_retries - 1:
            print_with_color(f"  Retrying in {install_wait_time // 2} seconds...", "cyan")
            time.sleep(install_wait_time // 2)
        else:
            print_with_color(f"[ERROR] Failed to install and verify '{app_name_from_apk}' after {max_install_retries} attempts.", "red")
            return

    if not installed_successfully:
        print_with_color(f"[ERROR] Unknown error: Installation loop completed without success for '{app_name_from_apk}'.", "red")
        return

    # --- Step 3: Run the Agent ---
    print_with_color("\n--- Workflow Step 3: Launching Agent ---", "blue")
    
    agent_app_name_arg = "".join(filter(str.isalnum, app_name_from_apk)) if app_name_from_apk else "UnknownApp"
    if not agent_app_name_arg: agent_app_name_arg = "DefaultApp"

    print_with_color(f"  Agent will use App Name for folders: {agent_app_name_arg}", "cyan")
    print_with_color(f"  Agent will target Package Name: {package_name}", "cyan")
    print_with_color(f"  Agent will use Task Description: {task_description}", "cyan")
    print_with_color(f"  Agent will use Root Directory: {os.path.abspath(root_dir_for_agent)}", "cyan")
    if agent_model_choice:
        print_with_color(f"  Agent will use Model Choice (override): {agent_model_choice}", "cyan")
    if agent_api_key:
        print_with_color(f"  Agent will use API Key (override): {'*' * (len(agent_api_key) - 4) + agent_api_key[-4:] if len(agent_api_key) > 4 else '********'}", "cyan") # Mask key

    try:
        from scripts.self_explorer import main as agent_main

        original_argv = sys.argv
        simulated_argv = [
            "scripts/self_explorer.py", 
            "--app_name", agent_app_name_arg,
            "--package_name", package_name,
            "--description", task_description,
            "--root_dir", os.path.abspath(root_dir_for_agent)
        ]
        
        # Add model choice and API key if provided to workflow_manager
        if agent_model_choice:
            simulated_argv.extend(["--model_choice", agent_model_choice])
        if agent_api_key:
            # Note: --api_key for self_explorer requires --model_choice to also be set (or determined from config/env)
            # The self_explorer.py script handles this validation.
            simulated_argv.extend(["--api_key", agent_api_key])

        sys.argv = simulated_argv
        
        print_with_color(f"\n[INFO] Executing agent with args: {simulated_argv}", "yellow")
        agent_main()

    except ImportError:
        print_with_color("[ERROR] Could not import agent's main function (scripts.self_explorer.main). Agent step skipped.", "red")
    except SystemExit as e:
        if e.code == 0:
            print_with_color("[INFO] Agent exited normally.", "green")
        else:
            print_with_color(f"[WARNING] Agent exited with code {e.code}.", "orange")
    except Exception as e:
        print_with_color(f"[ERROR] Error during agent execution: {e}", "red")
        import traceback
        traceback.print_exc()
    finally:
        if 'original_argv' in locals():
            sys.argv = original_argv

    print_with_color("\n--- Workflow Completed ---", "blue")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install an APK, run the agent, and manage the workflow.")
    parser.add_argument("apk_path", help="Path to the .apk file.")
    parser.add_argument("task_description", help="The task or description for the agent.")
    parser.add_argument("--agent_root_dir", default=".", help="Root directory for the agent's operations. Default: current directory.")
    # New arguments for model and API key to pass to the agent
    parser.add_argument("--agent_model_choice", type=str, default=None, choices=["OpenAI", "Qwen", "Gemini"],
                        help="Override VLM model choice for the agent (OpenAI, Qwen, Gemini).")
    parser.add_argument("--agent_api_key", type=str, default=None,
                        help="Override API key for the agent's chosen VLM. Use with --agent_model_choice.")
    
    parser.add_argument("--retries", type=int, default=2, help="Maximum installation retries.")
    parser.add_argument("--wait", type=int, default=5, help="Wait time in seconds after installation attempt.")

    args_workflow = parser.parse_args()

    if not os.path.isfile(args_workflow.apk_path):
        print_with_color(f"Error: Provided APK path is not a file or does not exist: {args_workflow.apk_path}", "red")
        sys.exit(1)
    if not args_workflow.apk_path.lower().endswith(".apk"):
        print_with_color(f"Error: Provided file does not seem to be an APK (expected .apk extension): {args_workflow.apk_path}", "red")
        sys.exit(1)

    main_workflow(args_workflow.apk_path, 
                  args_workflow.task_description, 
                  args_workflow.agent_root_dir,
                  args_workflow.agent_model_choice, # Pass to main_workflow
                  args_workflow.agent_api_key,      # Pass to main_workflow
                  args_workflow.retries, 
                  args_workflow.wait)