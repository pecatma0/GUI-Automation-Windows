import time
import os
import sys
import logging
from typing import Any, cast
import win32gui
import win32process
import win32con
import psutil
import pywinauto
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.controls.hwndwrapper import HwndWrapper

from gui_plugin.exceptions import (
    GUIPluginError,
    WindowNotFoundError,
    ElementNotFoundError,
    ElementDisabledError,
    ElementNotVisibleError,
    ActionNotSupportedError,
    TimeoutError,
    AccessDeniedError,
    BackendError,
    InvalidParamsError,
)
from gui_plugin.logger import logger
from gui_plugin.config import CONFIG

# UI要素を一時的にキャッシュして handle（整数キー）で操作できるようにする
# 実オブジェクトの参照ID (id()) をキーとして UIAWrapper を格納する
_element_cache: dict[int, UIAWrapper] = {}

def _register_element(element: UIAWrapper) -> int:
    """要素をキャッシュに登録し、一意のハンドル（整数ID）を返す。
    
    UI Automation 要素の多くは固有のHWNDを持たないため、
    PythonのオブジェクトIDを仮想ハンドルとして使用して一意特定可能にする意図。
    """
    element_id = id(element)
    _element_cache[element_id] = element
    return element_id

def _get_cached_element(element_id: int) -> UIAWrapper:
    """キャッシュから要素を取得する。存在しない場合はエラーとする。"""
    if element_id not in _element_cache:
        raise ElementNotFoundError(f"指定されたハンドル {element_id} の要素がキャッシュに見つかりません。再取得してください。")
    return _element_cache[element_id]

def get_windows(
    title_contains: str | None = None,
    process_name: str | None = None,
    visible_only: bool = True,
) -> list[dict[str, object]]:
    """起動中のウィンドウ一覧を取得する。
    
    操作対象アプリのハンドルを確認する際に最初に呼ぶ。
    """
    try:
        windows: list[dict[str, object]] = []

        def enum_windows_callback(hwnd: int, extra: object) -> bool:
            # 可視性チェック
            if visible_only and not win32gui.IsWindowVisible(hwnd):
                return True

            title = win32gui.GetWindowText(hwnd)
            # タイトルフィルタ
            if title_contains and title_contains not in title:
                return True

            # プロセスIDおよび名前の取得
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                proc_name = proc.name()
            except Exception:
                pid = 0
                proc_name = ""

            # プロセス名フィルタ
            if process_name and process_name.lower() not in proc_name.lower():
                return True

            # Rect取得
            rect = {"x": 0, "y": 0, "width": 0, "height": 0}
            if win32gui.IsWindow(hwnd):
                try:
                    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                    rect = {
                        "x": left,
                        "y": top,
                        "width": right - left,
                        "height": bottom - top,
                    }
                except Exception:
                    pass

            is_minimized = win32gui.IsIconic(hwnd) != 0

            windows.append({
                "title": title,
                "handle": hwnd,
                "process_id": pid,
                "process_name": proc_name,
                "visible": win32gui.IsWindowVisible(hwnd) != 0,
                "minimized": is_minimized,
                "rect": rect,
            })
            return True

        win32gui.EnumWindows(enum_windows_callback, None)
        return windows

    except Exception as e:
        logger.error(f"get_windows でエラーが発生しました: {str(e)}")
        raise BackendError(f"ウィンドウ一覧の取得中にエラーが発生しました: {str(e)}")


def focus_window(
    window_title: str | None = None,
    window_handle: int | None = None,
    restore_if_minimized: bool = True,
) -> dict[str, object]:
    """指定ウィンドウを最前面に移動してフォーカスを当てる。"""
    start_time = time.time()
    hwnd = window_handle

    if not hwnd and window_title:
        # タイトルから検索
        wins = get_windows(title_contains=window_title, visible_only=True)
        if not wins:
            raise WindowNotFoundError(f"タイトル '{window_title}' に一致する可視ウィンドウが見つかりません。")
        hwnd = cast(int, wins[0]["handle"])

    if not hwnd or not win32gui.IsWindow(hwnd):
        raise WindowNotFoundError(f"指定されたウィンドウハンドル {hwnd} は無効または存在しません。")

    try:
        # 最小化の復元
        if restore_if_minimized and win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.2)

        # 最前面表示とフォーカス
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(hwnd)
        
        # フォーカス完了を待機
        time.sleep(0.3)

        elapsed = int((time.time() - start_time) * 1000)
        return {
            "success": True,
            "action": "focus_window",
            "handle": hwnd,
            "elapsed_ms": elapsed,
            "error": None,
            "error_code": None,
            "state_after": None,
        }
    except Exception as e:
        logger.error(f"focus_window でエラーが発生しました (HWND={hwnd}): {str(e)}")
        raise AccessDeniedError(f"ウィンドウのフォーカスに失敗しました（管理者権限が必要な可能性があります）: {str(e)}")


