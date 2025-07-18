import os
import discord
from discord.ext import commands
from discord import app_commands
import logging
from messages_gspread import get_message, get_all_messages
from formulas_gspread import get_formula, get_all_formulas, get_formulas_by_type, search_formulas, get_random_formula, format_formula_for_display, get_available_formula_types
from daily_notifier import DailyFormulaNotifier

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
    
    async def on_ready(self):
        """Bot準備完了時"""
        print(f'{self.user} has connected to Discord!')
        print(f'Bot is in {len(self.guilds)} guilds')
        print("Bot is ready and commands should be available!")
        
        # 毎日通知機能を開始
        await self.start_daily_notifier()
    
    async def start_daily_notifier(self):
        """毎日通知機能を開始"""
        global daily_notifier
        
        # 通知チャンネルIDを環境変数から取得
        notification_channel_id = os.getenv('DAILY_NOTIFICATION_CHANNEL_ID')
        if not notification_channel_id:
            print("DAILY_NOTIFICATION_CHANNEL_ID環境変数が設定されていません。毎日通知機能は無効です。")
            return
        
        try:
            channel_id = int(notification_channel_id)
            daily_notifier = DailyFormulaNotifier(self, channel_id)
            daily_notifier.start()
            print(f"毎日通知機能を開始しました。通知チャンネル: {channel_id}")
        except ValueError:
            print("DAILY_NOTIFICATION_CHANNEL_IDが無効な値です。毎日通知機能は無効です。")
    
    async def close(self):
        """Bot終了時の処理"""
        global daily_notifier
        
        if daily_notifier:
            daily_notifier.stop()
            print("毎日通知機能を停止しました。")
        
        await super().close()
    
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

# 毎日通知機能の初期化
daily_notifier = None

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

@bot.tree.command(name="formula", description="数式データを取得します")
@app_commands.describe(
    formula_id="取得する数式のID（オプション）",
    formula_type="数式のタイプで絞り込み（オプション）",
    search="タイトルやタグで検索（オプション）",
    random="ランダムな数式を取得（オプション）"
)
async def formula_command(
    interaction: discord.Interaction,
    formula_id: str = None,
    formula_type: str = None,
    search: str = None,
    random: bool = False
):
    """数式データを取得・表示"""
    
    try:
        await interaction.response.defer()
        
        formula_data = None
        
        if random:
            # ランダム取得
            formula_data = get_random_formula()
            if formula_data:
                embed = discord.Embed(
                    title="ランダム数式",
                    description=format_formula_for_display(formula_data),
                    color=discord.Color.green()
                )
                if formula_data.get('image_url'):
                    embed.set_image(url=formula_data['image_url'])
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("数式データが見つかりませんでした。")
                
        elif formula_id:
            # 特定ID取得
            formula_data = get_formula(formula_id)
            if formula_data:
                embed = discord.Embed(
                    title=f"数式データ: {formula_data.get('title', 'N/A')}",
                    description=format_formula_for_display(formula_data),
                    color=discord.Color.blue()
                )
                if formula_data.get('image_url'):
                    embed.set_image(url=formula_data['image_url'])
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"ID '{formula_id}' の数式データが見つかりませんでした。")
                
        elif search:
            # 検索
            formulas = search_formulas(search)
            if formulas:
                embed = discord.Embed(
                    title=f"検索結果: '{search}'",
                    color=discord.Color.orange()
                )
                
                for i, formula in enumerate(formulas[:5]):  # 最大5件まで表示
                    embed.add_field(
                        name=f"{formula.get('id', 'N/A')} - {formula.get('title', 'N/A')}",
                        value=f"タイプ: {formula.get('formula_type', 'N/A')}\n数式: `{formula.get('formula', 'N/A')[:50]}...`" if len(formula.get('formula', '')) > 50 else f"タイプ: {formula.get('formula_type', 'N/A')}\n数式: `{formula.get('formula', 'N/A')}`",
                        inline=False
                    )
                
                if len(formulas) > 5:
                    embed.set_footer(text=f"他に{len(formulas) - 5}件の結果があります。")
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"'{search}' の検索結果が見つかりませんでした。")
                
        elif formula_type:
            # タイプ別取得
            formulas = get_formulas_by_type(formula_type)
            if formulas:
                embed = discord.Embed(
                    title=f"数式タイプ: {formula_type}",
                    color=discord.Color.purple()
                )
                
                for i, formula in enumerate(formulas[:5]):  # 最大5件まで表示
                    embed.add_field(
                        name=f"{formula.get('id', 'N/A')} - {formula.get('title', 'N/A')}",
                        value=f"数式: `{formula.get('formula', 'N/A')[:50]}...`" if len(formula.get('formula', '')) > 50 else f"数式: `{formula.get('formula', 'N/A')}`",
                        inline=False
                    )
                
                if len(formulas) > 5:
                    embed.set_footer(text=f"他に{len(formulas) - 5}件の結果があります。")
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"タイプ '{formula_type}' の数式データが見つかりませんでした。")
        else:
            # パラメータが何も指定されていない場合は使用方法を表示
            embed = discord.Embed(
                title="数式コマンドの使用方法",
                color=discord.Color.gold()
            )
            embed.add_field(
                name="使用例",
                value=(
                    "`/formula formula_id:001` - ID指定で取得\n"
                    "`/formula formula_type:circle` - タイプ別で取得\n"
                    "`/formula search:heart` - 検索\n"
                    "`/formula random:True` - ランダム取得"
                ),
                inline=False
            )
            
            # 利用可能なタイプを表示
            types = get_available_formula_types()
            if types:
                embed.add_field(
                    name="利用可能なタイプ",
                    value=", ".join(types[:10]) + ("..." if len(types) > 10 else ""),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f"エラーが発生しました: {str(e)}")
        else:
            await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="formula_list", description="管理者限定：数式データ一覧を表示")
