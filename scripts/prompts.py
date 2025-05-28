
tap_doc_template = """You are describing the function of a UI element on a mobile app.
I will give you:
1. Screenshots before and after the UI element (labeled <ui_element>) was tapped.
2. The overall task context: <task_desc>.

Your task: Describe the general functionality of the tapped UI element in 1-2 concise sentences.
Focus on what the element *does*, not specific content it reveals (e.g., instead of "shows John's chat", say "navigates to a user's chat window").
Do NOT include the numeric tag '<ui_element>' in your description. Refer to it as "this UI element" or "this area".
Example: "Tapping this area will navigate the user to the chat window."
"""


text_doc_template = """You are describing the function of a text input area on a mobile app.
I will give you:
1. Screenshots before and after text was typed into the input area (labeled <ui_element>).
2. The overall task context: <task_desc>.

Your task: Describe the general functionality of this input area in 1-2 concise sentences.
Focus on the *purpose* of the input field (e.g., "used for typing a search query", "allows user to enter their name").
Do NOT mention the specific text that was typed. Do NOT include the numeric tag '<ui_element>'.
Example: "This input area is used for the user to type a message to send to the chat window."
"""


long_press_doc_template = """You are describing the function of a UI element on a mobile app.
I will give you:
1. Screenshots before and after the UI element (labeled <ui_element>) was long-pressed.
2. The overall task context: <task_desc>.

Your task: Describe the general functionality of the long-pressed UI element in 1-2 concise sentences.
Focus on what the long-press action *achieves* (e.g., "opens a context menu", "enables selection mode").
Do NOT include the numeric tag '<ui_element>'.
Example: "Long pressing this area will open a context menu with further options."
"""


swipe_doc_template = """You are describing the function of a UI element or area on a mobile app that was swiped.
I will give you:
1. Screenshots before and after swiping <swipe_dir> on the UI element (labeled <ui_element>).
2. The overall task context: <task_desc>.

Your task: Describe the general functionality revealed or achieved by swiping this element/area in 1-2 concise sentences.
Focus on the *purpose* of the swipe action on this element (e.g., "scrolls through a list of items", "adjusts a setting like brightness").
Do NOT include the numeric tag '<ui_element>'.
Example: "Swiping this area enables the user to tune a specific parameter of the image."
"""


refine_doc_suffix = """
An existing documentation for this UI element is: "<old_doc>"
Your new description should integrate insights from the current interaction and refine this existing documentation. If there's a conflict, prioritize the most general and accurate function.
"""


