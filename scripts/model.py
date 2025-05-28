import re
import abc
import requests
import dashscope
from dashscope import MultiModalConversation
from http import HTTPStatus
from typing import List
import google.generativeai as genai 
from PIL import Image 
import traceback

from .utils import print_with_color, encode_image # Relative imports

class BaseModel(abc.ABC):
    def __init__(self):
        super().__init__()

    @abc.abstractmethod
    def get_model_response(self, prompt: str, images: List[str]) -> tuple[bool, str]:
        pass

class OpenAIModel(BaseModel):
    def __init__(self, base_url: str, api_key: str, model: str, temperature: float, max_tokens: int):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def get_model_response(self, prompt: str, images: List[str]) -> tuple[bool, str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        content = [{"type": "text", "text": prompt}]
        for img_path in images:
            base64_image = encode_image(img_path)
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        print_with_color("Sending request to OpenAI...", "yellow")
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()  # Raises an exception for HTTP error codes
            res = response.json()
            if "error" not in res:
                # Simple cost calculation (example, update with actual pricing)
                # Assuming gpt-4o pricing: $5/1M input tokens, $15/1M output tokens
                # This is a very rough estimate.
                # usage = res.get("usage", {})
                # prompt_tokens = usage.get("prompt_tokens", 0)
                # completion_tokens = usage.get("completion_tokens", 0)
                # cost = (prompt_tokens / 1000000 * 5) + (completion_tokens / 1000000 * 15)
                # print_with_color(f"OpenAI API call successful. Estimated cost: ${cost:.6f}", "green")
                return True, res["choices"][0]["message"]["content"]
            else:
                print_with_color(f"OpenAI API Error: {res['error']['message']}", "red")
                return False, res["error"]["message"]
        except requests.exceptions.RequestException as e:
            print_with_color(f"Request to OpenAI API failed: {e}", "red")
            return False, str(e)
        except Exception as e:
            print_with_color(f"An unexpected error occurred: {e}", "red")
            return False, str(e)

class QwenModel(BaseModel):
    def __init__(self, api_key: str, model: str):
        super().__init__()
        dashscope.api_key = api_key
        self.model = model

    def get_model_response(self, prompt: str, images: List[str]) -> tuple[bool, str]:
        content = [{'text': prompt}]
        for img_path in images:
            # DashScope SDK can handle local file paths for images
            content.append({"image": f"file://{img_path}"})
        
        messages = [{
            'role': 'user', 
            'content': content
        }]
        
        print_with_color("Sending request to Qwen (DashScope)...", "yellow")
        try:
            response = MultiModalConversation.call(model=self.model, messages=messages)
            if response.status_code == HTTPStatus.OK:
                # print_with_color("Qwen API call successful.", "green")
                return True, response.output.choices[0].message.content
            else:
                err_msg = f"Qwen API Error: Code: {response.code}, Message: {response.message}"
                print_with_color(err_msg, "red")
                return False, err_msg
        except Exception as e:
            print_with_color(f"An unexpected error occurred with Qwen API: {e}", "red")
            return False, str(e)

# Added GeminiModel class
class GeminiModel(BaseModel):
    def __init__(self, api_key: str, model_name: str):
        super().__init__()
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        # Assuming model_name is something like 'gemini-pro-vision' or 'gemini-1.5-pro-latest'

    def get_model_response(self, prompt: str, image_paths: List[str]) -> tuple[bool, str]:
        print_with_color(f"Sending request to Gemini ({self.model.model_name})...", "yellow")
        try:
            model_input = [prompt] # Start with the text prompt
            for img_path in image_paths:
                try:
                    img = Image.open(img_path)
                    model_input.append(img) # Append PIL Image object
                except FileNotFoundError:
                    print_with_color(f"Image file not found: {img_path}", "red")
                    return False, f"Image file not found: {img_path}"
                except Exception as e:
                    print_with_color(f"Error loading image {img_path}: {e}", "red")
                    return False, f"Error loading image {img_path}: {e}"
            
            # Generate content
            # For gemini-pro-vision, this is direct. For newer models like 1.5 Pro, 
            # you might use generate_content with a specific schema if needed for complex prompting.
            response = self.model.generate_content(model_input)
            
            # Ensure response.text is accessed correctly
            if hasattr(response, 'text') and response.text:
                # print_with_color("Gemini API call successful.", "green")
                return True, response.text
            elif hasattr(response, 'parts') and response.parts:
                 # If the response is structured with parts, concatenate text parts.
                text_parts = [part.text for part in response.parts if hasattr(part, 'text')]
                if text_parts:
                    # print_with_color("Gemini API call successful (from parts).", "green")
                    return True, " ".join(text_parts)
                else:
                    print_with_color("Gemini API Error: No text content found in response parts.", "red")
                    return False, "Gemini API Error: No text content found in response parts."
            else:
                # Check for prompt feedback or finish reason if no direct text
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    err_msg = f"Gemini API Error: Blocked - {response.prompt_feedback.block_reason}"
                    print_with_color(err_msg, "red")
                    return False, err_msg
                print_with_color("Gemini API Error: Response format not recognized or empty text.", "red")
                return False, "Gemini API Error: Response format not recognized or empty text."

        except Exception as e:
            # Catching general exceptions from the Gemini API call
            # Specific exceptions like google.api_core.exceptions.GoogleAPIError can also be caught
            error_message = f"An unexpected error occurred with Gemini API: {e}"
            # Try to get more detailed error if available (e.g. from response object if partially formed)
            if hasattr(e, 'message'): # Some Google API errors have a message attribute
                error_message = f"An unexpected error occurred with Gemini API: {e.message}"
            print_with_color(error_message, "red")
            return False, error_message

def parse_explore_rsp(rsp):
    try:
        obs_match = re.search(r"Observation:\s*(.*?)\s*Thought:", rsp, re.DOTALL | re.MULTILINE)
        thought_match = re.search(r"Thought:\s*(.*?)\s*Action:", rsp, re.DOTALL | re.MULTILINE)
        act_match = re.search(r"Action:\s*(.*?)\s*Summary:", rsp, re.DOTALL | re.MULTILINE)
        summary_match = re.search(r"Summary:\s*(.*)", rsp, re.DOTALL | re.MULTILINE)

        act_text_for_error = "ERROR: Action not found in initial full match" # For error reporting

        if not (obs_match and thought_match and act_match and summary_match):
            print_with_color("Full response pattern not matched, attempting partial extraction.", "yellow")
            obs_p = re.search(r"Observation:\s*(.*?)(?:\nThought:|$)", rsp, re.DOTALL | re.MULTILINE)
            thought_p = re.search(r"Thought:\s*(.*?)(?:\nAction:|$)", rsp, re.DOTALL | re.MULTILINE)
            act_p = re.search(r"Action:\s*(.*?)(?:\nSummary:|$)", rsp, re.DOTALL | re.MULTILINE)
            summary_p = re.search(r"Summary:\s*(.*)", rsp, re.DOTALL | re.MULTILINE)
            
            obs_text = obs_p.group(1).strip() if obs_p else "ERROR: Observation not found"
            thought_text = thought_p.group(1).strip() if thought_p else "ERROR: Thought not found"
            act_text = act_p.group(1).strip() if act_p else "ERROR: Action not found"
            summary_text = summary_p.group(1).strip() if summary_p else "ERROR: Summary not found"
            act_text_for_error = act_text # Update for error reporting
            
            if "ERROR:" in obs_text or "ERROR:" in thought_text or "ERROR:" in act_text or "ERROR:" in summary_text:
                error_details = f"Obs: '{obs_text}', Thought: '{thought_text}', Act: '{act_text}', Sum: '{summary_text}'"
                print_with_color(f"Failed to parse essential parts of VLM response. Details: {error_details} RSP: {rsp}", "red")
                return ["ERROR"]
        else:
            obs_text = obs_match.group(1).strip()
            thought_text = thought_match.group(1).strip()
            act_text = act_match.group(1).strip()
            summary_text = summary_match.group(1).strip()
            act_text_for_error = act_text # Update for error reporting

        # Clean act_text: remove backticks and leading/trailing spaces
        act_text_cleaned = act_text.strip("` ")

        print_with_color(f"Observation: {obs_text}", "green")
        print_with_color(f"Thought: {thought_text}", "green")
        print_with_color(f"Action (Raw): {act_text}", "magenta") # Log raw action
        print_with_color(f"Action (Cleaned): {act_text_cleaned}", "green")
        print_with_color(f"Summary: {summary_text}", "green")
        last_act = summary_text

        # Handle simple actions first (no parentheses or parameters)
        simple_action_match = re.match(r"(\w+)\s*(?:\(\s*\))?$", act_text_cleaned)
        parsed_simple_action_name = ""
        if simple_action_match:
            parsed_simple_action_name = simple_action_match.group(1).upper()

        if parsed_simple_action_name == "FINISH": return ["FINISH"]
        if parsed_simple_action_name == "PRESS_BACK": return ["press_back", last_act]
        if parsed_simple_action_name == "PRESS_HOME": return ["press_home", last_act]
        if parsed_simple_action_name == "PRESS_ENTER": return ["press_enter", last_act]
        if parsed_simple_action_name == "PRESS_DELETE": return ["press_delete", last_act]
        if parsed_simple_action_name == "OPEN_NOTIFICATIONS": return ["open_notifications", last_act]
        if parsed_simple_action_name == "PRESS_APP_SWITCH": return ["press_app_switch", last_act]
        if parsed_simple_action_name == "GRID": return ["grid"] 
        if parsed_simple_action_name == "EXIT_GRID": return ["exit_grid", last_act] # Added from task_template_grid


        # Parse actions with parameters: func_name(params)
        match = re.match(r"(\w+)\s*\((.*)\)", act_text_cleaned)
        if not match:
            print_with_color(f"Unknown action format (after checking simple actions): {act_text_cleaned}", "red")
            return ["ERROR"]

        act_name = match.group(1).lower()
        params_str = match.group(2).strip()

        if act_name == "tap" or act_name == "long_press":
            num_match = re.search(r'(\d+)', params_str) # Find the first sequence of digits
            if num_match:
                try:
                    area = int(num_match.group(1))
                    return [act_name, area, last_act]
                except ValueError: # Should not happen if \d+ matches
                    print_with_color(f"Invalid number in parameter for {act_name} after regex match: {params_str}", "red")
                    return ["ERROR"]
            else:
                print_with_color(f"Could not find numeric parameter for {act_name} in '{params_str}'", "red")
                return ["ERROR"]
        
        elif act_name == "type_global":
            # Parameters for type_global are just the string, quotes are optional in prompt example
            # Remove quotes if VLM adds them around the string parameter itself
            input_str = params_str
            if ((params_str.startswith("'") and params_str.endswith("'")) or \
                (params_str.startswith('"') and params_str.endswith('"'))):
                input_str = params_str[1:-1]
            return [act_name, input_str, last_act]
        
        elif act_name == "swipe_element": 
            try:
                parts = [p.strip(" '\"") for p in params_str.split(",")]
                if len(parts) == 3:
                    # First part is element, extract number
                    num_match_se = re.search(r'(\d+)', parts[0])
                    if not num_match_se:
                        print_with_color(f"Could not find element number for swipe_element in '{parts[0]}'", "red"); return ["ERROR"]
                    area = int(num_match_se.group(1))
                    
                    direction = parts[1].lower()
                    distance = parts[2].lower() 
                    if direction not in ["up", "down", "left", "right"] or \
                       distance not in ["short", "medium", "long"]:
                        print_with_color(f"Invalid direction/distance for swipe_element: '{direction}', '{distance}'", "red"); return ["ERROR"]
                    return [act_name, area, direction, distance, last_act]
                else:
                    print_with_color(f"Invalid parameters for swipe_element (expected 3 parts): {params_str}", "red"); return ["ERROR"]
            except (ValueError, IndexError) as e_swipe: # Catch parsing errors
                print_with_color(f"Error parsing swipe_element parameters ('{params_str}'): {e_swipe}", "red"); return ["ERROR"]
        
        elif act_name == "swipe_screen":
            try:
                parts = [p.strip(" '\"") for p in params_str.split(",")]
                if len(parts) == 2:
                    direction = parts[0].lower()
                    distance = parts[1].lower()
                    if direction not in ["up", "down", "left", "right"] or \
                       distance not in ["short", "medium", "long"]:
                        print_with_color(f"Invalid direction/distance for swipe_screen: '{direction}', '{distance}'", "red"); return ["ERROR"]
                    return [act_name, direction, distance, last_act]
                else:
                    print_with_color(f"Invalid parameters for swipe_screen (expected 2 parts): {params_str}", "red"); return ["ERROR"]
            except (ValueError, IndexError) as e_swipe_screen: # Catch parsing errors
                 print_with_color(f"Error parsing swipe_screen parameters ('{params_str}'): {e_swipe_screen}", "red"); return ["ERROR"]
        
        # For grid actions (if they are ever output by the main prompt, though unlikely)
        elif act_name == "tap" and "," in params_str: # Distinguish grid tap from element tap
            try:
                parts = [p.strip(" '\"") for p in params_str.split(",")]
                if len(parts) == 2:
                    area_grid = int(parts[0]) # Assuming first is number
                    subarea_grid = parts[1].lower()
                    # Add validation for subarea_grid if needed
                    return ["tap_grid", area_grid, subarea_grid, last_act] # Use a distinct action name
            except (ValueError, IndexError): pass # Fall through if not grid tap format
            # If it falls through, it will be caught by the final "Unknown action name"

        else:
            print_with_color(f"Unknown action name or parameter format: {act_name} with params '{params_str}' (from raw: '{act_text_for_error}')", "red")
            return ["ERROR"]

    except Exception as e:
        print_with_color(f"Critical error parsing VLM response: {e}. RSP: {rsp}", "red")
        traceback.print_exc()
        return ["ERROR"]

def parse_reflect_rsp(rsp):
    # ... (existing parse_reflect_rsp - keep as is for now) ...
    try:
        decision_text = "ERROR: Decision not found"
        thought_text = "ERROR: Thought not found"
        doc_text = "N/A" # Default for documentation, as it might be optional or not applicable

        decision_match = re.search(r"Decision:\s*(.*?)(?:\nThought:|\nDocumentation:|$)", rsp, re.DOTALL | re.MULTILINE | re.IGNORECASE)
        if decision_match:
            decision_text = decision_match.group(1).strip()

        thought_match = re.search(r"Thought:\s*(.*?)(?:\nDocumentation:|$)", rsp, re.DOTALL | re.MULTILINE | re.IGNORECASE)
        if thought_match:
            thought_text = thought_match.group(1).strip()
        
        doc_match = re.search(r"Documentation:\s*(.*)", rsp, re.DOTALL | re.MULTILINE | re.IGNORECASE)
        if doc_match:
            doc_text = doc_match.group(1).strip()
        
        if decision_text.startswith("ERROR:") or thought_text.startswith("ERROR:"):
            error_details = f"Parsed Decision: '{decision_text}', Parsed Thought: '{thought_text}', Parsed Doc: '{doc_text}'"
            print_with_color(f"Failed to parse essential parts of VLM reflection. Details: {error_details}. RSP: {rsp}", "red")
            return ["ERROR"]

        print_with_color(f"Decision: {decision_text}", "green")
        print_with_color(f"Thought: {thought_text}", "green")
        print_with_color(f"Documentation: {doc_text}", "green")
        
        decision_upper = decision_text.upper()
        valid_decisions = ["BACK", "CONTINUE", "SUCCESS", "INEFFECTIVE"]
        if decision_upper in valid_decisions:
            return [decision_upper, thought_text, doc_text]
        else:
            print_with_color(f"Unknown or malformed decision: '{decision_text}' (parsed as '{decision_upper}')", "red")
            return ["ERROR"]
            
    except Exception as e:
        print_with_color(f"Critical error in parse_reflect_rsp: {e}, RSP: {rsp}", "red")
        traceback.print_exc()
        return ["ERROR"]