class GUIPluginError(Exception):
    """GUI操作プラグインの基底例外クラス。
    
    各具体的なエラーケースに対して、適切なエラーコードと詳細メッセージを保持する。
    """
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code: str = error_code
        self.message: str = message


class WindowNotFoundError(GUIPluginError):
    """指定されたウィンドウが見つからない場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("WINDOW_NOT_FOUND", message)


class ElementNotFoundError(GUIPluginError):
    """指定されたUI要素が見つからない場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("ELEMENT_NOT_FOUND", message)


class ElementDisabledError(GUIPluginError):
    """要素が無効状態であり操作できない場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("ELEMENT_DISABLED", message)


class ElementNotVisibleError(GUIPluginError):
    """要素が非表示であり操作できない場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("ELEMENT_NOT_VISIBLE", message)


class ActionNotSupportedError(GUIPluginError):
    """要素が要求されたアクションに対応していない場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("ACTION_NOT_SUPPORTED", message)


class TimeoutError(GUIPluginError):
    """待機処理でタイムアウトした場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("TIMEOUT", message)


class AccessDeniedError(GUIPluginError):
    """OS権限不足などで操作が拒否された場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("ACCESS_DENIED", message)


class BackendError(GUIPluginError):
    """pywinautoなどの内部バックエンドライブラリでエラーが発生した場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("BACKEND_ERROR", message)


class InvalidParamsError(GUIPluginError):
    """パラメータが不正である場合のエラー。"""
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_PARAMS", message)
