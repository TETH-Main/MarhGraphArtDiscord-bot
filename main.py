import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from datetime import time, timezone, timedelta
from messages_gspread import get_message, get_all_messages
from firebase_client import FirebaseClient

# ログ設定
logging.basicConfig(level=logging.INFO)

# Intentsの設定
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
    
    async def setup_hook(self):
        """Bot起動時のセットアップ"""
        await self.tree.sync()
        print(f"Synced commands for {self.user}")
        
        # 定期通知タスクを開始
        self.daily_formula_notification.start()
    
    async def on_ready(self):
        """Bot準備完了時"""
        print(f'{self.user} has connected to Discord!')
        print(f'Bot is in {len(self.guilds)} guilds')
        print("Bot is ready and commands should be available!")
    
    @tasks.loop(time=time(hour=0, minute=0, tzinfo=timezone(timedelta(hours=9))))
    async def daily_formula_notification(self):
        """毎日0時（日本時間）の数式通知タスク"""
        try:
            # 通知チャンネルを環境変数から取得
            notification_channel_id = os.getenv('FORMULA_NOTIFICATION_CHANNEL_ID')
            if not notification_channel_id:
                print("FORMULA_NOTIFICATION_CHANNEL_ID環境変数が設定されていません。")
                return
            
            channel = self.get_channel(int(notification_channel_id))
            if not channel:
                print(f"通知チャンネル (ID: {notification_channel_id}) が見つかりません。")
                return
            
            # Firebaseから今日の数式を取得
            firebase_client = FirebaseClient()
            today_formulas = firebase_client.get_today_formulas()
            
            if not today_formulas:
                # 今日登録された数式がない場合
                embed = discord.Embed(
                    title="今日の数式登録",
                    description="今日はまだ新しい数式が登録されていません。",
                    color=0x888888
                )
                embed.set_footer(text="Graph + Library = Graphary")
                await channel.send(embed=embed)
                return
            
            # 数式が登録されている場合 - 各数式を個別のEmbedで送信
            for i, formula_data in enumerate(today_formulas):
                formatted_data = firebase_client.format_formula_for_discord(formula_data)
                
                # 個別のEmbedを作成
                embed = discord.Embed(
                    title=formatted_data['title'],
                    description=f"```\n{formatted_data['formula']}\n```",
                    color=0x00FF7F,
                    url=f"https://teth-main.github.io/Graphary/?formulaId={formatted_data['id']}"
                )
                
                # 数式タイプを追加
                if formatted_data['formula_type']:
                    type_list = "\n".join([f"`{t}`" for t in formatted_data['formula_type'].split(', ')])
                    embed.add_field(
                        name="数式タイプ",
                        value=type_list,
                        inline=True
                    )
                
                # タグを追加
                if formatted_data['tags'] and formatted_data['tags'] != 'なし':
                    tag_list = "\n".join([f"`{t}`" for t in formatted_data['tags'].split(', ')])
                    embed.add_field(
                        name="タグ",
                        value=tag_list,
                        inline=True
                    )
                
                # 画像を設定（必ずあるので大きく表示）
                if formatted_data['image_url']:
                    embed.set_image(url=formatted_data['image_url'])
                
                embed.set_footer(text="Graph + Library = Graphary")
                
                await channel.send(embed=embed)
                
                # 連続送信の間隔を少し空ける
                if i < len(today_formulas) - 1:
                    import asyncio
                    await asyncio.sleep(1)
            
            print(f"今日の数式通知を送信しました: {len(today_formulas)}件")
            
        except Exception as e:
            print(f"数式通知エラー: {e}")
    
    @daily_formula_notification.before_loop
    async def before_daily_notification(self):
        """通知タスク開始前の待機"""
        await self.wait_until_ready()
    
    async def on_member_join(self, member):
        """新しいメンバーがサーバーに参加した時"""
        try:
            # Welcomeチャンネルを環境変数から取得
            welcome_channel_id = os.getenv('WELCOME_CHANNEL_ID')
            if not welcome_channel_id:
                print("WELCOME_CHANNEL_ID環境変数が設定されていません。")
                return
            
            # チャンネルを取得
            channel = self.get_channel(int(welcome_channel_id))
            if not channel:
                print(f"Welcome チャンネル (ID: {welcome_channel_id}) が見つかりません。")
                return
            
            # Welcomeメッセージのembedを作成
            embed = discord.Embed(
                title="関数アートサーバへようこそ！ 🎉",
                description="Welcome to the Math Graph Art Server! 🎉",
                color=0x00FF7F  # 明るい緑色
            )
            
            # メンバーのアバターを設定
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            
            # フィールドを追加
            embed.add_field(
                name="まずは、認証ロールを貰いましょう！",
                value="First, get a Verified Human role!\nhttps://discord.com/channels/894421135985377290/894424053086044160/1078874458523189258",
                inline=False
            )
            
            embed.add_field(
                name="次に、自己紹介をしてみましょう！",
                value="Then, let's introduce ourselves in this channel!\n<#896354528641818635>",
                inline=False
            )
            
            embed.add_field(
                name="最後に、あなたに合うロールをつけましょう",
                value="Finally, get the role you need!\n<#1023514532544512141>",
                inline=False
            )
            
            # フッターを設定
            embed.set_footer(
                text=f"{member.display_name}さん、どうぞお楽しみください！",
                icon_url=member.avatar.url if member.avatar else member.default_avatar.url
            )
            
            # タイムスタンプを設定
            embed.timestamp = discord.utils.utcnow()
            
            # メッセージを送信
            await channel.send(f"{member.mention}", embed=embed)
            
            print(f"Welcome message sent for {member.name} ({member.id})")
            
        except Exception as e:
            print(f"Error sending welcome message: {e}")