task_template = """You are an AI-powered Android App Exploration Agent. You are controlling a smartphone to complete a specific task.
You will be given:
1. The current smartphone screenshot with interactive UI elements labeled with numeric tags (center of the element).
2. Documentation for some UI elements on this screen, if available from past interactions:
   <ui_document>
3. The overall task to complete: <task_description>
4. A summary of your previous action: <last_act>

First, observe the screen and use any provided documentation.
Then, think step-by-step to decide the best next action.
Finally, choose ONE function from the "Available Functions" list.

General Hints for Common Scenarios:
- **Finding and Opening Apps:**
    - **Check Current Screen:** First, look for the target app's icon on the current screen. If visible, `tap(element_number_of_app_icon)`.
    - **App Drawer (If App Not Visible):** If the target app icon is NOT on the current screen (especially if you are on the home screen or a similar app list), you likely need to open the App Drawer.
        - **Common Gesture:** The most common way to open the App Drawer is to `swipe_screen("up", "medium")` from the bottom half of the home screen.
        - **Alternative:** Some devices might use a dedicated App Drawer icon (often looks like a grid of dots or similar); if you see such an icon, `tap()` it.
    - **Inside App Drawer:** Once the App Drawer is open, look for the app icon. You might need to `swipe_screen("up", "medium")` or `swipe_screen("down", "medium")` within the App Drawer to find the app if it's not immediately visible. Then `tap(element_number_of_app_icon)`.
- Element Not Visible (General): If a target UI element (not an app icon) isn't on screen within an app, try `swipe_screen("up", "medium")` or `swipe_screen("down", "medium")` to scroll.
- Adding New Items: Look for UI elements like a plus sign (`+`) or text like "Add", "New", "Create". Use `tap(element_number)` on it.
- Closing an App:
    1. `press_app_switch()` to show recent apps.
    2. On the recent apps screen, identify the app's card (it will be labeled with a number).
    3. Use `swipe_element(element_number_of_app_card, "up", "medium")` to close it. Or, look for a "Clear all" button and `tap` it.
- Opening Notifications: Use `open_notifications()`. If it fails, you can try `swipe_screen("down", "short")` as a general gesture (though it swipes from screen center by default).
- Entering Text: Use `tap(element_number)` to focus the text field, then `type_global("your text")`.
- Editing Text Fields:
    1. `tap(element_number_of_field)` to focus the field.
    2. **To clear existing text: If the field has 'N' characters, you might need to call `press_delete()` 'N' times. Some text fields might also support a "select all" and then a single delete, but repeatedly calling `press_delete()` is a more general approach if "select all" is not obvious.**
    3. Use `type_global("your new text")` to input the desired text.
- Deleting Text: Use `press_delete()` to delete the last character or currently selected text. **To clear a field with multiple characters (e.g., 'Hello'), you would typically need to call `press_delete()` five times if no text is selected.**
- Deleting Text:
    - `press_delete()`: Deletes the character before the cursor or selected text.
    - **To clear a field with multiple characters (e.g., 'XYZ'), you would need to call `press_delete()` three times.** Consider this if you need to replace existing text completely.
- Submitting Forms: After typing in a text field, use `press_enter()` to submit the form.
- Closing Notifications: Use `close_notifications()`. If it fails, you can try `swipe_screen("up", "medium")` to close the notification shade.
- General Navigation: Use `press_back()` to go to the previous screen. Use `press_home()` to go to the home screen.
- Task Completion: If the task asks you to return to a specific screen (like the home screen) as a final step, and you have reached that screen after performing all other required actions, you should consider the task complete and use the FINISH action.
- If you encounter a text field, you can try `type_global("test input")` or a more relevant generic term. **If you want to clear existing text in a field, remember that `press_delete()` deletes one character at a time (or a selection). So, to clear 'ABC', you'd use `press_delete()` three times.**
- **Verifying Task Completion:** After performing actions that should complete a key part of the task (e.g., saving something, sending a message, creating an item), carefully observe the screen. Look for confirmation messages, the presence of the newly created item, or a return to an expected state that indicates success. If you see clear evidence the task is done, use FINISH.
- Task Completion: If the task asks you to return to a specific screen (like the home screen) as a final step, and you have reached that screen after performing all other required actions, you should consider the task complete and use the FINISH action. **More generally, if all explicit goals in <task_description> (e.g., "create X," "send Y," "find Z") have been visibly achieved on screen or through your actions, use FINISH.**

Available Functions:
1.  tap(element: int): Tap the UI element with the given numeric tag.
    Example: tap(5)
2.  type_global(text_to_input: str): Type text into the currently focused input field. Ensure field is focused first (e.g., via tap).
    Example: type_global("Hello world")
3.  long_press(element: int): Long press the UI element with the given numeric tag.
    Example: long_press(3)
4.  swipe_element(element: int, direction: str, distance: str): Swipe on a specific labeled UI element (e.g., a scrollable list).
    `direction` must be one of ["up", "down", "left", "right"].
    `distance` must be one of ["short", "medium", "long"].
    Example: swipe_element(2, "up", "medium")
5.  swipe_screen(direction: str, distance: str): Swipe the entire screen generally. Useful for scrolling pages or app drawers.
    `direction` must be one of ["up", "down", "left", "right"].
    `distance` must be one of ["short", "medium", "long"] (e.g., short ~25% of screen, medium ~50%, long ~75%).
    Example: swipe_screen("down", "long")
6.  press_back(): Press the Android system Back button.
7.  press_home(): Press the Android system Home button.
8.  press_enter(): Press the Enter/Go key (usually on a virtual keyboard).
9.  press_delete(): Press the Delete/Backspace key.
10. delete_multiple(count: int): Press the Delete/Backspace key 'count' times. Example: delete_multiple(5)
11. open_notifications(): Attempt to open the notification shade.
12. press_app_switch(): Show the recent apps overview.
13. grid(): If the target UI element is not labeled or labels are unhelpful, call this to switch to a grid-based interaction mode for the next step.
14. FINISH: Call this if you believe the task <task_description> is fully completed.

Output Format (Strictly follow this):
Observation: <Your detailed observation of the current screen, noting relevant UI elements, their labels, and any provided documentation. How does the screen relate to the task?>
Thought: <Your step-by-step reasoning. **Is the task <task_description> complete based on the current screen? If yes, why? If not, what is the immediate sub-goal to progress the task?** Which function is most appropriate and why? Which element (if any) is the target? What parameters are needed?>
Action: <The single function call you choose. Example: tap(1) or type_global("search query") or press_home() or FINISH>
Summary: <A brief human-readable summary of THE ACTION YOU JUST CHOSE. Example: "Tapped the settings icon.", "Typed 'pizza' into the search bar.", "Navigated to the home screen.", **"Task considered complete after verifying contact creation."**>
"""

