"""
メッセージ管理ファイル
ここでメッセージのテンプレートや設定を管理します
"""

# メッセージテンプレート
MESSAGES = {
    "welcome": {
        "content": "サーバーへようこそ！",
        "embed": {
            "title": "🎉 ようこそ！",
            "description": "このサーバーでお楽しみください",
            "color": "#00FF00"
        }
    },
    "rules": {
        "content": "サーバールールをご確認ください",
        "embed": {
            "title": "📋 サーバールール",
            "description": "1. 他の人を尊重しましょう\n2. スパムは禁止です\n3. 楽しく過ごしましょう",
            "color": "#0099FF"
        }
    },
    "announcement": {
        "content": "重要なお知らせがあります",
        "embed": {
            "title": "📢 お知らせ",
            "description": "重要な情報をお伝えします",
            "color": "#FF9900"
        }
    }
}

def get_message(message_key: str):
    """指定されたキーのメッセージを取得"""
    return MESSAGES.get(message_key, None)

def get_all_message_keys():
    """利用可能なメッセージキーの一覧を取得"""
    return list(MESSAGES.keys())

def add_message(key: str, content: str, embed_data: dict = None):
    """新しいメッセージを追加"""
    message_data = {"content": content}
    if embed_data:
        message_data["embed"] = embed_data
    MESSAGES[key] = message_data

def remove_message(key: str):
    """メッセージを削除"""
    if key in MESSAGES:
        del MESSAGES[key]
        return True
    return False
