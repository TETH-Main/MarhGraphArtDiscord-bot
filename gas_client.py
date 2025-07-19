"""
Google Apps Script クライアント
数式登録とタグ取得のためのGAS連携機能を提供
"""

import os
import aiohttp
import json
from typing import List, Dict, Optional

class GASClient:
    def __init__(self):
        """GAS クライアントを初期化"""
        self.gas_url = os.getenv('GAS_WEBAPP_URL')
        if not self.gas_url:
            raise ValueError("GAS_WEBAPP_URL環境変数が設定されていません")
        
        # スプレッドシートID（main.gsで使用されているもの）
        self.spreadsheet_id = '139qGcw2VXJRZF_zBLJ-wL-Lh8--hHZEFd0I1YYVsnqM'
    
    async def get_tags_list(self) -> List[Dict]:
        """
        タグリストを取得
        
        Returns:
            list: タグデータのリスト [{'tagID': '1', 'tagName': '美しい', 'tagName_EN': 'Beautiful'}, ...]
        """
        try:
            params = {
                'id': self.spreadsheet_id,
                'name': 'tagsList'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.gas_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list):
                            return data
                        else:
                            print(f"タグリスト取得エラー: 予期しないデータ形式 - {data}")
                            return []
                    else:
                        print(f"タグリスト取得エラー: HTTP {response.status}")
                        return []
        except Exception as e:
            print(f"タグリスト取得エラー: {e}")
            return []
    
    async def register_formula(self, formula_data: Dict) -> Dict:
        """
        数式を登録
        
        Args:
            formula_data (dict): 数式データ
                - title: タイトル
                - title_EN: 英語タイトル（オプション）
                - formula: 数式
                - formula_type: 数式タイプ（カンマ区切り文字列）
                - tags: 既存タグIDのカンマ区切り文字列
                - image_url: 画像URL
                
        Returns:
            dict: 登録結果 {'success': bool, 'result': dict or 'error': str}
        """
        try:
            # POSTデータを準備（main.gsのregisterFormula関数に合わせる）
            post_data = {
                'type': 'formula',
                'title': formula_data.get('title', ''),
                'title_EN': formula_data.get('title_EN', ''),
                'formula': formula_data.get('formula', ''),
                'formula_type': formula_data.get('formula_type', ''),
                'tags': formula_data.get('tags', ''),
                'image_url': formula_data.get('image_url', '')
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.gas_url,
                    headers={'Content-Type': 'application/json'},
                    data=json.dumps(post_data)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f'HTTP {response.status}: {error_text}'
                        }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def format_tags_for_display(self, tags_data: List[Dict], max_per_line: int = 6) -> str:
        """
        タグリストを表示用にフォーマット
        
        Args:
            tags_data: タグデータのリスト
            max_per_line: 1行あたりの最大タグ数
            
        Returns:
            str: フォーマットされたタグリスト文字列
        """
        if not tags_data:
            return "利用可能なタグがありません。"
        
        lines = []
        current_line = []
        
        for i, tag in enumerate(tags_data, 1):
            tag_name = tag.get('tagName', f"Tag{i}")
            tag_display = f"`{i}. {tag_name}`"
            current_line.append(tag_display)
            
            if len(current_line) >= max_per_line:
                lines.append(' '.join(current_line))
                current_line = []
        
        # 残りのタグがあれば追加
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)
    
    def parse_tag_selection(self, tags_data: List[Dict], user_input: str) -> str:
        """
        ユーザーの数字入力をタグIDに変換
        
        Args:
            tags_data: タグデータのリスト
            user_input: ユーザーの入力（例: "1, 3, 5"）
            
        Returns:
            str: タグIDのカンマ区切り文字列（例: "tag1,tag3,tag5"）
        """
        if not user_input or user_input.lower().strip() == 'なし':
            return ''
        
        try:
            # 入力をカンマで分割して数字を取得
            numbers = [int(num.strip()) for num in user_input.split(',') if num.strip().isdigit()]
            
            # 有効な範囲の数字のみフィルタ
            valid_numbers = [num for num in numbers if 1 <= num <= len(tags_data)]
            
            # 対応するタグIDを取得
            tag_ids = []
            for num in valid_numbers:
                tag = tags_data[num - 1]  # 1-based indexing
                tag_id = tag.get('tagID', str(num))
                tag_ids.append(str(tag_id))
            
            return ','.join(tag_ids)
            
        except Exception as e:
            print(f"タグ選択解析エラー: {e}")
            return ''
    
    def get_selected_tag_names(self, tags_data: List[Dict], tag_ids_str: str) -> List[str]:
        """
        タグIDからタグ名のリストを取得
        
        Args:
            tags_data: タグデータのリスト
            tag_ids_str: タグIDのカンマ区切り文字列
            
        Returns:
            list: タグ名のリスト
        """
        if not tag_ids_str:
            return []
        
        tag_ids = [tid.strip() for tid in tag_ids_str.split(',') if tid.strip()]
        tag_names = []
        
        for tag_id in tag_ids:
            # タグIDからタグ名を検索
            for tag in tags_data:
                if str(tag.get('tagID', '')) == tag_id:
                    tag_names.append(tag.get('tagName', tag_id))
                    break
            else:
                # 見つからない場合はIDをそのまま使用
                tag_names.append(tag_id)
        
        return tag_names
