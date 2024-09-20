## Select Language / 选择语言 / 言語を選択

- [English](README.md)｜[中文](README.zh.md)｜[日本語](README.ja.md)

## Demo

![demo](./render1726814437171.gif)

## Getting Started

To get started with `tdd-agents`, follow these steps:

### Installation:
- The Poetry package manager is required for installation. [Poetry Installation](https://python-poetry.org/docs/#installation) Depending on your environment, this might work:

```bash
pip install poetry
```

- if you want to use the openai API, you need an API_KEY; once you have the API_KEY, put it in .env.openai and rename it to .env.
- You can also use Ollama locally. In this case, rename .env.ollama to .env.
- Ensure that you have the environment of the specified development language in your environment, such as the nodejs environment of typescript, the cargo environment of rust, etc.

```bash
poetry install
poetry shell # activates virtual environment
python bin/tdd_develop.py
```

### define the requirements
You need to let the AI know what you want to do. Define the requirements in agent.toml. The format for defining the requirements is as follows

```toml
[project]
requirement = "requirements" # the definition of the requirements, the more detailed the better
language = "rust 1.79.0" # development language, it is recommended to specify the version number
libraries = ["wrap", "tokio", "serde_json"] # middleware and library specification
comment_language = "中文" # language used for comments
readme_language = "中文" # language used for README
base_path = "my_project" # project base path
```


### use ollama as the backend:

install ollama from [here](https://ollama.com/)

then download the model and run it as follows:

```bash
ollama pull llama3:8b
ollama run llama3:8b
```

then ollama will host a restful API at http://localhost:11434

once the ollama is runing, check if it working as follows:

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

## Thanks
This project was inspired by Dr. Andrew Ng's translation-agent project, and I am very grateful to Dr. Andrew Ng for sharing his knowledge.

https://github.com/andrewyng/translation-agent