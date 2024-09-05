import os
from typing import List, Dict, Tuple
import yaml, json
from .agent import get_completion, clean_file_content, get_skip_folders_and_file_extensions, get_project_structure

def read_project_documents(base_path: str) -> Tuple[str, str]:
    readme_path = os.path.join(base_path, "README.md")
    testing_design_path = os.path.join(base_path, "TESTING_DESIGN.txt")
    
    if not os.path.exists(readme_path):
        raise FileNotFoundError(f"{readme_path} does not exist.")
    if not os.path.exists(testing_design_path):
        raise FileNotFoundError(f"{testing_design_path} does not exist.")
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        readme_content = f.read()
    
    with open(testing_design_path, 'r', encoding='utf-8') as f:
        testing_design_content = f.read()
    
    return readme_content, testing_design_content

def read_technical_design(base_path: str) -> str:
    technical_design_path = os.path.join(base_path, "TECHNICAL_DESIGN.json")

    if not os.path.exists(technical_design_path):
        raise FileNotFoundError(f"{technical_design_path} does not exist.")

    with open(technical_design_path, 'r', encoding='utf-8') as f:
        technical_design_content = f.read()

    return technical_design_content

def find_test_files(base_path: str, skip_folders: List[str], file_extensions: List[str]) -> Tuple[List[str], Dict[str, List[str]]]:
    test_files = []
    project_structure = get_project_structure(base_path, skip_folders, file_extensions)
    for folder, files in project_structure.items():
        for file in files:
            if "test" in file.lower():
                test_files.append(os.path.join(folder, file))
    return test_files, project_structure

def analyze_test_coverage(requirement: str, language: str, libraries: List[str], readme_content: str, testing_design: str, test_files: List[str], technical_design: str, base_path: str, project_structure: Dict[str, List[str]]) -> str:
    system_message = "You are an expert QA engineer. Analyze the current test files, testing design, and technical design to identify gaps and deficiencies, considering the specified programming language and libraries."

    analysis_prompt = f"""Based on the project requirement, README content, testing design, technical design, the list of test files, the project base path, and the specified programming language and libraries, analyze the current testing coverage. Identify any gaps, such as missing test cases, insufficient scenarios, or incomplete test coverage.

In addition, suggest where the test files should be located within the project structure. Ensure the suggested locations align with standard practices for the given programming language.

Requirement:
{requirement}

Programming Language:
{language}

Libraries/Middleware:
{', '.join(libraries)}

README Content:
{readme_content}

Testing Design:
{testing_design}

Technical Design:
{technical_design}

Project Base Path:
{base_path}

Test Files:
{test_files}

Project Structure:
{json.dumps(project_structure, indent=2)}

Please provide your analysis and suggestions for improving the test coverage and the appropriate locations for test files within the project structure:
"""

    analysis = get_completion(analysis_prompt, system_message=system_message)
    return analysis.strip()

def improve_test_coverage(requirement: str, language: str, libraries: List[str], readme_content: str, testing_design: str, technical_design: str, analysis: str, base_path: str, project_structure: Dict[str, List[str]]) -> str:
    system_message = "You are an expert QA engineer. Improve the testing design based on the analysis of test coverage gaps, considering the specified programming language, libraries, technical design, and project base path. Ensure the new test files are placed in the correct locations within the project structure."

    improvement_prompt = f"""Based on the analysis of the current test coverage and considering the specified programming language, libraries, technical design, project base path, and project structure, improve the testing design to cover the identified gaps. Add necessary test cases, scenarios, and improve the overall effectiveness of the tests. Ensure that new test files are created in the appropriate locations within the project structure. If necessary, include new test files. Ensure that existing test cases are not modified unless explicitly required.

Requirement:
{requirement}

Programming Language:
{language}

Libraries/Middleware:
{', '.join(libraries)}

README Content:
{readme_content}

Testing Design:
{testing_design}

Technical Design:
{technical_design}

Project Base Path:
{base_path}

Project Structure:
{json.dumps(project_structure, indent=2)}

Analysis:
{analysis}

Please provide the improved testing design, including any new test files, ensuring they are located in the correct places:
"""

    improved_testing_design = get_completion(improvement_prompt, system_message=system_message)

    # 反省设计并确保测试文件路径正确
    reflection_prompt = f"""Please review the following improved testing design. Ensure that all test files are located in the appropriate paths according to the project structure. If any test file paths are incorrect, provide the corrected paths.

Improved Testing Design:
{improved_testing_design}

Project Structure:
{json.dumps(project_structure, indent=2)}

Return the corrected testing design if necessary:
"""
    corrected_testing_design = get_completion(reflection_prompt, system_message=system_message)
    return corrected_testing_design.strip()