def _serialize_element(element: UIAWrapper) -> dict[str, object]:
    """UIAWrapper要素を仕様書のJSON構造にシリアル化する。"""
    try:
        rect = element.rectangle()
        rect_dict = {
            "x": rect.left,
            "y": rect.top,
            "width": rect.width(),
            "height": rect.height(),
        }
    except Exception:
        rect_dict = {"x": 0, "y": 0, "width": 0, "height": 0}

    # 一意な仮想ハンドルを登録して取得する
    virtual_handle = _register_element(element)

    try:
        # control_type
        control_type = element.element_info.control_type
    except Exception:
        control_type = "Unknown"

    try:
        name = element.element_info.name or ""
    except Exception:
        name = ""

    try:
        automation_id = element.element_info.automation_id or ""
    except Exception:
        automation_id = ""

    try:
        class_name = element.element_info.class_name or ""
    except Exception:
        class_name = ""

    try:
        enabled = element.is_enabled()
    except Exception:
        enabled = False

    try:
        visible = element.is_visible()
    except Exception:
        visible = False

    # 現在の値 (Edit, ComboBoxなど)
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
        "rect": rect_dict,
        "value": value,
        "children": [],
    }


def _build_tree(element: UIAWrapper, current_depth: int, max_depth: int, include_invisible: bool) -> dict[str, object]:
    """再帰的に子要素を探索してツリーを構築する。"""
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
            child_node = _build_tree(child, current_depth + 1, max_depth, include_invisible)
            cast(list[dict[str, object]], node["children"]).append(child_node)
        except Exception:
            pass

    return node


def get_ui_tree(
    window_title: str | None = None,
    window_handle: int | None = None,
    process_name: str | None = None,
    depth: int = 3,
    include_invisible: bool = False,
) -> dict[str, object]:
    """指定ウィンドウの UI 要素ツリーを JSON で返す。"""
    if not (window_title or window_handle or process_name):
        raise InvalidParamsError("window_title, window_handle, process_name のいずれか一つを必ず指定してください。")

    hwnd = window_handle
    if not hwnd:
        wins = get_windows(title_contains=window_title, process_name=process_name, visible_only=True)
        if not wins:
            # 非表示含めて再検索
            wins = get_windows(title_contains=window_title, process_name=process_name, visible_only=False)
            if not wins:
                raise WindowNotFoundError("指定された条件のウィンドウが見つかりません。")
        hwnd = cast(int, wins[0]["handle"])

    try:
        # キャッシュのクリア（メモリリーク防止のため取得時に一度リセット）
        # ただし、操作中に再取得することもあるので、最新のツリーで再構成する
        _element_cache.clear()

        # pywinauto Application 接続
        app = pywinauto.Application(backend="uia").connect(handle=hwnd)
        root_window = app.window(handle=hwnd)
        
        # 接続が正しいか確認
        if not root_window.exists():
            raise WindowNotFoundError("指定ハンドルに対応するウィンドウが pywinauto から検出できませんでした。")

        # ウィンドウ情報のシリアライズ
        win_info = None
        for w in get_windows(visible_only=False):
            if w["handle"] == hwnd:
                win_info = w
                break

        tree_data = _build_tree(root_window, 0, depth, include_invisible)

        return {
            "window": win_info,
            "tree": tree_data
        }

    except Exception as e:
        logger.error(f"get_ui_tree でエラーが発生しました: {str(e)}")
        raise BackendError(f"UIツリーの取得に失敗しました: {str(e)}")


