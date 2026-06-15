import os
import sys
from dotenv import load_dotenv

def load_config() -> dict[str, str]:
    """.envファイルから設定値を読み込む。
    
    定数・デフォルト値を一元管理し、マジックナンバーのハードコーディングを防ぐ意図。
    読み込みに失敗した（あるいは必須キーが存在しない）場合はプログラムを異常終了させる。
    """
    # 開発・テスト環境両方で動作するように、cwdおよびスクリプト位置の.envをロード試行
    loaded = load_dotenv()
    if not loaded:
        # 予備的に親ディレクトリなども探索するが、見つからなければ異常終了
        alternative_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(alternative_path):
            loaded = load_dotenv(alternative_path)
            
    if not loaded:
        print("エラー: .env ファイルの読み込みに失敗しました。プロセスを終了します。", file=sys.stderr)
        sys.exit(1)
        
    config = {
        "DEFAULT_TIMEOUT": os.getenv("DEFAULT_TIMEOUT"),
        "DEFAULT_WAIT_AFTER": os.getenv("DEFAULT_WAIT_AFTER"),
        "LOG_FILE_PATH": os.getenv("LOG_FILE_PATH"),
    }
    
    # 必須キーの存在チェック
    for key, val in config.items():
        if val is None:
            print(f"エラー: 必須の設定キー {key} が .env に定義されていません。プロセスを終了します。", file=sys.stderr)
            sys.exit(1)
            
    return config

# アプリケーション全体で共有する設定オブジェクト
CONFIG = load_config()
