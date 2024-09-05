import os
from typing import List, Dict
import re, json
from .agent import get_completion, clean_file_content, parse_design, filter_out_test_files, clean_base_path, get_project_structure, generate_project_settings

def initial_tech_design(requirement: str, language: str, libraries: List[str], comment_language: str) -> str:
    system_message = "You are a tech lead. Your task is to design a highly modular technical solution for a given feature requirement. Ensure that the solution has a clear separation of concerns, where the main function only coordinates different modules and does not contain all the business logic itself."

    design_prompt = f"""Given the feature requirement, specified programming language, and required libraries or middleware, design a highly modular technical solution. Include the module design and file structure, and provide recommendations on where the test files should be located.

Ensure the following:
- The design is modular, with a clear separation of concerns and reusable components.
- The main function (or entry point) only coordinates the execution of different modules and does **not** contain the full business logic.
- Each module is independent and can be tested individually.
- The design must include a main function or entry point to ensure the solution is runnable.
- Include **all** necessary files as part of your design, with no missing components.

Return the file structure using the following format:
<file-structure>
文件路径
...
</file-structure>

Requirement:
{requirement}

Programming Language:
{language}

Libraries/Middleware:
{', '.join(libraries)}

Comment Language:
{comment_language}

Technical Design:"""

    design = get_completion(design_prompt, system_message=system_message)
    filtered_design = filter_out_test_files(design)
    return filtered_design.strip()

def reflect_on_tech_design(requirement: str, language: str, libraries: List[str], initial_design: str) -> str:
    system_message = "You are an expert tech lead who provides constructive feedback on technical design, with a focus on modularity and completeness."

    reflection_prompt = f"""You are tasked with reflecting on the following technical design for a feature requirement. Provide constructive feedback and suggestions to improve the design, with a focus on enhancing modularity, completeness, and file structure.

Requirement:
{requirement}

Programming Language:
{language}

Libraries/Middleware:
{', '.join(libraries)}

Initial Design:
{initial_design}
"""

    suggestions = get_completion(reflection_prompt, system_message=system_message)
    return suggestions.strip()

def rate_on_tech_design(requirement: str, language: str, libraries: List[str], design: str) -> str:
    system_message = "You are an expert tech lead who rates technical designs, with a focus on modularity, file structure, and overall quality."

    rating_prompt = f"""You are tasked with rating the following technical design for a feature requirement. Provide an overall score that reflects the general quality of the design, with a significant focus on the correctness and quality of the file structure.

Requirement:
{requirement}

Programming Language:
{language}

Libraries/Middleware:
{', '.join(libraries)}

Initial Design:
{design}

Considerations for Rating:
- Modularity of the design
- Completeness of the solution
- Correctness and quality of the file structure
- Overall adherence to best practices

Ratings:
Overall Score: [Rating out of 100]
"""

    rating = get_completion(rating_prompt, system_message=system_message)
    return rating.strip()

def improve_tech_design(requirement: str, language: str, libraries: List[str], initial_design: str, suggestions: str) -> str:
    system_message = "You are a tech lead. Your task is to improve the technical design based on expert suggestions, focusing on enhancing modularity, completeness, and file structure quality."

    improvement_prompt = f"""Based on the suggestions provided by the expert tech lead, improve the initial technical design with a focus on enhancing modularity, completeness, and especially the correctness and quality of the file structure.

Requirement:
{requirement}

Programming Language:
{language}

Libraries/Middleware:
{', '.join(libraries)}

Initial Design:
{initial_design}

Suggestions:
{suggestions}

Improved Technical Design:"""

    improved_design = get_completion(improvement_prompt, system_message=system_message)
    filtered_design = filter_out_test_files(improved_design)
    return filtered_design.strip()

def parse_score(rating: str) -> float:
    overall_score = 50.0
    for line in rating.splitlines():
        if "Overall Score:" in line:
            overall_score = re.sub(r"[^\d./]", "", line)
            overall_score = overall_score.split("/")[0].strip()
            try:
                overall_score = float(overall_score)
            except ValueError:
                overall_score = 50.0

    # 加重文件结构评分权重
    structure_score_weight = 0.5  # 50%权重给文件结构
    overall_score = overall_score * structure_score_weight + (overall_score * (1 - structure_score_weight))
    return overall_score

