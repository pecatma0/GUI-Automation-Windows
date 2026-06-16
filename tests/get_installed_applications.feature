Feature: インストール済みアプリケーション一覧の取得
  GUIプラグインを使用して、Windows環境にインストールされている
  アプリケーション一覧を取得し、正しくフィルタリングできることを検証する。

  Scenario: インストール済みアプリケーション一覧をすべて取得する
    Given Windows環境にいくつかのアプリケーションがインストールされていること
    When "get_installed_applications" ツールを引数なしで実行する
    Then インストールされているアプリケーションの一覧がDisplayNameの昇順で返されること
    And 返されたリストの各要素にname、version、publisher、install_location、uninstall_stringが含まれていること

  Scenario: アプリケーション名で部分一致フィルタリングを行う
    Given Windows環境に "Python" という名前を含むアプリケーションがインストールされていること
    When "get_installed_applications" ツールを引数 "name_contains: Python" で実行する
    Then "Python" という文字列を名前に含むアプリケーションのみがフィルタリングされて返されること
