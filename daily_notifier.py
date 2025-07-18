"""
毎日の数式通知機能
毎日0時に新しく登録された数式をチェックして通知する
"""
import asyncio
import datetime
from typing import List, Dict, Optional
import discord
from formulas_gspread import get_all_formulas, format_formula_for_display

class DailyFormulaNotifier:
    def __init__(self, bot, notification_channel_id: int):
        self.bot = bot
        self.notification_channel_id = notification_channel_id
        self.is_running = False
        self.task = None
    
    def start(self):
        """通知タスクを開始"""
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self._daily_notification_loop())
            print("数式通知タスクを開始しました。")
    
    def stop(self):
        """通知タスクを停止"""
        if self.is_running and self.task:
            self.is_running = False
            self.task.cancel()
            print("数式通知タスクを停止しました。")
    
    async def _daily_notification_loop(self):
        """毎日0時に実行されるメインループ"""
        while self.is_running:
            try:
                # 次の0時まで待機
                await self._wait_until_midnight()
                
                if self.is_running:
                    # 今日登録された数式をチェック
                    await self._check_and_notify_new_formulas()
                    
            except asyncio.CancelledError:
                print("数式通知タスクがキャンセルされました。")
                break
            except Exception as e:
                print(f"数式通知タスクエラー: {e}")
                # エラーが発生しても1時間後に再試行
                await asyncio.sleep(3600)
    
    async def _wait_until_midnight(self):
        """次の0時まで待機"""
        now = datetime.datetime.now()
        # 次の0時を計算
        next_midnight = (now + datetime.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        # 現在時刻が既に今日の0時を過ぎている場合は、今日の0時から計算
        if now.hour == 0 and now.minute < 5:  # 0時0分〜0時5分の間は今日の処理として実行
            sleep_time = 0
        else:
            sleep_time = (next_midnight - now).total_seconds()
        
        if sleep_time > 0:
            print(f"次の通知まで {sleep_time/3600:.2f} 時間待機します。")
            await asyncio.sleep(sleep_time)
    
    async def _check_and_notify_new_formulas(self):
        """今日登録された数式をチェックして通知"""
        try:
            # 通知チャンネルを取得
            channel = self.bot.get_channel(self.notification_channel_id)
            if not channel:
                print(f"通知チャンネル (ID: {self.notification_channel_id}) が見つかりません。")
                return
            
            # 今日の日付を取得
            today = datetime.date.today()
            today_str = today.strftime("%Y-%m-%d")
            
            # 全数式を取得
            all_formulas = get_all_formulas()
            if not all_formulas:
                print("数式データが取得できませんでした。")
                return
            
            # 今日登録された数式をフィルタリング
            today_formulas = self._filter_today_formulas(all_formulas, today_str)
            
            if today_formulas:
                # 通知メッセージを送信
                await self._send_notification(channel, today_formulas, today)
                print(f"{len(today_formulas)}件の新しい数式を通知しました。")
            else:
                print("今日登録された新しい数式はありませんでした。")
                
        except Exception as e:
            print(f"数式通知処理エラー: {e}")
    
    def _filter_today_formulas(self, formulas: List[Dict], target_date_str: str) -> List[Dict]:
        """指定日に登録された数式をフィルタリング"""
        target_formulas = []
        
        for formula in formulas:
            timestamp = formula.get('timestamp')
            if not timestamp:
                continue
            
            try:
                # タイムスタンプをパース (2025/03/06 12:09:08 形式)
                date_part = str(timestamp).split(' ')[0]  # "2025/03/06"
                formula_date = datetime.datetime.strptime(date_part, "%Y/%m/%d").date()
                
                if formula_date.strftime("%Y-%m-%d") == target_date_str:
                    target_formulas.append(formula)
                    
            except Exception as e:
                print(f"タイムスタンプパースエラー ({timestamp}): {e}")
                continue
        
        return target_formulas
    
    async def _send_notification(self, channel, formulas: List[Dict], date: datetime.date):
        """通知メッセージを送信"""
        try:
            # メインの通知メッセージ
            embed = discord.Embed(
                title=f"🎉 本日の新着数式 ({date.strftime('%Y年%m月%d日')})",
                description=f"今日は **{len(formulas)}件** の新しい数式が登録されました！",
                color=discord.Color.gold()
            )
            
            # 数式を最大5件まで表示
            for i, formula in enumerate(formulas[:5]):
                title = formula.get('title', 'タイトル未設定')
                formula_type = formula.get('formula_type', '未分類')
                formula_text = formula.get('formula', 'N/A')
                
                # 数式が長い場合は短縮
                if len(formula_text) > 100:
                    formula_text = formula_text[:100] + "..."
                
                embed.add_field(
                    name=f"📐 {formula.get('id', 'N/A')} - {title}",
                    value=f"**タイプ:** {formula_type}\n**数式:** `{formula_text}`",
                    inline=False
                )
            
            # 5件を超える場合は件数を表示
            if len(formulas) > 5:
                embed.add_field(
                    name="📊 その他",
                    value=f"他に **{len(formulas) - 5}件** の数式があります。\n`/formula` コマンドで検索してみてください！",
                    inline=False
                )
            
            # フッター
            embed.set_footer(
                text="詳細を見るには /formula formula_id:ID を使用してください",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
            )
            
            # タイムスタンプ
            embed.timestamp = datetime.datetime.now()
            
            await channel.send(embed=embed)
            
            # 画像付きの数式がある場合は個別に送信
            image_formulas = [f for f in formulas[:3] if f.get('image_url')]  # 最大3件
            for formula in image_formulas:
                try:
                    detail_embed = discord.Embed(
                        title=f"🖼️ {formula.get('title', 'N/A')}",
                        description=format_formula_for_display(formula),
                        color=discord.Color.blue()
                    )
                    
                    if formula.get('image_url'):
                        detail_embed.set_image(url=formula['image_url'])
                    
                    await channel.send(embed=detail_embed)
                    
                    # レート制限対策で少し待機
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"画像付き数式送信エラー: {e}")
            
        except Exception as e:
            print(f"通知メッセージ送信エラー: {e}")
    
    async def manual_check(self, channel, test_date: str = None) -> int:
        """手動で指定日の数式をチェック（テスト用）"""
        try:
            if test_date:
                # テスト用の日付を使用
                try:
                    target_date = datetime.datetime.strptime(test_date, "%Y-%m-%d").date()
                    today_str = test_date
                except ValueError:
                    await channel.send("❌ 日付形式が正しくありません。YYYY-MM-DD形式で入力してください。")
                    return 0
            else:
                # 今日の日付を使用
                target_date = datetime.date.today()
                today_str = target_date.strftime("%Y-%m-%d")
            
            all_formulas = get_all_formulas()
            if not all_formulas:
                await channel.send("❌ 数式データが取得できませんでした。")
                return 0
            
            target_formulas = self._filter_today_formulas(all_formulas, today_str)
            
            if target_formulas:
                await self._send_notification(channel, target_formulas, target_date)
                return len(target_formulas)
            else:
                embed = discord.Embed(
                    title=f"📅 {target_date.strftime('%Y年%m月%d日')}の数式",
                    description="指定された日に登録された数式はありませんでした。",
                    color=discord.Color.light_grey()
                )
                embed.set_footer(text="他の日付でもお試しください！")
                await channel.send(embed=embed)
                return 0
                
        except Exception as e:
            await channel.send(f"❌ エラーが発生しました: {str(e)}")
            return 0
