## Select Language / 选择语言 / 言語を選択

- [English](README.md)｜[中文](README.zh.md)｜[日本語](README.ja.md)

### Installation:
- python3.10。
- Poetry package manager

在python3.10环境下，执行下面的命令
```bash
pip install poetry
```

- 如果要使用 openai 的 API，则需要一个 API_KEY；一旦获得 API_KEY，请将其放入 .env.openai 并重命名为 .env。
- 也可以在本地使用 Ollama。 在这种情况下，将 .env.ollama 重命名为 .env。
- 确保你的环境中有指定的开发语言的环境，例如typescript的nodejs环境，rust的cargo环境等等

API准备就绪后，就可以执行以下命令来进行AI驱动的TDD开发：
```bash
poetry install
poetry shell # activates virtual environment
python bin/tdd_develop.py
```

### 定义需求
总得让AI知道你要做什么吧。在 agent.toml 中定义需求。定义需求的格式如下：

```toml
[project]
requirement = "开发需求" # 需求定义，越详细越好
language = "rust 1.79.0" # 开发语言，最好连版本号也指定
libraries = ["wrap", "tokio", "serde_json"] #  中间件和库的指定
comment_language = "中文" # 注释使用的语言
readme_language = "中文" # readme使用的语言
base_path = "my_project" # 项目的基本路径
```

### 可选项： 在本地使用 Ollama

 [从这里](https://ollama.com/) 下载和安装 Ollama。

安装完成后，使用以下命令下载模型

```bash
ollama pull llama3:8b
ollama run llama3:8b
```

Ollama 会在 http://localhost:11434 上托管restful API。（兼容openai）
当Ollama启动后，可以使用以下命令进行测试：

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

## 感谢
这个项目受到了吴恩达老师的翻译agent项目的启发，十分感谢吴恩达老师对于知识的分享。

https://github.com/andrewyng/translation-agent