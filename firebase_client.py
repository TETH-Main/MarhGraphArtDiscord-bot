"""
Firebase Firestore クライアント
今日登録された数式データを取得する機能を提供
"""

import os
import json
from datetime import datetime, timezone, timedelta
from google.cloud import firestore
from google.oauth2 import service_account

class FirebaseClient:
    def __init__(self):
        """Firebase Firestore クライアントを初期化"""
        # 環境変数からサービスアカウント情報を取得
        firebase_credentials = os.getenv('FIREBASE_CREDENTIALS')
        if not firebase_credentials:
            raise ValueError("FIREBASE_CREDENTIALS環境変数が設定されていません")
        
        try:
            # JSON文字列をパース
            credentials_dict = json.loads(firebase_credentials)
            credentials = service_account.Credentials.from_service_account_info(credentials_dict)
            
            # Firestoreクライアントを初期化
            self.db = firestore.Client(credentials=credentials, project=credentials_dict['project_id'])
        except Exception as e:
            raise ValueError(f"Firebase認証エラー: {e}")
    
    def get_today_formulas(self):
        """
        今日登録された数式データを取得
        
        Returns:
            list: 今日の数式データのリスト
        """
        try:
            # 日本時間で今日の開始時刻と終了時刻を計算
            jst = timezone(timedelta(hours=9))
            now_jst = datetime.now(jst)
            today_start = now_jst.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = now_jst.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # UTC時間に変換
            today_start_utc = today_start.astimezone(timezone.utc)
            today_end_utc = today_end.astimezone(timezone.utc)
            
            # Firestoreクエリ（timestampが今日の範囲内）
            items_ref = self.db.collection('items')
            query = items_ref.where('timestamp', '>=', today_start_utc).where('timestamp', '<=', today_end_utc)
            
            results = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)
            
            # timestampでソート（新しい順）
            results.sort(key=lambda x: x.get('timestamp', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
            
            return results
            
        except Exception as e:
            print(f"Firebase取得エラー: {e}")
            return []
    
    def get_random_formula(self):
        """
        Firestoreからランダムに1つの数式を取得
        
        Returns:
            dict: ランダムな数式データ、エラー時はNone
        """
        try:
            # 全ての数式を取得してからランダムに選択
            # より効率的な方法もあるが、データ量が少ない場合はこの方法で十分
            items_ref = self.db.collection('items')
            
            # 全ドキュメントを取得
            all_docs = []
            for doc in items_ref.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                all_docs.append(data)
            
            if not all_docs:
                return None
            
            # ランダムに1つ選択
            import random
            random_formula = random.choice(all_docs)
            
            return random_formula
            
        except Exception as e:
            print(f"ランダム数式取得エラー: {e}")
            return None
    
    def get_all_tags(self):
        """
        全てのタグリストを取得
        
        Returns:
            list: タグ情報のリスト [{'tagID': 1, 'tagName': 'タグ名'}, ...]
        """
        try:
            tags_ref = self.db.collection('tagsList')
            query = tags_ref.order_by('tagID')
            
            tags = []
            for doc in query.stream():
                data = doc.to_dict()
                if 'tagID' in data and 'tagName' in data:
                    tags.append({
                        'tagID': data['tagID'],
                        'tagName': data['tagName']
                    })
            
            return tags
            
        except Exception as e:
            print(f"タグリスト取得エラー: {e}")
            return []
    
    def register_formula_via_gas(self, formula_data):
        """
        Google Apps Script経由で数式を登録
        
        Args:
            formula_data (dict): 数式データ
            
        Returns:
            dict: 登録結果
        """
        try:
            import requests
            
            # GAS WebアプリのURL（環境変数から取得）
            gas_url = os.getenv('GAS_WEBAPP_URL')
            if not gas_url:
                raise ValueError("GAS_WEBAPP_URL環境変数が設定されていません")
            
            # POSTデータを準備
            post_data = {
                'type': 'formula',  # GASが期待するタイプ
                'title': formula_data.get('title', ''),
                'title_EN': formula_data.get('title_EN', ''),
                'formula': formula_data.get('formula', ''),
                'formula_type': formula_data.get('formula_type', ''),  # "関数, 陰関数" 形式
                'tags': formula_data.get('tags', ''),  # "1, 12, 25" 形式
                'image_url': formula_data.get('image_url', ''),
                'newTags': ''  # 新しいタグなし
            }
            
            # GASにPOSTリクエストを送信
            response = requests.post(gas_url, json=post_data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                return result.get('result', {})
            else:
                raise Exception(f"GAS登録エラー: {result.get('error', '不明なエラー')}")
                
        except Exception as e:
            print(f"GAS経由での数式登録エラー: {e}")
            raise e
    
    def get_tag_name(self, tag_id):
        """
        タグIDからタグ名を取得
        
        Args:
            tag_id (str): タグID
            
        Returns:
            dict: タグ情報（tagName, tagName_EN）
        """
        try:
            doc_ref = self.db.collection('tagsList').document(tag_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                return {'tagName': tag_id, 'tagName_EN': tag_id}
                
        except Exception as e:
            print(f"タグ取得エラー: {e}")
            return {'tagName': tag_id, 'tagName_EN': tag_id}
    
    def format_formula_for_discord(self, formula_data):
        """
        数式データをDiscord用のEmbed形式に変換
        
        Args:
            formula_data (dict): 数式データ
            
        Returns:
            dict: Discord Embed用のデータ
        """
        try:
            # タグ情報を取得
            tag_names = []
            if 'tags' in formula_data and formula_data['tags']:
                for tag_id in formula_data['tags']:
                    tag_info = self.get_tag_name(tag_id)
                    tag_names.append(tag_info.get('tagName', tag_id))
            
            # 数式タイプの処理
            formula_types = formula_data.get('formula_type', [])
            if isinstance(formula_types, list):
                formula_type_str = ', '.join(formula_types)
            else:
                formula_type_str = str(formula_types)
            
            # タイムスタンプの処理
            timestamp_str = "不明"
            if 'timestamp' in formula_data and formula_data['timestamp']:
                try:
                    # Firestore TimestampをJST文字列に変換
                    timestamp = formula_data['timestamp']
                    if hasattr(timestamp, 'astimezone'):
                        jst = timezone(timedelta(hours=9))
                        timestamp_jst = timestamp.astimezone(jst)
                        timestamp_str = timestamp_jst.strftime('%Y/%m/%d %H:%M:%S')
                    else:
                        timestamp_str = str(timestamp)
                except Exception as e:
                    print(f"Timestamp変換エラー: {e}")
            
            return {
                'title': formula_data.get('title', '無題'),
                'title_EN': formula_data.get('title_EN', 'Untitled'),
                'formula': formula_data.get('formula', ''),
                'formula_type': formula_type_str,
                'tags': ', '.join(tag_names) if tag_names else 'なし',
                'image_url': formula_data.get('image_url', ''),
                'timestamp': timestamp_str,
                'id': formula_data.get('id', '')
            }
            
        except Exception as e:
            print(f"フォーマットエラー: {e}")
            return {
                'title': '変換エラー',
                'title_EN': 'Conversion Error',
                'formula': '',
                'formula_type': '',
                'tags': '',
                'image_url': '',
                'timestamp': '',
                'id': ''
            }
