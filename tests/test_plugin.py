import unittest
from unittest.mock import MagicMock, patch
import os
import sys
from typing import Any, cast

# Ensure test target can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import (
    WindowNotFoundError,
    ElementNotFoundError,
    InvalidParamsError,
    get_windows,
    focus_window,
    get_ui_tree,
    start_application,
)

class TestGUIPlugin(unittest.TestCase):
    """GUI操作プラグインのユニットテストクラス。"""

    @patch("win32gui.IsWindow")
    @patch("win32gui.EnumWindows")
    @patch("win32gui.IsWindowVisible")
    @patch("win32gui.GetWindowText")
    @patch("win32process.GetWindowThreadProcessId")
    @patch("psutil.Process")
    @patch("win32gui.GetWindowRect")
    def test_get_windows_success(
        self,
        mock_get_rect: MagicMock,
        mock_process: MagicMock,
        mock_get_thread_pid: MagicMock,
        mock_get_text: MagicMock,
        mock_is_visible: MagicMock,
        mock_enum_windows: MagicMock,
        mock_is_window: MagicMock,
    ) -> None:
        """起動中のウィンドウ一覧取得が正常に動作することを検証する。"""
        mock_is_window.return_value = True
        mock_is_visible.return_value = True
        mock_get_text.return_value = "テストメモ帳"
        mock_get_thread_pid.return_value = (0, 1234)
        
        mock_proc_instance = MagicMock()
        mock_proc_instance.name.return_value = "notepad.exe"
        mock_process.return_value = mock_proc_instance
        
        mock_get_rect.return_value = (10, 10, 110, 110)

        # EnumWindowsがコールバックを呼び出すように擬似実装
        def enum_impl(callback: object, extra: object) -> None:
            func = cast(Any, callback)
            func(10001, None)

        mock_enum_windows.side_effect = enum_impl

        # 実行
        windows = get_windows(title_contains="テスト")
        
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["title"], "テストメモ帳")
        self.assertEqual(windows[0]["handle"], 10001)
        self.assertEqual(windows[0]["process_name"], "notepad.exe")
        self.assertEqual(windows[0]["rect"], {"x": 10, "y": 10, "width": 100, "height": 100})

    @patch("win32gui.IsWindow")
    @patch("win32gui.ShowWindow")
    @patch("win32gui.SetForegroundWindow")
    @patch("tools.get_windows")
    def test_focus_window_by_handle(
        self,
        mock_get_windows: MagicMock,
        mock_set_foreground: MagicMock,
        mock_show_window: MagicMock,
        mock_is_window: MagicMock,
    ) -> None:
        """ハンドル指定でのフォーカス処理が正常に動作することを検証する。"""
        mock_is_window.return_value = True

        result = focus_window(window_handle=12345)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["handle"], 12345)
        mock_set_foreground.assert_called_once_with(12345)

    def test_get_ui_tree_invalid_params(self) -> None:
        """不正な引数でget_ui_treeを呼び出した際にエラーが発生することを検証する。"""
        with self.assertRaises(InvalidParamsError):
            get_ui_tree()

    @patch("pywinauto.Application")
    @patch("tools.get_windows")
    def test_get_ui_tree_success(self, mock_get_windows: MagicMock, mock_app_class: MagicMock) -> None:
        """UIツリー取得が正常に動作し、シリアライズされることを検証する。"""
        mock_get_windows.return_value = [{
            "title": "テスト",
            "handle": 9999,
            "process_id": 123,
            "process_name": "test.exe",
            "visible": True,
            "minimized": False,
            "rect": {"x": 0, "y": 0, "width": 100, "height": 100}
        }]

        # pywinautoのモック構築
        mock_app = MagicMock()
        mock_window = MagicMock()
        
        # ElementInfoモック
        mock_info = MagicMock()
        mock_info.control_type = "Window"
        mock_info.name = "テスト"
        mock_info.automation_id = "win_1"
        mock_info.class_name = "MockClass"
        
        mock_window.element_info = mock_info
        mock_window.rectangle.return_value = MagicMock(left=0, top=0, width=lambda: 100, height=lambda: 100)
        mock_window.is_enabled.return_value = True
        mock_window.is_visible.return_value = True
        mock_window.children.return_value = []
        mock_window.exists.return_value = True

        mock_app.window.return_value = mock_window
        mock_app_class.return_value.connect.return_value = mock_app

        # 実行
        result = get_ui_tree(window_handle=9999, depth=1)
        
        self.assertIn("window", result)
        self.assertIn("tree", result)
        self.assertEqual(result["tree"]["control_type"], "Window")
        self.assertEqual(result["tree"]["name"], "テスト")

    @patch("subprocess.Popen")
    @patch("psutil.Process")
    @patch("time.sleep")
    def test_start_application_success(
        self,
        mock_sleep: MagicMock,
        mock_process: MagicMock,
        mock_popen: MagicMock,
    ) -> None:
        """start_application が正常にプロセスを起動しPIDを返すことを検証する。"""
        # Popenのモック
        mock_proc = MagicMock()
        mock_proc.pid = 9876
        mock_popen.return_value = mock_proc

        # Processのモック
        mock_proc_instance = MagicMock()
        mock_proc_instance.name.return_value = "notepad.exe"
        mock_process.return_value = mock_proc_instance

        result = start_application(cmd_line="notepad.exe")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["process_id"], 9876)
        self.assertEqual(result["process_name"], "notepad.exe")
        mock_popen.assert_called_once_with("notepad.exe", shell=True)

    @patch("winreg.OpenKey")
    @patch("winreg.QueryInfoKey")
    @patch("winreg.EnumKey")
    @patch("winreg.QueryValueEx")
    def test_get_installed_applications_success(
        self,
        mock_query_value: MagicMock,
        mock_enum_key: MagicMock,
        mock_query_info_key: MagicMock,
        mock_open_key: MagicMock,
    ) -> None:
        """インストール済みアプリケーション一覧取得およびフィルタリングが正常に動作することを検証する。"""
        import winreg
        
        # 各種キーの走査でのQueryInfoKeyの戻り値をモック化
        mock_query_info_key.side_effect = [
            (2, 0, 0),  # HKLM
            (1, 0, 0),  # HKCU
        ]
        
        mock_key_handle = MagicMock()
        mock_open_key.side_effect = [
            mock_key_handle,  # HKLM
            mock_key_handle,  # AppA subkey
            mock_key_handle,  # AppB subkey
            mock_key_handle,  # HKCU
            mock_key_handle,  # AppC subkey
            OSError("Wow6432Node not found"),  # Wow6432Node は存在しない想定
        ]
        
        mock_enum_key.side_effect = [
            "AppA_Key", "AppB_Key",  # HKLM subkeys
            "AppC_Key",              # HKCU subkeys
        ]
        
        # QueryValueExがDisplayNameなどの属性を取得する動作をモック化
        query_value_responses = [
            # AppA (Python 3.10)
            ("Python 3.10", winreg.REG_SZ),      # DisplayName
            ("3.10.5", winreg.REG_SZ),           # DisplayVersion
            ("Python Software Foundation", winreg.REG_SZ), # Publisher
            ("C:\\Python310", winreg.REG_SZ),    # InstallLocation
            ("C:\\Python310\\uninstall.exe", winreg.REG_SZ), # UninstallString
            
            # AppB (Google Chrome)
            ("Google Chrome", winreg.REG_SZ),    # DisplayName
            ("100.0", winreg.REG_SZ),            # DisplayVersion
            ("Google LLC", winreg.REG_SZ),       # Publisher
            ("C:\\Chrome", winreg.REG_SZ),       # InstallLocation
            OSError("No UninstallString"),       # UninstallString (存在しないエラー)
            
            # AppC (Slack)
            ("Slack", winreg.REG_SZ),            # DisplayName
            ("4.25.0", winreg.REG_SZ),           # DisplayVersion
            ("Slack Technologies", winreg.REG_SZ), # Publisher
            ("C:\\Slack", winreg.REG_SZ),        # InstallLocation
            ("C:\\Slack\\uninstall.exe", winreg.REG_SZ), # UninstallString
        ]
        
        mock_query_value.side_effect = query_value_responses

        from tools import get_installed_applications
        
        # 1. フィルタなしで全件取得
        apps = get_installed_applications()
        self.assertEqual(len(apps), 3)
        self.assertEqual(apps[0]["name"], "Google Chrome")
        self.assertEqual(apps[0]["uninstall_string"], None)  # エラー発生によりNoneとなる
        self.assertEqual(apps[1]["name"], "Python 3.10")
        self.assertEqual(apps[2]["name"], "Slack")
        
        # 2. フィルタありで取得
        mock_query_info_key.side_effect = [(1, 0, 0)]  # HKLMのみ
        mock_open_key.side_effect = [
            mock_key_handle,  # HKLM
            mock_key_handle,  # AppA subkey
            OSError("HKCU not found"),
            OSError("Wow6432Node not found"),
        ]
        mock_enum_key.side_effect = ["AppA_Key"]
        mock_query_value.side_effect = [
            ("Python 3.10", winreg.REG_SZ),      # DisplayName
            ("3.10.5", winreg.REG_SZ),           # DisplayVersion
            ("Python Software Foundation", winreg.REG_SZ), # Publisher
            ("C:\\Python310", winreg.REG_SZ),    # InstallLocation
            ("C:\\Python310\\uninstall.exe", winreg.REG_SZ), # UninstallString
        ]
        
        filtered_apps = get_installed_applications(name_contains="python")
        self.assertEqual(len(filtered_apps), 1)
        self.assertEqual(filtered_apps[0]["name"], "Python 3.10")


if __name__ == "__main__":
    unittest.main()
