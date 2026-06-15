# Windows GUI Automation Plugin for Hermes Agent

Hermes Agent に Windows GUI 操作能力を付与するためのプラグインです。
スクリーンショットによる画像認識ではなく、**Windows UI Automation API** を通じて UI 要素を JSON として取得・操作し、高精度かつ軽量な自動操作を実現します。

## 主な機能

- プログラムの起動 (`start_application`) とプロセスID (PID) の取得・記憶
- 起動中ウィンドウ一覧の取得 (`get_windows`) とフォーカス制御 (`focus_window`)
- ウィンドウ内の UI 要素ツリーの取得 (`get_ui_tree`) と条件検索 (`find_element`)
- クリック、テキスト入力、選択、キー入力などの要素操作 (`do_action`)
- 操作後の UI 状態変化の検証ループ (`verify`) 内包

---

## 動作要件

- **OS:** Windows 10 / 11
- **Python:** 3.13+
- **依存ライブラリ:**
  - `pywinauto` >= 0.6.8
  - `comtypes` >= 1.2.0
  - `pygetwindow` >= 0.0.9
  - `pywin32` >= 306
  - `psutil` >= 5.9.0
  - `python-dotenv` >= 1.0.0

---

## セットアップ手順

1. **仮想環境の作成**
   ```bash
   py -3.13 -m venv .venv
   ```

2. **依存パッケージのインストール**
   ```bash
   .venv\Scripts\pip install -r requirements.txt
   ```

3. **設定ファイル (`.env`) の配置**
   プロジェクトルートに `.env` ファイルを作成し、必要な定数を定義します（パッケージ内にサンプルあり）。
   ```env
   DEFAULT_TIMEOUT=5.0
   DEFAULT_WAIT_AFTER=0.5
   LOG_FILE_PATH=gui_plugin.log
   ```

---

## 主要 API ツール一覧

詳細は [Windows GUI 操作プラグイン仕様書](windows_gui_plugin_spec.md) をご参照ください。

### 1. `start_application`
コマンドラインからアプリを起動し、起動したプロセスの情報を返します。
```python
import gui_plugin
result = gui_plugin.start_application("notepad.exe")
print(result)
# 出力例: {'success': True, 'action': 'start_application', 'process_id': 12345, 'process_name': 'notepad.exe', ...}
```

### 2. `get_windows`
起動中のウィンドウ一覧を取得します。
```python
windows = gui_plugin.get_windows(title_contains="メモ帳")
```

### 3. `focus_window`
指定したウィンドウを最前面に表示してフォーカスを当てます。
```python
gui_plugin.focus_window(window_handle=12345)
```

### 4. `get_ui_tree`
指定ウィンドウの UI 要素ツリーを JSON 形式で再帰的に取得します。
```python
tree = gui_plugin.get_ui_tree(window_handle=12345, depth=3)
```

### 5. `find_element`
指定した条件（`control_type`, `automation_id` など）に合致する UI 要素を検索します。
```python
element = gui_plugin.find_element(
    window_handle=12345,
    conditions={"control_type": "Edit", "automation_id": "15"}
)
```

### 6. `do_action`
UI 要素に対してクリックやテキスト入力などの操作を実行します。
```python
gui_plugin.do_action(
    handle=element["handle"],
    action="type_text",
    params={"text": "Hello World", "clear_first": True}
)
```

---

## テストの実行方法

本プロジェクトは OS 依存処理をモック化してテスト可能なユニットテストを含んでいます。

```bash
.venv\Scripts\python -m unittest discover -s tests -p "test_*.py"
```

---

## Hermes Agent Desktop への取り込み（MCP サーバー）

本プラグインは MCP (Model Context Protocol) サーバーとして動作するため、Hermes Agent Desktop に登録して GUI 操作ツールとして利用できます。

### 1. 登録手順
1. Hermes Agent Desktop を起動します。
2. 設定画面（Settings）または設定ファイル（`config.json` / `hermes.json` など）の MCP サーバー設定箇所を開きます。
3. 新しい MCP サーバーを追加し、以下の起動コマンドと引数を設定します。

**設定例 (JSON形式の場合):**
```json
{
  "mcpServers": {
    "windows-gui-automation": {
      "command": "C:\\Antigravity\\GUI-Automation-Windows\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "gui_plugin.mcp_server"
      ],
      "env": {
        "PYTHONPATH": "C:\\Antigravity\\GUI-Automation-Windows"
      }
    }
  }
}
```
※ `command` や `PYTHONPATH` には本プロジェクトを配置した環境の実パスを適宜指定してください。

### 2. 手動での起動テスト
動作確認のために、コマンドラインから直接起動することも可能です：
```bash
.venv\Scripts\python -m gui_plugin.mcp_server
```
起動すると、標準入出力を通じた MCP プロトコル待ち受け状態になります。
