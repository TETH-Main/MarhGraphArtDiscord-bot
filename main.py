import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from datetime import time, timezone, timedelta
from messages_gspread import get_message, get_all_messages
from firebase_client import FirebaseClient
from gas_client import GASClient

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
    
    @tasks.loop(time=time(hour=0, minute=10, tzinfo=timezone(timedelta(hours=9))))
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

@bot.tree.command(name="random_graphary", description="Grapharyからランダムに数式を1つ表示します / Display a random formula from Graphary")
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

@bot.tree.command(name="register_graphary", description="Grapharyに新しい数式を登録します / Register a new formula to Graphary")
async def register_graphary_command(interaction: discord.Interaction):
    """誰でも使える：数式登録コマンド"""
    try:
        # 数式登録モーダルを表示
        modal = FormulaRegistrationModal()
        await interaction.response.send_modal(modal)
        
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

class FormulaRegistrationModal(discord.ui.Modal):
    """数式登録モーダル"""
    
    def __init__(self):
        super().__init__(title="数式登録 / Formula Registration")
        
        # タイトル（必須）
        self.title_input = discord.ui.TextInput(
            label="タイトル / Title",
            placeholder="数式のタイトルを入力してください / Enter the formula title",
            required=True,
            max_length=100
        )
        self.add_item(self.title_input)
        
        # 英語タイトル（オプション）
        self.title_en_input = discord.ui.TextInput(
            label="英語タイトル / English Title",
            placeholder="English title (optional)",
            required=False,
            max_length=100
        )
        self.add_item(self.title_en_input)
        
        # 数式（必須）
        self.formula_input = discord.ui.TextInput(
            label="数式 / Formula",
            placeholder="LaTeX形式で数式を入力してください / Enter formula in LaTeX format (e.g., x^2 + y^2 = 1)",
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )
        self.add_item(self.formula_input)
        
        # 画像URL（必須）
        self.image_url_input = discord.ui.TextInput(
            label="画像URL / Image URL",
            placeholder="外部からアクセスできる画像URLなら何でもOK / Any externally accessible image URL (e.g., https://example.com/image.png)",
            required=True,
            max_length=500
        )
        self.add_item(self.image_url_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """モーダル送信時の処理"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 入力データを保存
            self.form_data = {
                'title': self.title_input.value.strip(),
                'title_EN': self.title_en_input.value.strip(),
                'formula': self.formula_input.value.strip(),
                'image_url': self.image_url_input.value.strip()
            }
            
            # 数式タイプ選択メニューを表示
            view = FormulaTypeSelectView(self.form_data)
            embed = discord.Embed(
                title="数式タイプ選択 / Formula Type Selection",
                description="数式のタイプを選択してください（複数選択可能）：\nSelect formula types (multiple selection allowed):",
                color=0x00FF7F
            )
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)

class FormulaTypeSelectView(discord.ui.View):
    """数式タイプ選択ビュー"""
    
    def __init__(self, form_data):
        super().__init__(timeout=300)
        self.form_data = form_data
        
        # 数式タイプ選択メニュー
        self.type_select = FormulaTypeSelect(form_data)
        self.add_item(self.type_select)

class FormulaTypeSelect(discord.ui.Select):
    """数式タイプ選択メニュー"""
    
    def __init__(self, form_data):
        self.form_data = form_data
        
        # 選択肢を定義
        options = [
            discord.SelectOption(label="関数", value="関数", description="functions"),
            discord.SelectOption(label="陰関数", value="陰関数", description="implicit functions"),
            discord.SelectOption(label="媒介変数", value="媒介変数", description="parametric"),
            discord.SelectOption(label="極座標", value="極座標", description="polar coordinates"),
            discord.SelectOption(label="複素数", value="複素数", description="complex numbers"),
            discord.SelectOption(label="3D", value="3D", description="3D"),
        ]
        
        super().__init__(
            placeholder="数式タイプを選択 / Select formula types",
            min_values=1,
            max_values=len(options),
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """数式タイプ選択時の処理"""
        try:
            await interaction.response.defer(ephemeral=True)
            # 選択された数式タイプを保存
            self.form_data['formula_type'] = ', '.join(self.values)

            # まず「タグ情報を取得中...」のメッセージを送信
            loading_message = await interaction.followup.send(
                content="タグ情報を取得中です...しばらくお待ちください。\n(Loading tags from database...)",
                ephemeral=True
            )

            # タグ選択フェーズに進む
            gas_client = GASClient()
            tags_data = await gas_client.get_tags_list()

            if not tags_data:
                await interaction.followup.send("タグデータの取得に失敗しました。", ephemeral=True)
                return

            # タグリストを表示
            tags_display = gas_client.format_tags_for_display(tags_data)

            embed = discord.Embed(
                title="タグ選択 / Tag Selection",
                description=f"利用可能なタグ一覧：\nAvailable tags:\n{tags_display}\n\n**使用方法 / Usage:**\n• 番号をカンマ区切りで入力 / Enter numbers separated by commas: 例/e.g. `1, 3, 10`\n• タグなしの場合は「なし」と入力 / Enter \"なし\" for no tags",
                color=0x00FF7F
            )

            view = TagInputView(self.form_data, tags_data)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

            # ローディングメッセージを削除（エフェメラルなので消さなくてもOKだが、UX向上のため）
            try:
                await loading_message.delete()
            except Exception:
                pass

        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)

class TagInputView(discord.ui.View):
    """タグ入力ビュー"""
    
    def __init__(self, form_data, tags_data):
        super().__init__(timeout=300)
        self.form_data = form_data
        self.tags_data = tags_data
        
        # タグ入力モーダルボタン
        self.tag_button = TagInputButton(form_data, tags_data)
        self.add_item(self.tag_button)

class TagInputButton(discord.ui.Button):
    """タグ入力ボタン"""
    
    def __init__(self, form_data, tags_data):
        super().__init__(label="タグを選択 / Select Tags", style=discord.ButtonStyle.primary, emoji="🏷️")
        self.form_data = form_data
        self.tags_data = tags_data
    
    async def callback(self, interaction: discord.Interaction):
        """タグ入力ボタンクリック時の処理"""
        modal = TagInputModal(self.form_data, self.tags_data)
        await interaction.response.send_modal(modal)

class TagInputModal(discord.ui.Modal):
    """タグ入力モーダル"""
    
    def __init__(self, form_data, tags_data):
        super().__init__(title="タグ選択 / Tag Selection")
        self.form_data = form_data
        self.tags_data = tags_data
        
        # タグ入力フィールド
        self.tag_input = discord.ui.TextInput(
            label="タグ選択 / Tag Selection",
            placeholder="例/e.g.: 1, 3, 10 または/or なし",
            required=True,
            max_length=200
        )
        self.add_item(self.tag_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """タグ入力送信時の処理"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # タグ選択を解析
            gas_client = GASClient()
            tag_ids_str = gas_client.parse_tag_selection(self.tags_data, self.tag_input.value)
            selected_tag_names = gas_client.get_selected_tag_names(self.tags_data, tag_ids_str)
            
            self.form_data['tags'] = tag_ids_str
            
            # 最終確認を表示
            embed = discord.Embed(
                title="数式登録確認 / Formula Registration Confirmation",
                color=0x00FF7F
            )
            
            embed.add_field(name="タイトル / Title", value=self.form_data['title'][:250] + ("..." if len(self.form_data['title']) > 250 else ""), inline=False)
            
            if self.form_data['title_EN']:
                title_en_display = self.form_data['title_EN'][:250] + ("..." if len(self.form_data['title_EN']) > 250 else "")
                embed.add_field(name="英語タイトル / English Title", value=title_en_display, inline=False)
            else:
                embed.add_field(name="英語タイトル / English Title", value="なし / None", inline=False)
            
            # 数式を短縮表示
            formula_display = self.form_data['formula']
            if len(formula_display) > 100:
                formula_display = formula_display[:100] + "..."
            embed.add_field(name="数式 / Formula", value=f"```\n{formula_display}\n```", inline=False)
            
            embed.add_field(name="タイプ / Type", value=self.form_data['formula_type'], inline=False)
            
            tags_display = ', '.join(selected_tag_names) if selected_tag_names else 'なし / None'
            embed.add_field(name="タグ / Tags", value=tags_display, inline=False)
            
            # 画像をプレビュー表示
            if self.form_data['image_url']:
                embed.set_image(url=self.form_data['image_url'])
            
            view = ConfirmationView(self.form_data)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)