bot = MyBot()

# 管理者ユーザーIDのリスト（環境変数から取得）
ADMIN_USER_IDS = []
if os.getenv('ADMIN_USER_IDS'):
    ADMIN_USER_IDS = [int(uid) for uid in os.getenv('ADMIN_USER_IDS').split(',')]

# 管理者ロール名のリスト（環境変数から取得）
ADMIN_ROLES = []
if os.getenv('ADMIN_ROLES'):
    ADMIN_ROLES = [role.strip() for role in os.getenv('ADMIN_ROLES').split(',')]

def is_admin(interaction: discord.Interaction) -> bool:
    """管理者かどうかチェック"""
    # ユーザーIDチェック
    if interaction.user.id in ADMIN_USER_IDS:
        return True
    
    # ロールチェック（サーバー内でのみ有効）
    if interaction.guild and hasattr(interaction.user, 'roles'):
        user_roles = [role.name for role in interaction.user.roles]
        if any(role in ADMIN_ROLES for role in user_roles):
            return True
    
    return False

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="admin_message", description="管理者限定メッセージコマンド")
@app_commands.describe(
    message_key="送信するメッセージのキー（オプション）",
    content="送信するメッセージの内容",
    embed_title="Embedのタイトル（オプション）",
    embed_description="Embedの説明（オプション）",
    embed_color="Embedの色（16進数、例: #FF0000）",
    channel="送信先チャンネル（オプション）"
)
async def admin_message_command(
    interaction: discord.Interaction,
    content: str = None,
    message_key: str = None,
    embed_title: str = None,
    embed_description: str = None,
    embed_color: str = None,
    channel: discord.TextChannel = None
):
    """管理者限定のメッセージコマンド"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    try:
        # メッセージキーが指定されている場合は、登録されたメッセージを使用
        if message_key:
            message_data = get_message(message_key)
            if message_data:
                content = message_data["content"]
                if "embed" in message_data:
                    embed_data = message_data["embed"]
                    embed_title = embed_data.get("title")
                    embed_description = embed_data.get("description")
                    embed_color = embed_data.get("color")
            else:
                await interaction.response.send_message(f"メッセージキー '{message_key}' が見つかりません。", ephemeral=True)
                return
        
        if not content:
            await interaction.response.send_message("メッセージの内容またはメッセージキーを指定してください。", ephemeral=True)
            return
        
        # 送信先チャンネルの決定
        target_channel = channel if channel else interaction.channel
        
        # Embedの作成
        if embed_title or embed_description:
            embed = discord.Embed()
            
            if embed_title:
                embed.title = embed_title
            
            if embed_description:
                embed.description = embed_description
            
            # 色の設定
            if embed_color:
                try:
                    color_hex = embed_color.lstrip('#')
                    embed.color = int(color_hex, 16)
                except ValueError:
                    embed.color = discord.Color.red()
            else:
                embed.color = discord.Color.red()
            
            embed.set_footer(text=f"管理者コマンド | 実行者: {interaction.user.display_name}")
            
            # メッセージとEmbedを送信
            await target_channel.send(content)
            await target_channel.send(embed=embed)
        else:
            # 通常のメッセージのみ送信
            await target_channel.send(content)
        
        # 実行確認メッセージ
        if target_channel != interaction.channel:
            await interaction.response.send_message(f"メッセージを {target_channel.mention} に送信しました。", ephemeral=True)
        else:
            await interaction.response.send_message("メッセージを送信しました。", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

@bot.tree.command(name="ping", description="Botの応答時間を確認します")
async def ping_command(interaction: discord.Interaction):
    """Ping コマンド"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! レイテンシ: {latency}ms")

@bot.tree.command(name="random_graphary", description="Grapharyからランダムに数式を1つ表示します")
async def random_graphary_command(interaction: discord.Interaction):
    """誰でも使える：ランダムな数式を表示"""
    try:
        await interaction.response.defer()
        
        # Firebaseからランダムな数式を取得
        firebase_client = FirebaseClient()
        random_formula = firebase_client.get_random_formula()
        
        if not random_formula:
            # 数式が見つからない場合
            embed = discord.Embed(
                title="数式が見つかりません",
                description="現在、表示できる数式がありません。",
                color=0x888888
            )
            embed.set_footer(text="Graph + Library = Graphary")
            await interaction.followup.send(embed=embed)
            return
        
        # 数式データをフォーマット
        formatted_data = firebase_client.format_formula_for_discord(random_formula)
        
        # Embedを作成（通知と同じスタイル）
        embed = discord.Embed(
            title=formatted_data['title'],
            description=f"```\n{formatted_data['formula']}\n```",
            color=0x00FF7F,
            url=f"https://teth-main.github.io/Graphary/?formulaId={formatted_data['id']}"
        )
        
        # 数式タイプを追加
        if formatted_data['formula_type']:
            type_list = "\n".join([f"`{t}`" for t in formatted_data['formula_type'].split(', ')])
            embed.add_field(
                name="数式タイプ",
                value=type_list,
                inline=True
            )
        
        # タグを追加
        if formatted_data['tags'] and formatted_data['tags'] != 'なし':
            tag_list = "\n".join([f"`{t}`" for t in formatted_data['tags'].split(', ')])
            embed.add_field(
                name="タグ",
                value=tag_list,
                inline=True
            )
        
        # 画像を設定（大きく表示）
        if formatted_data['image_url']:
            embed.set_image(url=formatted_data['image_url'])
        
        embed.set_footer(text="Graph + Library = Graphary")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="register_graphary", description="管理者限定：Grapharyに新しい数式を登録します")
