# slack-bot-

指定されたSlackの絵文字リアクションを集計し、結果を通知するBotです。

### 概要

このSlack Botは、特定の団体に所属するメンバーが、指定された期間内に行った特定の絵文字リアクション（デフォルトでは「:回答:」）の回数を集計します。集計結果は団体ごとにまとめられ、指定したSlackチャンネルに降順でランキング形式で投稿されます。

GitHub Actionsを利用して定期的に、または手動で実行することが可能です。

### 主な機能

* **リアクション集計**:
    * 特定の絵文字（`TARGET_EMOJI`）のリアクション数をユーザーごとにカウントします。
    * 指定した団体名（`GROUP_NAMES`）がプロフィールに含まれるユーザーのみを対象とします。
    * スレッド内の返信についたリアクションも集計対象となります。
* **チャンネル横断での集計**: Botが参加しているすべてのパブリックおよびプライベートチャンネルを対象にメッセージを取得します。
* **自動チャンネル参加**: メッセージ取得の際、Botが参加していないパブリックチャンネルがあった場合は自動で参加を試みます。
* **結果レポート**:
    * 団体ごとの合計リアクション数を集計します。
    * 集計結果を指定されたチャンネル（`CHANNEL_ID`）に投稿します。
    * 結果は回数の多い順にソートして表示されます。
* **実行トリガー**:
    * GitHub Actionsの`workflow_dispatch`により、手動での実行が可能です。
    * （現在コメントアウトされていますが）cronスケジュールを設定することで、定期実行も可能です。

### 動作設定

#### 1. Slack Bot Tokenの設定

このBotを実行するにはSlack Bot Tokenが必要です。

* **GitHub Actionsで実行する場合**:
    リポジトリの `Settings` > `Secrets and variables` > `Actions` に `SLACK_BOT_TOKEN` という名前でSlack Bot Tokenを登録してください。ワークフローファイル (`.github/workflows/slack.yml`) がこのSecretを読み込みます。

* **ローカルで実行する場合**:
    リポジトリのルートディレクトリに `.env` ファイルを作成し、以下のように記述してください。`.gitignore`により、このファイルはGitの管理対象外となります。
    ```
    SLACK_BOT_TOKEN="xoxb-xxxxxxxxxxxx-xxxxxxxxxxxxxxxx-xxxxxxxx"
    ```

#### 2. スクリプト内の定数設定

`slack_bot.py`内の以下の定数を必要に応じて変更してください。

* `CHANNEL_ID`: 集計結果を投稿するSlackチャンネルのID。
* `START_JST`, `END_JST`: リアクションを集計する期間（日本時間）。
* `GROUP_NAMES`: 集計対象とする団体の名称リスト。ユーザーのプロフィール名にこれらのいずれかが含まれていると対象になります。
* `TARGET_EMOJI`: 集計対象の絵文字名（コロンは不要です）。

### 実行方法

#### ローカル環境での実行

1.  **リポジトリをクローンします。**
    ```bash
    git clone [https://github.com/yamada-mikiya/slack-bot-.git](https://github.com/yamada-mikiya/slack-bot-.git)
    cd slack-bot-
    ```
2.  **必要なライブラリをインストールします。**
    ```bash
    pip install slack_sdk pytz python-dotenv
    ```
3.  **`.env`ファイルを作成し、Slack Bot Tokenを設定します。（上記「動作設定」参照）**

4.  **スクリプトを実行します。**
    ```bash
    python slack_bot.py
    ```

#### GitHub Actionsでの実行

1.  **リポジトリに`SLACK_BOT_TOKEN`をSecretとして登録します。（上記「動作設定」参照）**

2.  **GitHubリポジトリの`Actions`タブに移動します。**

3.  **`Send Slack Notification`ワークフローを選択し、`Run workflow`ボタンをクリックして手動で実行します。**