def verify_and_improve_design(requirement: str, language: str, libraries: List[str], design: str) -> str:
    system_message = "You are a senior tech lead. Your task is to verify the completeness of a technical design, identify any missing components, reference issues, or other problems, and suggest improvements."

    verification_prompt = f"""Review the following technical design. Identify any missing files, incorrect references, or components that are necessary for the design to be complete and fully functional. Provide suggestions for improvements and correct any issues found.

Requirement:
{requirement}

Programming Language:
{language}

Libraries/Middleware:
{', '.join(libraries)}

Technical Design:
{design}

Suggestions:"""

    suggestions = get_completion(verification_prompt, system_message=system_message)

    improvement_prompt = f"""Based on the following suggestions, improve the technical design to address any missing components, reference issues, or other problems.

Technical Design:
{design}

Suggestions:
{suggestions}

Improved Technical Design:"""

    improved_design = get_completion(improvement_prompt, system_message=system_message)
    return improved_design.strip()

def generate_testing_design(design: str, project_structure: Dict[str, List[str]]) -> str:
    system_message = "You are a senior test engineer. Your task is to design a comprehensive testing strategy for a given technical design. Ensure that the testing covers both the modular parts of the code and the program's executability (including the main function)."

    testing_prompt = f"""Based on the following technical design and the generated file structure, create a comprehensive testing strategy. The strategy should include:
- The testing libraries to be used.
- The structure and location of test files based on the provided file structure.
- Ensure the tests cover the modular components (unit tests for each module) and the program's executability (integration tests for the main function or entry point).
- Example test cases for each module, including one simple test case for each.
- Instructions for running tests that include all test files, even those outside the default locations (e.g., in the 'tests' folder in Rust).
- Instructions for testing without Docker.

Technical Design:
{design}

Generated File Structure:
{json.dumps(project_structure, indent=2)}

No Docker Testing Instructions:
Include specific steps and commands for testing the project without Docker here.

Testing Strategy:"""

    testing_design = get_completion(testing_prompt, system_message=system_message)
    return testing_design.strip()

def improve_testing_design(testing_design: str, design: str) -> str:
    system_message = "You are an expert test engineer who provides constructive feedback on testing design, with a focus on coverage and effectiveness."

    reflection_prompt = f"""Review the following testing design and provide constructive feedback and suggestions to improve the coverage and effectiveness of the tests.

Testing Design:
{testing_design}

Technical Design:
{design}

"""

    suggestions = get_completion(reflection_prompt, system_message=system_message)

    improvement_prompt = f"""Based on the following suggestions, improve the testing design to enhance coverage, completeness, maintainability, and integration.

Testing Design:
{testing_design}

Suggestions:
{suggestions}

Improved Testing Design:"""

    improved_testing_design = get_completion(improvement_prompt, system_message=system_message)
    return improved_testing_design.strip()

def extract_files_from_json(json_design: str) -> List[str]:
    system_message = "You are a helpful assistant specialized in extracting file paths from JSON design documents."

    extraction_prompt = f"""Extract all file paths from the following JSON design document. Return the file paths in a list.

JSON Design Document:
{json_design}

File Paths:"""

    file_paths = get_completion(extraction_prompt, system_message=system_message)
    return file_paths.strip()

def generate_codes_from_basepath(json_design: str, base_path: str) -> str:
    system_message = "You are an expert software developer. Based on the following JSON design document, generate the content for all files according to the specified file structure, ensuring that the project root directory is not repeated in the paths."

    generation_prompt = f"""Based on the following JSON design document, generate the content for all files. Ensure that the content adheres to the design specifications and that file paths do not incorrectly repeat the project root directory.

Do not change the file paths or structure. Return the file paths and their corresponding content in the following format:

<gen-file path=文件路径>
文件内容
</gen-file>

JSON Design Document:
{json_design}

Base Path:
{base_path}

Generated Files:"""

    generated_files = get_completion(generation_prompt, system_message=system_message)
    return generated_files.strip()

def create_project_files(base_path: str, files: Dict[str, str]) -> str:
    for file_path, content in files.items():
        full_path = "{}/{}".format(base_path, file_path).replace("//", "/")
        
        # 校验路径，避免出现类似 my_project/my_project/Cargo.toml 的错误
        if full_path.count(base_path) > 1:
            full_path = full_path.replace(f"{base_path}/", "", 1)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Writed file: {full_path}")
    
