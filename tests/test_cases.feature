Feature: Windows GUI Automation Plugin Testing

  Scenario: 起動中のウィンドウ一覧を取得する (get_windows)
    Given GUI操作プラグインが初期化されている
    When ウィンドウ一覧取得を呼び出す
      | title_contains | process_name | visible_only |
      | None           | None         | True         |
    Then 起動中のウィンドウのリストが返却される
      And 各ウィンドウ情報に "title", "handle", "process_id", "process_name", "rect" が含まれる

  Scenario: 特定のウィンドウにフォーカスを当てる (focus_window)
    Given 起動中のウィンドウが存在する
      And 対象ウィンドウのハンドルを取得している
    When そのハンドルを指定してフォーカス関数を呼び出す
      | window_handle | restore_if_minimized |
      | <handle>      | True                 |
    Then 実行結果として成功ステータスが返却される
      And "success" が True である

  Scenario: ウィンドウのUI要素ツリーを取得する (get_ui_tree)
    Given 対象ウィンドウが存在する
    When そのハンドルを指定してUIツリー取得関数を呼び出す
      | window_handle | depth | include_invisible |
      | <handle>      | 2     | False             |
    Then 階層構造を持つJSONツリーが返却される
      And ルートノードの "control_type" が "Window" である
      And 子要素のリスト "children" が含まれる

  Scenario: 条件を指定して特定のUI要素を検索する (find_element)
    Given 対象ウィンドウが存在する
    When 検索条件を指定して要素検索を呼び出す
      | window_handle | conditions                                              |
      | <handle>      | {"control_type": "Button", "name_contains": "閉じる"}   |
    Then 条件に一致するUI要素ノードが返却される
      And 要素ノードに仮想 "handle" が含まれる

  Scenario: UI要素に対してクリック操作を行う (do_action - click)
    Given 操作対象のUI要素が存在する
      And その要素の仮想ハンドルを取得している
    When アクション "click" を呼び出す
      | handle   | action  | params |
      | <handle> | "click" | {}     |
    Then 操作結果のJSONが返却される
      And "success" が True である
      And "elapsed_ms" が含まれる
