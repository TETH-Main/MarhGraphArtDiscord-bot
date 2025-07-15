import os
import discord
from discord.ext import commands
from discord import app_commands
import logging
from messages import get_message, get_all_message_keys

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

@bot.tree.command(name="list_messages", description="管理者限定：利用可能なメッセージキー一覧を表示")
async def list_messages_command(interaction: discord.Interaction):
    """管理者限定：利用可能なメッセージキー一覧を表示"""
    
    # 管理者チェック
    if not is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return
    
    keys = get_all_message_keys()
    if keys:
        embed = discord.Embed(
            title="📝 利用可能なメッセージキー",
            color=discord.Color.blue()
        )
        
        for key in keys:
            message_data = get_message(key)
            content = message_data["content"]
            # コンテンツが長い場合は短縮
            if len(content) > 100:
                content = content[:100] + "..."
            
            embed_info = ""
            if "embed" in message_data:
                embed_data = message_data["embed"]
                embed_info = f"\n**Embed:** {embed_data.get('title', 'タイトルなし')}"
            
            embed.add_field(
                name=f"`{key}`",
                value=f"**Content:** {content}{embed_info}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("登録されているメッセージがありません。", ephemeral=True)

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
        
        # メッセージを更新（messages.pyのMESSAGES辞書を直接更新）
        from messages import MESSAGES
        MESSAGES[message_key] = updated_message
        
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
        
        # メッセージを追加（messages.pyのMESSAGES辞書を直接更新）
        from messages import MESSAGES
        MESSAGES[message_key] = new_message
        
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
        
        # メッセージを削除
        from messages import MESSAGES
        del MESSAGES[message_key]
        
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

# Botの実行
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("エラー: DISCORD_BOT_TOKEN環境変数が設定されていません。")
    else:
        bot.run(token)
