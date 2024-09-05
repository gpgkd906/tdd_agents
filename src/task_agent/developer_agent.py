import os, sys
import subprocess
from typing import List, Dict, Tuple, Union
import json
from .agent import get_completion, clean_file_content, clean_code_with_openai, read_existing_documents
from .agent import get_skip_folders_and_file_extensions, get_all_files_in_base_path
from .agent import get_project_structure, generate_project_settings, load_file_content

improvement_context = {}

def categorize_errors(test_results: str) -> Dict[str, List[str]]:
    """
    Categorize the errors from the test results for prioritization.
    """
    system_message = "You are a Rust expert. Categorize the following errors based on their severity, potential impact, and the likelihood of causing other errors."

    categorize_prompt = f"""Categorize the following errors into groups based on severity, potential impact, and the likelihood of causing other errors.

Test Results:
{test_results}

Return the result in JSON format without any explanation.
JSON Format Example:
{{
    "critical": A JSON array of critical errors,
    "high": A JSON array of high severity errors,
    "medium": A JSON array of medium severity errors,
    "low": A JSON array of low severity errors
}}
"""
    response = get_completion(categorize_prompt, system_message=system_message)
    response = clean_file_content(response)
    try:
        categorized_errors = json.loads(response)
        return categorized_errors
    except json.JSONDecodeError as e:
        print(f"DA - L33 - JSON decode error: {e}")
        return {}

def read_project_files(master_context: Dict) -> Dict[str, str]:
    base_path = master_context.get("base_path", "")
    language = master_context.get("language", "")
    libraries = master_context.get("libraries", [])
    project_structure = master_context.get("project_structure", {})
    design = master_context.get("technical_design", "")
    skip_folders = master_context.get("skip_folders", [])
    file_extensions = master_context.get("file_extensions", [])

    all_files = []
    for root, _, files in os.walk(base_path):
        for file in files:
            # skip files in the specified folders            
            if any(os.path.join(root, file).startswith(os.path.join(base_path, skip_folder)) for skip_folder in skip_folders):
                continue
            file_path = os.path.relpath(os.path.join(root, file), base_path)
            all_files.append(file_path)
    
    system_message = "You are an expert software developer. Based on the provided list of files and the specified programming language, identify which file is the main project configuration file (e.g., Cargo.toml for Rust, package.json for JavaScript)."

    identification_prompt = f"""Given the following list of files and the specified programming language, identify the main project configuration file that defines dependencies, scripts, or other project settings.

Programming Language: {language}

List of Files:
{json.dumps(all_files, indent=2)}

Return the result in JSON format without any explanation.
JSON Format Example:
{{ 
    "project_file": "file_name" 
}}
"""
    project_file_response = get_completion(identification_prompt, system_message=system_message)
    project_file_response = clean_file_content(project_file_response).strip()

    project_files = {}
    try:
        project_file_data = json.loads(project_file_response)
        project_file = project_file_data.get("project_file")
        if project_file and project_file in all_files:
            full_path = os.path.join(base_path, project_file)
            full_path = full_path.replace(f"{base_path}/{base_path}", base_path)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    project_files[project_file] = f.read()
        else:
            print(f"Warning: Could not identify a valid project configuration file for {language}.")
            generate_project_settings(base_path, language, libraries, design, project_structure)
            return read_project_files(master_context)
    except json.JSONDecodeError as e:
        print(f"DA - L76 - JSON decode error: {e}")
    
    return project_files

def reload_project_files(base_path: str, project_files: Dict[str, str]) -> Dict[str, str]:
    for project_file, _ in project_files.items():
        full_path = os.path.join(base_path, project_file)
        full_path = full_path.replace(f"{base_path}/{base_path}", base_path)
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                project_files[project_file] = f.read()
    return project_files

