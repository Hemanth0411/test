# 🤖 NavMind: AI-Powered Android App Exploration & Task Automation Agent

NavMind is an intelligent agent designed to interact with Android applications. It leverages Large Vision Models (VLMs) to understand UI screens, make decisions, and perform actions to either explore an application's features or complete specific user-defined tasks. This project builds upon concepts demonstrated in works like AppAgent.

---

## ✨ Features

### 🌟 Dual Modes of Operation

* **🎮 Task Mode**: Executes a sequence of actions to achieve a specific goal described by the user (e.g., "send an email to X," "search for Y on YouTube and play the first video"). The agent attempts to finish once the task is complete.
* **🔍 Explore Mode**: Autonomously navigates an application to discover its features and functionalities by setting its own sub-goals at each step. Runs for a configured number of rounds or until manually stopped.

### 🧠 VLM Integration & Persona

* Supports multiple VLMs: OpenAI (e.g., GPT-4V), Google Gemini (e.g., Gemini 1.5 Flash/Pro Vision), and Anthropic Qwen (via DashScope).
* Agent persona ("AI-powered Android App Exploration Agent") embedded in prompts for consistent VLM responses.

### 📲 Device Interaction via ADB

* Full control over connected Android devices/emulators using ADB.
* Supports launching/closing apps, screen capture, XML UI dump, taps, long presses, text input, swipes, and system key events (back, home, enter, delete, notifications, app switch).

### 🖼️ Automated UI Analysis

* Parses XML layout dumps to identify interactive UI elements and their properties (resource-ID, content-desc, class, bounds).
* Generates unique IDs and role hints (e.g., search bar, navigation item).
* Labels elements on screenshots with numeric tags for VLM reference.

### 📝 Persistent UI Element Documentation

* Automatically generates textual documentation for UI elements.
* Stores documentation in text files (auto\_docs per app) and reuses it in future runs.

### ⚙️ Flexible Configuration

* Behavior, VLM choice, API keys, and operational parameters configurable via:

  * `config.yaml`
  * Environment variables
  * Command-line arguments (highest precedence)

### ⟳ Reflection and Self-Correction

* Reflects on the effectiveness of each action.
* Detects ineffective actions or dead states and can recover by navigating back.
* Tracks and avoids "useless" elements during the session.

### 🧹 Automatic Cleanup

* Gracefully closes target app on exit.
* Cleans up temporary files but retains logs and documentation.

### 🎨 Enhanced Visuals & Logging

* Colored console logs for better readability.
* Screenshots labeled with numbered tags and customizable styles.

---

## 📁 Project Structure

```
NavMind/
├── scripts/
│   ├── __init__.py
│   ├── self_explorer.py       # Main agent logic
│   ├── and_controller.py      # ADB interaction
│   ├── model.py               # VLM interaction
│   ├── prompts.py             # Prompt templates
│   ├── config.py              # Config loading
│   └── utils.py               # Utilities
├── tools/
│   ├── apk_info.py
│   ├── install_apk.py
│   └── check_package.py
├── config.yaml
└── README.md
```

---

## 🔄 Key Implementation Differences from AppAgent

* **Unified Logic**: `self_explorer.py` handles both task and exploration.
* **Simple Config Hierarchy**: YAML < Environment Variables < CLI
* **Direct VLM Calls**: via SDK/API in `model.py`
* **Text-Based Docs**: Stored as .txt per UI element

---

## 👋 Prerequisites

* Python 3.9+
* Android Debug Bridge (ADB) installed and in PATH
* Connected Android device/emulator with USB Debugging enabled
* Python Packages:

```bash
pip install pyyaml requests Pillow opencv-python numpy colorama \
            google-generativeai dashscope openai
```

---

## ⚙️ Configuration Example (config.yaml)

```yaml
MODEL: "Gemini"  # OpenAI, Gemini, Qwen
GEMINI_API_KEY: "your_gemini_key_here"
GEMINI_MODEL_NAME: "gemini-1.5-flash"
OPENAI_API_KEY: "sk-your_openai_key_here"
OPENAI_API_BASE: "https://api.openai.com/v1/chat/completions"
OPENAI_API_MODEL: "gpt-4o"
MAX_ROUNDS: 20
REQUEST_INTERVAL: 3
APP_LOAD_DELAY_SECONDS: 5
DARK_MODE: false
DOC_REFINE: true
ANDROID_SCREENSHOT_DIR: "/sdcard/"
ANDROID_XML_DIR: "/sdcard/"
MIN_DIST: 10
```

---

## 🚀 Usage Examples

### Run Directly:

```bash
# Task Mode
python -m scripts.self_explorer \
    --app_name "AppName" \
    --package_name "com.example.targetapp" \
    --description "Send a message to John"

# Explore Mode
python -m scripts.self_explorer \
    --app_name "AppExplore" \
    --package_name "com.example.targetapp" \
    --description "Explore this app"
```

---

## 📊 Output Structure

```
./apps/<app_name>/demos/<timestamp>/
├── logs/
│   ├── explore_log.txt
│   └── reflect_log.txt
└── (temporary screenshots and dumps are cleaned)

./apps/<app_name>/auto_docs/
├── <element_id>.txt  # Persisted documentation
```

---

## 🔮 Future Plans

* Pinch & multi-finger gestures
* Multi-step task planning
* Enhanced recovery logic
* Visual memory across screens
* Richer documentation (screenshots, relationships)
* Exploration/task metrics

---

## 🤝 Contributing

Contributions welcome! Please open issues for bugs or feature requests.

---

## 🙏 Acknowledgments

Inspired by AppAgent from Tencent Gxlab. Special thanks for pioneering multimodal LLM UI automation research.

---
