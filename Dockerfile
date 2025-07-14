# Python 3.11のスリムイメージを使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なシステムパッケージをインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# requirements.txtをコピーして依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY . .

# 非rootユーザーでアプリケーションを実行
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Botを起動
CMD ["python", "main.py"]