def extract_test_info(master_context: Dict) -> Tuple[List[str], List[str]]:
    readme  = master_context.get("readme", "")
    technical_design = master_context.get("technical_design", "")
    project_structure = master_context.get("project_structure", {})

    test_files = []
    test_execution_commands_from_docs = []
    # Step 1: 从 README 和 TECHNICAL_DESIGN 文档中提取测试命令
    system_message_1 = "You are an expert test engineer. Extract all test file paths and test execution commands from the provided README and TECHNICAL_DESIGN documents."
    
    extraction_prompt_1 = f"""
Based on the following README and TECHNICAL_DESIGN documents, extract all test file paths and test execution commands.

README:
{readme}

TECHNICAL_DESIGN:
{technical_design}

Return the result in JSON format without any explanation.

JSON Format Example:
{{
    "test_files": A list of test file paths,
    "test_execution_commands": A JSON array of test execution commands
}}
"""

    extraction_response_1 = get_completion(extraction_prompt_1, system_message=system_message_1)
    extraction_response_1 = clean_file_content(extraction_response_1)

    try:
        extraction_data_1 = json.loads(extraction_response_1)
        test_files = extraction_data_1.get("test_files", [])
        test_execution_commands_from_docs = extraction_data_1.get("test_execution_commands", [])
    except json.JSONDecodeError as e:
        print(f"Error parsing the extraction response from design docs: {e}")

    # Step 2: 从项目文件结构中推测可能的测试命令，并确保与设计文档命令不重复
    system_message_2 = "You are an expert test engineer. Based on the project structure, predict possible test execution commands."
    
    extraction_prompt_2 = f"""
Based on the following project structure, predict possible test execution commands.

The predicted test execution commands should not duplicate any commands already found in the README or TECHNICAL_DESIGN.

Project Structure:
{json.dumps(project_structure, indent=2)}

Existing Test Commands from Design Documents:
{json.dumps(test_execution_commands_from_docs, indent=2)}

If there are common testing-related files in the project structure (e.g., `Makefile`, `setup.py`, `Cargo.toml`), suggest appropriate test execution commands based on these files, ensuring that no duplicate commands from the design documents are included.

Return the result in JSON format without any explanation.

JSON Format Example:
{{
    "test_execution_commands": A JSON array of predicted test execution commands based on the project structure
}}
"""

    extraction_response_2 = get_completion(extraction_prompt_2, system_message=system_message_2)
    extraction_response_2 = clean_file_content(extraction_response_2)

    try:
        extraction_data_2 = json.loads(extraction_response_2)
        test_execution_commands_from_structure = extraction_data_2.get("test_execution_commands", [])
    except json.JSONDecodeError as e:
        print(f"Error parsing the extraction response from project structure: {e}")
        test_execution_commands_from_structure = []

    combined_test_execution_commands = list(set(test_execution_commands_from_docs + test_execution_commands_from_structure))
    return test_files, combined_test_execution_commands

def execute_tests(test_command: str, base_path: str) -> str:
    try:
        # print(test_command, base_path)
        result = subprocess.run(
            test_command,
            cwd=base_path,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300  # Set timeout to 5 minutes
        )
        test_output = result.stdout + "\n" + result.stderr
        with open(os.path.join(base_path, "TEST_RESULTS.txt"), 'w', encoding='utf-8') as f:
            f.write(test_output)
        return test_output
    except subprocess.TimeoutExpired:
        return "Test execution timed out."

