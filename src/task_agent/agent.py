import os
from typing import List, Dict, Tuple
import re
import openai
from dotenv import load_dotenv
import json

load_dotenv()

client = openai.OpenAI(
    base_url=os.getenv("PROVIDER"),
    api_key=os.getenv("OPENAI_API_KEY")
)
MODEL = os.getenv("MODEL")

def get_completion(prompt: str, system_message: str = "You are a helpful assistant.", model: str = MODEL, temperature: float = 0.3) -> str:
    full_response = ""
    current_prompt = prompt
    stop_sequence = "<comp>continue...</comp>"
    max_tokens_per_request = 2048

    while True:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens_per_request,
            stop=[stop_sequence],
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": current_prompt},
            ],
        )

        current_response = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason

        full_response += current_response.rstrip(stop_sequence)

        if finish_reason == "stop" or not current_response.endswith(stop_sequence):
            break
        else:
            current_prompt = "go on..."

    return full_response.strip()

def clean_file_content(content: str) -> str:
    lines = content.split('\n')
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines[-1].startswith("```"):
        lines = lines[:-1]
    lines = [line for line in lines if not (line.startswith("<") and line.endswith(">"))]
    return "\n".join(lines).strip()

def clean_code_with_openai(content: str) -> str:
    """
    Use OpenAI to clean the file content, extracting only the code parts and removing unrelated content.
    """
    system_message = "You are an expert software developer. Extract only the code from the following content and remove all unrelated text."

    cleaning_prompt = f"""Extract the code from the following content and remove all unrelated text:

Content:
{content}

Return only the cleaned code content."""
    
    cleaned_code = get_completion(cleaning_prompt, system_message=system_message)
    return clean_file_content(cleaned_code)

def parse_design(design: str) -> Dict[str, str]:
    parsed_files = {}

    file_pattern = r"<gen-file path=['\"]?([^>]+?)['\"]?>\s*(.*?)\s*</gen-file>"
    matches = re.findall(file_pattern, design, re.DOTALL)

    for match in matches:
        file_path = match[0].strip()
        content = clean_file_content(match[1])
        parsed_files[file_path] = content

    return parsed_files

def filter_out_test_files(design: str) -> str:
    lines = design.splitlines()
    filtered_lines = [line for line in lines if "test" not in line.lower()]
    return "\n".join(filtered_lines)

def get_skip_folders_and_file_extensions(language: str, libraries: List[str]) -> Tuple[List[str], List[str]]:
    system_message = "You are an expert software developer. Return only common build or output directories to skip and the file extensions to check during file processing."

    skip_and_ext_prompt = f"""
Based on the following programming language and libraries, list the common directories that should be skipped and the file extensions that should be checked during file processing.

Programming Language:
{language}

Libraries:
{', '.join(libraries)}

Ensure the following:
1. **skip_folders** should only contain folder names, not specific files.
2. **file_extensions** should contain valid file extensions to be checked, including test-related file extensions.

Return the result in JSON format without any explanation.

JSON Format Example:
{{
    "skip_folders": A JSON array of folder names to be skipped (directories only),
    "file_extensions": A JSON array of file extensions to be checked (including test files)
}}
"""
    response = get_completion(skip_and_ext_prompt, system_message=system_message)
    response = clean_file_content(response)
    try:
        data = json.loads(response)
        skip_folders = data.get("skip_folders", [])
        file_extensions = data.get("file_extensions", [])
        return skip_folders, file_extensions
    except json.JSONDecodeError as e:
        print(f"A - L135 - JSON decode error: {e}")
        return [], []
    
def get_all_files_in_base_path(base_path: str, skip_folders: List[str], file_extensions: List[str]) -> Tuple[List[str], Dict[str, List[str]]]:
    all_files = []
    project_structure = get_project_structure(base_path, skip_folders, file_extensions)
    for folder, files in project_structure.items():
        for file in files:
            all_files.append(os.path.join(base_path, folder, file).replace("/./", "/"))
    return all_files, project_structure

