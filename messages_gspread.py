"""
Google Sheets（GAS API）でメッセージ管理を行うためのラッパー
.envにAPI_URL, API_KEY等を設定して利用してください
"""
import os
import requests

API_URL = os.getenv("MESSAGES_API_URL")  # 例: https://script.google.com/macros/s/xxxxxx/exec
API_KEY = os.getenv("MESSAGES_API_KEY")  # 必要なら

# --- 基本関数 ---
def get_message(key):
    """指定キーのメッセージを取得"""
    params = {"key": key}
    if API_KEY:
        params["api_key"] = API_KEY
    r = requests.get(API_URL, params=params)
    if r.status_code == 200:
        return r.json()
    return None

def get_all_messages():
    """全メッセージ一覧を取得"""
    params = {}
    if API_KEY:
        params["api_key"] = API_KEY
    r = requests.get(API_URL, params=params)
    if r.status_code == 200:
        try:
            return r.json()
        except Exception:
            return []
    return []

def add_or_update_message(key, content, embed=None):
    """新規追加または更新（POST）"""
    data = {
        "key": key,
        "content": content,
        "embed_title": embed["title"] if embed and "title" in embed else "",
        "embed_description": embed["description"] if embed and "description" in embed else "",
        "embed_color": embed["color"] if embed and "color" in embed else ""
    }
    if API_KEY:
        data["api_key"] = API_KEY
    r = requests.post(API_URL, json=data)
    return r.status_code == 200

def remove_message(key):
    """メッセージ削除（DELETE）"""
    params = {"key": key}
    if API_KEY:
        params["api_key"] = API_KEY
    r = requests.delete(API_URL, params=params)
    return r.status_code == 200