def extract_test_files(improved_testing_design: str, base_path: str, project_structure: Dict[str, List[str]]) -> List[Dict[str, str]]:
    system_message = "You are an expert QA engineer. Based on the improved testing design, extract the file paths and generate corresponding test code. Ensure the tests cover critical functionalities, edge cases, and integration points, and that file paths are correct according to the project structure."

    extraction_prompt = f"""Based on the following improved testing design, generate the file paths and corresponding test code. Ensure that:
1. The test cases cover all critical functionalities and integration points.
2. Edge cases are adequately covered.
3. The test code is concrete and executable.
4. The file paths are correctly placed in appropriate locations within the project structure.

Improved Testing Design:
{improved_testing_design}

Project Base Path:
{base_path}

Project Structure:
{json.dumps(project_structure, indent=2)}

Return the result in Yaml format without any extra explanation. The format should be:
- path: The file path (relative to base_path).
  content: The full content of the generated test code
"""

    extraction_results = get_completion(extraction_prompt, system_message=system_message)
    extraction_results = clean_file_content(extraction_results)
    # 反省路径，并检查是否符合项目结构
    reflection_prompt = f"""Review the following generated test file paths. Ensure that all paths are valid and conform to the project structure. If any paths are incorrect, correct them.

Generated Test Files:
{extraction_results}

Project Structure:
{json.dumps(project_structure, indent=2)}

Return the result in Yaml format without any extra explanation. The format should be:
- path: The file path (relative to base_path).
  content: The full content of the generated test code
"""
    corrected_extraction_results = get_completion(reflection_prompt, system_message=system_message)
    corrected_extraction_results = clean_file_content(corrected_extraction_results)

    try:
        return yaml.safe_load(corrected_extraction_results)
    except yaml.YAMLError as e:
        return []

def sanitize_file_path(base_path: str, file_path: str) -> str:
    sanitized_path = os.path.normpath(os.path.join(base_path, file_path))
    if not sanitized_path.startswith(base_path):
        raise ValueError(f"Invalid file path generated: {file_path}")
    return sanitized_path

def update_test_files(base_path: str, test_files: List[Dict[str, str]]) -> None:
    for test_file in test_files:
        try:
            file_path = sanitize_file_path(base_path, test_file["path"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(test_file["content"])
            print(f"Updated test file: {file_path}")
        except ValueError as e:
            print(f"Error updating file: {e}")

def qa_engineer_agent(
    requirement: str,
    language: str,
    libraries: List[str],
    base_path: str,
    comment_language: str,
    readme_language: str
) -> None:
    print("Load project documents...")
    skip_folders, file_extensions = get_skip_folders_and_file_extensions(language, libraries)

    try:
        readme_content, testing_design = read_project_documents(base_path)
    except FileNotFoundError as e:
        print(e)
        return

    print("Load technical design document...")
    try:
        technical_design = read_technical_design(base_path)
    except FileNotFoundError as e:
        print(e)
        return

    print("find test codes...")
    test_files, project_structure = find_test_files(base_path, skip_folders, file_extensions)

    print("Analyze the test coverage...")
    analysis = analyze_test_coverage(requirement, language, libraries, readme_content, testing_design, test_files, technical_design, base_path, project_structure)    
    with open(os.path.join(base_path, "TESTING_ANALYSIS.txt"), 'w', encoding='utf-8') as f:
        f.write(analysis)

    print("Improving the testing design...")
    improved_testing_design = improve_test_coverage(requirement, language, libraries, readme_content, testing_design, technical_design, analysis, base_path, project_structure)

    print("Save the improved testing design...")
    with open(os.path.join(base_path, "TESTING_DESIGN.txt"), 'w', encoding='utf-8') as f:
        f.write(improved_testing_design)

    print("Extracting test files...")
    new_test_files = extract_test_files(improved_testing_design, base_path, project_structure)

    print("Updating test files:")
    update_test_files(base_path, new_test_files)

    print("QA Engineer task completed successfully.")
