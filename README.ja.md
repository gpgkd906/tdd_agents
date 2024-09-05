## Select Language / 选择语言 / 言語を選択

- [English](README.md)｜[中文](README.zh.md)｜[日本語](README.ja.md)

### Installation:
- python3.10。
- Poetry package manager

python3.10がある環境にて、下記コマンドを実行してpoetryをインストールしてください。
```bash
pip install poetry
```

- openaiのAPIを使う場合、API_KEYが必要です。API_KEYを取得次第、.env.openaiに記載して、.envにリネームしてください。
- ローカルでOllamaを使うことも可能です。この場合 .env.ollamaをそのまま.envにリネームしてください。
- 指定した開発言語の環境が整っていることを確認してください。例えば、typescriptのnodejs環境、rustのcargo環境など。

いずれのAPIが準備できた場合は、下記コマンドを実行してAIによるTDD開発を行うことができます。
```bash
poetry install
poetry shell # activates virtual environment
python bin/tdd_develop.py
```

### 開発要件の定義
agent.tomlにて、開発要件を定義してください。開発要件の定義は下記のようになります:

```toml
[project]
requirement = "要件定義" # 要件定義、詳しければほど良い
language = "rust 1.79.0" # 開発言語、バージョンまで指定推奨
libraries = ["wrap", "tokio", "serde_json"] # ミドルウェアやライブラリの指定
comment_language = "日本語" # コメントの言語
readme_language = "日本語" # READMEの言語
base_path = "my_project" # プロジェクトのベースパス
```

### オプション：ローカルでOllamaを使う方法

 [ここ](https://ollama.com/)からollamaをインストールしてください。

インストール完了後、下記コマンドでモデルをダウンロードしてください:

```bash
ollama pull llama3:8b
ollama run llama3:8b
```

Ollamaは http://localhost:11434 にてrestful APIをホストします。

一旦Ollamaが起動したら、下記コマンドで動作確認をしてください:

```bash
curl http://localhost:11434/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "llama3:8b",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": "Hello!"
            }
        ]
    }'
```

## 感謝
このプロジェクトは、アンドリュー・ウン博士の翻訳エージェント・プロジェクトにインスパイアされたもので、彼の知識を共有してくれたアンドリュー・ウン博士にとても感謝している。

https://github.com/andrewyng/translation-agent