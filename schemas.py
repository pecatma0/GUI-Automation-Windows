"""Schemas for Hermes Agent GUI Automation plugin tools."""

GET_WINDOWS_SCHEMA = {
    "name": "get_windows",
    "description": "Retrieve a list of active windows. This should be called first to check the handle of the target application.",
    "parameters": {
        "type": "object",
        "properties": {
            "title_contains": {
                "type": "string",
                "description": "Partial match filter for window titles (optional)."
            },
            "process_name": {
                "type": "string",
                "description": "Process name filter (e.g., notepad.exe)."
            }
        }
    }
}

FOCUS_WINDOW_SCHEMA = {
    "name": "focus_window",
    "description": "Bring the specified window to the foreground and focus it. Recommended to call before performing actions.",
    "parameters": {
        "type": "object",
        "properties": {
            "window_handle": {
                "type": "integer",
                "description": "Window handle (HWND)."
            },
            "restore_if_minimized": {
                "type": "boolean",
                "description": "Whether to restore the window if it is minimized (default: true).",
                "default": True
            }
        }
    }
}

GET_UI_TREE_SCHEMA = {
    "name": "get_ui_tree",
    "description": "Get the UI element tree of the specified window or element. Call before actions to understand the UI structure. You can specify a range of depths or start from a specific element handle. Note: Element coordinates (rect) are not included in the tree. To obtain rect, call find_element instead.",
    "parameters": {
        "type": "object",
        "properties": {
            "window_title": {
                "type": "string",
                "description": "Window title (partial match)."
            },
            "window_handle": {
                "type": "integer",
                "description": "Window handle (obtained via get_windows)."
            },
            "element_handle": {
                "type": "integer",
                "description": "Element handle to start traversing from (obtained via get_ui_tree or find_element)."
            },
            "min_depth": {
                "type": "integer",
                "description": "Minimum depth to start serializing properties. Nodes shallower than this will be output as placeholder nodes containing only handles and children (default: 0).",
                "default": 0
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum depth of the hierarchy to retrieve (default: 3, max: 10).",
                "default": 3
            }
        }
    }
}

FIND_ELEMENT_SCHEMA = {
    "name": "find_element",
    "description": "Search for UI elements matching specific conditions. Used to locate target elements and obtain their screen coordinates (rect) after inspecting the tree structure with get_ui_tree.",
    "parameters": {
        "type": "object",
        "properties": {
            "window_handle": {
                "type": "integer",
                "description": "Window handle."
            },
            "conditions": {
                "type": "object",
                "description": "Search conditions (e.g., control_type, name, name_contains, automation_id, etc.)."
            },
            "find_all": {
                "type": "boolean",
                "description": "Whether to return all matching elements (default: false).",
                "default": False
            },
            "timeout": {
                "type": "number",
                "description": "Seconds to wait for the element to appear (default: 5.0).",
                "default": 5.0
            }
        },
        "required": ["conditions"]
    }
}

