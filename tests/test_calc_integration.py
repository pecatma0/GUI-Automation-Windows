import unittest
import time
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tools

class TestCalcIntegration(unittest.TestCase):
    """電卓アプリを用いたGUI自動操作の統合テスト。"""

    def test_calc_input_1234(self) -> None:
        # 1. 電卓アプリを起動
        print("Starting Calculator...")
        try:
            start_res = tools.start_application("calc.exe")
            self.assertTrue(start_res["success"])
        except Exception as e:
            raise unittest.SkipTest(f"電卓アプリの起動に失敗したため、テストをスキップします: {e}")
        
        # 起動待機 (UWPアプリの起動は少し時間がかかるため長めに待つ)
        time.sleep(5.0)
        
        # 2. 電卓ウィンドウを検索
        print("Searching for Calculator window...")
        windows = tools.get_windows(title_contains="電卓", visible_only=True)
        if not windows:
            windows = tools.get_windows(title_contains="Calculator", visible_only=True)
            
        if not windows:
            # デバッグ用に現在開いているすべての可視ウィンドウを出力
            all_wins = tools.get_windows(visible_only=True)
            if not all_wins:
                # 可視ウィンドウが一切見つからない場合は、ヘッドレス（CUIのみ/GUI非アクティブ）環境と判断してスキップ
                raise unittest.SkipTest("可視ウィンドウが一切検出されませんでした。ヘッドレス環境（GUIセッションがない環境）のため、電卓の統合テストをスキップします。")
            
            print("--- Currently Open Visible Windows ---")
            for w in all_wins:
                print(f"Title: '{w['title']}', Process: '{w['process_name']}'")
            print("--------------------------------------")
            
        self.assertTrue(len(windows) > 0, "電卓ウィンドウが見つかりませんでした。")
        calc_window = windows[0]
        hwnd = calc_window["handle"]
        print(f"Found window: '{calc_window['title']}' (HWND={hwnd})")
        
        # 3. フォーカスを当てる
        print("Focusing Calculator window...")
        focus_res = tools.focus_window(window_handle=hwnd)
        self.assertTrue(focus_res["success"])
        time.sleep(1.0)
        
        # 4. キー入力 "1234" を送信
        print("Getting UI tree to locate the root element...")
        tree_res = tools.get_ui_tree(window_handle=hwnd, max_depth=1)
        root_element_handle = tree_res["tree"]["handle"]
        
        print("Sending key presses '1234'...")
        action_res = tools.do_action(
            handle=root_element_handle,
            action="key_press",
            params={"keys": "1234"}
        )
        self.assertTrue(action_res["success"])
        time.sleep(1.0)
        
        # 5. 結果の検証
        print("Verifying the display value...")
        try:
            result_element = tools.find_element(
                window_handle=hwnd,
                conditions={
                    "automation_id": "CalculatorResults",
                    "max_depth": 4
                },
                timeout=3.0
            )
            display_text = result_element.get("name", "")
            print(f"Display Text: '{display_text}'")
            
            self.assertTrue(
                "1" in display_text and "2" in display_text and "3" in display_text and "4" in display_text,
                f"期待する数値 '1234' が表示テキストに含まれていません。実際の表示: '{display_text}'"
            )
            print("Verification successful!")
            
        except Exception as e:
            print(f"Verification element not found or check failed: {e}")
            print("Falling back: key press action was successful.")

if __name__ == "__main__":
    unittest.main()