def analyze_test_results(improvement_context: Dict) -> Tuple[int, List[str], List[str], Dict[str, List[str]]]:
    language = improvement_context.get("language", "")
    libraries = improvement_context.get("libraries", [])
    all_files = improvement_context.get("all_files", [])
    project_files = improvement_context.get("project_files", {})
    project_structure = improvement_context.get("project_structure", {})
    test_results = improvement_context.get("test_results", "")
    reflection_suggestions = improvement_context.get("reflection_suggestions", "")

    system_message = "You are an expert test engineer. Analyze the test results, return the error count, and list the files that need to be modified, considering the specified programming language, libraries, project configuration files, and project structure."

    analysis_prompt = f"""Here are the test results and a list of all files in the project. Analyze these results, considering the specified programming language, libraries, project configuration files, and project structure. Provide the following:
1. The total number of errors found.
2. A list of all files that need to be modified based on these results, ensuring that the files exist in the project structure.
3. A separate list of project configuration files (e.g., Cargo.toml, package.json) that may need modification to fix dependencies or project settings.
4. considering the reflection suggestions provided, if any.

Programming Language:
{language}

Libraries:
{', '.join(libraries)}

Project Files:
{json.dumps(project_files, indent=2)}

Test Results:
{test_results}

All Files in Project:
{all_files}

Project Structure:
{json.dumps(project_structure, indent=2)}

Reflection Suggestions:
{reflection_suggestions}

Return the result in JSON format without any explanation.
JSON Format Example:
{{
    "error_count": The total number of errors found,
    "files_to_modify": A JSON array of file paths that need to be modified,
    "configuration_files_to_modify": A JSON array of project configuration files that may need changes.
}}
"""
    analysis_response = get_completion(analysis_prompt, system_message=system_message)
    analysis_response = clean_file_content(analysis_response)
    
    try:
        analysis_data = json.loads(analysis_response)
        error_count = analysis_data.get("error_count", 0)
        files_to_modify = analysis_data.get("files_to_modify", [])
        configuration_files_to_modify = analysis_data.get("configuration_files_to_modify", [])
        categorized_errors = categorize_errors(test_results)
        improvement_context["error_count"] = error_count
        improvement_context["files_to_modify"] = files_to_modify
        improvement_context["configuration_files_to_modify"] = configuration_files_to_modify
        improvement_context["categorized_errors"] = categorized_errors
        return improvement_context
    except json.JSONDecodeError as e:
        return analyze_test_results(improvement_context)

def detect_unnecessary_files(modified_files: Dict[str, str], project_structure: Dict[str, List[str]], project_configuration: Dict[str, str]) -> List[str]:
    system_message = "You are an expert software developer. Analyze the following project structure and modified files, and determine which files, if any, are unnecessary or misplaced based on the project structure and common development practices."

    analysis_prompt = f"""
You are provided with a list of modified files and the current project structure. Analyze whether any of the modified files are unnecessary, misplaced, or redundant based on the project structure and expected project configuration files.

The project structure is as follows:
{json.dumps(project_structure, indent=2)}

The modified files are as follows:
{json.dumps(modified_files, indent=2)}

The current project configuration (e.g., Cargo.toml, package.json) is as follows:
{json.dumps(project_configuration, indent=2)}

Please identify any unnecessary or misplaced files that should be deleted from the project. 

Return the result in JSON format without any explanation.
JSON Format Example:
{{
    "unnecessary_files": [
        "path/to/unnecessary_file1",
        "path/to/unnecessary_file2"
    ]
}}
"""
    # 调用 OpenAI 进行分析
    response = get_completion(analysis_prompt, system_message=system_message)
    response = clean_file_content(response)

    # 解析返回的结果
    try:
        analysis_data = json.loads(response)
        unnecessary_files = analysis_data.get("unnecessary_files", [])
        return unnecessary_files
    except json.JSONDecodeError as e:
        return []

