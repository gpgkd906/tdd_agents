import task_agent as ta
import toml

if __name__ == "__main__":
    with open("agent.toml", 'r', encoding='utf-8') as f:
        config = toml.load(f)
        
        requirement_description = config['project']['requirement']
        language = config['project']['language']
        libraries = config['project']['libraries']
        comment_language = config['project']['comment_language']
        readme_language = config['project']['readme_language']
        base_path = config['project']['base_path']

        ta.developer_agent(requirement_description, language, libraries, base_path, comment_language, readme_language)
