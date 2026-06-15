"""Schemas for Hermes Agent GUI Automation plugin tools."""

GET_WINDOWS_SCHEMA = {
    "name": "get_windows",
    "description": "起動中のウィンドウ一覧を取得する。操作対象アプリのハンドルを確認する際に最初に呼ぶ。",
    "parameters": {
        "type": "object",
        "properties": {
            "title_contains": {
                "type": "string",
                "description": "ウィンドウタイトルの部分一致フィルタ（省略可）"
            },
            "process_name": {
                "type": "string",
                "description": "プロセス名フィルタ（例: notepad.exe）"
            }
        }
    }
}

FOCUS_WINDOW_SCHEMA = {
    "name": "focus_window",
    "description": "指定ウィンドウを最前面に移動してフォーカスを当てる。操作前に呼ぶことを推奨。",
    "parameters": {
        "type": "object",
        "properties": {
            "window_handle": {
                "type": "integer",
                "description": "ウィンドウハンドル"
            },
            "restore_if_minimized": {
                "type": "boolean",
                "description": "最小化されている場合に復元するか（デフォルト: true）",
                "default": True
            }
        }
    }
}

GET_UI_TREE_SCHEMA = {
    "name": "get_ui_tree",
    "description": "指定ウィンドウのUI要素ツリーをJSONで取得する。操作前に呼び出してUI構造を把握する。",
    "parameters": {
        "type": "object",
        "properties": {
            "window_title": {
                "type": "string",
                "description": "ウィンドウタイトル（部分一致）"
            },
            "window_handle": {
                "type": "integer",
                "description": "ウィンドウハンドル（get_windows で取得）"
            },
            "depth": {
                "type": "integer",
                "description": "取得階層の深さ（デフォルト3、最大10）",
                "default": 3
            }
        }
    }
}

FIND_ELEMENT_SCHEMA = {
    "name": "find_element",
    "description": "UI要素を条件で検索して返す。get_ui_tree でツリー構造を確認した後に、操作対象を特定する際に使う。",
    "parameters": {
        "type": "object",
        "properties": {
            "window_handle": {
                "type": "integer",
                "description": "ウィンドウハンドル"
            },
            "conditions": {
                "type": "object",
                "description": "検索条件（control_type, name, name_contains, automation_id 等）"
            },
            "find_all": {
                "type": "boolean",
                "description": "全件返却するか（デフォルト: false）",
                "default": False
            },
            "timeout": {
                "type": "number",
                "description": "要素出現待機秒数（デフォルト: 5.0）",
                "default": 5.0
            }
        },
        "required": ["conditions"]
    }
}

DO_ACTION_SCHEMA = {
    "name": "do_action",
    "description": "UI要素に対して操作（クリック・テキスト入力・選択等）を実行する。",
    "parameters": {
        "type": "object",
        "properties": {
            "handle": {
                "type": "integer",
                "description": "操作対象要素のハンドル（get_ui_tree または find_element で取得）"
            },
            "action": {
                "type": "string",
                "description": "アクション種別（click/double_click/right_click/type_text/select/check/uncheck/scroll/key_press/set_value 等）"
            },
            "params": {
                "type": "object",
                "description": "アクション固有パラメータ（type_text なら text と clear_first 等）"
            },
            "verify": {
                "type": "object",
                "description": "操作後の検証条件（省略可）"
            }
        },
        "required": ["handle", "action"]
    }
}

START_APPLICATION_SCHEMA = {
    "name": "start_application",
    "description": "指定されたコマンドラインでプログラムを起動する。起動したプロセスのIDとプロセス名を返す。",
    "parameters": {
        "type": "object",
        "properties": {
            "cmd_line": {
                "type": "string",
                "description": "起動するプログラムのコマンドライン（例: notepad.exe）"
            },
            "timeout": {
                "type": "number",
                "description": "起動待機秒数（デフォルト: 5.0）",
                "default": 5.0
            }
        },
        "required": ["cmd_line"]
    }
}