def clean_base_path(base_path: str):
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    else:
        for root, dirs, files in os.walk(base_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

def get_project_structure(base_path: str, skip_folders: List[str], file_extensions: List[str]) -> Dict[str, List[str]]:
    project_structure = {}
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if not any(os.path.join(root, d).startswith(os.path.join(base_path, skip_folder)) for skip_folder in skip_folders)]
        relative_root = os.path.relpath(root, base_path)
        project_structure[relative_root] = [file for file in files if any(file.endswith(ext) for ext in file_extensions)]
    return project_structure

def generate_project_settings(base_path, language: str, libraries: List[str], design: str, project_structure: Dict[str, List[str]]) -> str:
    system_message = "You are an expert in configuring project settings for software development."

    settings_prompt = f"""Based on the following technical design and the existing file structure, determine if a suitable project configuration file (like Cargo.toml for Rust, package.json for Node.js) already exists. If it does, skip generating a new one. If it doesn't exist, create an appropriate configuration file.

File Structure:
{json.dumps(project_structure, indent=2)}

Technical Design:
{design}

Programming Language: 
{language}

Libraries/Middleware: 
{', '.join(libraries)}

Return the result in JSON format without any explanation.
JSON Format Example:
{{ 
    "project_file": path/to/file,
    "settings_content": file_content
}}
"""

    settings_content = get_completion(settings_prompt, system_message=system_message)
    settings_content = clean_file_content(settings_content)
    try:
        data = json.loads(settings_content)
        project_file = data.get("project_file", "")
        settings_content = data.get("settings_content", "")
        with open(os.path.join(base_path, project_file), "w") as f:
            f.write(settings_content)
        print(f"Writed file: {base_path}/{project_file}")
    except json.JSONDecodeError as e:
        print(f"generate_project_settings - JSON decode error: {e}")
        generate_project_settings(base_path, language, libraries, design, project_structure)

def validate_paths(suggested_paths: Dict[str, str], base_path: str, project_structure: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Validate the paths suggested by OpenAI and correct any that do not exist in the project structure.
    """
    valid_paths = {}
    for path, content in suggested_paths.items():
        relative_path = os.path.normpath(path)
        folder = os.path.dirname(relative_path)
        if folder in project_structure and relative_path in [os.path.join(folder, f) for f in project_structure[folder]]:
            valid_paths[relative_path] = content
        else:
            correction_prompt = f"""The following path was suggested but does not exist in the project: {relative_path}. 
Please provide the correct file path based on the actual project structure.

Project Structure:
{json.dumps(project_structure, indent=2)}
"""
            corrected_path_response = get_completion(correction_prompt)
            corrected_path = clean_file_content(corrected_path_response).strip()
            if corrected_path and corrected_path in project_structure.get(os.path.dirname(corrected_path), []):
                valid_paths[corrected_path] = content
            else:
                pass  # Skip invalid paths
    
    return valid_paths

def read_existing_documents(base_path: str) -> Tuple[str, str]:
    readme_path = os.path.join(base_path, "README.md")
    design_path = os.path.join(base_path, "TECHNICAL_DESIGN.json")
    
    if not os.path.exists(readme_path):
        raise FileNotFoundError(f"{readme_path} does not exist.")
    if not os.path.exists(design_path):
        raise FileNotFoundError(f"{design_path} does not exist.")
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        readme_content = f.read()
    
    with open(design_path, 'r', encoding='utf-8') as f:
        design_content = f.read()
    
    return readme_content, design_content

def load_file_content(base_path: str, file_list: List[str]) -> str:
    files_content = {}
    for file_path in file_list:
        full_path = os.path.join(base_path, file_path)
        full_path = full_path.replace(f"{base_path}/{base_path}", base_path)
        if not os.path.exists(full_path):
            print(f"File {full_path} does not exist, skipping.")
            continue
        with open(full_path, 'r', encoding='utf-8') as f:
            files_content[file_path] = f.read()
    return files_content