def find_element(
    window_title: str | None = None,
    window_handle: int | None = None,
    conditions: dict[str, object] = {},
    find_all: bool = False,
    timeout: float = 5.0,
) -> dict[str, object] | list[dict[str, object]]:
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

    start_time = time.time()
    
    # タイムアウトループ
    while True:
        try:
            # 要素ツリー全体を取得して走査する
            tree_response = get_ui_tree(window_handle=hwnd, depth=cast(int, conditions.get("depth", 5)), include_invisible=True)
            root_node = tree_response["tree"]
            
            matched_nodes: list[dict[str, object]] = []

            def traverse_and_match(node: dict[str, object]) -> None:
                # 一致判定
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

                # 子要素の走査
                for child in cast(list[dict[str, object]], node.get("children", [])):
                    traverse_and_match(child)

            traverse_and_match(cast(dict[str, object], root_node))

            if matched_nodes:
                if find_all:
                    return matched_nodes
                else:
                    return matched_nodes[0]

        except Exception as e:
            logger.warning(f"find_element 中の試行でエラー（再試行します）: {str(e)}")

        if time.time() - start_time > timeout:
            break
            
        time.sleep(0.5)

    raise ElementNotFoundError(f"条件 {conditions} に一致する要素がタイムアウト {timeout} 秒以内に見つかりませんでした。")


