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
- **Hermes Agent:** v0.16.0 (2026.6.5)
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

## hermesへプラグインとしてのセットアップ手順

## 1. gui-automation フォルダをコピー
`hermes` の `plugins` フォルダへ `gui_plugin` フォルダをコピーします。
**コピー先**
```text
C:\Users\<UserName>\AppData\Local\hermes\plugins
```
---

## 2. 仮想環境の作成（未作成の場合）
`hermes-agent` 配下に仮想環境 (`venv`) が存在しない場合は作成します。
**作業ディレクトリ**
```text
C:\Users\<UserName>\AppData\Local\hermes\hermes-agent
```

**実行コマンド**
```bash
python3 -m venv venv
```
---

## 3. 仮想環境へ pip をインストール
以下のコマンドを実行して、仮想環境内に `pip` をインストールします。
```bash
C:\Users\<UserName>\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe -m ensurepip
```
---

## 4. 必要なライブラリをインストール
以下のコマンドを実行します。
```bash
C:\Users\<UserName>\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe -m pip install pywinauto comtypes pygetwindow pywin32 psutil
```
---

## 5. プラグインを有効化
以下の設定ファイルを編集します。
**設定ファイル**
```text
C:\Users\<UserName>\AppData\Local\hermes\config.yaml
```
**追記内容**
```yaml
plugins:
  enabled:
    - gui-automation
  disabled: []
```
---

## 6. 有効化確認
`hermes` を起動し、以下のコマンドを実行します。
```text
/ plugins
```
`gui-automation` プラグインが表示されていれば、有効化は完了です。


## 任意作業
プログラム検索でget_installed_applicationsを利用しない場合が有った為、利用する様にメモリに追加
```text
C:\Users\inaga\AppData\Local\hermes\memories
```
### MEMORY.md
```MD
To start an installed Windows application via Hermes: use get_installed_applications with name_contains to find the install location, then use search_files to locate the executable (e.g., pattern '*.exe'), and finally call start_application with cmd_line set to the full path to the executable.
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
py -m unittest tests/test_plugin.py
```