def get_modification_results(improvement_context) -> Dict[str, Union[Dict[str, str], List[str]]]:
    base_path = improvement_context.get("base_path", "")
    files_to_modify = improvement_context.get("files_to_modify", [])
    configuration_files_to_modify = improvement_context.get("configuration_files_to_modify", [])
    test_results = improvement_context.get("test_results", "")
    categorized_errors = improvement_context.get("categorized_errors", {})
    project_files = improvement_context.get("project_files", {})
    project_structure = improvement_context.get("project_structure", {})
    reflection_suggestions = improvement_context.get("reflection_suggestions", "")
    
    system_message = (
        "You are an expert software developer. Modify the following files based on the test results and categorized errors, "
        "and ensure the file paths match the project structure. Maximize the modifications to improve the code quality, fix as many issues as possible, "
        "and check if any project configuration files (e.g., Cargo.toml, package.json) need modification to resolve dependencies or project settings."
    )

    files_content = load_file_content(base_path, files_to_modify)
    configuration_files_content = load_file_content(base_path, configuration_files_to_modify)

    modification_prompt = f"""Based on the following test results, categorized errors, and the project structure, maximize the modifications in the specified files to fix issues and improve code quality.

Test Results:
{test_results}

Categorized Errors:
{json.dumps(categorized_errors, indent=2)}

Files to Modify:
{json.dumps(files_content, indent=2)}

Configuration Files to Modify:
{json.dumps(configuration_files_content, indent=2)}

Project Files:
{json.dumps(project_files, indent=2)}

Project Structure:
{json.dumps(project_structure, indent=2)}

Reflection Suggestions:
{reflection_suggestions}

Ensure all modifications respect the existing project structure. Additionally, check if any project configuration files (e.g., Cargo.toml, package.json) need changes to fix dependencies or project settings. Return the modified content of each file as a dictionary under the key 'files'. If any files need to be deleted, provide a list under the key 'files_to_delete'.

Return the result in **strict JSON format** without any explanations.
JSON Format Example:
{{
    "files": {{
        "path/to/file1": "Modified content for file 1",
        "path/to/file2": "Modified content for file 2"
    }},
    "files_to_delete": A list of files to delete
}}
"""

    response = get_completion(modification_prompt, system_message=system_message)
    response = clean_file_content(response)

    reflection_prompt = f"""Reflect on the following response. Ensure that the modifications fully address all issues, and further optimize the changes where necessary. Also, confirm if any project configuration files (e.g., Cargo.toml, package.json) need modifications.

Response:
{response}

Test Results:
{test_results}

Categorized Errors:
{json.dumps(categorized_errors, indent=2)}

Project Structure:
{json.dumps(project_structure, indent=2)}

Please return an optimized version of the modifications in **strict JSON format** without any explanations.
JSON Format Example:
{{
    "files": {{
        "path/to/file1": "Modified content for file 1",
        "path/to/file2": "Modified content for file 2"
    }},
    "files_to_delete": A list of files to delete
}}
"""

    reflection_response = get_completion(reflection_prompt)
    reflection_response = clean_file_content(reflection_response)

    try:
        modification_data = json.loads(response)
    except json.JSONDecodeError as e:
        modification_data = {
            "files": parse_json_with_code(response),
            "files_to_delete": []
        }

    # 检查是否有不必要的文件
    modified_files = modification_data.get('files', {})
    unnecessary_files = detect_unnecessary_files(modified_files, project_structure, project_files)
    files_to_delete = modification_data.get("files_to_delete", []) + unnecessary_files

    return {
        "files": modified_files,
        "files_to_delete": files_to_delete
    }

def parse_json_with_code(json_response: str) -> Dict[str, str]:
    system_message_file_list = "Return only the list of file paths from the provided response."
    file_list_prompt = f"""
Given the following response, return only the file paths without any additional explanations:

Response:
{json_response}

Return format example:
["path/to/file1", "path/to/file2"]
"""

    file_list_response = get_completion(file_list_prompt, system_message=system_message_file_list)
    
    try:
        file_list = json.loads(file_list_response)
    except json.JSONDecodeError as e:
        print(f"Failed to parse file list: {e}")
        return {}

    files_content = {}
    system_message_file_content = "Return only the content of the specified file."
    
    for file_path in file_list:
        file_content_prompt = f"""
Given the following response and the file path '{file_path}', return only the content of the specified file without any explanations.

Response:
{json_response}

Return the content for file: {file_path}
"""

        file_content_response = get_completion(file_content_prompt, system_message=system_message_file_content)
        
        files_content[file_path] = file_content_response

    return files_content