async def formula_list_command(interaction: discord.Interaction):
    """管理者限定：数式データ一覧を表示"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        formulas = get_all_formulas()
        if formulas:
            embed = discord.Embed(
                title="数式データ一覧",
                color=discord.Color.blue()
            )
            
            for i, formula in enumerate(formulas[:10]):  # 最大10件まで表示
                embed.add_field(
                    name=f"{formula.get('id', 'N/A')} - {formula.get('title', 'N/A')}",
                    value=f"タイプ: {formula.get('formula_type', 'N/A')}\n数式: `{formula.get('formula', 'N/A')[:30]}...`" if len(formula.get('formula', '')) > 30 else f"タイプ: {formula.get('formula_type', 'N/A')}\n数式: `{formula.get('formula', 'N/A')}`",
                    inline=False
                )
            
            if len(formulas) > 10:
                embed.set_footer(text=f"他に{len(formulas) - 10}件のデータがあります。総数: {len(formulas)}件")
            else:
                embed.set_footer(text=f"総数: {len(formulas)}件")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send("数式データが登録されていません。", ephemeral=True)
            
    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)
        else:
            await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="daily_notification_test", description="管理者限定：毎日通知機能のテスト")
@app_commands.describe(
    test_date="テストする日付（YYYY-MM-DD形式、省略時は今日）"
)
async def daily_notification_test_command(
    interaction: discord.Interaction,
    test_date: str = None
):
    """管理者限定：毎日通知機能のテスト"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    global daily_notifier
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        if not daily_notifier:
            await interaction.followup.send("❌ 毎日通知機能が初期化されていません。DAILY_NOTIFICATION_CHANNEL_ID環境変数を確認してください。", ephemeral=True)
            return
        
        # 手動で指定日または今日の数式をチェック
        count = await daily_notifier.manual_check(interaction.channel, test_date)
        
        if test_date:
            if count > 0:
                await interaction.followup.send(f"✅ テスト完了: {test_date}に{count}件の数式を発見し、通知しました。", ephemeral=True)
            else:
                await interaction.followup.send(f"✅ テスト完了: {test_date}に登録された数式はありませんでした。", ephemeral=True)
        else:
            if count > 0:
                await interaction.followup.send(f"✅ テスト完了: 今日{count}件の新着数式を通知しました。", ephemeral=True)
            else:
                await interaction.followup.send("✅ テスト完了: 今日登録された新しい数式はありませんでした。", ephemeral=True)
            
    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ エラーが発生しました: {str(e)}", ephemeral=True)

@app_commands.default_permissions(administrator=True)
@bot.tree.command(name="daily_notification_status", description="管理者限定：毎日通知機能の状態確認")
async def daily_notification_status_command(interaction: discord.Interaction):
    """管理者限定：毎日通知機能の状態確認"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    global daily_notifier
    
    try:
        embed = discord.Embed(
            title="📊 毎日通知機能の状態",
            color=discord.Color.blue()
        )
        
        # 環境変数の確認
        notification_channel_id = os.getenv('DAILY_NOTIFICATION_CHANNEL_ID')
        if notification_channel_id:
            try:
                channel_id = int(notification_channel_id)
                channel = bot.get_channel(channel_id)
                channel_name = channel.name if channel else "チャンネルが見つかりません"
                embed.add_field(
                    name="🔧 設定",
                    value=f"**通知チャンネル:** {channel_name} (`{channel_id}`)",
                    inline=False
                )
            except ValueError:
                embed.add_field(
                    name="❌ 設定エラー",
                    value="DAILY_NOTIFICATION_CHANNEL_IDが無効な値です",
                    inline=False
                )
        else:
            embed.add_field(
                name="❌ 設定エラー",
                value="DAILY_NOTIFICATION_CHANNEL_ID環境変数が設定されていません",
                inline=False
            )
        
        # 通知機能の状態
        if daily_notifier:
            status = "🟢 実行中" if daily_notifier.is_running else "🔴 停止中"
            embed.add_field(
                name="📡 通知機能",
                value=f"**状態:** {status}",
                inline=False
            )
        else:
            embed.add_field(
                name="📡 通知機能",
                value="**状態:** ❌ 初期化されていません",
                inline=False
            )
        
        # 使用方法
        embed.add_field(
            name="💡 使用方法",
            value=(
                "`/daily_notification_test` - 今日の数式をテスト\n"
                "`/daily_notification_test test_date:2025-03-06` - 指定日をテスト\n"
                "毎日0時に自動で新着数式を通知します"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ エラーが発生しました: {str(e)}", ephemeral=True)


# Botの実行
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("エラー: DISCORD_BOT_TOKEN環境変数が設定されていません。")
    else:
        bot.run(token)
