"""MCP (Model Context Protocol) サーバー実装。

Hermes Agent Desktop などの MCP クライアントから本プラグインの GUI 操作ツールを
呼び出せるようにするためのインターフェースを提供します。
"""

import os
import sys
from mcp.server.fastmcp import FastMCP
import gui_plugin

# FastMCP インスタンスの初期化
mcp = FastMCP("Windows GUI Automation")


@mcp.tool()
def get_windows(
    title_contains: str | None = None,
    process_name: str | None = None,
    visible_only: bool = True,
) -> list[dict]:
    """起動中のウィンドウ一覧を取得する。

    操作対象アプリのハンドル（HWND）を確認する際に最初に呼び出す。

    Args:
        title_contains: ウィンドウタイトルの部分一致フィルタ（省略可）
        process_name: プロセス名フィルタ（例: 'notepad.exe'）
        visible_only: 表示中のウィンドウのみ取得するか（デフォルト: True）
    """
    return gui_plugin.get_windows(
        title_contains=title_contains,
        process_name=process_name,
        visible_only=visible_only,
    )


@mcp.tool()
def focus_window(
    window_title: str | None = None,
    window_handle: int | None = None,
    restore_if_minimized: bool = True,
) -> dict:
    """指定ウィンドウを最前面に移動してフォーカスを当てる。

    Args:
        window_title: ウィンドウタイトル（部分一致）
        window_handle: ウィンドウハンドル（HWND）
        restore_if_minimized: 最小化されている場合に復元するか（デフォルト: True）
    """
    return gui_plugin.focus_window(
        window_title=window_title,
        window_handle=window_handle,
        restore_if_minimized=restore_if_minimized,
    )


@mcp.tool()
def get_ui_tree(
    window_title: str | None = None,
    window_handle: int | None = None,
    process_name: str | None = None,
    depth: int = 3,
    include_invisible: bool = False,
) -> dict:
    """指定ウィンドウの UI 要素ツリーを JSON で取得する。

    Args:
        window_title: ウィンドウタイトル（部分一致）
        window_handle: ウィンドウハンドル
        process_name: プロセス名（例: 'notepad.exe'）
        depth: 取得する階層の深さ（デフォルト: 3、最大: 10）
        include_invisible: 非表示の要素も含めるか（デフォルト: False）
    """
    return gui_plugin.get_ui_tree(
        window_title=window_title,
        window_handle=window_handle,
        process_name=process_name,
        depth=depth,
        include_invisible=include_invisible,
    )


@mcp.tool()
def find_element(
    window_title: str | None = None,
    window_handle: int | None = None,
    conditions: dict | None = None,
    find_all: bool = False,
    timeout: float = 5.0,
) -> dict | list[dict]:
    """検索条件に一致する UI 要素を返す。

    Args:
        window_title: ウィンドウタイトル
        window_handle: ウィンドウハンドル
        conditions: 検索条件（control_type, name, name_contains, automation_id など）
        find_all: 全件返却するか（デフォルト: False）
        timeout: 要素出現待機秒数（デフォルト: 5.0）
    """
    if conditions is None:
        conditions = {}
    return gui_plugin.find_element(
        window_title=window_title,
        window_handle=window_handle,
        conditions=conditions,
        find_all=find_all,
        timeout=timeout,
    )


@mcp.tool()
def do_action(
    handle: int | None = None,
    element: dict | None = None,
    action: str = "",
    params: dict | None = None,
    wait_after: float = 0.5,
    verify: dict | None = None,
) -> dict:
    """UI 要素に対してクリック、テキスト入力、キー入力などの操作を実行する。

    Args:
        handle: 要素のオートメーションハンドル (get_ui_tree等で得られる仮想ハンドル)
        element: find_element の返却値をそのまま渡すことも可能
        action: アクション種別（click, double_click, type_text, key_press 等）
        params: アクション固有パラメータ（text, keys 等）
        wait_after: 操作後の待機秒数（デフォルト: 0.5）
        verify: 操作後検証条件（expect, timeout 等）
    """
    if params is None:
        params = {}
    return gui_plugin.do_action(
        handle=handle,
        element=element,
        action=action,
        params=params,
        wait_after=wait_after,
        verify=verify,
    )


@mcp.tool()
def start_application(
    cmd_line: str,
    timeout: float = 5.0,
) -> dict:
    """指定されたコマンドラインでプログラムを起動する。

    Args:
        cmd_line: 起動するプログラムのコマンドライン（例: 'notepad.exe'）
        timeout: 起動待機秒数（デフォルト: 5.0）
    """
    return gui_plugin.start_application(
        cmd_line=cmd_line,
        timeout=timeout,
    )


if __name__ == "__main__":
    mcp.run()