async def register_graphary_command(interaction: discord.Interaction):
    """管理者限定：数式登録"""
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    try:
        # 基本情報入力モーダルを作成
        modal = FormulaRegistrationModal()
        await interaction.response.send_modal(modal)
        
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

class FormulaRegistrationModal(discord.ui.Modal, title='数式登録 - 基本情報'):
    def __init__(self):
        super().__init__()
    
    title_input = discord.ui.TextInput(
        label='タイトル',
        placeholder='数式のタイトルを入力してください',
        required=True,
        max_length=100
    )
    
    title_en_input = discord.ui.TextInput(
        label='英語タイトル（オプション）',
        placeholder='English title (optional)',
        required=False,
        max_length=100
    )
    
    formula_input = discord.ui.TextInput(
        label='数式',
        placeholder='数式を入力してください\n例: y = sin(x) * cos(x)',
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    image_url_input = discord.ui.TextInput(
        label='画像URL',
        placeholder='https://example.com/image.png',
        required=True,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 入力データを保存（次のステップで使用）
            self.formula_data = {
                'title': self.title_input.value.strip(),
                'title_EN': self.title_en_input.value.strip() if self.title_en_input.value else '',
                'formula': self.formula_input.value.strip(),
                'image_url': self.image_url_input.value.strip()
            }
            
            # URL形式の簡易チェック
            if not (self.formula_data['image_url'].startswith('http://') or 
                   self.formula_data['image_url'].startswith('https://')):
                await interaction.followup.send("画像URLが正しい形式ではありません。http://またはhttps://で始まるURLを入力してください。", ephemeral=True)
                return
            
            # 数式タイプ選択メニューを表示
            view = FormulaTypeSelectView(self.formula_data, interaction.user)
            embed = discord.Embed(
                title="数式タイプを選択",
                description="この数式に当てはまるタイプを選択してください（複数選択可能）",
                color=0x00FF7F
            )
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)

class FormulaTypeSelectView(discord.ui.View):
    def __init__(self, formula_data, user):
        super().__init__(timeout=300)
        self.formula_data = formula_data
        self.user = user
        
    @discord.ui.select(
        placeholder="数式タイプを選択してください（複数選択可）",
        min_values=1,
        max_values=6,
        options=[
            discord.SelectOption(label="関数", value="関数"),
            discord.SelectOption(label="陰関数", value="陰関数"),
            discord.SelectOption(label="媒介変数", value="媒介変数"),
            discord.SelectOption(label="極座標", value="極座標"),
            discord.SelectOption(label="複素数", value="複素数"),
            discord.SelectOption(label="3D", value="3D"),
        ]
    )
    async def formula_type_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            if interaction.user != self.user:
                await interaction.response.send_message("このメニューは他のユーザーが開始した登録プロセスです。", ephemeral=True)
                return
                
            await interaction.response.defer(ephemeral=True)
            
            # 選択された数式タイプをカンマ区切りで保存
            self.formula_data['formula_type'] = ', '.join(select.values)
            
            # タグ選択フェーズに進む
            firebase_client = FirebaseClient()
            tags = firebase_client.get_all_tags()
            
            if not tags:
                await interaction.followup.send("タグの取得に失敗しました。", ephemeral=True)
                return
            
            # タグリストを表示
            tag_list = []
            for i, tag in enumerate(tags, 1):
                tag_list.append(f"`{i}. {tag['tagName']}`")
            
            # タグリストを複数メッセージに分割（2000文字制限対応）
            tag_text = " ".join(tag_list)
            if len(tag_text) > 1800:  # 余裕を持って1800文字で区切り
                # タグを半分に分ける
                mid_point = len(tags) // 2
                tag_text1 = " ".join(tag_list[:mid_point])
                tag_text2 = " ".join(tag_list[mid_point:])
                
                embed1 = discord.Embed(
                    title="利用可能なタグ一覧 (1/2)",
                    description=tag_text1,
                    color=0x00FF7F
                )
                embed2 = discord.Embed(
                    title="利用可能なタグ一覧 (2/2)",
                    description=tag_text2,
                    color=0x00FF7F
                )
                await interaction.followup.send(embed=embed1, ephemeral=True)
                await interaction.followup.send(embed=embed2, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="利用可能なタグ一覧",
                    description=tag_text,
                    color=0x00FF7F
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            
            # タグ入力用のモーダルを表示
            tag_modal = TagSelectionModal(self.formula_data, tags, self.user)
            await interaction.followup.send("タグを選択してください:", view=TagSelectionView(tag_modal), ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)

class TagSelectionView(discord.ui.View):
    def __init__(self, tag_modal):
        super().__init__(timeout=300)
        self.tag_modal = tag_modal
        
    @discord.ui.button(label="タグを入力", style=discord.ButtonStyle.primary)
    async def open_tag_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(self.tag_modal)

class TagSelectionModal(discord.ui.Modal, title='タグ選択'):
    def __init__(self, formula_data, tags, user):
        super().__init__()
        self.formula_data = formula_data
        self.tags = tags
        self.user = user
    
    tag_input = discord.ui.TextInput(
        label='タグ番号',
        placeholder='番号をカンマ区切りで入力: 例 1, 3, 10\nタグなしの場合は「なし」',
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            tag_input = self.tag_input.value.strip()
            
            # タグIDの処理
            if tag_input.lower() == 'なし':
                self.formula_data['tags'] = ''
                selected_tag_names = ['なし']
            else:
                # 番号をパース
                try:
                    tag_numbers = [int(num.strip()) for num in tag_input.split(',') if num.strip()]
                    tag_ids = []
                    selected_tag_names = []
                    
                    for num in tag_numbers:
                        if 1 <= num <= len(self.tags):
                            tag_data = self.tags[num - 1]  # 0ベースのインデックス
                            tag_ids.append(str(tag_data['tagID']))
                            selected_tag_names.append(tag_data['tagName'])
                        else:
                            await interaction.followup.send(f"無効なタグ番号です: {num} (1-{len(self.tags)}の範囲で入力してください)", ephemeral=True)
                            return
                    
                    # 重複を除去
                    tag_ids = list(dict.fromkeys(tag_ids))  # 順序を保持して重複除去
                    selected_tag_names = list(dict.fromkeys(selected_tag_names))
                    
                    self.formula_data['tags'] = ', '.join(tag_ids)
                    
                except ValueError:
                    await interaction.followup.send("タグ番号は数字で入力してください。例: 1, 3, 10", ephemeral=True)
                    return
            
            # 最終確認画面を表示
            embed = discord.Embed(
                title="数式登録確認",
                description="以下の内容で登録します。よろしいですか？",
                color=0x00FF7F
            )
            
            embed.add_field(name="タイトル", value=self.formula_data['title'], inline=False)
            if self.formula_data['title_EN']:
                embed.add_field(name="英語タイトル", value=self.formula_data['title_EN'], inline=False)
            
            formula_preview = self.formula_data['formula'][:100]
            if len(self.formula_data['formula']) > 100:
                formula_preview += "..."
            embed.add_field(name="数式", value=f"```\n{formula_preview}\n```", inline=False)
            
            embed.add_field(name="数式タイプ", value=self.formula_data['formula_type'], inline=True)
            embed.add_field(name="タグ", value=', '.join(selected_tag_names), inline=True)
            embed.add_field(name="画像URL", value=self.formula_data['image_url'], inline=False)
            
            # 画像プレビュー
            try:
                embed.set_image(url=self.formula_data['image_url'])
            except:
                pass
            
            view = ConfirmRegistrationView(self.formula_data, self.user)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)

class ConfirmRegistrationView(discord.ui.View):
    def __init__(self, formula_data, user):
        super().__init__(timeout=300)
        self.formula_data = formula_data
        self.user = user
        
    @discord.ui.button(label="✅ 登録する", style=discord.ButtonStyle.success)
    async def confirm_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user != self.user:
                await interaction.response.send_message("この登録は他のユーザーが開始したものです。", ephemeral=True)
                return
                
            await interaction.response.defer(ephemeral=True)
            
            # Firebase経由でGASに登録
            firebase_client = FirebaseClient()
            
            # newTagsフィールドを追加（現在は空だが、将来的に新規タグ機能を追加可能）
            registration_data = {
                **self.formula_data,
                'newTags': ''  # 現在は新規タグなし、将来的に機能追加可能
            }
            
            result = firebase_client.register_formula_via_gas(registration_data)
            
            # 登録完了通知
            embed = discord.Embed(
                title="✅ 登録完了",
                description="数式が正常に登録されました！",
                color=0x00FF00
            )
            embed.add_field(name="登録ID", value=result.get('id', '不明'), inline=False)
            embed.add_field(
                name="Grapharyで確認", 
                value=f"[こちらをクリック](https://teth-main.github.io/Graphary/?formulaId={result.get('id', '')})", 
                inline=False
            )
            embed.set_footer(text="Graph + Library = Graphary")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # 登録完了を公開チャンネルにも通知（オプション）
            public_embed = discord.Embed(
                title="📝 新しい数式が登録されました",
                description=f"**{self.formula_data['title']}** が登録されました！",
                color=0x00FF7F
            )
            public_embed.add_field(name="登録者", value=interaction.user.mention, inline=True)
            public_embed.add_field(name="数式タイプ", value=self.formula_data['formula_type'], inline=True)
            public_embed.set_footer(text="Graph + Library = Graphary")
            
            await interaction.channel.send(embed=public_embed)
            
        except Exception as e:
            await interaction.followup.send(f"登録エラー: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="❌ キャンセル", style=discord.ButtonStyle.danger)
    async def cancel_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("この登録は他のユーザーが開始したものです。", ephemeral=True)
            return
            
        await interaction.response.send_message("数式登録をキャンセルしました。", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="list_messages", description="管理者限定：利用可能なメッセージキー一覧を表示")
async def list_messages_command(interaction: discord.Interaction):
    """管理者限定：利用可能なメッセージキー一覧を表示"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    messages = get_all_messages()
    if messages:
        embed = discord.Embed(
            title="📝 利用可能なメッセージキー",
            color=discord.Color.blue()
        )
        for msg in messages:
            key = msg.get("key")
            content = msg.get("content", "")
            # コンテンツが長い場合は短縮
            if len(content) > 100:
                content = content[:100] + "..."
            embed_info = ""
            embed_data = msg.get("embed", {})
            if embed_data:
                embed_info = f"\n**Embed:** {embed_data.get('title', 'タイトルなし')}"
            embed.add_field(
                name=f"`{key}`",
                value=f"**Content:** {content}{embed_info}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("登録されているメッセージがありません。", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="edit_message", description="管理者限定：登録済みメッセージを編集")
@app_commands.describe(
    message_key="編集するメッセージのキー",
    new_content="新しいメッセージ内容（オプション）",
    new_embed_title="新しいEmbedタイトル（オプション）",
    new_embed_description="新しいEmbed説明（オプション）",
    new_embed_color="新しいEmbed色（16進数、例: #FF0000）（オプション）"
)
async def edit_message_command(
    interaction: discord.Interaction,
    message_key: str,
    new_content: str = None,
    new_embed_title: str = None,
    new_embed_description: str = None,
    new_embed_color: str = None
):
    """管理者限定：登録済みメッセージを編集"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    try:
        # 既存のメッセージを取得
        existing_message = get_message(message_key)
        if not existing_message:
            await interaction.response.send_message(f"メッセージキー '{message_key}' が見つかりません。", ephemeral=True)
            return
        
        # 新しいメッセージデータを作成
        updated_message = existing_message.copy()
        
        # コンテンツの更新
        if new_content:
            updated_message["content"] = new_content
        
        # Embedの更新
        if new_embed_title or new_embed_description or new_embed_color:
            if "embed" not in updated_message:
                updated_message["embed"] = {}
            
            if new_embed_title:
                updated_message["embed"]["title"] = new_embed_title
            
            if new_embed_description:
                updated_message["embed"]["description"] = new_embed_description
            
            if new_embed_color:
                updated_message["embed"]["color"] = new_embed_color
        
        # メッセージを更新（スプレッドシートAPIで更新）
        from messages_gspread import add_or_update_message
        success = add_or_update_message(message_key, updated_message["content"], updated_message.get("embed", {}))
        
        # 確認メッセージを送信
        embed = discord.Embed(
            title="✅ メッセージ編集完了",
            description=f"メッセージキー `{message_key}` を更新しました。",
            color=discord.Color.green()
        )
        
        # 更新された内容を表示
        embed.add_field(name="更新後のコンテンツ", value=updated_message["content"], inline=False)
        
        if "embed" in updated_message:
            embed_data = updated_message["embed"]
            embed_info = f"**タイトル:** {embed_data.get('title', 'なし')}\n"
            embed_info += f"**説明:** {embed_data.get('description', 'なし')}\n"
            embed_info += f"**色:** {embed_data.get('color', 'なし')}"
            embed.add_field(name="Embed情報", value=embed_info, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="add_message", description="管理者限定：新しいメッセージキーを追加")
@app_commands.describe(
    message_key="新しいメッセージのキー",
    content="メッセージの内容",
    embed_title="Embedのタイトル（オプション）",
    embed_description="Embedの説明（オプション）",
    embed_color="Embedの色（16進数、例: #FF0000）（オプション）"
)
async def add_message_command(
    interaction: discord.Interaction,
    message_key: str,
    content: str,
    embed_title: str = None,
    embed_description: str = None,
    embed_color: str = None
):
    """管理者限定：新しいメッセージキーを追加"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    try:
        # 既存のキーかチェック
        existing_message = get_message(message_key)
        if existing_message:
            await interaction.response.send_message(f"メッセージキー '{message_key}' は既に存在します。編集したい場合は `/edit_message` を使用してください。", ephemeral=True)
            return
        
        # 新しいメッセージデータを作成
        new_message = {"content": content}
        
        # Embedデータがある場合は追加
        if embed_title or embed_description or embed_color:
            embed_data = {}
            if embed_title:
                embed_data["title"] = embed_title
            if embed_description:
                embed_data["description"] = embed_description
            if embed_color:
                embed_data["color"] = embed_color
            new_message["embed"] = embed_data
        
        # メッセージを追加（スプレッドシートAPIで追加）
        from messages_gspread import add_or_update_message
        success = add_or_update_message(message_key, new_message["content"], new_message.get("embed", {}))
        
        # 確認メッセージを送信
        embed = discord.Embed(
            title="✅ メッセージ追加完了",
            description=f"新しいメッセージキー `{message_key}` を追加しました。",
            color=discord.Color.green()
        )
        
        # 追加された内容を表示
        embed.add_field(name="コンテンツ", value=content, inline=False)
        
        if "embed" in new_message:
            embed_data = new_message["embed"]
            embed_info = f"**タイトル:** {embed_data.get('title', 'なし')}\n"
            embed_info += f"**説明:** {embed_data.get('description', 'なし')}\n"
            embed_info += f"**色:** {embed_data.get('color', 'なし')}"
            embed.add_field(name="Embed情報", value=embed_info, inline=False)
        
        embed.set_footer(text="⚠️ 注意: Bot再起動時に変更は失われます")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="remove_message", description="管理者限定：メッセージキーを削除")
@app_commands.describe(
    message_key="削除するメッセージのキー"
)
async def remove_message_command(
    interaction: discord.Interaction,
    message_key: str
):
    """管理者限定：メッセージキーを削除"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    try:
        # メッセージが存在するかチェック
        existing_message = get_message(message_key)
        if not existing_message:
            await interaction.response.send_message(f"メッセージキー '{message_key}' が見つかりません。", ephemeral=True)
            return
        
        # メッセージを削除（スプレッドシートAPIで削除）
        from messages_gspread import remove_message
        success = remove_message(message_key)
        
        # 確認メッセージを送信
        embed = discord.Embed(
            title="🗑️ メッセージ削除完了",
            description=f"メッセージキー `{message_key}` を削除しました。",
            color=discord.Color.red()
        )
        embed.set_footer(text="⚠️ 注意: Bot再起動時に変更は失われます")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="edit_bot_message", description="管理者限定：Botが送信した過去のメッセージを編集")
@app_commands.describe(
    message_id="編集するメッセージのID",
    new_content="新しいメッセージ内容（オプション）",
    new_embed_title="新しいEmbedタイトル（オプション）",
    new_embed_description="新しいEmbed説明（オプション）",
    new_embed_color="新しいEmbed色（16進数、例: #FF0000）（オプション）",
    channel="メッセージがあるチャンネル（オプション、省略時は現在のチャンネル）"
)
async def edit_bot_message_command(
    interaction: discord.Interaction,
    message_id: str,
    new_content: str = None,
    new_embed_title: str = None,
    new_embed_description: str = None,
    new_embed_color: str = None,
    channel: discord.TextChannel = None
):
    """管理者限定：Botが送信した過去のメッセージを編集"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    try:
        # チャンネルの決定
        target_channel = channel if channel else interaction.channel
        
        # メッセージIDを整数に変換
        try:
            msg_id = int(message_id)
        except ValueError:
            await interaction.response.send_message("無効なメッセージIDです。", ephemeral=True)
            return
        
        # メッセージを取得
        try:
            message = await target_channel.fetch_message(msg_id)
        except discord.NotFound:
            await interaction.response.send_message("指定されたメッセージが見つかりません。", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.response.send_message("メッセージにアクセスする権限がありません。", ephemeral=True)
            return
        
        # Botが送信したメッセージか確認
        if message.author != bot.user:
            await interaction.response.send_message("このメッセージはBotが送信したものではありません。", ephemeral=True)
            return
        
        # 編集内容が何も指定されていない場合
        if not any([new_content, new_embed_title, new_embed_description, new_embed_color]):
            await interaction.response.send_message("編集する内容を少なくとも1つ指定してください。", ephemeral=True)
            return
        
        # 現在の内容を取得
        current_content = message.content if message.content else None
        current_embeds = message.embeds
        
        # 新しい内容を設定
        edited_content = new_content if new_content else current_content
        
        # Embedの処理
        edited_embed = None
        if new_embed_title or new_embed_description or new_embed_color:
            # 既存のEmbedがある場合はそれをベースにする
            if current_embeds:
                embed_dict = current_embeds[0].to_dict()
                edited_embed = discord.Embed.from_dict(embed_dict)
            else:
                edited_embed = discord.Embed()
            
            # 新しいEmbed内容を設定
            if new_embed_title:
                edited_embed.title = new_embed_title
            if new_embed_description:
                edited_embed.description = new_embed_description
            if new_embed_color:
                try:
                    color_hex = new_embed_color.lstrip('#')
                    edited_embed.color = int(color_hex, 16)
                except ValueError:
                    edited_embed.color = discord.Color.blue()
        elif current_embeds:
            # 新しいEmbed情報がないが既存のEmbedがある場合はそのまま保持
            edited_embed = current_embeds[0]
        
        # メッセージを編集
        if edited_embed:
            await message.edit(content=edited_content, embed=edited_embed)
        else:
            await message.edit(content=edited_content)
        
        # 確認メッセージを送信
        confirm_embed = discord.Embed(
            title="✅ メッセージ編集完了",
            description=f"メッセージID `{message_id}` を編集しました。",
            color=discord.Color.green()
        )
        
        if target_channel != interaction.channel:
            confirm_embed.add_field(
                name="編集されたメッセージ", 
                value=f"[こちらをクリック](https://discord.com/channels/{interaction.guild.id}/{target_channel.id}/{message_id})",
                inline=False
            )
        
        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="get_message_id", description="管理者限定：指定したメッセージのIDを取得")
@app_commands.describe(
    message_link="メッセージのリンクまたはメッセージID"
)
async def get_message_id_command(
    interaction: discord.Interaction,
    message_link: str
):
    """管理者限定：指定したメッセージのIDを取得（メッセージリンクから）"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    try:
        # メッセージリンクからIDを抽出
        if "discord.com/channels/" in message_link:
            # Discord メッセージリンクの形式: https://discord.com/channels/guild_id/channel_id/message_id
            parts = message_link.split("/")
            if len(parts) >= 3:
                message_id = parts[-1]
                channel_id = parts[-2]
                guild_id = parts[-3]
                
                embed = discord.Embed(
                    title="📋 メッセージ情報",
                    color=discord.Color.blue()
                )
                embed.add_field(name="メッセージID", value=f"`{message_id}`", inline=False)
                embed.add_field(name="チャンネルID", value=f"`{channel_id}`", inline=False)
                embed.add_field(name="サーバーID", value=f"`{guild_id}`", inline=False)
                embed.add_field(
                    name="使用例", 
                    value=f"`/edit_bot_message message_id:{message_id} new_content:新しいメッセージ内容`",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("無効なメッセージリンクです。", ephemeral=True)
        else:
            # 数字のみの場合はメッセージIDとして扱う
            try:
                int(message_link)
                embed = discord.Embed(
                    title="📋 メッセージID確認",
                    description=f"メッセージID: `{message_link}`",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="使用例", 
                    value=f"`/edit_bot_message message_id:{message_link} new_content:新しいメッセージ内容`",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except ValueError:
                await interaction.response.send_message("無効な形式です。メッセージリンクまたはメッセージIDを入力してください。", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="extract_embed_text", description="管理者限定：Botが送信したEmbedメッセージをプレーンテキストで出力")
@app_commands.describe(
    message_id="対象メッセージのID",
    channel="メッセージがあるチャンネル（オプション、省略時は現在のチャンネル）"
)
async def extract_embed_text_command(
    interaction: discord.Interaction,
    message_id: str,
    channel: discord.TextChannel = None
):
    """管理者限定：Botが送信したEmbedメッセージをプレーンテキストで出力（長文は分割表示）"""
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    try:
        # チャンネルの決定
        target_channel = channel if channel else interaction.channel
        # メッセージIDを整数に変換
        try:
            msg_id = int(message_id)
        except ValueError:
            await interaction.response.send_message("無効なメッセージIDです。", ephemeral=True)
            return
        # メッセージを取得
        try:
            message = await target_channel.fetch_message(msg_id)
        except discord.NotFound:
            await interaction.response.send_message("指定されたメッセージが見つかりません。", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.response.send_message("メッセージにアクセスする権限がありません。", ephemeral=True)
            return
        # Botが送信したメッセージか確認
        if message.author != bot.user:
            await interaction.response.send_message("このメッセージはBotが送信したものではありません。", ephemeral=True)
            return
        # Embedがあるか確認
        if not message.embeds:
            await interaction.response.send_message("このメッセージにはEmbedがありません。", ephemeral=True)
            return
        embed = message.embeds[0]
        # Embed内容をテキスト化
        text_parts = []
        if embed.title:
            text_parts.append(f"タイトル: {embed.title}")
        if embed.description:
            text_parts.append(f"説明: {embed.description}")
        for field in embed.fields:
            text_parts.append(f"{field.name}: {field.value}")
        if embed.footer and embed.footer.text:
            text_parts.append(f"フッター: {embed.footer.text}")
        # 結果を送信
        plain_text = "\n".join(text_parts)
        if not plain_text:
            plain_text = "Embedに表示可能なテキストがありません。"
        # 2000文字ごとに分割して送信
        max_length = 2000
        chunks = [plain_text[i:i+max_length] for i in range(0, len(plain_text), max_length)]
        for idx, chunk in enumerate(chunks):
            if idx == 0:
                await interaction.response.send_message(f"```{chunk}```", ephemeral=True)
            else:
                await interaction.followup.send(f"```{chunk}```", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="send_formula_notification", description="管理者限定：今日の数式通知を手動送信")
async def send_formula_notification_command(interaction: discord.Interaction):
    """管理者限定：今日の数式通知を手動送信"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        # Firebaseから今日の数式を取得
        firebase_client = FirebaseClient()
        today_formulas = firebase_client.get_today_formulas()
        
        if not today_formulas:
            # 今日登録された数式がない場合
            embed = discord.Embed(
                title="今日の数式登録",
                description="今日はまだ新しい数式が登録されていません。",
                color=0x888888
            )
            embed.set_footer(text="Graph + Library = Graphary")
            await interaction.channel.send(embed=embed)
            await interaction.followup.send("通知を送信しました（今日の登録なし）", ephemeral=True)
            return
        
        # 数式が登録されている場合 - 各数式を個別のEmbedで送信
        for i, formula_data in enumerate(today_formulas):
            formatted_data = firebase_client.format_formula_for_discord(formula_data)
            
            # 個別のEmbedを作成
            embed = discord.Embed(
                title=formatted_data['title'],
                description=f"```\n{formatted_data['formula']}\n```",
                color=0x00FF7F,
                url=f"https://teth-main.github.io/Graphary/?formulaId={formatted_data['id']}"
            )
            
            # 数式タイプを追加
            if formatted_data['formula_type']:
                type_list = "\n".join([f"`{t}`" for t in formatted_data['formula_type'].split(', ')])
                embed.add_field(
                    name="数式タイプ",
                    value=type_list,
                    inline=True
                )
            
            # タグを追加
            if formatted_data['tags'] and formatted_data['tags'] != 'なし':
                tag_list = "\n".join([f"`{t}`" for t in formatted_data['tags'].split(', ')])
                embed.add_field(
                    name="タグ",
                    value=tag_list,
                    inline=True
                )
            
            # 画像を設定（必ずあるので大きく表示）
            if formatted_data['image_url']:
                embed.set_image(url=formatted_data['image_url'])
            
            embed.set_footer(text="Graph + Library = Graphary")
            
            await interaction.channel.send(embed=embed)
            
            # 連続送信の間隔を少し空ける
            if i < len(today_formulas) - 1:
                import asyncio
                await asyncio.sleep(1)
        
        await interaction.followup.send(f"今日の数式通知を送信しました: {len(today_formulas)}件", ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="test_formula_embed", description="管理者限定：数式通知のEmbedスタイルをテスト表示")
async def test_formula_embed_command(interaction: discord.Interaction):
    """管理者限定：数式通知のEmbedスタイルをテスト表示"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        # テスト用のサンプルデータを作成
        sample_formulas = [
            {
                'id': 'test001',
                'title': 'サンプル数式1：美しい螺旋',
                'title_EN': 'Sample Formula 1: Beautiful Spiral',
                'formula': 'r = a * theta^2 + b * sin(c * theta)',
                'formula_type': ['極座標', '螺旋'],
                'tags': ['美しい', '螺旋', '数学アート'],
                'image_url': 'https://via.placeholder.com/600x400/FF6B6B/FFFFFF?text=Sample+Formula+1',
                'timestamp': '2025/07/19 12:30:45'
            },
            {
                'id': 'test002',
                'title': 'サンプル数式2：フラクタル図形',
                'title_EN': 'Sample Formula 2: Fractal Pattern',
                'formula': 'z_{n+1} = z_n^2 + c, where c = -0.7269 + 0.1889i',
                'formula_type': ['複素数', 'フラクタル'],
                'tags': ['フラクタル', '複素数', 'マンデルブロ'],
                'image_url': 'https://via.placeholder.com/600x400/4ECDC4/FFFFFF?text=Sample+Formula+2',
                'timestamp': '2025/07/19 15:22:10'
            },
            {
                'id': 'test003',
                'title': 'サンプル数式3：波動パターン',
                'title_EN': 'Sample Formula 3: Wave Pattern',
                'formula': 'y = A * sin(ωx + φ) * exp(-αx)',
                'formula_type': ['三角関数', '減衰波'],
                'tags': ['波動', '三角関数', '物理'],
                'image_url': 'https://via.placeholder.com/600x400/45B7D1/FFFFFF?text=Sample+Formula+3',
                'timestamp': '2025/07/19 18:45:33'
            }
        ]
        
        # テスト用Embedを作成（実際の通知と同じスタイル）
        embed = discord.Embed(
            title="サンプル数式1：美しい螺旋",
            description="```\nr = a * theta^2 + b * sin(c * theta)\n```",
            color=0x00FF7F,
            url="https://teth-main.github.io/Graphary/?formulaId=test001"
        )
        
        # 数式タイプを追加
        embed.add_field(
            name="数式タイプ",
            value="`極座標`\n`螺旋`",
            inline=True
        )
        
        # タグを追加
        embed.add_field(
            name="タグ",
            value="`美しい`\n`螺旋`\n`数学アート`",
            inline=True
        )
        
        # 画像を設定（大きく表示）
        embed.set_image(url="https://via.placeholder.com/600x400/FF6B6B/FFFFFF?text=Sample+Formula+1")
        
        embed.set_footer(text="Graph + Library = Graphary")
        
        await interaction.channel.send(embed=embed)
        await interaction.followup.send("テスト用のEmbed表示を送信しました（新スタイル）。", ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="check_formula_status", description="管理者限定：現在のFirebase接続状況と今日の数式登録状況を確認")
async def check_formula_status_command(interaction: discord.Interaction):
    """管理者限定：現在のFirebase接続状況と今日の数式登録状況を確認"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        # Firebase接続テスト
        try:
            firebase_client = FirebaseClient()
            connection_status = "✅ 正常"
        except Exception as e:
            connection_status = f"❌ エラー: {str(e)}"
            await interaction.followup.send(f"Firebase接続エラー: {str(e)}", ephemeral=True)
            return
        
        # 今日の数式取得テスト
        try:
            today_formulas = firebase_client.get_today_formulas()
            formula_count = len(today_formulas)
            formula_status = f"✅ 今日の登録: {formula_count}件"
        except Exception as e:
            formula_status = f"❌ 取得エラー: {str(e)}"
            formula_count = 0
        
        # ステータス情報をEmbedで表示
        embed = discord.Embed(
            title="🔍 Firebase 接続・データ状況",
            color=0x00FF7F if connection_status.startswith("✅") else 0xFF0000
        )
        
        embed.add_field(
            name="Firebase接続状況",
            value=connection_status,
            inline=False
        )
        
        embed.add_field(
            name="今日の数式登録状況",
            value=formula_status,
            inline=False
        )
        
        # 環境変数チェック
        env_checks = []
        required_envs = [
            ('FIREBASE_CREDENTIALS', 'Firebase認証情報'),
            ('FORMULA_NOTIFICATION_CHANNEL_ID', '通知チャンネルID')
        ]
        
        for env_var, description in required_envs:
            value = os.getenv(env_var)
            if value:
                env_checks.append(f"✅ {description}")
            else:
                env_checks.append(f"❌ {description} (未設定)")
        
        embed.add_field(
            name="環境変数設定状況",
            value="\n".join(env_checks),
            inline=False
        )
        
        # 通知チャンネル確認
        notification_channel_id = os.getenv('FORMULA_NOTIFICATION_CHANNEL_ID')
        if notification_channel_id:
            try:
                channel = bot.get_channel(int(notification_channel_id))
                if channel:
                    channel_status = f"✅ チャンネル: #{channel.name}"
                else:
                    channel_status = "❌ チャンネルが見つかりません"
            except:
                channel_status = "❌ 無効なチャンネルID"
        else:
            channel_status = "❌ チャンネルID未設定"
        
        embed.add_field(
            name="通知チャンネル状況",
            value=channel_status,
            inline=False
        )
        
        # 次回通知予定時刻
        from datetime import datetime
        jst = timezone(timedelta(hours=9))
        now_jst = datetime.now(jst)
        next_notification = now_jst.replace(hour=0, minute=0, second=0, microsecond=0)
        if next_notification <= now_jst:
            next_notification += timedelta(days=1)
        
        embed.add_field(
            name="次回自動通知予定",
            value=f"🕐 {next_notification.strftime('%Y/%m/%d %H:%M:%S')} (JST)",
            inline=False
        )
        
        embed.set_footer(text="Math Graph Art - System Status")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"ステータス確認エラー: {str(e)}", ephemeral=True)


# Botの実行
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("エラー: DISCORD_BOT_TOKEN環境変数が設定されていません。")
    else:
        bot.run(token)
