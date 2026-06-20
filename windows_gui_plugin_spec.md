# Windows GUI 操作プラグイン仕様書

**対象エージェント:** Hermes Agent  
**対象OS:** 11  
**言語:** Python 3.13+  
**バージョン:** 1.0.0  

---

## 目次

1. [概要](#1-概要)
2. [アーキテクチャ](#2-アーキテクチャ)
3. [依存ライブラリ](#3-依存ライブラリ)
4. [ツール関数仕様](#4-ツール関数仕様)
   - 4.1 [get_ui_tree](#41-get_ui_tree)
   - 4.2 [find_element](#42-find_element)
   - 4.3 [do_action](#43-do_action)
   - 4.4 [get_windows](#44-get_windows)
   - 4.5 [focus_window](#45-focus_window)
   - 4.6 [start_application](#46-start_application)
   - 4.7 [get_installed_applications](#47-get_installed_applications)
5. [JSON スキーマ定義](#5-json-スキーマ定義)
   - 5.1 [UI ツリーノード](#51-ui-ツリーノード)
   - 5.2 [検索条件](#52-検索条件)
   - 5.3 [アクション](#53-アクション)
   - 5.4 [実行結果](#54-実行結果)
6. [アプリ種別対応マトリクス](#6-アプリ種別対応マトリクス)
7. [エラー定義](#7-エラー定義)
8. [実装ガイドライン](#8-実装ガイドライン)
9. [Hermes Agent へのツール登録](#9-hermes-agent-へのツール登録)
10. [利用例](#10-利用例)

---

## 1. 概要

本プラグインは Hermes Agent に Windows GUI 操作能力を付与する。  
スクリーンショットではなく **Windows UI Automation API** を通じて UI 要素を JSON として取得・操作することで、高精度かつ軽量な自動操作を実現する。

### 設計方針

- UI 要素は **JSON ツリー** として取得し、エージェントが構造を把握してから操作する
- バックエンドは `uia`（UI Automation）を基本とし、Win32 固有操作のみ `win32` にフォールバック
- Win32 / WPF / Electron / UWP の **混在環境に対応**
- 操作後の状態確認（検証ループ）を各アクション関数に内包し、エージェントが明示的に待機管理をしなくてよい設計とする

---

## 2. アーキテクチャ

```
┌─────────────────────────────────────────────┐
│              Hermes Agent                   │
│   タスク指示 → ツール呼び出し (JSON)          │
└────────────────────┬────────────────────────┘
                     │ ツール呼び出し
┌────────────────────▼────────────────────────┐
│          GUI Plugin Layer (Python)           │
│                                             │
│  get_ui_tree()  find_element()  do_action() │
│  get_windows()  focus_window()              │
└──────┬──────────────┬──────────────┬────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼────────┐
│ pywinauto   │ │comtypes/   │ │pygetwindow  │
│(win32/uia)  │ │uiautomation│ │             │
└──────┬──────┘ └─────┬──────┘ └────┬────────┘
       └──────────────┴─────────────┘
                     │
┌────────────────────▼────────────────────────┐
│         Windows OS                          │
│  IUIAutomation (Win32 / WPF / UWP / Electron│
└─────────────────────────────────────────────┘
```

### 処理フロー

```
Agent
  │
  ├─① get_windows()          ← 起動中アプリ一覧を取得
  │
  ├─② get_ui_tree(max_depth=2)   ← UI 構造を浅く把握
  │
  ├─③ find_element(...)      ← 操作対象要素を特定
  │
  ├─④ do_action(...)         ← 操作実行 + 結果検証
  │
  └─⑤ get_ui_tree(max_depth=1)  ← 操作後の状態確認
```

---

## 3. 依存ライブラリ

| ライブラリ | バージョン | 用途 |
|------------|-----------|------|
| `pywinauto` | >= 0.6.8 | UI Automation / Win32 操作の主軸 |
| `comtypes` | >= 1.2.0 | IUIAutomation COM インターフェース直接利用 |
| `pygetwindow` | >= 0.0.9 | ウィンドウ一覧・フォーカス管理 |
| `pywin32` | >= 306 | Win32 API 補完 |

インストール:

```bash
pip install pywinauto comtypes pygetwindow pywin32
```

---

## 4. ツール関数仕様

### 4.1 `get_ui_tree`

指定ウィンドウの UI 要素ツリーを JSON で返す。

**シグネチャ:**

```python
def get_ui_tree(
    window_title: str | None = None,
    window_handle: int | None = None,
    process_name: str | None = None,
    element_handle: int | None = None,
    min_depth: int = 0,
    max_depth: int = 3,
    include_invisible: bool = False,
) -> dict
```

**パラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|------------|-----|------|------|
| `window_title` | str | ※1 | ウィンドウタイトル（部分一致） |
| `window_handle` | int | ※1 | ウィンドウハンドル（HWND） |
| `process_name` | str | ※1 | プロセス名（例: `notepad.exe`） |
| `element_handle` | int | - | 開始要素のハンドル（指定時はウィンドウ探索を行わずその要素から開始） |
| `min_depth` | int | - | シリアライズを開始する最小階層（デフォルト: 0） |
| `max_depth` | int | - | 取得する階層の最大深さ（デフォルト: 3、最大: 10） |
| `include_invisible` | bool | - | 非表示要素を含めるか（デフォルト: false） |

※1: `window_title` / `window_handle` / `process_name` / `element_handle` のいずれか一つを指定すること。

**返却値:** [UI ツリーノード](#51-ui-ツリーノード) を参照

---

### 4.2 `find_element`

検索条件に一致する UI 要素を返す。

**シグネチャ:**

```python
def find_element(
    window_title: str | None = None,
    window_handle: int | None = None,
    conditions: dict,
    find_all: bool = False,
    timeout: float = 5.0,
) -> dict | list[dict]
```

**パラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|------------|-----|------|------|
| `window_title` | str | ※1 | ウィンドウタイトル |
| `window_handle` | int | ※1 | ウィンドウハンドル |
| `conditions` | dict | ✓ | 検索条件（[検索条件](#52-検索条件) 参照） |
| `find_all` | bool | - | 全件返却するか（デフォルト: false = 先頭1件） |
| `timeout` | float | - | 要素出現待機秒数（デフォルト: 5.0） |

※1: `window_title` / `window_handle` のいずれか一つを指定すること。

**返却値:** [UI ツリーノード](#51-ui-ツリーノード)（`find_all=true` の場合はリスト）

---

### 4.3 `do_action`

UI 要素に対して操作を実行する。

**シグネチャ:**

```python
def do_action(
    handle: int | None = None,
    element: dict | None = None,
    action: str,
    params: dict = {},
    wait_after: float = 0.5,
    verify: dict | None = None,
) -> dict
```

**パラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|------------|-----|------|------|
| `handle` | int | ※1 | 要素のオートメーションハンドル |
| `element` | dict | ※1 | `find_element` の返却値をそのまま渡す |
| `action` | str | ✓ | アクション種別（[アクション一覧](#アクション一覧) 参照） |
| `params` | dict | - | アクション固有パラメータ |
| `wait_after` | float | - | 操作後の待機秒数（デフォルト: 0.5） |
| `verify` | dict | - | 操作後検証条件（[実行結果](#54-実行結果) 参照） |

※1: `handle` または `element` のいずれか一つを指定すること。

**返却値:** [実行結果](#54-実行結果) を参照

#### アクション一覧

| アクション | 説明 | 主な params |
|------------|------|------------|
| `click` | 左クリック | `x_offset`, `y_offset` |
| `double_click` | ダブルクリック | `x_offset`, `y_offset` |
| `right_click` | 右クリック | `x_offset`, `y_offset` |
| `type_text` | テキスト入力 | `text`, `clear_first` |
| `clear` | テキストクリア | - |
| `select` | ドロップダウン選択 | `value` または `index` |
| `check` | チェックボックスをオン | - |
| `uncheck` | チェックボックスをオフ | - |
| `scroll` | スクロール | `direction`, `amount` |
| `hover` | ホバー | `duration` |
| `key_press` | キー入力 | `keys`（例: `"ctrl+s"`） |
| `invoke` | UIA Invoke パターン | - |
| `expand` | ツリー/ドロップダウン展開 | - |
| `collapse` | ツリー/ドロップダウン折畳 | - |
| `set_value` | 値の直接設定 | `value` |

---

### 4.4 `get_windows`

起動中のウィンドウ一覧を返す。

**シグネチャ:**

```python
def get_windows(
    title_contains: str | None = None,
    process_name: str | None = None,
    visible_only: bool = True,
) -> list[dict]
```

**返却値の各要素:**

```json
{
  "title": "メモ帳 - 無題",
  "handle": 12345,
  "process_id": 6789,
  "process_name": "notepad.exe",
  "visible": true,
  "minimized": false
}
```

---

### 4.5 `focus_window`

指定ウィンドウを最前面に移動してフォーカスを当てる。

**シグネチャ:**

```python
def focus_window(
    window_title: str | None = None,
    window_handle: int | None = None,
    restore_if_minimized: bool = True,
) -> dict
```

**返却値:** [実行結果](#54-実行結果) を参照

---

### 4.6 `start_application`

指定されたコマンドラインでプログラムを起動する。

**シグネチャ:**

```python
def start_application(
    cmd_line: str,
    timeout: float = 5.0,
) -> dict
```

**パラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|------------|-----|------|------|
| `cmd_line` | str | ✓ | 起動するプログラムのコマンドライン（例: `notepad.exe`） |
| `timeout` | float | - | 起動待機秒数（デフォルト: 5.0） |

**返却値:**
```json
{
  "success": true,
  "action": "start_application",
  "process_id": 12345,
  "process_name": "notepad.exe",
  "elapsed_ms": 500,
  "error": null,
  "error_code": null
}
```

---

### 4.7 `get_installed_applications`

Windowsにインストールされているアプリケーション（プログラム）の一覧を取得する。

**シグネチャ:**

```python
def get_installed_applications(
    name_contains: str | None = None,
) -> list[dict]
```

**パラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|------------|-----|------|------|
| `name_contains` | str | - | アプリケーション名の部分一致フィルタ（大文字・小文字を区別しない、省略可） |

**返却値の各要素:**

```json
{
  "name": "Python 3.10.5 (64-bit)",
  "version": "3.10.5",
  "publisher": "Python Software Foundation",
  "install_location": "C:\\Program Files\\Python310",
  "uninstall_string": "C:\\Program Files\\Python310\\uninstall.exe"
}
```

---

## 5. JSON スキーマ定義

### 5.1 UI ツリーノード

`get_ui_tree` および `find_element` の返却形式。
※ `get_ui_tree` の返却値には `rect` は含まれません。`find_element` で要素を取得した時のみ `rect` が付与されます。

```json
{
  "window": {
    "title": "メモ帳 - 無題",
    "handle": 12345,
    "process_id": 6789,
    "process_name": "notepad.exe",
    "rect": { "x": 100, "y": 50, "width": 800, "height": 600 }
  },
  "tree": {
    "control_type": "Window",
    "name": "メモ帳 - 無題",
    "automation_id": "",
    "class_name": "Notepad",
    "handle": 12345,
    "enabled": true,
    "visible": true,
    "value": null,
    "children": [
      {
        "control_type": "MenuBar",
        "name": "アプリケーション",
        "automation_id": "",
        "class_name": "MenuBar",
        "handle": 12346,
        "enabled": true,
        "visible": true,
        "value": null,
        "children": [
          {
            "control_type": "MenuItem",
            "name": "ファイル(F)",
            "automation_id": "",
            "class_name": "",
            "handle": 12347,
            "enabled": true,
            "visible": true,
            "value": null,
            "children": []
          }
        ]
      },
      {
        "control_type": "Edit",
        "name": "テキストエディター",
        "automation_id": "15",
        "class_name": "Edit",
        "handle": 12348,
        "enabled": true,
        "visible": true,
        "value": "現在のテキスト内容",
        "children": []
      }
    ]
  }
}
```

#### フィールド定義

| フィールド | 型 | 説明 |
|------------|-----|------|
| `control_type` | string | UI Automation コントロール種別 |
| `name` | string | 要素名（アクセシビリティ名） |
| `automation_id` | string | AutomationId（空文字あり） |
| `class_name` | string | Win32 クラス名 |
| `handle` | int | 要素の内部ハンドル（操作時に使用） |
| `enabled` | bool | 操作可能かどうか |
| `visible` | bool | 表示されているかどうか |
| `rect` | object | 画面座標（x, y, width, height）※`find_element`でのみ返却される |
| `value` | string\|null | 現在の値（Edit, ComboBox 等） |
| `children` | array | 子要素リスト |

#### 主な control_type 一覧

| control_type | 説明 |
|--------------|------|
| `Window` | ウィンドウ |
| `Button` | ボタン |
| `Edit` | テキスト入力欄 |
| `CheckBox` | チェックボックス |
| `RadioButton` | ラジオボタン |
| `ComboBox` | ドロップダウン |
| `ListBox` | リストボックス |
| `ListItem` | リスト項目 |
| `MenuItem` | メニュー項目 |
| `MenuBar` | メニューバー |
| `ToolBar` | ツールバー |
| `Tab` | タブコントロール |
| `TabItem` | タブ項目 |
| `TreeItem` | ツリー項目 |
| `DataGrid` | データグリッド |
| `Document` | ドキュメント（リッチエディタ等） |
| `Pane` | ペイン |
| `Group` | グループ |
| `Text` | ラベル |
| `StatusBar` | ステータスバー |

---

### 5.2 検索条件

`find_element` の `conditions` パラメータ形式。

```json
{
  "control_type": "Button",
  "name": "OK",
  "name_contains": "OK",
  "automation_id": "btn_ok",
  "class_name": "Button",
  "enabled": true,
  "visible": true,
  "depth": 5
}
```

#### フィールド定義

| フィールド | 型 | 説明 |
|------------|-----|------|
| `control_type` | string | コントロール種別で絞り込み |
| `name` | string | 名前で完全一致 |
| `name_contains` | string | 名前で部分一致 |
| `automation_id` | string | AutomationId で完全一致 |
| `class_name` | string | Win32 クラス名で一致 |
| `enabled` | bool | 操作可能状態で絞り込み |
| `visible` | bool | 表示状態で絞り込み |
| `depth` | int | 探索する階層の深さ上限（デフォルト: 5） |

> 複数フィールドを指定した場合は **AND 条件** で絞り込む。

---

### 5.3 アクション

`do_action` の `params` フィールドの各アクション別定義。

#### `click` / `double_click` / `right_click`

```json
{
  "x_offset": 0,
  "y_offset": 0
}
```

- `x_offset`, `y_offset`: 要素中心からのピクセルオフセット（省略時は中心をクリック）

#### `type_text`

```json
{
  "text": "入力するテキスト",
  "clear_first": true,
  "with_enter": false
}
```

#### `select`

```json
{
  "value": "選択肢のテキスト",
  "index": 0
}
```

- `value` または `index` のいずれかを指定（`value` 優先）

#### `scroll`

```json
{
  "direction": "down",
  "amount": 3
}
```

- `direction`: `"up"` / `"down"` / `"left"` / `"right"`
- `amount`: スクロール量（ホイール単位、デフォルト: 3）

#### `key_press`

```json
{
  "keys": "ctrl+s"
}
```

- `keys`: キーの組み合わせ文字列（例: `"ctrl+c"`, `"alt+F4"`, `"enter"`, `"tab"`）

#### `set_value`

```json
{
  "value": "設定する値"
}
```

---

### 5.4 実行結果

`do_action` / `focus_window` の返却形式。

```json
{
  "success": true,
  "action": "click",
  "handle": 12348,
  "elapsed_ms": 120,
  "error": null,
  "error_code": null,
  "state_after": {
    "control_type": "Button",
    "name": "OK",
    "enabled": true,
    "visible": false
  }
}
```

#### フィールド定義

| フィールド | 型 | 説明 |
|------------|-----|------|
| `success` | bool | 操作が成功したか |
| `action` | string | 実行したアクション名 |
| `handle` | int | 操作対象のハンドル |
| `elapsed_ms` | int | 処理時間（ミリ秒） |
| `error` | string\|null | エラーメッセージ（成功時は null） |
| `error_code` | string\|null | エラーコード（[エラー定義](#7-エラー定義) 参照） |
| `state_after` | object\|null | 操作後の要素状態（`verify` 指定時のみ） |

---

## 6. アプリ種別対応マトリクス

| アプリ種別 | バックエンド | UI ツリー取得 | 操作可否 | 備考 |
|------------|------------|--------------|---------|------|
| Win32（メモ帳・電卓等） | `win32` / `uia` | ◎ 完全 | ◎ | 最も安定 |
| WPF / .NET | `uia` | ◎ 完全 | ◎ | AutomationId が豊富 |
| MFC | `win32` | ○ 概ね取得可 | ○ | 一部 ID 不明 |
| Electron | `uia` | △ 限定的 | △ | 主要コントロールのみ |
| UWP | `uia` (COM直接) | ○ | ○ | UAC 権限が必要な場合あり |
| Java Swing | `uia` | △ | △ | Java Access Bridge 要インストール |

### バックエンド選択ロジック

```python
def select_backend(window_class: str) -> str:
    uia_only = ["WpfFramework", "Chrome_WidgetWin", "Windows.UI"]
    if any(c in window_class for c in uia_only):
        return "uia"
    return "uia"  # 原則 uia を使用、失敗時のみ win32 へフォールバック
```

---

## 7. エラー定義

| エラーコード | 説明 | 対処 |
|-------------|------|------|
| `WINDOW_NOT_FOUND` | 指定ウィンドウが見つからない | `get_windows()` で存在確認 |
| `ELEMENT_NOT_FOUND` | 指定要素が見つからない | `depth` を増やす、条件を緩める |
| `ELEMENT_DISABLED` | 要素が無効状態 | 前提条件を確認してから再試行 |
| `ELEMENT_NOT_VISIBLE` | 要素が非表示 | スクロールや画面遷移を確認 |
| `ACTION_NOT_SUPPORTED` | 要素がそのアクションに非対応 | 別の `action` を試す |
| `TIMEOUT` | 待機タイムアウト | `timeout` 値を増やす |
| `ACCESS_DENIED` | OS 権限不足 | 管理者権限で実行 |
| `BACKEND_ERROR` | pywinauto 内部エラー | バックエンドを切り替えて再試行 |
| `INVALID_PARAMS` | パラメータ不正 | スキーマを確認 |

---

## 8. 実装ガイドライン

### 深さ制御の方針

全ツリー取得はノード数が数百規模になる場合があるため、エージェントには以下の2段階を使い分けさせる。

```python
# Step 1: まず浅く構造を把握
get_ui_tree(window_title="メモ帳", max_depth=2)

# Step 2: 操作対象が深い場合に深掘り
get_ui_tree(window_title="メモ帳", max_depth=5)
```

深さの目安:

| max_depth | 用途 |
|-------|------|
| 1〜2 | ウィンドウ直下の主要コントロール把握 |
| 3〜4 | フォーム内の入力欄・ボタン特定（標準的な用途） |
| 5〜7 | 深くネストされたツリービュー・グリッド操作 |
| 8〜10 | 複雑な IDE・ドキュメントエディタ（低速注意） |

### 待機・検証の組み込み

操作後に即次の操作をすると状態変化が追いつかないため、アクション関数内に検証ループを内包する。

```python
# ダイアログ出現を待機してから次の操作へ
do_action(
    handle=12347,
    action="click",
    verify={
        "expect": "element_appears",
        "control_type": "Dialog",
        "timeout": 5.0
    }
)
```

#### `verify` パラメータ

| `expect` 値 | 意味 |
|-------------|------|
| `element_appears` | 指定 control_type の要素が出現するまで待つ |
| `element_disappears` | 指定要素が消えるまで待つ |
| `value_changes` | 操作対象の `value` が変化するまで待つ |
| `window_closes` | ウィンドウが閉じるまで待つ |

### テキスト入力の注意点

- 日本語 IME を使用するアプリでは `type_text` の `text` に直接日本語文字列を渡してよい（`set_value` の方が安定する場合あり）
- パスワード欄は `value` が返却されない仕様（セキュリティ上の制約）
- `clear_first: true` を指定しないと既存テキストに追記される

### Electron / UWP の制限事項

- Electron アプリは内部が Chromium DOM のため、UI Automation で取得できる要素は最外層コントロールのみとなる場合がある
- その場合はブラウザプラグイン（既存機能）を使用すること
- UWP アプリは UAC 昇格が必要な場合があり、`ACCESS_DENIED` エラー時は管理者権限での実行を要求する

---

## 9. Hermes Agent へのツール登録

Hermes Agent のツール登録形式に合わせた定義例。

```python
GUI_PLUGIN_TOOLS = [
    {
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
    },
    {
        "name": "get_ui_tree",
        "description": (
            "指定ウィンドウのUI要素ツリーをJSONで取得する。"
            "操作前に呼び出してUI構造を把握する。depth=2〜3から始め、"
            "必要に応じて深くする。"
        ),
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
    },
    {
        "name": "find_element",
        "description": (
            "UI要素を条件で検索して返す。"
            "get_ui_tree でツリー構造を確認した後に、操作対象を特定する際に使う。"
        ),
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
    },
    {
        "name": "do_action",
        "description": (
            "UI要素に対して操作（クリック・テキスト入力・選択等）を実行する。"
            "操作後の結果（success/error）を返すので、失敗時はエラーコードを確認して対処する。"
        ),
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
    },
    {
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
    },
    {
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
    },
    {
        "name": "get_installed_applications",
        "description": "インストール済みのアプリケーション一覧を取得する。アプリ名で部分一致検索することも可能。",
        "parameters": {
            "type": "object",
            "properties": {
                "name_contains": {
                    "type": "string",
                    "description": "アプリケーション名の部分一致フィルタ（大文字・小文字を区別しない、省略可）"
                }
            }
        }
    }
]
```

---

## 10. 利用例

### 例 1: メモ帳にテキストを入力して保存する

```
Agent の操作手順:

1. get_windows(title_contains="メモ帳")
   → handle: 12345 を取得

2. focus_window(window_handle=12345)

3. get_ui_tree(window_handle=12345, max_depth=3)
   → Edit コントロール（handle: 12348）を確認

4. do_action(handle=12348, action="click")

5. do_action(handle=12348, action="type_text",
             params={"text": "Hello World", "clear_first": true})

6. do_action(handle=12345, action="key_press",
             params={"keys": "ctrl+s"})

7. find_element(window_handle=12345,
               conditions={"control_type": "Dialog"},
               timeout=3.0)
   → 「名前を付けて保存」ダイアログ（handle: 20000）を取得

8. find_element(window_handle=20000,
               conditions={"control_type": "Edit", "name_contains": "ファイル名"})
   → ファイル名入力欄（handle: 20001）を取得

9. do_action(handle=20001, action="type_text",
             params={"text": "test.txt", "clear_first": true})

10. find_element(window_handle=20000,
                conditions={"control_type": "Button", "name": "保存(S)"})
    → 保存ボタン（handle: 20002）を取得

11. do_action(handle=20002, action="click",
              verify={"expect": "window_closes", "timeout": 5.0})
```

### 例 2: アプリのメニューを操作する

```
1. get_ui_tree(window_handle=..., max_depth=2)
   → MenuBar 直下の MenuItem を確認

2. find_element(window_handle=...,
               conditions={"control_type": "MenuItem", "name_contains": "編集"})

3. do_action(handle=..., action="click",
             verify={"expect": "element_appears",
                     "control_type": "Menu", "timeout": 2.0})
   → サブメニューが展開されるまで待機

4. find_element(window_handle=...,
               conditions={"control_type": "MenuItem", "name": "すべて選択(A)"})

5. do_action(handle=..., action="click")
```

---

*本仕様書は Hermes Agent GUI Plugin v1.0.0 に対応する。*
