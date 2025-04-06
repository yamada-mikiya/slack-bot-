import time
import pytz
from collections import Counter
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os

# ✅ GitHub Actions の環境変数から Slack Bot Token を取得
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
client = WebClient(token=SLACK_BOT_TOKEN)

# ✅ 送信先チャンネル
CHANNEL_ID = "C08GB08NU6L"

# 🔹 集計対象期間（日本時間）
START_JST = datetime(2024, 5, 9, 18, 30, 0)
END_JST = datetime(2025, 5, 19, 23, 59, 59)

# 🔹 ユーザー情報とチャンネル情報を取得
USERS_LIST = client.users_list()['members']

# 🔹 **公開チャンネル & プライベートチャンネル両方を取得**
CHANNELS_LIST = client.conversations_list(limit=1000, types="public_channel,private_channel")['channels']

BOT_USER_ID = client.auth_test()["user_id"]  # BotのユーザーIDを取得

# 🔹 対象ユーザー
TARGET_USERS = ["情知　A4", "運営_A4", "電電　A4", "情知2 A4 ふな","海洋　A4","グロ文 2 神戸大学混声合唱団アポロン","経済 A4 まつゆき","文学部　A4","農 3 陸上競技部","保健 3 陸上競技部"]
TARGET_EMOJI = "回答"

# 🔹 ユーザー名 → ユーザーID の変換
target_user_ids = {user['id']: user.get('real_name') for user in USERS_LIST if user.get('real_name') in TARGET_USERS}

def join_channel(channel_id):
    """ ボットをチャンネルに参加させる（公開チャンネルのみ） """
    try:
        response = client.conversations_join(channel=channel_id)
        print(f"✅ {channel_id} に参加しました")
        return True
    except SlackApiError as e:
        print(f"⚠️ {channel_id} の参加エラー: {e.response['error']}")
        return False


def _get_conversations_info(CHANNELS_ID: str):
    emoji_message_count = Counter({user_id: 0 for user_id in target_user_ids})  # **初期化**
    
    start_utc = START_JST.astimezone(pytz.utc).timestamp()
    end_utc = END_JST.astimezone(pytz.utc).timestamp()
    
    try:
        messages = []
        cursor = None

        while True:
            response = client.conversations_history(
                channel=CHANNELS_ID,
                limit=1000,
                cursor=cursor
            )
    
            messages.extend(response['messages'])

            cursor = response.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                break  # 取得するメッセージがなくなったら終了

            time.sleep(1)  # API レート制限対策

        print(f"✅ {CHANNELS_ID} のメッセージ取得成功: {len(messages)} 件")
    except SlackApiError as e:
        error_msg = e.response['error']
        channel_name = get_channel_name(CHANNELS_ID)  # チャンネル名を取得

        if error_msg == "not_in_channel":
            print(f"⚠️ {channel_name} ({CHANNELS_ID}) にボットが未参加。参加を試みます...")
            if join_channel(CHANNELS_ID):  # 参加成功したらもう一度メッセージ取得を試す
                return _get_conversations_info(CHANNELS_ID)

        print(f"⚠️ {channel_name} ({CHANNELS_ID}) のメッセージ取得エラー: {error_msg}")


        return emoji_message_count

    # メッセージごとの絵文字リアクションをカウント
    for post in messages:
        if 'user' in post and post['user'] in target_user_ids and 'reactions' in post:
            for reaction in post['reactions']:
                if reaction['name'] == TARGET_EMOJI:
                    emoji_message_count[post['user']] += 1
                    break

        if 'thread_ts' in post and 'subtype' not in post:
            try:
                replies = client.conversations_replies(channel=CHANNELS_ID, ts=post['thread_ts'], limit=100, oldest=start_utc, latest=end_utc)
                for reply in replies['messages'][1:]:
                    if 'subtype' in reply or 'reactions' not in reply or reply['user'] not in target_user_ids:
                        continue
                    for reaction in reply['reactions']:
                        if reaction['name'] == TARGET_EMOJI:
                            emoji_message_count[reply['user']] += 1
                            break
            except Exception as e:
                print(f"⚠️ スレッド取得エラー（{CHANNELS_ID}）: {e}")

    return emoji_message_count

def get_channel_name(channel_id):
    """ チャンネルIDからチャンネル名を取得 """
    try:
        response = client.conversations_info(channel=channel_id)
        return response["channel"]["name"]
    except SlackApiError as e:
        print(f"⚠️ {channel_id} のチャンネル名取得エラー: {e.response['error']}")
        return "Unknown"


def extract_group_name(user_name):
    """ ユーザー名から団体名を抽出する """
    GROUP_NAMES = ["A4","神戸大学混声合唱団アポロン","陸上競技部"]
    for group in GROUP_NAMES:
        if group in user_name:
            return group
    return user_name

def generate_report():
    """集計結果を作成"""
    total_emoji_message_count = Counter({user_id: 0 for user_id in target_user_ids})

    for channel in CHANNELS_LIST:
        emoji_message_count = _get_conversations_info(channel['id'])
        total_emoji_message_count.update(emoji_message_count)

    grouped_counts = Counter()

    for user_id, count in total_emoji_message_count.items():
        user_name = target_user_ids.get(user_id, "Unknown")
        group_name = extract_group_name(user_name)
        grouped_counts[group_name] += count

    now_jst = datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")

    result = f"━━━━━━━━━━━━━━━━━━\n"
    result += f"{now_jst} 時点の集計結果\n"
    result += f"━━━━━━━━━━━━━━━━━━\n\n"

    result += "🟢全チャンネル合計の回答回数降順:\n"
    sorted_groups = sorted(grouped_counts.items(), key=lambda x: x[1], reverse=True)

    for group_name, count in sorted_groups:
        result += f"  - {group_name}: {count}回\n"

    return result

def send_slack_message():
    """Slack にレポートを送信"""
    report = generate_report()
    
    try:
        response = client.chat_postMessage(channel=CHANNEL_ID, text=report)
        print(f"✅ Slack メッセージ送信成功: {response['ts']}")
    except SlackApiError as e:
        print(f"❌ エラー: {e.response['error']}")

send_slack_message()
