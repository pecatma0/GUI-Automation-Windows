"""Tools for Windows GUI automation. All features consolidated into a single module."""
import time
import os
import sys
import logging
import ctypes
from typing import Any, cast
from dotenv import load_dotenv

import win32gui
import win32process
import win32con
import psutil
import pywinauto
from pywinauto.controls.uiawrapper import UIAWrapper

# ==========================================
# 1. Configuration & Environment Variables
# ==========================================
# Load environment variables from .env file.
# Exit if config file fails to load or required keys are missing.
loaded = load_dotenv()
if not loaded:
    # Try directory where this script is located
    alt_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(alt_path):
        loaded = load_dotenv(alt_path)

if not loaded:
    print("エラー: .env ファイルの読み込みに失敗しました。プロセスを終了します。", file=sys.stderr)
    sys.exit(1)

CONFIG = {
    "DEFAULT_TIMEOUT": os.getenv("DEFAULT_TIMEOUT"),
    "DEFAULT_WAIT_AFTER": os.getenv("DEFAULT_WAIT_AFTER"),
    "LOG_FILE_PATH": os.getenv("LOG_FILE_PATH"),
}

for key, val in CONFIG.items():
    if val is None:
        print(f"エラー: 必須の設定キー {key} が .env に定義されていません。プロセスを終了します。", file=sys.stderr)
        sys.exit(1)

# ==========================================
# 2. Exceptions
# ==========================================
class GUIPluginError(Exception):
    """GUI操作プラグインの基底例外クラス。"""
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code: str = error_code
        self.message: str = message

class WindowNotFoundError(GUIPluginError):
    """指定されたウィンドウが見つからない場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("WINDOW_NOT_FOUND", message)

class ElementNotFoundError(GUIPluginError):
    """指定されたUI要素が見つからない場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("ELEMENT_NOT_FOUND", message)

class ElementDisabledError(GUIPluginError):
    """要素が無効状態であり操作できない場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("ELEMENT_DISABLED", message)

class ElementNotVisibleError(GUIPluginError):
    """要素が非表示であり操作できない場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("ELEMENT_NOT_VISIBLE", message)

class ActionNotSupportedError(GUIPluginError):
    """要素が要求されたアクションに対応していない場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("ACTION_NOT_SUPPORTED", message)

class TimeoutError(GUIPluginError):
    """待機処理でタイムアウトした場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("TIMEOUT", message)

class AccessDeniedError(GUIPluginError):
    """OS権限不足などで操作が拒否された場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("ACCESS_DENIED", message)

class BackendError(GUIPluginError):
    """内部バックエンドライブラリでエラーが発生した場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("BACKEND_ERROR", message)