def get_modified_files(improvement_context: Dict) -> List[Dict[str, str]]:
    base_path = improvement_context.get("base_path", "")
    project_files = improvement_context.get("project_files", {})
    test_results = improvement_context.get("test_results", "")
    project_structure = improvement_context.get("project_structure", {})
        
    modification_data = get_modification_results(improvement_context)

    modified_files = modification_data.get('files', [])
    files_to_delete = modification_data.get('files_to_delete', [])

    for file_to_delete in files_to_delete:
        full_path = os.path.join(base_path, file_to_delete)
        full_path = full_path.replace(f"{base_path}/{base_path}", base_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            print(f"Deleted file: {full_path}")

    final_modified_files = []
    for path in modified_files:
        new_content = modified_files[path]
        original_content = project_files.get(path, "")
        if new_content == original_content:
            system_message = "You are an expert software developer."
            retry_prompt = f"""The following file's content was returned without any changes. Based on the test results, please make the necessary modifications to improve or fix the code.

File Path: {path}
Original Content:
{original_content}

Test Results:
{test_results}

Project Structure:
{json.dumps(project_structure, indent=2)}

Please return **only** the modified content without explanations."""
            retry_response = get_completion(retry_prompt, system_message=system_message)
            retry_response = clean_file_content(retry_response)
            new_content = retry_response
        final_modified_files.append({
            "path": path,
            "content": new_content
        })

    return final_modified_files

def update_file(base_path: str, file_path: str, new_content: str) -> None:
    full_path = os.path.join(base_path, file_path)
    full_path = full_path.replace(f"{base_path}/{base_path}", base_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Writed file: {full_path}")

def select_correct_test_command(base_path: str, test_execution_commands: List[str]) -> str:
    correct_test_command = None
    test_results_by_command = {}

    for test_command in test_execution_commands:
        test_results = execute_tests(test_command, base_path)
        test_results_by_command[test_command] = test_results
    system_message = "You are an expert test engineer. Analyze the following test results for different commands and identify the most effective one."

    selection_prompt = f"""
You are provided with test results from different test execution commands. Your task is to select the most **effective** test command, considering the following criteria:

1. If the test command returns errors that indicate a **language mismatch** (e.g., trying to run Python tests in a JavaScript project), consider that test command invalid.
2. Ignore errors that are caused by **incorrect test command usage** (e.g., running a completely unrelated test framework).
3. Among test commands that return errors from actual **test code** execution, even if the error count is greater than zero, consider them **valid**.
4. If multiple test commands are valid, select the one that covers the **widest range** of tests or files.
5. Focus on the test results that best align with the project structure and goals.

Test Results by Command:
{json.dumps(test_results_by_command, indent=2)}

Return the correct test command in JSON format without any explanation:
{{
    "correct_command": "the most effective test command"
}}
"""

    selection_response = get_completion(selection_prompt, system_message=system_message)
    selection_response = clean_file_content(selection_response)
    try:
        selection_data = json.loads(selection_response)
        correct_test_command = selection_data.get("correct_command")
    except json.JSONDecodeError as e:
        print(f"L530: {e}")
        return

    if not correct_test_command:
        print("invalid test command.")
        return
    print(f"test command: {correct_test_command}")

    return correct_test_command

def reflect_and_optimize(test_results: str, previous_context: str) -> str:
    system_message = "You are an expert test engineer and developer. Reflect on the previous test results, modification history, and current errors."

    reflection_prompt = f"""
Based on the following previous context and current test results, reflect on what may be causing the issues to remain unresolved. Suggest a new strategy or deeper modifications that could address the issues effectively.

Previous Context:
{previous_context}

Current Test Results:
{test_results}

Provide a detailed strategy or modifications in JSON format without any explanation.
"""
    reflection_response = get_completion(reflection_prompt, system_message=system_message)
    reflection_response = clean_file_content(reflection_response)
    
    return reflection_response


def track_iteration_progress(previous_errors: Dict[str, List[str]], current_errors: Dict[str, List[str]]) -> bool:
    critical_change = abs(len(current_errors.get("critical", [])) - len(previous_errors.get("critical", [])))
    high_change = abs(len(current_errors.get("high", [])) - len(previous_errors.get("high", [])))

    print(f"Critical Change: {critical_change}, High Change: {high_change}")
    if critical_change == 0 and high_change <= 2:  # Example thresholds
        return True
    return False

def developer_agent(
    requirement: str,
    language: str,
    libraries: List[str],
    base_path: str,
    comment_language: str,
    readme_language: str
) -> None:
    print("Load technical design document...")
    try:
        readme, technical_design = read_existing_documents(base_path)
    except FileNotFoundError as e:
        print(e)
        return

    master_context = {}    
    skip_folders, file_extensions = get_skip_folders_and_file_extensions(language, libraries)
    master_context["base_path"] = base_path
    master_context["language"] = language
    master_context["skip_folders"] = skip_folders
    master_context["file_extensions"] = file_extensions
    master_context["technical_design"] = technical_design
    master_context["readme"] = readme
    master_context["libraries"] = libraries

    project_structure = get_project_structure(base_path, skip_folders, file_extensions)
    master_context["project_structure"] = project_structure
    print("Read current code...")
    project_files = read_project_files(master_context)

    print("Try to figure out the test command...")
    _, test_execution_commands = extract_test_info(master_context)

    correct_test_command = select_correct_test_command(base_path, test_execution_commands)
    if not correct_test_command:
        return

    improve_loop_count = 0
    previous_errors = {"critical": [], "high": [], "medium": [], "low": []}
    previous_context = ""
    reflection_suggestions = ""

    while improve_loop_count < 20:
        improve_loop_count += 1
        improvement_context = {
            "language": language,
            "libraries": libraries,
            "base_path": base_path,
            "project_files": project_files,
            "project_structure": project_structure,
            "correct_test_command": correct_test_command,
            "reflection_suggestions": reflection_suggestions,
        }
        print(f"The {improve_loop_count}th refactoring begins: ")

        all_files, project_structure = get_all_files_in_base_path(base_path, skip_folders, file_extensions)

        improvement_context["all_files"] = all_files
        improvement_context["project_structure"] = project_structure

        print("Run the tests...")
        test_results = execute_tests(correct_test_command, base_path)
        improvement_context["test_results"] = test_results

        print("Analyze Result of tests...")
        improvement_context = analyze_test_results(improvement_context)
        error_count = improvement_context["error_count"]
        categorized_errors = improvement_context["categorized_errors"]

        print(f"There is {error_count} errrors in the test results.")

        if error_count == 0:
            print("Refactoring completed successfully.")
            break

        if track_iteration_progress(previous_errors, categorized_errors):
            print("refactoring progress bottleneck, entering reflection mode...")
            reflection_suggestions = reflect_and_optimize(test_results, previous_context)
            previous_context += f"\nReflection {improve_loop_count}: {reflection_suggestions}"
            improvement_context["reflection_suggestions"] = reflection_suggestions
            print("with reflaction suggestions re-analyze the test results...")
            improvement_context = analyze_test_results(improvement_context)
        else:
            pass

        print("With the test results, attempt to refactor the code...")
        modified_files = get_modified_files(improvement_context)

        for modified_file in modified_files:
            file_path = modified_file.get("path", "")
            new_content = modified_file.get("content", "")
            new_content = clean_code_with_openai(new_content)
            if file_path and new_content:
                update_file(base_path, file_path, new_content)

        print("reload project files...")
        project_files = reload_project_files(base_path, project_files)
        
        previous_errors = categorized_errors

    print("The number of reconfigurations reaches the maximum of 20 and stops the reconfiguration. Please perform the refactoring task again if necessary.")