def generate_readme(requirement: str, language: str, libraries: List[str], comment_language: str, readme_language: str, design: str, testing_design: str, project_structure: Dict[str, List[str]]) -> str:
    system_message = "You are an expert in creating documentation for software projects."

    readme_prompt = f"""Create a README file for the following project. The README should include:
- Project background and goals
- Design philosophy with a focus on modularity
- Runbook explaining how to start and use the project, considering the specified programming language and libraries.
- Testing instructions including how to write and run tests, using the specified testing library and the test command provided in the Dockerfile.
- Ensure that the testing instructions cover all test files, even those located outside default test directories (e.g., 'tests' folder in Rust), based on the file structure.
- Instructions for testing without Docker.

Requirement:
{requirement}

Programming Language:
{language}

Libraries/Middleware:
{', '.join(libraries)}

Comment Language:
{comment_language}

Technical Design:
{design}

Testing Design:
{testing_design}

File Structure:
{json.dumps(project_structure, indent=2)}

No Docker Testing Instructions:
Include specific steps and commands for testing the project without Docker here.

README Language:
{readme_language}

README Content:"""

    readme_content = get_completion(readme_prompt, system_message=system_message)
    return readme_content.strip()

def convert_design_to_json(requirement: str, design: str) -> str:
    system_message = "You are an expert in technical documentation. Convert the following technical design document into a structured JSON format, capturing all key components and details, including the original requirement."

    json_prompt = f"""Convert the following technical design into a structured JSON format, including the original requirement:

Original Requirement:
{requirement}

Technical Design:
{design}

JSON:"""

    json_content = get_completion(json_prompt, system_message=system_message)
    return json_content.strip()

def senior_developer_agent(requirement: str, language: str, libraries: List[str], base_path: str, comment_language: str, readme_language: str) -> None:
    print("Checking project folder and cleaning up obsolete project files...")
    clean_base_path(base_path)

    print("Initial Design...")
    design = initial_tech_design(requirement, language, libraries, comment_language)

    print("Reviewing and reflecting on the design...")
    suggestions = reflect_on_tech_design(requirement, language, libraries, design)
    rated_score = rate_on_tech_design(requirement, language, libraries, design)
    overall_score = parse_score(rated_score)
    design_list = [(design, overall_score)]

    print(f"Improving the design ...")
    design = improve_tech_design(requirement, language, libraries, design, suggestions)
    rated_score = rate_on_tech_design(requirement, language, libraries, design)
    overall_score = parse_score(rated_score)
    design_list.append((design, overall_score))

    print("Choosing the best design and verifying its completeness...")
    best_design = max(design_list, key=lambda x: x[1])
    best_design_document = verify_and_improve_design(requirement, language, libraries, best_design[0])

    json_design = convert_design_to_json(requirement, best_design_document)
    json_design = clean_file_content(json_design)

    with open(os.path.join(base_path, "TECHNICAL_DESIGN.json"), 'w', encoding='utf-8') as f:
        f.write(json_design)

    print("Generating Codes...")
    generated_files = generate_codes_from_basepath(json_design, base_path)
    parsed_files = parse_design(generated_files)

    print("Creating project files...")
    create_project_files(base_path, parsed_files)
    file_structure = get_project_structure(base_path, [], [])
    
    print("Generating project settings...")
    generate_project_settings(base_path, language, libraries, best_design_document, file_structure)

    print("Generating Testing Design...")
    testing_design = generate_testing_design(best_design_document, file_structure)

    print("Improving Testing Design...")
    improved_testing_design = improve_testing_design(testing_design=testing_design, design=best_design_document)

    print("Updated Testing Design...")
    with open(os.path.join(base_path, "TESTING_DESIGN.txt"), 'w', encoding='utf-8') as f:
        f.write(improved_testing_design)

    readme_content = generate_readme(requirement, language, libraries, comment_language, readme_language, best_design_document, improved_testing_design, file_structure)

    print("Updated README Content...")
    with open(os.path.join(base_path, "README.md"), 'w', encoding='utf-8') as f:
        f.write(readme_content)
