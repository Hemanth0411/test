import argparse
import ast
import datetime
import json
import os
import re
import sys
import time
import warnings 
import shutil 
import traceback 

warnings.filterwarnings("ignore")

from . import prompts
from .config import load_config
from .and_controller import list_all_devices, AndroidController, traverse_tree
from .model import parse_explore_rsp, parse_reflect_rsp, OpenAIModel, QwenModel, GeminiModel
from .utils import draw_bbox_multi, print_with_color

# configs = load_config() # Moved inside main() after CLI parsing for overrides

def main():
    parser = argparse.ArgumentParser(description="AI-powered Android App Exploration Agent.")
    
    # Required arguments
    parser.add_argument("--app_name", type=str, required=True, 
                        help="Name of the target application. Used for directory naming (e.g., ./apps/<app_name>/).")
    parser.add_argument("--package_name", type=str, required=True,
                        help="Android package name of the target application (e.g., com.example.app).")
    parser.add_argument("--description", type=str, required=True,
                        help="Description of the task to accomplish or a directive for general exploration.")

    # Optional arguments for Docker/Flexibility
    parser.add_argument("--model_choice", type=str, choices=["OpenAI", "Qwen", "Gemini"], default=None,
                        help="Override VLM choice (OpenAI, Qwen, Gemini). Defaults to config/env var.")
    parser.add_argument("--api_key", type=str, default=None,
                        help="API key for the chosen VLM. Overrides config/env var. Use with --model_choice.")
    
    parser.add_argument("--root_dir", default=".",
                        help="Root directory for agent operations (e.g., where 'apps' folder will be).")

    args = parser.parse_args()

    # --- Configuration Loading & VLM Initialization ---
    configs = load_config() 

    if args.model_choice:
        print_with_color(f"CLI Override: Model choice set to '{args.model_choice}'.", "yellow")
        configs["MODEL"] = args.model_choice

    final_model_choice = configs.get("MODEL")

    if args.api_key:
        if not final_model_choice:
            print_with_color("Error: --api_key provided without a VLM model being specified (via --model_choice, env, or config.yaml).", "red")
            sys.exit(1)
        
        print_with_color(f"CLI Override: API key provided for model '{final_model_choice}'.", "yellow")
        if final_model_choice == "OpenAI":
            configs["OPENAI_API_KEY"] = args.api_key
        elif final_model_choice == "Qwen":
            configs["DASHSCOPE_API_KEY"] = args.api_key
        elif final_model_choice == "Gemini":
            configs["GEMINI_API_KEY"] = args.api_key
        else:
            print_with_color(f"Warning: API key provided via CLI, but the model '{final_model_choice}' is unknown. Key not assigned.", "orange")

    if not final_model_choice:
        print_with_color("Error: VLM Model (MODEL) not specified in config, environment variables, or via --model_choice.", "red")
        sys.exit(1)

    api_key_to_check = None
    if final_model_choice == "OpenAI":
        api_key_to_check = configs.get("OPENAI_API_KEY")
    elif final_model_choice == "Qwen":
        api_key_to_check = configs.get("DASHSCOPE_API_KEY")
    elif final_model_choice == "Gemini":
        api_key_to_check = configs.get("GEMINI_API_KEY")
    else:
        print_with_color(f"Unsupported model: {final_model_choice}. Cannot validate API key.", "red")
        sys.exit(1)

    if not api_key_to_check:
        print_with_color(f"Error: API key for the selected model '{final_model_choice}' is missing or empty.", "red")
        print_with_color("Please set it via --api_key, environment variable, or in config.yaml.", "red")
        sys.exit(1)
    
    model_name = final_model_choice
    mllm = None
    if model_name == "OpenAI":
        mllm = OpenAIModel(base_url=configs.get("OPENAI_API_BASE"),
                             api_key=configs["OPENAI_API_KEY"], 
                             model=configs.get("OPENAI_API_MODEL"),
                             temperature=float(configs.get("TEMPERATURE", 0.0)),
                             max_tokens=int(configs.get("MAX_TOKENS", 1024)))
    elif model_name == "Qwen":
        mllm = QwenModel(api_key=configs["DASHSCOPE_API_KEY"], 
                           model=configs.get("QWEN_MODEL"))
    elif model_name == "Gemini": 
        mllm = GeminiModel(api_key=configs["GEMINI_API_KEY"], 
                           model_name=configs.get("GEMINI_MODEL_NAME"))
    else:
        print_with_color(f"Unsupported model after validation: {model_name}. This should not happen.", "red")
        sys.exit(1)

    # --- Directory Setup ---
    work_dir = os.path.join(args.root_dir, "apps")
    app_dir = os.path.join(work_dir, args.app_name)

    demo_timestamp = int(time.time())
    demo_name = datetime.datetime.fromtimestamp(demo_timestamp).strftime("self_explore_%Y-%m-%d_%H-%M-%S")
    task_dir = os.path.join(app_dir, "demos", demo_name)
    screenshot_dir = os.path.join(task_dir, "screenshots")
    xml_dir = os.path.join(task_dir, "xmls")
    log_dir = os.path.join(task_dir, "logs")
    docs_dir = os.path.join(app_dir, "auto_docs") 

    os.makedirs(screenshot_dir, exist_ok=True)
    os.makedirs(xml_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)

    log_explore_path = os.path.join(log_dir, "explore_log.txt")
    log_reflect_path = os.path.join(log_dir, "reflect_log.txt")

    # --- Device Connection ---
    device_list = list_all_devices()
    if not device_list:
        print_with_color("No device found. Please connect your Android device and enable USB debugging.", "red")
        sys.exit(1)
    device = ""
    if len(device_list) == 1:
        device = device_list[0]
        print_with_color(f"Device connected: {device}", "green")
    else:
        print_with_color("Multiple devices found. Please select one:", "blue")
        for i, dev in enumerate(device_list):
            print_with_color(f"{i + 1}. {dev}", "blue")
        while True:
            try:
                choice = int(input("Enter the number of the device: "))
                if 1 <= choice <= len(device_list):
                    device = device_list[choice - 1]
                    break
                else:
                    print_with_color("Invalid choice.", "red")
            except ValueError:
                print_with_color("Invalid input. Please enter a number.", "red")
    
    controller = AndroidController(device)

    # --- Launch Application ---
    print_with_color(f"Launching application: {args.package_name}", "blue")
    if not controller.launch_app(args.package_name):
        print_with_color(f"Failed to launch application {args.package_name}. Please check the package name and device connectivity.", "red")
        sys.exit(1) 
    
    app_load_delay_str = configs.get("APP_LOAD_DELAY_SECONDS", "5") # Get as string first
    app_load_delay = 5 # Default
    try:
        app_load_delay = int(app_load_delay_str)
    except ValueError:
        print_with_color(f"Warning: Invalid APP_LOAD_DELAY_SECONDS value '{app_load_delay_str}'. Defaulting to 5 seconds.", "yellow")
        
    print_with_color(f"Waiting {app_load_delay} seconds for app to load...", "cyan")
    time.sleep(app_load_delay)

    if controller.width == 0 or controller.height == 0:
        print_with_color("Critical: Device screen resolution is 0x0 after controller initialization and app launch attempt. Agent cannot proceed.", "red")
        sys.exit(1)
    else:
        print_with_color(f"Screen size reported by controller: {controller.width}x{controller.height}", "green")

    # --- Determine Agent Behavior Mode ---
    agent_mode = "task" 
    classification_prompt_text = prompts.description_classification_template.replace("<description_text>", args.description)
    print_with_color("Classifying user description to determine agent mode (TASK or EXPLORE)...", "blue")
    status_classify, rsp_classify = mllm.get_model_response(classification_prompt_text, [])
    
    if not status_classify:
        print_with_color(f"VLM call for description classification failed: {rsp_classify}. Defaulting to 'task' mode.", "red")
    else:
        cleaned_response = rsp_classify.strip().upper()
        if cleaned_response == "TASK":
            agent_mode = "task"
        elif cleaned_response == "EXPLORE":
            agent_mode = "explore"
        else:
            print_with_color(f"Unexpected response from VLM for description classification: '{rsp_classify}'. Defaulting to 'task' mode.", "yellow")
            with open(log_explore_path, "a", encoding="utf-8") as f_log:
                f_log.write(f"Description Classification Attempt:\nPrompt: {classification_prompt_text}\nRaw VLM Response: {rsp_classify}\nCleaned Response: {cleaned_response}\nOutcome: Defaulted to 'task' mode.\n-----------------------------\n")
    print_with_color(f"Agent mode set to: {agent_mode.upper()}", "green")

    manual_stop_requested = False
    task_desc_for_prompt = args.description # Primary input from user

    try:
        round_count = 0
        last_act = "None"
        useless_list = [] 
        doc_count = 0
        task_complete = False

        max_rounds_config = configs.get("MAX_ROUNDS", "20")
        max_rounds_for_loop = 20
        try:
            max_rounds_for_loop = int(max_rounds_config)
        except ValueError:
             print_with_color(f"Warning: Invalid MAX_ROUNDS value '{max_rounds_config}'. Defaulting to 20 rounds.", "yellow")


        if agent_mode == "explore":
            max_rounds_config = configs.get("MAX_EXPLORE_ROUNDS", "50") # Default to 50 for explore
            try:
                max_rounds_for_loop = int(max_rounds_config)
                if max_rounds_for_loop <= 0: # Ensure positive
                    print_with_color(f"Warning: MAX_EXPLORE_ROUNDS ('{max_rounds_config}') must be positive. Defaulting to 50.", "yellow")
                    max_rounds_for_loop = 50
            except ValueError:
                print_with_color(f"Warning: Invalid MAX_EXPLORE_ROUNDS value '{max_rounds_config}'. Defaulting to 50 rounds.", "yellow")
                max_rounds_for_loop = 50
            print_with_color(f"EXPLORE MODE: Agent will run for MAX_EXPLORE_ROUNDS ({max_rounds_for_loop}) or until manually stopped.", "magenta")
        else: # agent_mode == "task"
            max_rounds_config = configs.get("MAX_ROUNDS", "20") # Default to 20 for task
            try:
                max_rounds_for_loop = int(max_rounds_config)
                if max_rounds_for_loop <= 0: # Ensure positive
                    print_with_color(f"Warning: MAX_ROUNDS ('{max_rounds_config}') must be positive. Defaulting to 20.", "yellow")
                    max_rounds_for_loop = 20
            except ValueError:
                print_with_color(f"Warning: Invalid MAX_ROUNDS value '{max_rounds_config}'. Defaulting to 20 rounds.", "yellow")
                max_rounds_for_loop = 20
        print_with_color(f"TASK MODE: Agent will run for MAX_ROUNDS ({max_rounds_for_loop}) or until task is marked FINISH.", "magenta")

        while round_count < max_rounds_for_loop:
            if manual_stop_requested:
                print_with_color("Manual stop acknowledged. Exiting main loop.", "yellow")
                break
            round_count += 1
            print_with_color(f"Round {round_count} ({agent_mode.upper()} MODE)", "yellow")
            
            screenshot_before = controller.get_screenshot(f"{round_count}_before", screenshot_dir)
            xml_path = controller.get_xml(f"{round_count}", xml_dir)
            if screenshot_before == "ERROR" or xml_path == "ERROR":
                print_with_color("Failed to get screenshot or XML. Ending current round.", "red")
                time.sleep(configs.get("REQUEST_INTERVAL", 3)) 
                if round_count >= max_rounds_for_loop : 
                     print_with_color("Failed to get screenshot/XML on last round. Exiting loop.", "red")
                     break
                continue 

            clickable_list = []
            focusable_list = []
            traverse_tree(xml_path, clickable_list, "clickable")
            traverse_tree(xml_path, focusable_list, "focusable")
            elem_list = [e for e in clickable_list + focusable_list if e.uid not in useless_list]
            screenshot_before_labeled_path = os.path.join(screenshot_dir, f"{round_count}_before_labeled.png")
            draw_bbox_multi(screenshot_before, screenshot_before_labeled_path, elem_list, dark_mode=str(configs.get("DARK_MODE", "false")).lower() == 'true')


            ui_documentation_str = ""
            for idx, elem_obj in enumerate(elem_list):
                doc_file_name = f"{elem_obj.uid.replace('/', '_').replace(':', '.')}.txt"
                doc_file_path = os.path.join(docs_dir, doc_file_name)
                if os.path.exists(doc_file_path):
                    try:
                        with open(doc_file_path, "r", encoding="utf-8") as f_doc:
                            doc_content = f_doc.read().strip()
                            ui_documentation_str += f"Element {idx + 1} (UID: {elem_obj.uid}): {doc_content}\n"
                    except Exception as e:
                        print_with_color(f"Error reading doc file {doc_file_path}: {e}", "red")
            if not ui_documentation_str:
                ui_documentation_str = "No documentation available for elements on this screen."

            prompt_to_vlm = ""
            if agent_mode == "explore":
                prompt_to_vlm = prompts.app_explore_template \
                                         .replace("<ui_document>", ui_documentation_str) \
                                         .replace("<last_act>", last_act) \
                                         .replace("<exploration_directive>", task_desc_for_prompt)
            else: # agent_mode == "task"
                prompt_to_vlm = prompts.task_template \
                                         .replace("<task_description>", task_desc_for_prompt) \
                                         .replace("<last_act>", last_act) \
                                         .replace("<ui_document>", ui_documentation_str)
            
            status, rsp = mllm.get_model_response(prompt_to_vlm, [screenshot_before_labeled_path])
            with open(log_explore_path, "a", encoding="utf-8") as f_log:
                f_log.write(f"Round {round_count} ({agent_mode.upper()} Mode) Explore Phase:\nPrompt: {prompt_to_vlm}\nResponse: {rsp}\n-----------------------------\n")
            
            if not status:
                print_with_color(f"VLM call failed: {rsp}. Ending current round.", "red")
                last_act = f"VLM call failed: {rsp}"
                time.sleep(configs.get("REQUEST_INTERVAL", 3))
                if round_count >= max_rounds_for_loop : break
                continue

            action_res = parse_explore_rsp(rsp)
            if not action_res or action_res[0] == "ERROR":
                print_with_color("Failed to parse VLM response for action. Ending current round.", "red")
                last_act = "Error in parsing VLM response."
                time.sleep(configs.get("REQUEST_INTERVAL", 3))
                if round_count >= max_rounds_for_loop : break
                continue
            
            act_name = action_res[0]
            if len(action_res) > 1 and act_name not in ["FINISH", "grid"]: 
                last_act = action_res[-1] 
            elif act_name == "FINISH":
                if agent_mode == "task":
                    last_act = "Task finished by agent."
                    task_complete = True
                else: 
                    last_act = "VLM unexpectedly chose FINISH in EXPLORE mode. Continuing exploration."
                    print_with_color("VLM chose FINISH in EXPLORE mode. This is unexpected. Agent will continue if rounds permit.", "yellow")
            elif act_name == "grid":
                last_act = "Switched to grid mode."
            else:
                last_act = f"Executed {act_name}"

            if agent_mode == "task" and act_name == "FINISH":
                print_with_color("Task marked as FINISH by VLM in TASK mode.", "green")
                break
            
            interacted_element_uid = ""
            elem_idx = -1 

            request_interval_str = configs.get("REQUEST_INTERVAL", "3")
            try:
                current_request_interval = int(request_interval_str)
            except ValueError:
                current_request_interval = 3


            if act_name == "tap":
                elem_idx = action_res[1]
                if 1 <= elem_idx <= len(elem_list):
                    x, y = (elem_list[elem_idx-1].bbox[0][0] + elem_list[elem_idx-1].bbox[1][0]) // 2, \
                           (elem_list[elem_idx-1].bbox[0][1] + elem_list[elem_idx-1].bbox[1][1]) // 2
                    controller.tap(x, y)
                    interacted_element_uid = elem_list[elem_idx-1].uid
                else:
                    print_with_color(f"Invalid element index for tap: {elem_idx}", "red")
                    last_act += " (Invalid tap index)"; time.sleep(current_request_interval); 
                    if round_count >= max_rounds_for_loop : break
                    continue
            
            elif act_name == "type_global":
                controller.text(action_res[1]) 
            
            elif act_name == "long_press":
                elem_idx = action_res[1]
                if 1 <= elem_idx <= len(elem_list):
                    x, y = (elem_list[elem_idx-1].bbox[0][0] + elem_list[elem_idx-1].bbox[1][0]) // 2, \
                           (elem_list[elem_idx-1].bbox[0][1] + elem_list[elem_idx-1].bbox[1][1]) // 2
                    controller.long_press(x,y)
                    interacted_element_uid = elem_list[elem_idx-1].uid
                else:
                    print_with_color(f"Invalid element index for long_press: {elem_idx}", "red")
                    last_act += " (Invalid long_press index)"; time.sleep(current_request_interval); 
                    if round_count >= max_rounds_for_loop : break
                    continue
            
            elif act_name == "swipe_element": 
                elem_idx, direction, distance = action_res[1], action_res[2], action_res[3]
                if 1 <= elem_idx <= len(elem_list):
                    x, y = (elem_list[elem_idx-1].bbox[0][0] + elem_list[elem_idx-1].bbox[1][0]) // 2, \
                           (elem_list[elem_idx-1].bbox[0][1] + elem_list[elem_idx-1].bbox[1][1]) // 2
                    controller.swipe_element(x, y, direction, distance) 
                    interacted_element_uid = elem_list[elem_idx-1].uid
                else:
                    print_with_color(f"Invalid element index for swipe_element: {elem_idx}", "red")
                    last_act += " (Invalid swipe_element index)"; time.sleep(current_request_interval); 
                    if round_count >= max_rounds_for_loop : break
                    continue
            
            elif act_name == "swipe_screen":
                direction, distance_str = action_res[1], action_res[2]
                dist_map = {"short": 0.25, "medium": 0.5, "long": 0.75}
                distance_factor = dist_map.get(distance_str.lower(), 0.5) 
                controller.swipe_screen_direction(direction, distance_factor)
            
            elif act_name == "delete_multiple":
                try:
                    count = int(action_res[1])
                    controller.delete_multiple(count)
                except (IndexError, ValueError):
                    print_with_color(f"Invalid parameter for delete_multiple: {action_res}", "red")

            elif act_name == "press_home": controller.press_home()
            elif act_name == "press_enter": controller.press_enter()
            elif act_name == "press_delete": controller.press_delete()
            elif act_name == "open_notifications": controller.open_notifications()
            elif act_name == "press_app_switch": controller.press_app_switch()
            elif act_name == "press_back": controller.back()
            elif act_name == "grid":
                print_with_color("GRID action called. Implement grid mode logic if needed.", "magenta")
            else:
                print_with_color(f"Unknown action to execute: {act_name}", "red")
                last_act += f" (Unknown action: {act_name})"
                time.sleep(current_request_interval); 
                if round_count >= max_rounds_for_loop : break
                continue

            time.sleep(current_request_interval) 

            element_details_for_reflection = "N/A"
            if elem_idx != -1 and interacted_element_uid: 
                element_details_for_reflection = f"Element {elem_idx} (UID: {interacted_element_uid})"
            elif act_name == "type_global":
                element_details_for_reflection = "Text input via type_global"
            else: 
                element_details_for_reflection = f"Global action ({act_name})"

            if act_name not in ["grid"]:
                screenshot_after = controller.get_screenshot(f"{round_count}_after", screenshot_dir)
                if screenshot_after == "ERROR":
                    print_with_color("Failed to get screenshot after action. Skipping reflection.", "red")
                else:
                    xml_after_path = controller.get_xml(f"{round_count}_after_xml", xml_dir)
                    elem_list_after = []
                    if xml_after_path != "ERROR":
                        clickable_list_after, focusable_list_after = [], []
                        traverse_tree(xml_after_path, clickable_list_after, "clickable")
                        traverse_tree(xml_after_path, focusable_list_after, "focusable")
                        elem_list_after = clickable_list_after + focusable_list_after
                    
                    screenshot_after_labeled_path = os.path.join(screenshot_dir, f"{round_count}_after_labeled.png")
                    draw_bbox_multi(screenshot_after, screenshot_after_labeled_path, elem_list_after, dark_mode=str(configs.get("DARK_MODE", "false")).lower() == 'true')

                    reflect_prompt = prompts.self_explore_reflect_template \
                                        .replace("<task_desc>", task_desc_for_prompt) \
                                        .replace("<action_type>", act_name) \
                                        .replace("<element_details>", element_details_for_reflection) \
                                        .replace("<last_act_summary>", last_act)
                    
                    status_reflect, rsp_reflect = mllm.get_model_response(reflect_prompt, 
                                                                            [screenshot_before_labeled_path, screenshot_after_labeled_path])
                    with open(log_reflect_path, "a", encoding="utf-8") as f_log:
                        f_log.write(f"Round {round_count} ({agent_mode.upper()} Mode) Reflect Phase:\nPrompt: {reflect_prompt}\nResponse: {rsp_reflect}\n-----------------------------\n")
                    
                    current_reflection_decision = "ERROR" # Default before parsing
                    if not status_reflect:
                        print_with_color(f"VLM call for reflection failed: {rsp_reflect}.", "red")
                    else:
                        reflect_res = parse_reflect_rsp(rsp_reflect)
                        if reflect_res and reflect_res[0] != "ERROR":
                            current_reflection_decision = reflect_res[0]
                            documentation = reflect_res[2] 

                            if current_reflection_decision == "INEFFECTIVE" or current_reflection_decision == "BACK" or current_reflection_decision == "CONTINUE":
                                if interacted_element_uid and interacted_element_uid not in useless_list:
                                    useless_list.append(interacted_element_uid)
                                if current_reflection_decision == "BACK":
                                    controller.back()
                                    time.sleep(current_request_interval) 
                            
                            if documentation and documentation.lower() != "n/a" and current_reflection_decision != "INEFFECTIVE" and interacted_element_uid:
                                doc_path = os.path.join(docs_dir, f"{interacted_element_uid.replace('/', '_').replace(':', '.')}.txt")
                                final_documentation = documentation
                                if os.path.exists(doc_path) and str(configs.get("DOC_REFINE", "false")).lower() == 'true':
                                    try:
                                        with open(doc_path, "r", encoding="utf-8") as f_doc: existing_doc = f_doc.read()
                                        final_documentation = f"{existing_doc}\n---\nRefined ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n{documentation}"
                                        print_with_color(f"Refining documentation for {interacted_element_uid}", "cyan")
                                    except Exception as e:
                                        print_with_color(f"Error reading existing doc for refinement: {e}", "red")
                                try:
                                    with open(doc_path, "w", encoding="utf-8") as f_doc: f_doc.write(final_documentation)
                                    doc_count +=1
                                    print_with_color(f"Documentation generated/updated for element {interacted_element_uid}: {final_documentation[:100]}...", "magenta") # Print snippet
                                except Exception as e:
                                    print_with_color(f"Error writing doc file {doc_path}: {e}", "red")
                        else:
                            print_with_color("Failed to parse reflection response.", "red")
            
            # End of round sleep, ensuring it happens unless 'BACK' was just decided and executed by reflection.
            # However, the controller.back() call now includes its own sleep.
            # A simple unconditional sleep here ensures consistent round timing if other paths are taken.
            # The previous logic: `if act_name != "press_back" or decision != "BACK":`
            # might be complex if `decision` is not always set from reflection.
            # Let's ensure a delay unless the BACK action from reflection *just* happened.
            if not (act_name == "press_back" and current_reflection_decision == "BACK"): # Avoid double sleep if reflection did BACK
                 # The general action execution already has a time.sleep(current_request_interval).
                 # Reflection's BACK also has a sleep. So, this might be redundant unless other actions don't have sleeps.
                 # For simplicity, removing this potentially redundant end-of-round sleep, 
                 # relying on sleeps after action execution or after reflection's BACK.
                 pass


        if not manual_stop_requested:
            if agent_mode == "task" and task_complete:
                print_with_color("Task completed successfully!", "green")
            elif agent_mode == "task" and not task_complete:
                print_with_color(f"Max rounds ({max_rounds_for_loop}) reached for TASK. Task may not be complete.", "yellow")
            elif agent_mode == "explore":
                print_with_color(f"Max rounds ({max_rounds_for_loop}) reached for EXPLORATION. Exploration session ended.", "blue")
        
        print_with_color(f"Total documentations generated/updated: {doc_count}", "blue")

    except KeyboardInterrupt:
        print_with_color("\nManual interruption (Ctrl+C) detected. Initiating graceful shutdown...", "orange")
        manual_stop_requested = True
    except Exception as e:
        print_with_color(f"An unexpected error occurred during main operation: {e}", "red")
        traceback.print_exc()
        manual_stop_requested = True 

    finally:
        print_with_color("Executing finally block: Closing app and cleaning up...", "cyan")
        
        if 'controller' in locals() and controller is not None and hasattr(args, 'package_name') and args.package_name:
            print_with_color(f"Attempting to close application: {args.package_name}", "yellow")
            if not controller.close_app(args.package_name):
                print_with_color(f"Could not ensure application {args.package_name} is closed.", "orange")
            else:
                print_with_color(f"Application {args.package_name} close command sent.", "green")
        else:
            if 'controller' not in locals() or controller is None: print_with_color("Controller not initialized, skipping app closure.", "yellow")
            else: print_with_color("Package name not available, skipping app closure.", "yellow")

        print_with_color("Starting selective file cleanup...", "magenta")
        if 'screenshot_dir' in locals() and screenshot_dir and os.path.isdir(screenshot_dir):
            try:
                shutil.rmtree(screenshot_dir)
                print_with_color(f"Successfully removed screenshot directory: {screenshot_dir}", "magenta")
            except Exception as e: print_with_color(f"Error removing screenshot directory {screenshot_dir}: {e}", "red")
        elif 'screenshot_dir' in locals() and screenshot_dir: print_with_color(f"Screenshot directory not found or not a directory, skipping cleanup: {screenshot_dir}", "yellow")
        else: print_with_color("Screenshot directory variable not defined, skipping cleanup.", "yellow")

        if 'xml_dir' in locals() and xml_dir and os.path.isdir(xml_dir):
            try:
                shutil.rmtree(xml_dir)
                print_with_color(f"Successfully removed XML directory: {xml_dir}", "magenta")
            except Exception as e: print_with_color(f"Error removing XML directory {xml_dir}: {e}", "red")
        elif 'xml_dir' in locals() and xml_dir: print_with_color(f"XML directory not found or not a directory, skipping cleanup: {xml_dir}", "yellow")
        else: print_with_color("XML directory variable not defined, skipping cleanup.", "yellow")
            
        if 'log_dir' in locals() and log_dir and os.path.isdir(log_dir): print_with_color(f"Log directory retained: {log_dir}", "green")
        if 'docs_dir' in locals() and docs_dir and os.path.isdir(docs_dir): print_with_color(f"Documentation directory retained: {docs_dir}", "green")

        print_with_color("Agent shutdown process complete.", "blue")
        if 'manual_stop_requested' in locals() and manual_stop_requested:
            current_agent_mode = locals().get('agent_mode', 'unknown')
            current_task_complete_status = locals().get('task_complete', False)
            if current_agent_mode == "task" and not current_task_complete_status: print_with_color("Task was manually interrupted and may not be complete.", "yellow")
            elif current_agent_mode == "explore": print_with_color("Exploration was manually interrupted.", "yellow")
            elif current_agent_mode == "unknown": print_with_color("Operation manually interrupted.", "yellow")

if __name__ == "__main__":
    main()