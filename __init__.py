import json
from . import tools
from .schemas import (
    GET_WINDOWS_SCHEMA,
    FOCUS_WINDOW_SCHEMA,
    GET_UI_TREE_SCHEMA,
    FIND_ELEMENT_SCHEMA,
    DO_ACTION_SCHEMA,
    START_APPLICATION_SCHEMA,
)


def handle_get_windows(params, **kwargs):
    """Retrieve list of currently open windows."""
    try:
        title_contains = params.get("title_contains")
        process_name = params.get("process_name")
        res = tools.get_windows(title_contains=title_contains, process_name=process_name)
        return json.dumps({"success": True, "windows": res}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

def handle_focus_window(params, **kwargs):
    """Bring the specified window to the foreground and focus it."""
    try:
        window_handle = params.get("window_handle")
        restore_if_minimized = params.get("restore_if_minimized", True)
        res = tools.focus_window(window_handle=window_handle, restore_if_minimized=restore_if_minimized)
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

def handle_get_ui_tree(params, **kwargs):
    """Get the UI element tree of the specified window."""
    try:
        window_title = params.get("window_title")
        window_handle = params.get("window_handle")
        depth = params.get("depth", 3)
        res = tools.get_ui_tree(window_title=window_title, window_handle=window_handle, depth=depth)
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

def handle_find_element(params, **kwargs):
    """Find UI elements matching specific conditions."""
    try:
        window_handle = params.get("window_handle")
        conditions = params.get("conditions", {})
        find_all = params.get("find_all", False)
        timeout = params.get("timeout", 5.0)
        res = tools.find_element(window_handle=window_handle, conditions=conditions, find_all=find_all, timeout=timeout)
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

def handle_do_action(params, **kwargs):
    """Perform action on the specified UI element."""
    try:
        handle = params.get("handle")
        action = params.get("action")
        action_params = params.get("params", {})
        verify = params.get("verify")
        res = tools.do_action(handle=handle, action=action, params=action_params, verify=verify)
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

def handle_start_application(params, **kwargs):
    """Launch application with the specified command line."""
    try:
        cmd_line = params.get("cmd_line")
        timeout = params.get("timeout", 5.0)
        res = tools.start_application(cmd_line=cmd_line, timeout=timeout)
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

def register(ctx):
    """Register tools to Hermes Agent context."""
    ctx.register_tool(
        name="get_windows",
        toolset="gui_automation",
        schema=GET_WINDOWS_SCHEMA,
        handler=handle_get_windows,
        description="起動中のウィンドウ一覧を取得する。"
    )

    ctx.register_tool(
        name="focus_window",
        toolset="gui_automation",
        schema=FOCUS_WINDOW_SCHEMA,
        handler=handle_focus_window,
        description="指定ウィンドウを最前面に移動してフォーカスを当てる。"
    )

    ctx.register_tool(
        name="get_ui_tree",
        toolset="gui_automation",
        schema=GET_UI_TREE_SCHEMA,
        handler=handle_get_ui_tree,
        description="指定ウィンドウのUI要素ツリーをJSONで取得する。"
    )

    ctx.register_tool(
        name="find_element",
        toolset="gui_automation",
        schema=FIND_ELEMENT_SCHEMA,
        handler=handle_find_element,
        description="UI要素を条件で検索して返す。"
    )

    ctx.register_tool(
        name="do_action",
        toolset="gui_automation",
        schema=DO_ACTION_SCHEMA,
        handler=handle_do_action,
        description="UI要素に対して操作を実行する。"
    )

    ctx.register_tool(
        name="start_application",
        toolset="gui_automation",
        schema=START_APPLICATION_SCHEMA,
        handler=handle_start_application,
        description="指定されたコマンドラインでプログラムを起動する。"
    )

