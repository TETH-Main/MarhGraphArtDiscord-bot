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

@bot.tree.command(name="message", description="メッセージを送信します")
@app_commands.describe(
    message_key="送信するメッセージのキー（オプション）",
    content="送信するメッセージの内容",
    embed_title="Embedのタイトル（オプション）",
    embed_description="Embedの説明（オプション）",
    embed_color="Embedの色（16進数、例: #FF0000）"
)
async def message_command(
    interaction: discord.Interaction,
    content: str = None,
    message_key: str = None,
    embed_title: str = None,
    embed_description: str = None,
    embed_color: str = None
):
    """通常のメッセージコマンド"""
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
        
        # 通常のメッセージを送信
        await interaction.response.send_message(content)
        
        # Embedが指定されている場合は追加で送信
        if embed_title or embed_description:
            embed = discord.Embed()
            
            if embed_title:
                embed.title = embed_title
            
            if embed_description:
                embed.description = embed_description
            
            # 色の設定
            if embed_color:
                try:
                    # #を除去して16進数として解釈
                    color_hex = embed_color.lstrip('#')
                    embed.color = int(color_hex, 16)
                except ValueError:
                    embed.color = discord.Color.blue()
            else:
                embed.color = discord.Color.blue()
            
            # フッターを追加
            embed.set_footer(text=f"送信者: {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

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

@bot.tree.command(name="list_messages", description="利用可能なメッセージキー一覧を表示")
async def list_messages_command(interaction: discord.Interaction):
    """利用可能なメッセージキー一覧を表示"""
    keys = get_all_message_keys()
    if keys:
        key_list = "\n".join([f"• `{key}`" for key in keys])
        embed = discord.Embed(
            title="📝 利用可能なメッセージキー",
            description=key_list,
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("登録されているメッセージがありません。")

# Botの実行
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("エラー: DISCORD_BOT_TOKEN環境変数が設定されていません。")
    else:
        bot.run(token)