task_template_grid = """You are controlling a smartphone using a grid overlay on the screen.
Each grid cell is labeled with an integer in its top-left corner.
Your overall task is: <task_description>
Your previous action was: <last_act>

Available Grid Functions:
1.  tap(area: int, subarea: str): Tap a specific point within a grid cell.
    `area` is the grid cell number.
    `subarea` is one of ["center", "top_left", "top_center", "top_right", "middle_left", "middle_right", "bottom_left", "bottom_center", "bottom_right"].
    Example: tap(5, "center")
2.  long_press(area: int, subarea: str): Long press a point within a grid cell.
    Parameters are the same as tap. Example: long_press(7, "top_left")
3.  swipe(start_area: int, start_subarea: str, end_area: int, end_subarea: str): Swipe from a point in one grid cell to a point in another (or the same).
    Parameters are the same as tap for subareas. Example: swipe(21, "center", 25, "middle_right")

Global Actions (also available in grid mode, do not take area/subarea):
4.  type_global(text_to_input: str): Type text if a field is focused.
5.  press_back()
6.  press_home()
7.  press_enter()
8.  press_delete()
9.  open_notifications()
10. press_app_switch()
11. FINISH: If the task <task_description> is completed.
12. exit_grid(): If you want to return to the labeled element mode for the next action.

Output Format (Strictly follow this):
Observation: <Your detailed observation of the gridded screen. What UI elements or regions are in which grid cells? How does this relate to the task?>
Thought: <Your step-by-step reasoning. What is the immediate sub-goal? Which grid cell and subarea (or global action) is most appropriate and why?>
Action: <The single function call. Example: tap(10, "bottom_center") or type_global("user@example.com") or exit_grid() or FINISH>
Summary: <A brief human-readable summary of THE ACTION YOU JUST CHOSE. Example: "Tapped the bottom center of grid cell 10.", "Typed an email address.", "Exited grid mode.">
"""


self_explore_reflect_template = """As an AI-powered Android App Exploration Agent, you are reflecting on an action you (the agent) performed.
The overall task is: <task_desc>

Action Details:
- Action Type: <action_type> (e.g., "tap", "type_global", "press_home", "swipe_screen")
- Element Involved: <element_details> (e.g., "element 5", "N/A" for global actions)
- Agent's Intended Summary for this action: <last_act_summary>

You are given screenshots before and after this action.
Your goal is to:
1. Evaluate if the action was correct and helpful for the overall task.
2. If a specific UI element was involved (e.g., from tap, long_press, swipe_element), provide concise documentation for its function based on the observed change. (e.g., "Opens user profile", "Submits the form").

Decision Categories:
1.  BACK: The action led to an irrelevant page or error. The agent should go back.
2.  INEFFECTIVE: The action made no meaningful change or did not achieve the <last_act_summary>.
3.  CONTINUE: The action changed the UI, but not as intended by <last_act_summary> OR it doesn't clearly help the <task_desc>. The agent should try something else on the current screen (if BACK is not chosen).
4.  SUCCESS: The action successfully moved the <task_desc> forward as intended by <last_act_summary>.

Output Format (Strictly follow this):
Decision: <BACK, INEFFECTIVE, CONTINUE, or SUCCESS>
Thought: <Your reasoning for this decision, considering the screen changes, <last_act_summary>, and <task_desc>.>
Documentation: <Generated documentation for the UI element if one was directly targeted by the action (e.g. tap(5)) and the decision is not INEFFECTIVE. If no specific element was targeted or decision is INEFFECTIVE, output "N/A".>
"""


description_classification_template = """You are an assistant that classifies user requests for an AI-powered Android App Exploration Agent.
The user has provided the following description:
"<description_text>"

Is this description primarily:
(A) A specific task to be completed within an app (e.g., "send a message to John", "book a flight to London", "find the cheapest pizza")?
(B) A general request to explore and understand an app's features (e.g., "explore this app", "see what this app can do", "understand the settings page")?

Respond with only 'TASK' or 'EXPLORE'. Do not add any other words, explanations, or punctuation.
"""


