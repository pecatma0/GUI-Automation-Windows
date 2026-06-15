import logging
from gui_plugin.config import CONFIG

def setup_logger() -> logging.Logger:
    """プラグイン用のロガーを設定する。
    
    エラーや警告をファイルに出力してトラブルシューティングを容易にする意図。
    ログファイルパスは環境変数/設定ファイルから取得する。
    """
    logger = logging.getLogger("gui_plugin")
    logger.setLevel(logging.DEBUG)
    
    # 既存のハンドラがある場合は重複を避けるために追加しない
    if not logger.handlers:
        log_file = CONFIG["LOG_FILE_PATH"]
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.WARNING) # エラーおよび警告ログのみをファイル出力して管理する
        
        # ログフォーマットの設定
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # コンソール出力用のハンドラも開発/デバッグ用に設定しておく（INFOレベル以上）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger

logger: logging.Logger = setup_logger()
