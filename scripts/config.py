import os
import yaml

def load_config(config_path="./config.yaml"):
    yaml_configs = {}
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                yaml_configs = yaml.safe_load(f)
                if yaml_configs is None: # Handle empty YAML file
                    yaml_configs = {}
        except Exception as e:
            print(f"Warning: Could not load or parse {config_path}: {e}. Proceeding without it.")
            yaml_configs = {} # Ensure it's a dict
    else:
        print(f"Info: Configuration file {config_path} not found. Relying on environment variables and CLI args.")

    env_configs = dict(os.environ)

    final_configs = yaml_configs.copy() # Start with YAML content
    final_configs.update(env_configs)   # Environment variables overwrite/add

    return final_configs