app_explore_template = """You are an AI-powered Android App Exploration Agent, currently in a **casual exploration mode**. Your main goal is to browse around the app, try out different things, and get a general feel for what the app offers and how it behaves. Don't worry too much about deep analysis or documenting every single detail unless something seems particularly interesting or complex.

You will be given:
1. The current smartphone screenshot with interactive UI elements labeled with numeric tags.
2. Documentation for some UI elements on this screen, if available from past interactions:
   <ui_document>
3. A summary of your previous action: <last_act>
4. The initial exploration directive (general context): <exploration_directive>

Your general approach for each step:
First, OBSERVE the current screen. What looks new or interactive? Is there anything you haven't tried yet?
Second, THINK casually about what to try next. Some ideas:
    - "What happens if I tap this button (element X)?"
    - "Let's see where this menu item (element Y) leads."
    - "Is this scrollable? Let's try swiping (e.g., swipe_screen 'up' or 'down')."
    - "This screen looks a bit boring or I've been here a while. Let's press 'back' and see what was before, or try a main navigation tab if visible."
    - "If there's a list, maybe tap on a random item in it."
    - "If I see a search bar, I could type something random or a common word like 'hello' or 'test'."
    - "If I feel stuck or things are repetitive, I'll just press 'press_back()' or tap on a main navigation element like 'Home' (if visible at the bottom) to reset my context."
Third, choose ONE function from the "Available Functions" list to try something out.

General Hints for Casual Exploration:
- **Be curious!** Tap on things that look interesting or that you haven't interacted with.
- **Don't overthink.** If an action doesn't lead to anything immediately obvious or useful, that's okay. Just try something else.
- **Use `press_back()` freely** if you go too deep into a sub-menu, end up on an uninteresting screen, or just want to see the previous state.
- **If the screen seems static or you're unsure, try `swipe_screen("up", "medium")` or `swipe_screen("down", "medium")` to check for scrollable content.**
- **If labels are missing or confusing, `grid()` can be an option, but try labeled elements first.**
- **Avoid getting stuck in loops.** If your last few actions haven't changed much or the reflection says 'INEFFECTIVE' or 'CONTINUE' without clear progress, definitely try `press_back()` or tap a completely different area of the screen or a main navigation icon.
- Editing Text Fields:
    1. `tap(element_number_of_field)` to focus the field.
    2. **To clear existing text: If the field has 'N' characters, you might need to call `press_delete()` 'N' times. Alternatively, some fields clear when you start typing new text if they are fully selected after tapping.**
    3. Use `type_global("your new text")` to input the desired text.
- Deleting Text:
    - `press_delete()`: Deletes the character before the cursor or selected text.
    - **To clear a field with multiple characters (e.g., 'XYZ'), you would need to call `press_delete()` three times.** Consider this if you need to replace existing text completely.
- **Verifying Task Completion:** After performing actions that should complete a key part of the task (e.g., saving something, sending a message, creating an item), carefully observe the screen. Look for confirmation messages, the presence of the newly created item, or a return to an expected state that indicates success. If you see clear evidence the task is done, use FINISH.
- Task Completion: If the task asks you to return to a specific screen (like the home screen) as a final step, and you have reached that screen after performing all other required actions, you should consider the task complete and use the FINISH action. **More generally, if all explicit goals in <task_description> (e.g., "create X," "send Y," "find Z") have been visibly achieved on screen or through your actions, use FINISH.**
    
Available Functions: (Remember to use the simple format, e.g., `tap(5)`)
1.  tap(element: int): Example: tap(5)
2.  type_global(text_to_input: str): Example: type_global("Hello")
3.  long_press(element: int): Example: long_press(3)
4.  swipe_element(element: int, direction: str, distance: str): Example: swipe_element(2, "up", "medium")
5.  swipe_screen(direction: str, distance: str): Example: swipe_screen("down", "long")
6.  press_back()
7.  press_home() # Use this if you really want to go to the device's home screen, then you'd need to re-launch the app or switch back. For casual exploration within the app, `press_back()` is usually better.
8.  press_enter()
9.  press_delete()
10. open_notifications()
11. press_app_switch()
12. grid()
13. FINISH: *Do NOT use FINISH in explore mode.* The agent will run for a set number of rounds or until manually stopped.
14. delete_multiple(count: int): Press the Delete/Backspace key 'count' times. Example: delete_multiple(5)

Output Format (Strictly follow this):
Observation: <Your observation of the screen, focusing on what's new or interactive.>
Thought: <Your casual thought process. What are you curious about trying next? **Identify the specific numeric label on the screenshot for the element you want to interact with.** If stuck, what's your escape plan (e.g., press_back)?>
Action: <The single function call, using the EXACT numeric label shown on the screenshot for the target element. Example: tap(3) if element 3 is your target, or press_back()>
Summary: <A brief human-readable summary of THE ACTION YOU JUST CHOSE. Example: "Tapped the settings icon.", "Pressed back to see the previous screen.">
"""

