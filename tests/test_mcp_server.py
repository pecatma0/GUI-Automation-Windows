import unittest
import os
import sys

# パスを通す
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestMCPServer(unittest.TestCase):
    """MCP サーバーのツール登録状態などをテストするクラス。"""

    def test_tools_registered(self) -> None:
        """必要なツールがすべて MCP サーバーに登録されていることを検証する。"""
        import asyncio
        from gui_plugin.mcp_server import mcp

        async def get_tools() -> list[str]:
            return [t.name for t in await mcp.list_tools()]

        # 登録されているツール一覧を取得
        tools = asyncio.run(get_tools())

        expected_tools = [
            "get_windows",
            "focus_window",
            "get_ui_tree",
            "find_element",
            "do_action",
            "start_application",
        ]

        for tool in expected_tools:
            with self.subTest(tool=tool):
                self.assertIn(tool, tools)


if __name__ == "__main__":
    unittest.main()
