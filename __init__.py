import os
from pathlib import Path
import json
from . import tools
from .schemas import (
    GET_WINDOWS_SCHEMA,
    FOCUS_WINDOW_SCHEMA,
    GET_UI_TREE_SCHEMA,
    FIND_ELEMENT_SCHEMA,
    DO_ACTION_SCHEMA,
    START_APPLICATION_SCHEMA,
    GET_INSTALLED_APPLICATIONS_SCHEMA,
)


def handle_get_windows(params, **kwargs):
    """Retrieve list of currently open windows."""
    try:
        title_contains = params.get("title_contains")
        process_name = params.get("process_name")
        res = tools.get_windows(title_contains=title_contains, process_name=process_name)
        return json.dumps({"success": True, "windows": res}, ensure_ascii=False)
    except tools.GUIPluginError as e:
        return json.dumps({"success": False, "error": e.message, "error_code": e.error_code}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "error_code": "UNKNOWN_ERROR"}, ensure_ascii=False)

def handle_focus_window(params, **kwargs):
    """Bring the specified window to the foreground and focus it."""
    try:
        window_handle = params.get("window_handle")
        restore_if_minimized = params.get("restore_if_minimized", True)
        res = tools.focus_window(window_handle=window_handle, restore_if_minimized=restore_if_minimized)
        return json.dumps(res, ensure_ascii=False)
    except tools.GUIPluginError as e:
        return json.dumps({"success": False, "error": e.message, "error_code": e.error_code}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "error_code": "UNKNOWN_ERROR"}, ensure_ascii=False)

def handle_get_ui_tree(params, **kwargs):
    """Get the UI element tree of the specified window."""
    try:
        window_title = params.get("window_title")
        window_handle = params.get("window_handle")
        element_handle = params.get("element_handle")
        min_depth = params.get("min_depth", 0)
        max_depth = params.get("max_depth", 3)
        res = tools.get_ui_tree(
            window_title=window_title,
            window_handle=window_handle,
            element_handle=element_handle,
            min_depth=min_depth,
            max_depth=max_depth
        )
        return json.dumps(res, ensure_ascii=False)
    except tools.GUIPluginError as e:
        return json.dumps({"success": False, "error": e.message, "error_code": e.error_code}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "error_code": "UNKNOWN_ERROR"}, ensure_ascii=False)

def handle_find_element(params, **kwargs):
    """Find UI elements matching specific conditions."""
    try:
        window_handle = params.get("window_handle")
        conditions = params.get("conditions", {})
        find_all = params.get("find_all", False)
        timeout = params.get("timeout", 5.0)
        res = tools.find_element(window_handle=window_handle, conditions=conditions, find_all=find_all, timeout=timeout)
        return json.dumps(res, ensure_ascii=False)
    except tools.GUIPluginError as e:
        return json.dumps({"success": False, "error": e.message, "error_code": e.error_code}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "error_code": "UNKNOWN_ERROR"}, ensure_ascii=False)

def handle_do_action(params, **kwargs):
    """Perform action on the specified UI element."""
    try:
        handle = params.get("handle")
        action = params.get("action")
        action_params = params.get("params", {})
        verify = params.get("verify")
        res = tools.do_action(handle=handle, action=action, params=action_params, verify=verify)
        return json.dumps(res, ensure_ascii=False)
    except tools.GUIPluginError as e:
        return json.dumps({"success": False, "error": e.message, "error_code": e.error_code}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "error_code": "UNKNOWN_ERROR"}, ensure_ascii=False)

def handle_start_application(params, **kwargs):
    """Launch application with the specified command line."""
    try:
        cmd_line = params.get("cmd_line")
        timeout = params.get("timeout", 5.0)
        res = tools.start_application(cmd_line=cmd_line, timeout=timeout)
        return json.dumps(res, ensure_ascii=False)
    except tools.GUIPluginError as e:
        return json.dumps({"success": False, "error": e.message, "error_code": e.error_code}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "error_code": "UNKNOWN_ERROR"}, ensure_ascii=False)

def handle_get_installed_applications(params, **kwargs):
    """Retrieve list of installed applications."""
    try:
        name_contains = params.get("name_contains")
        res = tools.get_installed_applications(name_contains=name_contains)
        return json.dumps({"success": True, "applications": res}, ensure_ascii=False)
    except tools.GUIPluginError as e:
        return json.dumps({"success": False, "error": e.message, "error_code": e.error_code}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "error_code": "UNKNOWN_ERROR"}, ensure_ascii=False)

def register(ctx):
    """Register tools to Hermes Agent context."""
    ctx.register_tool(
        name="get_windows",
        toolset="gui_automation",
        schema=GET_WINDOWS_SCHEMA,
        handler=handle_get_windows,
        description="Use this tool when you need to retrieve a list of currently open visible windows to find the target window's handle or title. It provides window handles, titles, and process names. Returns a JSON string with 'success': true and the list of 'windows', or 'success': false with an 'error' message."
    )

    ctx.register_tool(
        name="focus_window",
        toolset="gui_automation",
        schema=FOCUS_WINDOW_SCHEMA,
        handler=handle_focus_window,
        description="Use this tool to bring a specific window to the foreground and focus it before performing GUI operations. Returns a JSON string with 'success': true if the window is focused successfully, or 'success': false with an 'error' message."
    )

    ctx.register_tool(
        name="get_ui_tree",
        toolset="gui_automation",
        schema=GET_UI_TREE_SCHEMA,
        handler=handle_get_ui_tree,
        description="Use this tool to fetch the hierarchical UI element tree of a window to analyze its components (e.g., buttons, text boxes). Returns a JSON string containing the structured element tree under 'success': true, or 'success': false with an 'error' message."
    )

    ctx.register_tool(
        name="find_element",
        toolset="gui_automation",
        schema=FIND_ELEMENT_SCHEMA,
        handler=handle_find_element,
        description="Use this tool to search for specific UI elements within a window based on matching criteria (like class name, automation ID, or name). Returns a JSON string containing details of the matched element(s) with 'success': true, or 'success': false with an 'error' message."
    )

    ctx.register_tool(
        name="do_action",
        toolset="gui_automation",
        schema=DO_ACTION_SCHEMA,
        handler=handle_do_action,
        description="Use this tool to interact with a specific UI element (e.g., click, type text, select item) using its element handle. Returns a JSON string with 'success': true if the action completes and verifies successfully, or 'success': false with an 'error' message."
    )

    ctx.register_tool(
        name="start_application",
        toolset="gui_automation",
        schema=START_APPLICATION_SCHEMA,
        handler=handle_start_application,
        description="Use this tool to launch a Windows application or command line process. Returns a JSON string with 'success': true and process info (like PID or window handle) if launched, or 'success': false with an 'error' message."
    )

    ctx.register_tool(
        name="get_installed_applications",
        toolset="gui_automation",
        schema=GET_INSTALLED_APPLICATIONS_SCHEMA,
        handler=handle_get_installed_applications,
        description="Use this tool to search for installed programs on the system, optionally filtering by name. Returns a JSON string with 'success': true and a list of matching 'applications' (names and paths), or 'success': false with an 'error' message."
    )

    current_dir = Path(os.path.dirname(__file__))
    skill_path = current_dir / "skills" / "SKILL.md"
    if skill_path.exists():
        ctx.register_skill(
            name="gui-automation",
            path=skill_path,
            description="Windows GUI Automation skill guide."
        )