class ConfirmationView(discord.ui.View):
    """最終確認ビュー"""
    
    def __init__(self, form_data):
        super().__init__(timeout=300)
        self.form_data = form_data
    
    @discord.ui.button(label="登録する / Register", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        """登録確定ボタン"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # GASに送信
            gas_client = GASClient()
            result = await gas_client.register_formula(self.form_data)
            
            if result.get('success'):
                # 成功
                formula_id = result.get('result', {}).get('id', '不明')
                embed = discord.Embed(
                    title="登録申請完了 / Registration Request Complete",
                    description=(
                        "✅ 数式の登録申請が完了しました！\n"
                        "\n"
                        "この数式は運営による精査後、毎日0:10(JST)に正式登録されます。\n"
                        "（不適切な内容の場合は登録されません）\n"
                        "\n"
                        "---\n"
                        "✅ Your formula registration request has been received!\n"
                        "\n"
                        "This formula will be reviewed by the admin and officially registered at 00:10 (JST) each day.\n"
                        "(If the content is inappropriate, it will not be registered.)"
                    ),
                    color=0x00FF00
                )
                embed.add_field(name="ID", value=str(formula_id), inline=False)
                embed.set_footer(text="Graph + Library = Graphary")
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # 失敗
                error_msg = result.get('error', '不明なエラー')
                embed = discord.Embed(
                    title="登録失敗 / Registration Failed",
                    description=f"❌ 数式の登録に失敗しました。\nFailed to register formula.\n\nエラー/Error: {error_msg}",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            embed = discord.Embed(
                title="登録エラー / Registration Error",
                description=f"❌ 予期しないエラーが発生しました。\nAn unexpected error occurred.\n\nエラー/Error: {str(e)}",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="キャンセル / Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        """キャンセルボタン"""
        embed = discord.Embed(
            title="登録キャンセル / Registration Cancelled",
            description="数式の登録をキャンセルしました。\nFormula registration has been cancelled.",
            color=0x888888
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

# 誰でも使える: 個人用ダイスコマンド
@bot.tree.command(name="dice_seacret", description="個人用ダイス: minからmaxの間でランダムな数字を表示します")
@app_commands.describe(
    min="最小値 (省略時は1)",
    max="最大値 (省略時は100)"
)
async def dice_seacret_command(
    interaction: discord.Interaction,
    min: int = 1,
    max: int = 100
):
    import random
    if min > max:
        await interaction.response.send_message("最小値は最大値以下にしてください。", ephemeral=True)
        return
    result = random.randint(min, max)
    embed = discord.Embed(
        title="🎲 ダイス結果 (シークレット)",
        description=f"{min} から {max} の間で…\n**{result}** が出ました！",
        color=0x00FF7F
    )
    embed.set_footer(text="この結果はあなただけに表示されています")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 誰でも使える: みんなに見えるダイスコマンド
@bot.tree.command(name="dice", description="みんなに見えるダイス: minからmaxの間でランダムな数字を表示します")
@app_commands.describe(
    min="最小値 (省略時は1)",
    max="最大値 (省略時は100)"
)
async def dice_command(
    interaction: discord.Interaction,
    min: int = 1,
    max: int = 100
):
    import random
    if min > max:
        await interaction.response.send_message("最小値は最大値以下にしてください。", ephemeral=False)
        return
    result = random.randint(min, max)
    embed = discord.Embed(
        title="🎲 ダイス結果",
        description=f"{min} から {max} の間で…\n**{result}** が出ました！",
        color=0x00FF7F
    )
    embed.set_footer(text=f"実行者: {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed, ephemeral=False)

# Botの実行
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("エラー: DISCORD_BOT_TOKEN環境変数が設定されていません。")
    else:
        bot.run(token)