DO_ACTION_SCHEMA = {
    "name": "do_action",
    "description": "Perform an action (click, type text, select, etc.) on a UI element.",
    "parameters": {
        "type": "object",
        "properties": {
            "handle": {
                "type": "integer",
                "description": "Handle of the target UI element (obtained via get_ui_tree or find_element)."
            },
            "action": {
                "type": "string",
                "description": (
                    "Action type. Supported values are:\n"
                    "- click: Click the element\n"
                    "- double_click: Double-click the element\n"
                    "- right_click: Right-click the element\n"
                    "- type_text: Type text into the element\n"
                    "- clear: Clear the text input field\n"
                    "- select: Select an item (for combo boxes, etc.)\n"
                    "- check: Check a checkbox or radio button\n"
                    "- uncheck: Uncheck a checkbox\n"
                    "- scroll: Scroll the element\n"
                    "- hover: Hover the mouse over the element\n"
                    "- key_press: Send special keys or shortcuts\n"
                    "- invoke: Execute the UIA Invoke pattern (e.g., button press)\n"
                    "- expand: Expand the element (for tree views, combo boxes, etc.)\n"
                    "- collapse: Collapse the element (for tree views, combo boxes, etc.)\n"
                    "- set_value: Directly set the value of an edit control\n"
                    "- type_text_background: Type text in background using SendMessage\n"
                    "- key_press_background: Press a key in background using SendMessage"
                )
            },
            "params": {
                "type": "object",
                "description": (
                    "Action-specific parameters. Specify the following keys depending on the action:\n"
                    "- click, double_click, right_click:\n"
                    "  - x_offset (integer): X offset from the element center (pixels)\n"
                    "  - y_offset (integer): Y offset from the element center (pixels)\n"
                    "- type_text:\n"
                    "  - text (string): Text string to type\n"
                    "  - clear_first (boolean): Whether to clear the existing text first (default: true)\n"
                    "  - with_enter (boolean): Whether to press Enter after typing (default: false)\n"
                    "- select:\n"
                    "  - value (string): Value of the item to select\n"
                    "  - index (integer): Zero-based index of the item to select\n"
                    "- scroll:\n"
                    "  - direction (string): Scroll direction ('up', 'down', 'left', 'right'; default: 'down')\n"
                    "  - amount (integer): Scroll amount (default: 3)\n"
                    "- hover:\n"
                    "  - duration (number): Hover duration in seconds (default: 0.0)\n"
                    "- key_press:\n"
                    "  - keys (string): Key string to send (e.g., '{ENTER}', '^a{BACKSPACE}', 'F5', pywinauto format)\n"
                    "- set_value:\n"
                    "  - value (string): Value to set directly\n"
                    "- type_text_background:\n"
                    "  - text (string): Text string to type in background\n"
                    "- key_press_background:\n"
                    "  - vk_code (integer): Virtual key code to send in background\n"
                    "  - key (string): Key name ('enter', 'tab', 'escape', 'backspace')"
                )
            },
            "verify": {
                "type": "object",
                "description": (
                    "Verification conditions after performing the action (optional). Supported keys:\n"
                    "- expect (string): Expected verification outcome, one of:\n"
                    "  - 'element_appears': Wait for a new UI element matching conditions to appear\n"
                    "  - 'element_disappears': Wait for the target element to hide or disappear\n"
                    "  - 'value_changes': Wait for the value of the target element to match the expected value\n"
                    "  - 'window_closes': Wait for the top-level window of the target element to close\n"
                    "- timeout (number): Verification timeout in seconds (default: 5.0)\n"
                    "- value (any): Expected value when expect is 'value_changes'\n"
                    "- control_type (string): control_type of the element to appear when expect is 'element_appears'\n"
                    "- name (string): name of the element to appear when expect is 'element_appears'\n"
                    "- name_contains (string): substring in the name of the element to appear when expect is 'element_appears'"
                )
            }
        },
        "required": ["handle", "action"]
    }
}

START_APPLICATION_SCHEMA = {
    "name": "start_application",
    "description": "Start a program with the specified command line. Returns the process ID and process name of the launched application.",
    "parameters": {
        "type": "object",
        "properties": {
            "cmd_line": {
                "type": "string",
                "description": "Command line to launch the program (e.g., notepad.exe)."
            },
            "timeout": {
                "type": "number",
                "description": "Seconds to wait for the program to launch (default: 5.0).",
                "default": 5.0
            }
        },
        "required": ["cmd_line"]
    }
}

GET_INSTALLED_APPLICATIONS_SCHEMA = {
    "name": "get_installed_applications",
    "description": "Retrieve a list of installed applications. Supports case-insensitive partial match filtering by application name.",
    "parameters": {
        "type": "object",
        "properties": {
            "name_contains": {
                "type": "string",
                "description": "Case-insensitive partial match filter for the application name (optional)."
            }
        }
    }
}
