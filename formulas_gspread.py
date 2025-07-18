"""
Google Sheets（GAS API）で数式データ管理を行うためのラッパー
テーブル構造: id, title, title_EN, formula, formula_type, tags, image_url, timestamp
.envにFORMULAS_API_URL, FORMULAS_API_KEY等を設定して利用してください
"""
import os
import requests
from typing import List, Dict, Optional

FORMULAS_API_URL = os.getenv("FORMULAS_API_URL")  # 例: https://script.google.com/macros/s/xxxxxx/exec
FORMULAS_API_KEY = os.getenv("FORMULAS_API_KEY")  # 必要なら

# --- 基本関数 ---
def get_formula(formula_id: str) -> Optional[Dict]:
    """指定IDの数式データを取得"""
    if not FORMULAS_API_URL:
        print("エラー: FORMULAS_API_URL環境変数が設定されていません。")
        return None
    
    params = {"id": formula_id}
    if FORMULAS_API_KEY:
        params["api_key"] = FORMULAS_API_KEY
    
    try:
        r = requests.get(FORMULAS_API_URL, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, dict):
                return data
        return None
    except requests.exceptions.RequestException as e:
        print(f"数式データ取得エラー: {e}")
        return None
    except Exception as e:
        print(f"数式データ取得エラー: {e}")
        return None

def get_all_formulas() -> List[Dict]:
    """全数式データ一覧を取得"""
    if not FORMULAS_API_URL:
        print("エラー: FORMULAS_API_URL環境変数が設定されていません。")
        return []
    
    params = {}
    if FORMULAS_API_KEY:
        params["api_key"] = FORMULAS_API_KEY
    
    try:
        r = requests.get(FORMULAS_API_URL, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list):
                return data
        return []
    except requests.exceptions.RequestException as e:
        print(f"数式データ一覧取得エラー: {e}")
        return []
    except Exception as e:
        print(f"数式データ一覧取得エラー: {e}")
        return []

def get_formulas_by_type(formula_type: str) -> List[Dict]:
    """指定タイプの数式データ一覧を取得"""
    if not FORMULAS_API_URL:
        print("エラー: FORMULAS_API_URL環境変数が設定されていません。")
        return []
    
    params = {"type": formula_type}
    if FORMULAS_API_KEY:
        params["api_key"] = FORMULAS_API_KEY
    
    try:
        r = requests.get(FORMULAS_API_URL, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list):
                return data
        return []
    except requests.exceptions.RequestException as e:
        print(f"数式データタイプ別取得エラー: {e}")
        return []
    except Exception as e:
        print(f"数式データタイプ別取得エラー: {e}")
        return []

def search_formulas(query: str) -> List[Dict]:
    """タイトルやタグで数式データを検索"""
    if not FORMULAS_API_URL:
        print("エラー: FORMULAS_API_URL環境変数が設定されていません。")
        return []
    
    params = {"search": query}
    if FORMULAS_API_KEY:
        params["api_key"] = FORMULAS_API_KEY
    
    try:
        r = requests.get(FORMULAS_API_URL, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list):
                return data
        return []
    except requests.exceptions.RequestException as e:
        print(f"数式データ検索エラー: {e}")
        return []
    except Exception as e:
        print(f"数式データ検索エラー: {e}")
        return []

def add_or_update_formula(formula_id: str, title: str, title_en: str, formula: str, 
                         formula_type: str, tags: str = "", image_url: str = "") -> bool:
    """新規追加または更新（POST）"""
    if not FORMULAS_API_URL:
        print("エラー: FORMULAS_API_URL環境変数が設定されていません。")
        return False
    
    data = {
        "id": formula_id,
        "title": title,
        "title_EN": title_en,
        "formula": formula,
        "formula_type": formula_type,
        "tags": tags,
        "image_url": image_url
    }
    if FORMULAS_API_KEY:
        data["api_key"] = FORMULAS_API_KEY
    
    try:
        r = requests.post(FORMULAS_API_URL, json=data, timeout=10)
        return r.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"数式データ追加/更新エラー: {e}")
        return False
    except Exception as e:
        print(f"数式データ追加/更新エラー: {e}")
        return False

def remove_formula(formula_id: str) -> bool:
    """数式データ削除（DELETE）"""
    if not FORMULAS_API_URL:
        print("エラー: FORMULAS_API_URL環境変数が設定されていません。")
        return False
    
    params = {"id": formula_id}
    if FORMULAS_API_KEY:
        params["api_key"] = FORMULAS_API_KEY
    
    try:
        r = requests.delete(FORMULAS_API_URL, params=params, timeout=10)
        return r.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"数式データ削除エラー: {e}")
        return False
    except Exception as e:
        print(f"数式データ削除エラー: {e}")
        return False

def get_random_formula() -> Optional[Dict]:
    """ランダムな数式データを1つ取得"""
    if not FORMULAS_API_URL:
        print("エラー: FORMULAS_API_URL環境変数が設定されていません。")
        return None
    
    params = {"random": "true"}
    if FORMULAS_API_KEY:
        params["api_key"] = FORMULAS_API_KEY
    
    try:
        r = requests.get(FORMULAS_API_URL, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, dict):
                return data
        return None
    except requests.exceptions.RequestException as e:
        print(f"ランダム数式データ取得エラー: {e}")
        return None
    except Exception as e:
        print(f"ランダム数式データ取得エラー: {e}")
        return None

# --- ユーティリティ関数 ---
def format_formula_for_display(formula_data: Dict) -> str:
    """数式データを表示用にフォーマット"""
    if not formula_data:
        return "データがありません。"
    
    result = []
    result.append(f"**ID:** {formula_data.get('id', 'N/A')}")
    result.append(f"**タイトル:** {formula_data.get('title', 'N/A')}")
    
    if formula_data.get('title_EN'):
        result.append(f"**英語タイトル:** {formula_data.get('title_EN')}")
    
    result.append(f"**数式:** `{formula_data.get('formula', 'N/A')}`")
    result.append(f"**タイプ:** {formula_data.get('formula_type', 'N/A')}")
    
    if formula_data.get('tags'):
        result.append(f"**タグ:** {formula_data.get('tags')}")
    
    if formula_data.get('timestamp'):
        result.append(f"**更新日時:** {formula_data.get('timestamp')}")
    
    return "\n".join(result)

def get_available_formula_types() -> List[str]:
    """利用可能な数式タイプ一覧を取得"""
    formulas = get_all_formulas()
    types = set()
    for formula in formulas:
        if formula.get('formula_type'):
            types.add(formula['formula_type'])
    return sorted(list(types))