class InvalidParamsError(GUIPluginError):
    """パラメータが不正である場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_PARAMS", message)

# ==========================================
# 3. Logging Setup
# ==========================================
def setup_logger() -> logging.Logger:
    """プラグイン用のロガーを設定する。"""
    logger = logging.getLogger("gui_plugin")
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        log_file = CONFIG["LOG_FILE_PATH"]
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.WARNING) # エラーおよび警告ログのみをファイル出力して管理する
        
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger

logger = setup_logger()

# ==========================================
# 4. Element Cache Operations
# ==========================================
_element_cache: dict[int, UIAWrapper] = {}

def _register_element(element: UIAWrapper) -> int:
    """要素をキャッシュに登録し、一意のハンドル（整数ID）を返す。"""
    element_id = id(element)
    _element_cache[element_id] = element
    return element_id

def _get_cached_element(element_id: int) -> UIAWrapper:
    """キャッシュから要素を取得する。存在しない場合はエラーとする。"""
    if element_id not in _element_cache:
        raise ElementNotFoundError(f"指定されたハンドル {element_id} の要素がキャッシュに見つかりません。再取得してください。")
    return _element_cache[element_id]

# ==========================================
# 5. Serialization & Tree Builders
# ==========================================
def _get_element_info_property(element: UIAWrapper, prop_name: str, default: Any = "") -> Any:
    """UIAWrapperのelement_infoからプロパティを安全に取得する。"""
    try:
        val = getattr(element.element_info, prop_name)
        return val if val is not None else default
    except Exception:
        return default


def _call_element_method(element: UIAWrapper, method_name: str, default: Any) -> Any:
    """UIAWrapperのメソッドを安全に呼び出す。"""
    try:
        method = getattr(element, method_name)
        return method()
    except Exception:
        return default


def _serialize_element(element: UIAWrapper) -> dict[str, Any]:
    """UIAWrapper要素をシリアル化する。"""
    virtual_handle = _register_element(element)

    control_type = _get_element_info_property(element, "control_type", "Unknown")
    name = _get_element_info_property(element, "name", "")
    automation_id = _get_element_info_property(element, "automation_id", "")
    class_name = _get_element_info_property(element, "class_name", "")

    enabled = _call_element_method(element, "is_enabled", False)
    visible = _call_element_method(element, "is_visible", False)

    value = None
    try:
        if hasattr(element, "get_value"):
            value = element.get_value()
        elif hasattr(element, "texts") and element.texts():
            value = element.texts()[0]
    except Exception:
        pass

    return {
        "control_type": control_type,
        "name": name,
        "automation_id": automation_id,
        "class_name": class_name,
        "handle": virtual_handle,
        "enabled": enabled,
        "visible": visible,
        "value": value,
        "children": [],
    }

def _build_tree(element: UIAWrapper, current_depth: int, min_depth: int, max_depth: int, include_invisible: bool) -> dict[str, Any]:
    """再帰的に子要素を探索してツリーを構築する。"""
    if current_depth < min_depth:
        virtual_handle = _register_element(element)
        node = {
            "control_type": "Placeholder",
            "handle": virtual_handle,
            "children": [],
        }
    else:
        node = _serialize_element(element)
    
    if current_depth >= max_depth:
        return node

    try:
        children = element.children()
    except Exception:
        children = []

    for child in children:
        try:
            if not include_invisible and not child.is_visible():
                continue
            child_node = _build_tree(child, current_depth + 1, min_depth, max_depth, include_invisible)
            node["children"].append(child_node)
        except Exception:
            pass

    return node

# ==========================================
# 6. Core Plugin Tools
# ==========================================
def get_windows(
    title_contains: str | None = None,
    process_name: str | None = None,
    visible_only: bool = True,
) -> list[dict[str, Any]]:
    """起動中のウィンドウ一覧を取得する。"""
    try:
        windows: list[dict[str, Any]] = []
        # PIDからプロセス名へのキャッシュ
        pid_to_name: dict[int, str] = {}

        def enum_windows_callback(hwnd: int, extra: object) -> bool:
            try:
                if visible_only and not win32gui.IsWindowVisible(hwnd):
                    return True

                title = win32gui.GetWindowText(hwnd)
                if title_contains and title_contains not in title:
                    return True

                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid in pid_to_name:
                        proc_name = pid_to_name[pid]
                    else:
                        proc = psutil.Process(pid)
                        proc_name = proc.name()
                        pid_to_name[pid] = proc_name
                except Exception:
                    pid = 0
                    proc_name = ""

                if process_name and process_name.lower() not in proc_name.lower():
                    return True

                is_minimized = win32gui.IsIconic(hwnd) != 0

                windows.append({
                    "title": title,
                    "handle": hwnd,
                    "process_id": pid,
                    "process_name": proc_name,
                    "visible": win32gui.IsWindowVisible(hwnd) != 0,
                    "minimized": is_minimized,
                })
            except Exception as ex:
                logger.warning(f"enum_windows_callback error for hwnd {hwnd}: {ex}")
            return True

        ctypes.windll.kernel32.SetLastError(0)
        win32gui.EnumWindows(enum_windows_callback, None)
        return windows

    except Exception as e:
        logger.error(f"get_windows でエラーが発生しました: {str(e)}")
        raise BackendError(f"ウィンドウ一覧の取得中にエラーが発生しました: {str(e)}")


def focus_window(
    window_title: str | None = None,
    window_handle: int | None = None,
    restore_if_minimized: bool = True,
) -> dict[str, Any]:
    """指定ウィンドウを最前面に移動してフォーカスを当てる。"""
    start_time = time.time()
    hwnd = window_handle

    if not hwnd and window_title:
        wins = get_windows(title_contains=window_title, visible_only=True)
        if not wins:
            raise WindowNotFoundError(f"タイトル '{window_title}' に一致する可視ウィンドウが見つかりません。")
        hwnd = cast(int, wins[0]["handle"])

    if not hwnd or not win32gui.IsWindow(hwnd):
        raise WindowNotFoundError(f"指定されたウィンドウハンドル {hwnd} は無効または存在しません。")

    try:
        if restore_if_minimized and win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.2)

        # 現在のフォアグラウンドウィンドウのスレッドIDにアタッチしてフォーカス設定権限を借用する
        attached = False
        this_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        fore_thread_id = 0
        try:
            fore_hwnd = win32gui.GetForegroundWindow()
            if fore_hwnd != 0 and fore_hwnd != hwnd:
                fore_thread_id, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
                if fore_thread_id != this_thread_id:
                    win32process.AttachThreadInput(this_thread_id, fore_thread_id, True)
                    attached = True
        except Exception:
            pass

        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        
        # 複数回試行して確実にフォアグラウンドにする
        success_focus = False
        for _ in range(3):
            try:
                # Altキーをシミュレートしてフォアグラウンド制限を回避する
                # VK_MENU (Altキー) = 0x12, KEYEVENTF_KEYUP = 0x0002
                ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
                win32gui.SetForegroundWindow(hwnd)
                ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
                
                # 少し待ってアクティブウィンドウを確認
                time.sleep(0.1)
                if win32gui.GetForegroundWindow() == hwnd:
                    success_focus = True
                    break
            except Exception:
                time.sleep(0.1)

        # アタッチした入力を解除
        if attached:
            try:
                win32process.AttachThreadInput(this_thread_id, fore_thread_id, False)
            except Exception:
                pass

        if not success_focus:
            # 代替手段としてBringWindowToTopやSwitchToThisWindowを試みる
            try:
                win32gui.BringWindowToTop(hwnd)
            except Exception:
                pass
            try:
                ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
            except Exception:
                pass
            # 最終確認 (切り替えのタイムラグを考慮して数回リトライ)
            final_fore = 0
            for _ in range(5):
                final_fore = win32gui.GetForegroundWindow()
                if final_fore == hwnd:
                    break
                time.sleep(0.1)
            
            if final_fore != hwnd:
                if final_fore == 0:
                    logger.warning(f"SetForegroundWindow実行後、フォアグラウンドウィンドウが0（非対話型セッションまたはフォーカス未設定）です。警告を出力し、処理を続行します。(HWND={hwnd})")
                else:
                    raise AccessDeniedError(f"SetForegroundWindow実行後もウィンドウ(HWND={hwnd})がアクティブになっていません。(現在のフォアグラウンド={final_fore})")

        elapsed = int((time.time() - start_time) * 1000)
        return {
            "success": True,
            "action": "focus_window",
            "handle": hwnd,
            "elapsed_ms": elapsed,
            "error": None,
            "error_code": None,
            "state_after": {},
        }
    except Exception as e:
        logger.error(f"focus_window でエラーが発生しました (HWND={hwnd}): {str(e)}")
        raise AccessDeniedError(f"ウィンドウのフォーカスに失敗しました（管理者権限が必要な可能性があります）: {str(e)}")


def get_ui_tree(
    window_title: str | None = None,
    window_handle: int | None = None,
    process_name: str | None = None,
    element_handle: int | None = None,
    min_depth: int = 0,
    max_depth: int = 3,
    include_invisible: bool = False,
) -> dict[str, Any]:
    """指定ウィンドウまたは要素の UI 要素ツリーを JSON で返す。"""
    if not (window_title or window_handle or process_name or element_handle):
        raise InvalidParamsError("window_title, window_handle, process_name, element_handle のいずれか一つを必ず指定してください。")

    try:
        if element_handle is not None:
            # キャッシュから要素を取得
            root_element = _get_cached_element(element_handle)
        else:
            hwnd = window_handle
            if not hwnd:
                wins = get_windows(title_contains=window_title, process_name=process_name, visible_only=True)
                if not wins:
                    wins = get_windows(title_contains=window_title, process_name=process_name, visible_only=False)
                    if not wins:
                        raise WindowNotFoundError("指定された条件のウィンドウが見つかりません。")
                hwnd = cast(int, wins[0]["handle"])

            _element_cache.clear()

            app = pywinauto.Application(backend="uia").connect(handle=hwnd)
            root_element = app.window(handle=hwnd)
            
            if not root_element.exists():
                raise WindowNotFoundError("指定ハンドルに対応するウィンドウが pywinauto から検出できませんでした。")

        # ツリーデータを構築
        tree_data = _build_tree(root_element, 0, min_depth, max_depth, include_invisible)

        # 最上位親ウィンドウ情報を取得
        win_info = None
        try:
            if element_handle is not None:
                top_hwnd = root_element.top_level_parent().handle
            else:
                top_hwnd = hwnd
            
            for w in get_windows(visible_only=False):
                if w["handle"] == top_hwnd:
                    win_info = w
                    break
        except Exception:
            pass

        return {
            "window": win_info,
            "tree": tree_data
        }

    except GUIPluginError:
        raise
    except Exception as e:
        logger.error(f"get_ui_tree でエラーが発生しました: {str(e)}")
        raise BackendError(f"UIツリーの取得に失敗しました: {str(e)}")


def find_element(
    window_title: str | None = None,
    window_handle: int | None = None,
    conditions: dict[str, Any] = {},
    find_all: bool = False,
    timeout: float = 5.0,
) -> Any:
    """検索条件に一致する UI 要素を返す。"""
    if not conditions:
        raise InvalidParamsError("検索条件(conditions)を指定してください。")

    hwnd = window_handle
    if not hwnd and window_title:
        wins = get_windows(title_contains=window_title, visible_only=True)
        if not wins:
            raise WindowNotFoundError(f"タイトル '{window_title}' に一致するウィンドウが見つかりません。")
        hwnd = cast(int, wins[0]["handle"])

    if not hwnd:
        raise InvalidParamsError("window_handle または window_title を指定してください。")

    initial_depth = cast(int, conditions.get("max_depth", conditions.get("depth", 3)))
    current_depth = initial_depth
    max_allowed_depth = 10

    start_time = time.time()
    
    while True:
        try:
            tree_response = get_ui_tree(window_handle=hwnd, max_depth=current_depth, include_invisible=True)
            root_node = tree_response["tree"]
            
            matched_nodes: list[dict[str, Any]] = []

            def traverse_and_match(node: dict[str, Any]) -> None:
                match = True
                
                if "control_type" in conditions:
                    if node.get("control_type") != conditions["control_type"]:
                        match = False
                
                if match and "name" in conditions:
                    if node.get("name") != conditions["name"]:
                        match = False
                        
                if match and "name_contains" in conditions:
                    cond_name = cast(str, conditions["name_contains"])
                    if cond_name not in cast(str, node.get("name", "")):
                        match = False

                if match and "automation_id" in conditions:
                    if node.get("automation_id") != conditions["automation_id"]:
                        match = False

                if match and "class_name" in conditions:
                    if node.get("class_name") != conditions["class_name"]:
                        match = False

                if match and "enabled" in conditions:
                    if node.get("enabled") != conditions["enabled"]:
                        match = False

                if match and "visible" in conditions:
                    if node.get("visible") != conditions["visible"]:
                        match = False

                if match:
                    matched_nodes.append(node)

                for child in cast(list[dict[str, Any]], node.get("children", [])):
                    traverse_and_match(child)

            traverse_and_match(root_node)

            if matched_nodes:
                for node in matched_nodes:
                    try:
                        uia_element = _get_cached_element(node["handle"])
                        rect = uia_element.rectangle()
                        node["rect"] = {
                            "x": rect.left,
                            "y": rect.top,
                            "width": rect.width(),
                            "height": rect.height(),
                        }
                    except Exception:
                        node["rect"] = {"x": 0, "y": 0, "width": 0, "height": 0}

                if find_all:
                    return matched_nodes
                else:
                    return matched_nodes[0]

            # 見つからなかった場合は深さを増やす
            if current_depth < max_allowed_depth:
                current_depth += 1

        except Exception as e:
            logger.warning(f"find_element 中の試行でエラー（再試行します）: {str(e)}")

        if time.time() - start_time > timeout:
            break
            
        time.sleep(0.1)

    raise ElementNotFoundError(f"条件 {conditions} に一致する要素がタイムアウト {timeout} 秒以内に見つかりませんでした。")


def do_action(
    handle: int | None = None,
    element: dict[str, Any] | None = None,
    action: str = "",
    params: dict[str, Any] = {},
    wait_after: float = 0.5,
    verify: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """UI 要素に対して操作を実行する。"""
    start_time = time.time()
    
    target_handle = handle
    if not target_handle and element:
        target_handle = cast(int | None, element.get("handle"))

    if not target_handle:
        raise InvalidParamsError("handle または element のいずれかを指定してください。")

    uia_element = _get_cached_element(target_handle)

    try:
        if not uia_element.is_visible():
            raise ElementNotVisibleError("操作対象の要素が非表示です。")
        if not uia_element.is_enabled():
            raise ElementDisabledError("操作対象の要素が無効状態です。")
    except GUIPluginError:
        raise
    except Exception as e:
        raise BackendError(f"要素の状態検証中にエラーが発生しました: {str(e)}")

    try:
        if action in ("click", "double_click", "right_click"):
            x = cast(int, params.get("x_offset", 0))
            y = cast(int, params.get("y_offset", 0))
            coords = (x, y) if (x != 0 or y != 0) else None
            
            if action == "click":
                uia_element.click_input(coords=coords) if coords else uia_element.click_input()
            elif action == "double_click":
                uia_element.double_click_input(coords=coords) if coords else uia_element.double_click_input()
            elif action == "right_click":
                uia_element.right_click_input(coords=coords) if coords else uia_element.right_click_input()

        elif action == "type_text":
            text = cast(str, params.get("text", ""))
            clear_first = cast(bool, params.get("clear_first", True))
            with_enter = cast(bool, params.get("with_enter", False))
            
            if clear_first:
                uia_element.set_focus()
                uia_element.type_keys("^a{BACKSPACE}", set_foreground=False)
                
            if text:
                uia_element.type_keys(text, with_spaces=True, with_tabs=True, with_newlines=True, set_foreground=False)
            if with_enter:
                uia_element.type_keys("{ENTER}", set_foreground=False)

        elif action == "clear":
            uia_element.set_focus()
            uia_element.type_keys("^a{BACKSPACE}", set_foreground=False)

        elif action == "select":
            value = params.get("value")
            index = params.get("index")
            
            if hasattr(uia_element, "select"):
                if value is not None:
                    uia_element.select(cast(str, value))
                elif index is not None:
                    uia_element.select(cast(int, index))
                else:
                    raise InvalidParamsError("select アクションには value または index を指定してください。")
            else:
                raise ActionNotSupportedError("この要素は select アクションをサポートしていません。")

        elif action == "check":
            if hasattr(uia_element, "check"):
                uia_element.check()
            else:
                raise ActionNotSupportedError("この要素は check アクションをサポートしていません。")

        elif action == "uncheck":
            if hasattr(uia_element, "uncheck"):
                uia_element.uncheck()
            else:
                raise ActionNotSupportedError("この要素は uncheck アクションをサポートしていません。")

        elif action == "scroll":
            direction = cast(str, params.get("direction", "down"))
            amount = cast(int, params.get("amount", 3))
            if hasattr(uia_element, "scroll"):
                uia_element.scroll(direction=direction, amount=amount)
            else:
                raise ActionNotSupportedError("この要素は直接の scroll をサポートしていません。")

        elif action == "hover":
            uia_element.move_mouse_input()
            duration = cast(float, params.get("duration", 0.0))
            if duration > 0:
                time.sleep(duration)

        elif action == "key_press":
            keys = cast(str, params.get("keys", ""))
            if not keys:
                raise InvalidParamsError("key_press アクションには keys パラメータが必要です。")
            uia_element.type_keys(keys, set_foreground=False)

        elif action == "type_text_background":
            text = cast(str, params.get("text", ""))
            if not text:
                raise InvalidParamsError("type_text_background アクションには text パラメータが必要です。")
            hwnd = uia_element.handle
            if not hwnd or not win32gui.IsWindow(hwnd):
                raise BackendError("有効なウィンドウハンドル(HWND)を取得できませんでした。")
            WM_CHAR = 0x0102
            for char in text:
                win32gui.SendMessage(hwnd, WM_CHAR, ord(char), 0)
                time.sleep(0.01)

        elif action == "key_press_background":
            vk_code = params.get("vk_code")
            key_name = params.get("key")
            hwnd = uia_element.handle
            if not hwnd or not win32gui.IsWindow(hwnd):
                raise BackendError("有効なウィンドウハンドル(HWND)を取得できませんでした。")
            vk = None
            if vk_code is not None:
                vk = cast(int, vk_code)
            elif key_name:
                key_name_lower = str(key_name).lower()
                if key_name_lower == "enter":
                    vk = win32con.VK_RETURN
                elif key_name_lower == "tab":
                    vk = win32con.VK_TAB
                elif key_name_lower == "escape":
                    vk = win32con.VK_ESCAPE
                elif key_name_lower == "backspace":
                    vk = win32con.VK_BACK
                else:
                    raise InvalidParamsError(f"サポートされていないキー名です: {key_name}")
            else:
                raise InvalidParamsError("key_press_background アクションには vk_code または key パラメータが必要です。")
            win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
            win32gui.SendMessage(hwnd, win32con.WM_KEYUP, vk, 0)

        elif action == "invoke":
            if hasattr(uia_element, "invoke"):
                uia_element.invoke()
            else:
                raise ActionNotSupportedError("この要素は invoke アクションをサポートしていません。")

        elif action == "expand":
            if hasattr(uia_element, "expand"):
                uia_element.expand()
            else:
                raise ActionNotSupportedError("この要素は expand アクションをサポートしていません。")

        elif action == "collapse":
            if hasattr(uia_element, "collapse"):
                uia_element.collapse()
            else:
                raise ActionNotSupportedError("この要素は collapse アクションをサポートしていません。")

        elif action == "set_value":
            val = cast(str, params.get("value", ""))
            if hasattr(uia_element, "set_edit_text"):
                uia_element.set_edit_text(val)
            elif hasattr(uia_element, "set_value"):
                try:
                    uia_element.iface_value.SetValue(val)
                except Exception:
                    raise ActionNotSupportedError("この要素は値の直接設定(set_value)をサポートしていません。")
            else:
                raise ActionNotSupportedError("この要素は値の直接設定(set_value)をサポートしていません。")
        else:
            raise ActionNotSupportedError(f"アクション '{action}' はサポートされていません。")

    except GUIPluginError:
        raise
    except Exception as e:
        logger.error(f"do_action 実行エラー (action={action}, handle={target_handle}): {str(e)}")
        raise BackendError(f"アクションの実行中にエラーが発生しました: {str(e)}")

    time.sleep(wait_after)

    state_after = None
    if verify:
        expect = verify.get("expect")
        timeout = cast(float, verify.get("timeout", 5.0))
        verify_start = time.time()
        verified = False
        
        while time.time() - verify_start < timeout:
            try:
                if expect == "element_appears":
                    conds = {
                        "control_type": verify.get("control_type"),
                        "name": verify.get("name"),
                        "name_contains": verify.get("name_contains"),
                        "visible": True
                    }
                    conds = {k: v for k, v in conds.items() if v is not None}
                    
                    try:
                        top_window = uia_element.top_level_parent()
                        top_hwnd = top_window.handle
                        find_element(window_handle=top_hwnd, conditions=conds, timeout=0.1)
                        verified = True
                        break
                    except ElementNotFoundError:
                        pass
                        
                elif expect == "element_disappears":
                    try:
                        if not uia_element.is_visible():
                            verified = True
                            break
                    except Exception:
                        verified = True
                        break
                        
                elif expect == "value_changes":
                    expected_value = verify.get("value")
                    current_value = None
                    if hasattr(uia_element, "get_value"):
                        current_value = uia_element.get_value()
                    elif hasattr(uia_element, "texts") and uia_element.texts():
                        current_value = uia_element.texts()[0]
                        
                    if expected_value is not None:
                        if current_value == expected_value:
                            verified = True
                            break
                        
                elif expect == "window_closes":
                    top_window = uia_element.top_level_parent()
                    top_hwnd = top_window.handle
                    if not win32gui.IsWindow(top_hwnd):
                        verified = True
                        break
            except Exception:
                pass
                
            time.sleep(0.5)
            
        if not verified:
            raise TimeoutError(f"検証条件 '{expect}' がタイムアウト {timeout} 秒以内に満たされませんでした。")

        try:
            state_after = {
                "control_type": uia_element.element_info.control_type,
                "name": uia_element.element_info.name or "",
                "enabled": uia_element.is_enabled(),
                "visible": uia_element.is_visible(),
            }
        except Exception:
            pass

    elapsed = int((time.time() - start_time) * 1000)
    return {
        "success": True,
        "action": action,
        "handle": target_handle,
        "elapsed_ms": elapsed,
        "error": None,
        "error_code": None,
        "state_after": state_after,
    }


def start_application(cmd_line: str, timeout: float = 5.0) -> dict[str, Any]:
    """指定されたコマンドラインでプログラムを起動する。"""
    if not cmd_line:
        raise InvalidParamsError("起動するコマンドライン(cmd_line)を指定してください。")
        
    start_time = time.time()
    try:
        import subprocess
        proc = subprocess.Popen(cmd_line, shell=False)
        pid = proc.pid
        
        time.sleep(0.5)
        
        try:
            p = psutil.Process(pid)
            proc_name = p.name()
        except Exception:
            proc_name = os.path.basename(cmd_line.split()[0])

        elapsed = int((time.time() - start_time) * 1000)
        return {
            "success": True,
            "action": "start_application",
            "process_id": pid,
            "process_name": proc_name,
            "elapsed_ms": elapsed,
            "error": None,
            "error_code": None,
        }
    except Exception as e:
        logger.error(f"start_application でエラーが発生しました (cmd={cmd_line}): {str(e)}")
        raise BackendError(f"プログラムの起動に失敗しました: {str(e)}")


def get_installed_applications(name_contains: str | None = None) -> list[dict[str, Any]]:
    """インストールされているアプリケーションの一覧を取得する。

    Windowsのレジストリ（Uninstallキー）から、インストールされている
    アプリケーションのDisplayName、DisplayVersion、Publisher、InstallLocation、UninstallStringを取得する。

    Args:
        name_contains: フィルタリング用の文字列。アプリケーション名にこの文字列が含まれるもののみを抽出する（大文字小文字は区別しない）。

    Returns:
        アプリケーション情報の辞書のリスト。DisplayNameで昇順ソートされている。

    Raises:
        BackendError: レジストリ処理中に予期せぬエラーが発生した場合。
    """
    import winreg
    
    # 走査対象のレジストリパスとルートキーの定義
    registry_targets = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
    ]
    
    # 64bit OSで動作している32bitプロセスのためのWow6432Node
    # 自身のアーキテクチャにかかわらず、両方を探索するためにWow6432Nodeも明示的に走査する
    registry_targets.append(
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall")
    )

    apps_dict: dict[str, dict[str, Any]] = {}

    def _get_registry_value(sub_key: Any, val_name: str) -> Any:
        try:
            val, _ = winreg.QueryValueEx(sub_key, val_name)
            return val
        except OSError:
            return None

    for root_key, sub_key_path in registry_targets:
        try:
            # winreg.KEY_READ | winreg.KEY_WOW64_64KEY を指定することで、
            # 32bit/64bitのレジストリビューリダイレクトを回避してアクセス
            access_mask = winreg.KEY_READ
            # Wow6432Nodeではない通常のキーにアクセスする際、64bitビューを明示的に指定
            if "Wow6432Node" not in sub_key_path:
                access_mask |= winreg.KEY_WOW64_64KEY
                
            with winreg.OpenKey(root_key, sub_key_path, 0, access_mask) as key:
                sub_keys_count, _, _ = winreg.QueryInfoKey(key)
                for i in range(sub_keys_count):
                    try:
                        sub_key_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub_key_name) as sub_key:
                            # DisplayNameが無いものはシステムパッチや内部コンポーネントである可能性が高いためスキップ
                            try:
                                name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                                if not name or not isinstance(name, str):
                                    continue
                            except OSError:
                                continue

                            # フィルタ条件がある場合、部分一致（大文字小文字無視）を確認
                            if name_contains and name_contains.lower() not in name.lower():
                                continue

                            # その他の情報を取得（存在しない場合はNone）
                            version = _get_registry_value(sub_key, "DisplayVersion")
                            publisher = _get_registry_value(sub_key, "Publisher")
                            install_location = _get_registry_value(sub_key, "InstallLocation")
                            uninstall_string = _get_registry_value(sub_key, "UninstallString")

                            # 重複はDisplayNameをキーとして排除。最初に見つかったものを優先し、上書きしない
                            if name not in apps_dict:
                                apps_dict[name] = {
                                    "name": name,
                                    "version": version,
                                    "publisher": publisher,
                                    "install_location": install_location,
                                    "uninstall_string": uninstall_string,
                                }
                    except OSError as e:
                        # 個別のサブキーの読み込み失敗はログ出力して継続（アクセス権限不足など）
                        logger.warning(f"レジストリサブキーの読み込みに失敗しました: {e}")
                        continue
        except OSError as e:
            # キー自体が存在しない場合や、アクセス権限エラーなどは警告ログを出力して処理を継続する
            logger.warning(f"レジストリキー {sub_key_path} のオープンに失敗しました: {e}")
            continue
        except Exception as e:
            logger.error(f"レジストリ走査中に予期しないエラーが発生しました: {e}")
            raise BackendError(f"インストール済みアプリケーションの取得に失敗しました: {str(e)}")

    # 表示名で昇順ソートしたリストを返却
    sorted_apps = sorted(apps_dict.values(), key=lambda x: x["name"].lower())
    return sorted_apps