def do_action(
    handle: int | None = None,
    element: dict[str, object] | None = None,
    action: str = "",
    params: dict[str, object] = {},
    wait_after: float = 0.5,
    verify: dict[str, object] | None = None,
) -> dict[str, object]:
    """UI 要素に対して操作を実行する。"""
    start_time = time.time()
    
    target_handle = handle
    if not target_handle and element:
        target_handle = cast(int | None, element.get("handle"))

    if not target_handle:
        raise InvalidParamsError("handle または element のいずれかを指定してください。")

    # キャッシュから要素を取得
    uia_element = _get_cached_element(target_handle)

    # 操作前の可視・有効状態の検証
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
        # アクション実行
        if action == "click":
            x = cast(int, params.get("x_offset", 0))
            y = cast(int, params.get("y_offset", 0))
            if x != 0 or y != 0:
                uia_element.click_input(coords=(x, y))
            else:
                uia_element.click_input()
                
        elif action == "double_click":
            x = cast(int, params.get("x_offset", 0))
            y = cast(int, params.get("y_offset", 0))
            if x != 0 or y != 0:
                uia_element.double_click_input(coords=(x, y))
            else:
                uia_element.double_click_input()
                
        elif action == "right_click":
            x = cast(int, params.get("x_offset", 0))
            y = cast(int, params.get("y_offset", 0))
            if x != 0 or y != 0:
                uia_element.right_click_input(coords=(x, y))
            else:
                uia_element.right_click_input()

        elif action == "type_text":
            text = cast(str, params.get("text", ""))
            clear_first = cast(bool, params.get("clear_first", True))
            with_enter = cast(bool, params.get("with_enter", False))
            
            if clear_first:
                # テキストクリア
                uia_element.set_focus()
                uia_element.type_keys("^a{BACKSPACE}", set_foreground=False)
                
            # 入力
            if text:
                # 日本語などのIME入力も考慮して、type_keys(..., with_spaces=True)
                # type_keysの引数において、`%` `{` などの特殊文字がエスケープされているか確認されるため、
                # 直接テキストを送るための処理
                uia_element.type_keys(text, with_spaces=True, with_tabs=True, with_newlines=True, set_foreground=False)
            if with_enter:
                uia_element.type_keys("{ENTER}", set_foreground=False)

        elif action == "clear":
            uia_element.set_focus()
            uia_element.type_keys("^a{BACKSPACE}", set_foreground=False)

        elif action == "select":
            value = params.get("value")
            index = params.get("index")
            
            # ComboBox or ListBox
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
                # Clickで代用するか、例外
                raise ActionNotSupportedError("この要素は check アクションをサポートしていません。")

        elif action == "uncheck":
            if hasattr(uia_element, "uncheck"):
                uia_element.uncheck()
            else:
                raise ActionNotSupportedError("この要素は uncheck アクションをサポートしていません。")

        elif action == "scroll":
            direction = cast(str, params.get("direction", "down"))
            amount = cast(int, params.get("amount", 3))
            # pywinautoのscroll機能を利用
            # direction: up, down, left, right
            if hasattr(uia_element, "scroll"):
                # scrollメソッドを持つコントロール（例: ComboBoxやListBoxなど）
                # または、単純なマウスホイールエミュレーション
                # directionに応じたスクロール
                uia_element.scroll(direction=direction, amount=amount)
            else:
                # フォールバックとしてマウスホイール
                # pywinauto.mouse.scroll を使うことも可能
                raise ActionNotSupportedError("この要素は直接の scroll をサポートしていません。")

        elif action == "hover":
            # ホバー処理
            uia_element.move_mouse_input()
            duration = cast(float, params.get("duration", 0.0))
            if duration > 0:
                time.sleep(duration)

        elif action == "key_press":
            keys = cast(str, params.get("keys", ""))
            if not keys:
                raise InvalidParamsError("key_press アクションには keys パラメータが必要です。")
            uia_element.type_keys(keys, set_foreground=False)

        elif action == "invoke":
            # UIA Invoke Pattern の呼び出し
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
                # UIA value pattern
                # pywinautoでは直接の set_value メソッドがない場合もあるが、
                # uia_element.iface_value.SetValue(val) などを comtypes 経由で呼べる
                # ここでは安全のために型に応じてフォールバック
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

    # 指定された待機時間
    time.sleep(wait_after)

    # verify (検証ループ)
    state_after = None
    if verify:
        expect = verify.get("expect")
        timeout = cast(float, verify.get("timeout", 5.0))
        verify_start = time.time()
        verified = False
        
        while time.time() - verify_start < timeout:
            try:
                if expect == "element_appears":
                    # 指定されたcontrol_typeなどの要素が出現するか確認
                    # ウィンドウ内の要素を再検索する
                    # 検索条件を構築
                    conds = {
                        "control_type": verify.get("control_type"),
                        "name": verify.get("name"),
                        "name_contains": verify.get("name_contains"),
                        "visible": True
                    }
                    # Noneや未指定を取り除く
                    conds = {k: v for k, v in conds.items() if v is not None}
                    
                    try:
                        # find_elementに親ウィンドウなどの情報を引き継ぎたいが、
                        # 今回はキャッシュ全体の要素を走査するか、親ウィンドウを見つけて走査する。
                        # 操作対象要素(uia_element)のトップレベルウィンドウを取得する
                        top_window = uia_element.top_level_parent()
                        top_hwnd = top_window.handle
                        find_element(window_handle=top_hwnd, conditions=conds, timeout=0.1)
                        verified = True
                        break
                    except ElementNotFoundError:
                        pass
                        
                elif expect == "element_disappears":
                    # 要素が消えるまで待つ
                    try:
                        # is_visible() が False になるか、存在しなくなるか
                        if not uia_element.is_visible():
                            verified = True
                            break
                    except Exception:
                        # 存在しなくなると例外が発生するため、それも消滅とみなす
                        verified = True
                        break
                        
                elif expect == "value_changes":
                    # value値が変わるまで待つ
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
                    else:
                        # 単に変化したか
                        # 初期値が params にあれば、それと異なるか判定可能。
                        # ここでは簡易的に期待する値への変化をサポート
                        pass
                        
                elif expect == "window_closes":
                    # トップレベルウィンドウが閉じるまで待つ
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

        # verify成功時の最新状態を構築
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


def start_application(cmd_line: str, timeout: float = 5.0) -> dict[str, object]:
    """指定されたコマンドラインでプログラムを起動する。
    
    起動したプロセスのPIDおよびプロセス名を返却し、LLMがこれを記憶・追跡できるようにする意図。
    """
    if not cmd_line:
        raise InvalidParamsError("起動するコマンドライン(cmd_line)を指定してください。")
        
    start_time = time.time()
    try:
        import subprocess
        # 非同期でプロセスを起動
        proc = subprocess.Popen(cmd_line, shell=True)
        pid = proc.pid
        
        # プロセスが起動するまで少し待機し、psutilでプロセス情報を取得
        time.sleep(0.5)
        
        try:
            p = psutil.Process(pid)
            proc_name = p.name()
        except Exception:
            # cmd_lineの最初のワードからフォールバック名を取得
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

