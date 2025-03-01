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

# ✅ 集計対象期間（日本時間）
START_JST = datetime(2024, 5, 9, 18, 30, 0)
END_JST = datetime(2025, 5, 19, 23, 59, 59)

# ✅ ユーザー情報とチャンネル情報を取得
USERS_LIST = client.users_list()['members']
CHANNELS_LIST = client.conversations_list(limit=1000)['channels']
BOT_USER_ID = client.auth_test()["user_id"]

# ✅ 対象ユーザー
TARGET_USERS = ["情報知能工学科A4", "ふな", "経済1 A4"]
TARGET_EMOJI = "回答"

# ✅ ユーザー名 → ユーザーID の変換
target_user_ids = {user['id']: user.get('real_name') for user in USERS_LIST if user.get('real_name') in TARGET_USERS}

def _get_conversations_info(CHANNELS_ID: str):
    emoji_message_count = Counter({user_id: 0 for user_id in target_user_ids})
    
    start_utc = START_JST.astimezone(pytz.utc).timestamp()
    end_utc = END_JST.astimezone(pytz.utc).timestamp()
    
    try:
        messages = []
        cursor = None

        while True:
            response = client.conversations_history(channel=CHANNELS_ID, limit=1000, cursor=cursor)
            messages.extend(response['messages'])

            cursor = response.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                break  # メッセージがなくなったら終了

            time.sleep(1)  # API レート制限対策

        print(f"✅ {CHANNELS_ID} のメッセージ取得成功: {len(response['messages'])} 件")
        posts = response['messages']
    except SlackApiError as e:
        print(f"⚠️ {CHANNELS_ID} のメッセージ取得エラー: {e.response['error']}")
        return emoji_message_count

    for post in posts:
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

def extract_group_name(user_name):
    """ ユーザー名から団体名を抽出 """
    GROUP_NAMES = ["陸上部", "水泳部", "ボランティアサークル", "経済学会", "文化研究会", "A4"]
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
