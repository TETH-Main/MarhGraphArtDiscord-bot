# 🤖 MarhGraphArt Discord Bot

汎用的なDiscord Bot - メッセージ送信とEmbed機能を持つ多機能Bot

## 📋 機能

### 基本コマンド
- `/admin_message` - 管理者限定のメッセージ送信
- `/ping` - Botの応答時間を確認

### メッセージ管理機能
- `/list_messages` - 利用可能なメッセージキー一覧を表示
- `/add_message` - 新しいメッセージキーを追加
- `/edit_message` - 登録済みメッセージを編集
- `/remove_message` - メッセージキーを削除

### 過去メッセージ編集機能
- `/edit_bot_message` - Botが送信した過去のメッセージを直接編集
- `/get_message_id` - メッセージリンクからIDを取得

### 自動機能
- **Welcome Message** - 新規メンバー参加時の自動歓迎メッセージ


### 管理機能
- **ユーザーID制限**: 特定のユーザーIDのみが管理者コマンドを使用可能
- **ロール制限**: 指定されたロールを持つユーザーのみが管理者コマンドを使用可能
- **チャンネル指定**: 管理者は任意のチャンネルにメッセージを送信可能

## 🚀 セットアップ

### 前提条件
- Python 3.8以上
- Discord Developer Portal でのBot作成
- Railway アカウント（デプロイ用）

### ローカル開発

1. **リポジトリのクローン**
```bash
git clone https://github.com/TETH-Main/MarhGraphArtDiscord-bot.git
cd MarhGraphArtDiscord-bot
```

2. **依存関係のインストール**
```bash
pip install -r requirements.txt
```

3. **環境変数の設定**
以下の環境変数を設定してください：

```bash
# 必須
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# オプション（管理者設定）
ADMIN_USER_IDS=123456789012345678,987654321098765432
ADMIN_ROLES=Administrator,Moderator

# オプション（Welcome機能）
WELCOME_CHANNEL_ID=1234567890123456789
```

4. **Botの実行**
```bash
python bot.py
```

## 🛠️ Discord Bot セットアップ

### 1. Discord Developer Portal での設定

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. 「New Application」をクリックしてアプリケーションを作成
3. 「Bot」セクションに移動
4. 「Add Bot」をクリック
5. Bot Token をコピー（環境変数として使用）

### 2. Bot の権限設定

以下の権限が必要です：
- `Send Messages` - メッセージ送信
- `Use Slash Commands` - スラッシュコマンド使用
- `Embed Links` - Embed送信
- `Read Message History` - メッセージ履歴読み取り

### 3. Bot Invite URL の生成

OAuth2セクションで以下のスコープを選択：
- `bot`
- `applications.commands`

## 🌐 Railway デプロイ

### 1. Railway プロジェクトの作成

1. [Railway](https://railway.app) にアクセスしてログイン
2. 「New Project」から「Deploy from GitHub repo」を選択
3. このリポジトリを選択

### 2. 環境変数の設定

Railwayのプロジェクト設定で以下の環境変数を設定：

```
DISCORD_BOT_TOKEN=your_discord_bot_token
ADMIN_USER_IDS=123456789012345678,987654321098765432
ADMIN_ROLES=Administrator,Moderator
WELCOME_CHANNEL_ID=1234567890123456789
```

### 3. デプロイ

GitHubにプッシュすると自動的にデプロイされます。

## 📖 コマンド詳細

### `/message`
基本的なメッセージ送信コマンド

**パラメータ:**
- `content` (必須): 送信するメッセージ内容
- `embed_title` (オプション): Embedのタイトル
- `embed_description` (オプション): Embedの説明
- `embed_color` (オプション): Embedの色（16進数、例: #FF0000）

**使用例:**
```
/message content:こんにちは！
/message content:お知らせ embed_title:重要なお知らせ embed_description:明日はメンテナンスです embed_color:#FF0000
```

### `/admin_message`
管理者限定のメッセージコマンド

**パラメータ:**
- `content` (必須): 送信するメッセージ内容
- `embed_title` (オプション): Embedのタイトル
- `embed_description` (オプション): Embedの説明
- `embed_color` (オプション): Embedの色（16進数）
- `channel` (オプション): 送信先チャンネル

**使用例:**
```
/admin_message content:管理者からのお知らせ
/admin_message content:緊急連絡 channel:#general embed_title:緊急 embed_color:#FF0000
```

## 🔧 カスタマイズ

### 管理者権限の設定方法

#### 1. ユーザーIDによる制限
```bash
ADMIN_USER_IDS=123456789012345678,987654321098765432
```

#### 2. ロールによる制限
```bash
ADMIN_ROLES=Administrator,Moderator,Staff
```

### 新しいコマンドの追加

`bot.py`に新しいコマンドを追加する例：

```python
@bot.tree.command(name="custom", description="カスタムコマンド")
async def custom_command(interaction: discord.Interaction):
    await interaction.response.send_message("カスタムレスポンス")
```

## 📝 ファイル構成

```
MarhGraphArtDiscord-bot/
├── bot.py              # メインのBotファイル
├── requirements.txt    # Python依存関係
├── Dockerfile         # Docker設定
├── railway.json       # Railway設定
├── .gitignore        # Git無視ファイル
└── README.md         # このファイル
```

## 🐛 トラブルシューティング

### よくある問題

1. **Bot が応答しない**
   - Bot Token が正しく設定されているか確認
   - Botがサーバーに招待されているか確認
   - 必要な権限が付与されているか確認

2. **スラッシュコマンドが表示されない**
   - `await self.tree.sync()` が実行されているか確認
   - Botを一度サーバーから削除して再招待

3. **管理者コマンドが使えない**
   - `ADMIN_USER_IDS` または `ADMIN_ROLES` が正しく設定されているか確認
   - ユーザーIDが正しいか確認（開発者モードで確認可能）

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

##  サポート

問題や質問がある場合は、GitHubのIssueを作成してください。

---

**作成者**: TETH-Main  
**バージョン**: 1.0.0  
**最終更新**: 2025年7月