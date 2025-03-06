import os
import sys
import shutil
from git import Repo
from pydriller import Repository
import re
import json
from diff_to_jsonl import diff_extractor
from util.whitespace_only import remove_all_whitespace, remove_all_whitespace_pass_2
from util.assoc_fixer import assoc_fixer
from util.diff_fixer import process_diffs
from util.extract_common_info import common_info
from util.lines import fix_docstring_code_lines

last_commit = None

def clone_repository(username, repository):
    """
    Clone the repository if it does not exist

    :param username: Username of the repository owner
    :param repository: Name of the repository
    """
    repo_url = f'https://github.com/{username}/{repository}.git'
    repo_path = f'{username}_{repository}'

    if not os.path.exists(repo_path):
        os.system(f'git clone {repo_url} {repo_path}')

    return repo_path

def find_and_files(directory, prefix):
    """
    Recursively search for files that begin with the given prefix in the specified directory.

    :param directory: Directory to search for files
    :param prefix: Prefix to match the files
    """
    matching_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.startswith(prefix):
                matching_files.append(os.path.join(root, file))
    return matching_files

def get_last_commit(repo_path):
    """
    Get the last commit of the repository

    :param repo_path: Path to the cloned repository
    """
    repo = Repo(repo_path)
    return repo.head.commit.hexsha

def get_commits(username, repository, filename, repo_path=None):
    """
    Get the commits for the file and save the functions and their docstrings in a JSON file
    Writes other metadata like commit date time, commit SHA, project name, owner, filename and file path to the JSON file as well
    Also, find the differences between the consecutive versions and save them in text files

    :param username: Username of the repository owner
    :param repository: Name of the repository
    :param filename: Name of the file
    :param repo_path: Path to the cloned repository
    """

    global last_commit

    # reclone the repository if the repo_path is not provided
    repo_path = clone_repository(username, repository)

    # get the last commit of the repository
    last_commit = get_last_commit(repo_path)

    print(f"Last commit: {last_commit}")

    version_count = 1  # Initialize version count

    all_functions = {}  # Dictionary to store all functions and their docstrings

    for commit in Repository(repo_path, filepath=filename).traverse_commits():
        commit_sha = commit.hash
        commit_date_time = str(commit.committer_date)
        commit_message = commit.msg
        print(f"Commit SHA: {commit_sha}")
        function = download_file_at_commit(repo_path, commit_sha, filename, version_count)
        all_functions["v" + str(version_count)] = function
        # add commit date time to the function dictionary
        if all_functions["v" + str(version_count)] is not None:
            all_functions["v" + str(version_count)]["commit_date_time"] = commit_date_time
            all_functions["v" + str(version_count)]["commit_sha"] = commit_sha
            all_functions["v" + str(version_count)]["project"] = repository
            all_functions["v" + str(version_count)]["owner"] = username
            all_functions["v" + str(version_count)]["filename"] = filename
            all_functions["v" + str(version_count)]["file_path"] = str(os.path.join(repo_path, filename)).split(repo_path + '/')[1]
            all_functions["v" + str(version_count)]["commit_message"] = commit_message
        version_count += 1  # Increment version count

    # write out the function dictionary to a file
    with open(f"functions_{filename.replace('/', '_')}.json", 'w') as function_file:
        json.dump(all_functions, function_file, indent=4)

    what_changed_between_versions(f"functions_{filename.replace('/', '_')}.json")
    clean_up(repo_path, filename, last_commit)

def download_file_at_commit(repo_path, commit_sha, filename, version_count):
    """
    Download the file at the specified commit and save the comments and code in separate text files
    Also, split the comments and code and save them in separate files

    :param repo_path: Path to the cloned repository
    :param commit_sha: Commit SHA to checkout
    :param filename: Name of the file
    :param version_count: Version count
    """

    repo = Repo(repo_path)
    repo.git.reset('--hard', commit_sha)

    source_path = os.path.join(repo_path, filename)
    save_path = f"v{version_count}_{commit_sha}_{filename.replace('/', '_')}"

    try:
        with open(source_path, 'r') as file:
            try:
                content = file.read()
            except UnicodeDecodeError:
                with open('your_file.txt', 'r', encoding='utf-8') as file:
                    content = file.read()
            comments, code, function = split_comments_and_code(content)
            # # add a layer of "docstring" to the function dictionary between the key and value
            # function = {k: {"docstring": v} for k, v in function.items()}
            save_comments_and_code(save_path, comments, code)
            print(f"File saved at: {save_path}")
            # reset the repo to the original state
            repo.git.reset('--hard', 'HEAD')
            return function
            # write out the function dictionary to a file
    except FileNotFoundError:
        print(f"Saving file at: {save_path}")
        print(f"Source path: {source_path}")
        print(f"File not found at commit {commit_sha}")
        # move to the next commit



def split_comments_and_code(content):
    """
    Split the comments and code from the content on a function level

    Docstrings and its line numbers are extracted; code and its line numbers are extracted

    :param content: Content of the file
    """
    comments_with_line = []  # List to store comments along with line numbers
    code = []  # List to store code lines
    lines = content.split('\n')
    current_line_number = 1

    in_docstring = False
    docstring_lines = []
    current_function = None  # Variable to store the current function being parsed
    functions = {}  # Dictionary to store functions and their docstrings

    for line in lines:
        # Check if the line is within a docstring block
        if in_docstring:
            if '"""' in line:
                docstring_lines.append(line.strip())
                comments_with_line.append((current_line_number, '\n'.join(docstring_lines)))
                in_docstring = False
                start_code_line = current_line_number + 1

                # Associate docstring with the current function
                if current_function:
                    functions[current_function] = {
                        'docstring_lines': {'start_line': start_line, 'end_line': start_code_line},
                        'docstring': '\n'.join(docstring_lines),
                        'code': '\n'.join(code),
                        'code_lines': {'start_line': start_code_line, 'end_line': current_line_number}
                    }
            else:
                docstring_lines.append(line.strip())
        # all possible # statements in C code
        elif line.strip().startswith('#include') or line.strip().startswith('#define') or line.strip().startswith(
                '#ifndef') or line.strip().startswith('#ifdef') or line.strip().startswith('#endif') or line.strip().startswith(
            '#if') or line.strip().startswith('#else') or line.strip().startswith('#elif') or line.strip().startswith(
            '#pragma') or line.strip().startswith('#undef') or line.strip().startswith('#error') or line.strip().startswith(
            '#warning') or line.strip().startswith('#line'):
            # Skip #include statements but add them to the code
            code.append(line)
        # Check if the line contains a comment
        elif '//' in line or '/*' in line or '#' in line:
            # Extract comments and their line numbers
            comment_matches = re.finditer(r'(\/\/.*|\/\*[\s\S]*?\*\/|#.*)', line)
            for match in comment_matches:
                comment = match.group(1).strip()
                comments_with_line.append((current_line_number, comment))
            # Extract code and remove comments
            code.append(re.sub(r'(\/\/.*|\/\*[\s\S]*?\*\/|#.*)', '', line).strip())
        # if """ is in line twice, then it is also a docstring
        elif line.count('"""') == 2:
            comments_with_line.append((current_line_number, line.strip()))
            start_code_line = current_line_number + 1
            if current_function:
                functions[current_function] = {
                    'docstring_lines': {'start_line': start_line, 'end_line': start_code_line},
                    'docstring': line.strip(),
                    'code': '\n'.join(code),
                    'code_lines': {'start_line': start_code_line, 'end_line': current_line_number}
                }
                docstring_lines = [line.strip()]
        elif '"""' in line:
            in_docstring = True
            start_line = current_line_number
            # start_code_line = current_line_number + 1
            # empty the docstring_lines list
            docstring_lines = []
            docstring_lines.append(line.strip())
        else:
            # Check if the line contains a function definition
            function_match = re.match(
                r'\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)\s*(?:->\s*([a-zA-Z_][a-zA-Z0-9_.\[\]]*)\s*)?:', line)
            # if function_match is empty, try to match a class definition
            if function_match is None:
                function_match = re.match(r'\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*\)\s*:', line)
            if function_match:
                # If there was a previous function, store its code
                if current_function:
                    if len('\n'.join(docstring_lines)) == 0:
                        functions[current_function] = {
                            'docstring_lines': {'start_line': start_line, 'end_line': start_line},
                            'docstring': '\n'.join(docstring_lines),
                            'code': '\n'.join(code),
                            'code_lines': {'start_line': start_code_line, 'end_line': current_line_number - 1}
                        }
                    else:
                        functions[current_function] = {
                            'docstring_lines': {'start_line': start_line, 'end_line': start_code_line},
                            'docstring': '\n'.join(docstring_lines),
                            'code': '\n'.join(code),
                            'code_lines': {'start_line': start_code_line, 'end_line': current_line_number - 1}
                        }
                start_code_line = current_line_number + 1
                current_function = function_match.group(1)
                start_line = current_line_number
                # start_code_line = current_line_number + 1
                code = []  # Reset code lines for the new function
                docstring_lines = []  # Reset docstring lines for the new function

            code.append(line)

        current_line_number += 1

    # If there's still a current function after parsing, store its code
    if current_function:
        if len('\n'.join(docstring_lines)) == 0:
            functions[current_function] = {
                'docstring_lines': {'start_line': start_line, 'end_line': start_line},
                'docstring': '\n'.join(docstring_lines),
                'code': '\n'.join(code),
                'code_lines': {'start_line': start_code_line, 'end_line': current_line_number - 1}
            }
        else:
            functions[current_function] = {
                'docstring_lines': {'start_line': start_line, 'end_line': start_code_line},
                'docstring': '\n'.join(docstring_lines),
                'code': '\n'.join(code),
                'code_lines': {'start_line': start_code_line, 'end_line': current_line_number - 1}
            }

    return comments_with_line, '\n'.join(code), functions



def save_comments_and_code(save_path, comments_with_line, code):
    """
    This function saves the comments and code to a text file

    :param save_path: Path to save the files
    :param comments_with_line: List of comments with line numbers
    :param code: Code to be saved
    """
    print(f"Saving comments and code at: {save_path}")
    with open(f"{save_path}_comments.txt", 'w') as comment_file:
        for line_number, comment in comments_with_line:
            comment_file.write(f"Line {line_number}: {comment}\n")
    with open(f"{save_path}_code.txt", 'w') as code_file:
        code_file.write(code)

def what_changed_between_versions(json_file):
    """
    This function compares the functions between consecutive versions and prints the differences in code, docstring and both
    It also saves the differences in a text file, with the naming convention: code_diff_<filename>.txt, docstring_diff_<filename>.txt, differ_<filename>.txt

    :param json_file: Name of the JSON file containing the functions
    """
    # go consecutive versions and compare the functions to see if code or docstring or both changed
    with open(json_file, 'r') as function_file:
        functions = json.load(function_file)

    version_count = len(functions)
    version = 1

    code_differ_file = f"code_diff_{json_file.replace('.json', '.txt')}"
    docstring_differ_file = f"docstring_diff_{json_file.replace('.json', '.txt')}"
    differ_file = f"differ_{json_file.replace('.json', '.txt')}"

    while version < version_count:
        current_version = functions[f"v{version}"]
        next_version = functions[f"v{version + 1}"]

        if current_version is None or next_version is None:
            version += 1
            continue

        if current_version == {} or next_version == {}:
            version += 1
            continue

        for function_name in current_version:
            print(f"Function: {function_name}")
            if function_name == 'commit_date_time' or function_name == 'commit_sha' or function_name == 'project' or function_name == 'owner' or function_name == 'filename' or function_name == 'file_path' or function_name == 'code_lines' or function_name == 'docstring_lines' or function_name == 'commit_message':
                continue
            if function_name in next_version:
                current_function = current_version[function_name]
                next_function = next_version[function_name]

                # if not 'commit_date_time' in current_function or not 'commit_date_time' in next_function:

                if current_function['docstring'] != next_function['docstring'] and current_function['code'] != next_function['code']:
                    print(f"Docstring and code changed for function {function_name} between versions {version} and {version + 1}")
                    with open(differ_file, 'a') as diff_file:
                        diff_file.write(f"Docstring and code changed for function {function_name} between versions {version} and {version + 1}\n")
                    with open(f"{function_name}_v{version}_docstring.txt", 'w') as docstring_file:
                        docstring_file.write(current_function['docstring'])
                    with open(f"{function_name}_v{version + 1}_docstring.txt", 'w') as docstring_file:
                        docstring_file.write(next_function['docstring'])
                    with open(f"{function_name}_v{version}_code.txt", 'w') as code_file:
                        code_file.write(current_function['code'])
                    with open(f"{function_name}_v{version + 1}_code.txt", 'w') as code_file:
                        code_file.write(next_function['code'])
                    # print the exact changes between the two versions like git diff
                    # print(f"Diff for function {function_name} between versions {version} and {version + 1}")
                    os.system(f"diff -u {function_name}_v{version}_docstring.txt {function_name}_v{version + 1}_docstring.txt")
                    with open(differ_file, 'a') as diff_file:
                        os.system(f"diff -u {function_name}_v{version}_docstring.txt {function_name}_v{version + 1}_docstring.txt >> {differ_file}")
                        diff_file.write("\n")
                    os.system(f"diff -u {function_name}_v{version}_code.txt {function_name}_v{version + 1}_code.txt")
                    with open(differ_file, 'a') as diff_file:
                        os.system(f"diff -u {function_name}_v{version}_code.txt {function_name}_v{version + 1}_code.txt >> {differ_file}")
                        diff_file.write("\n")
                    # remove the temporary code files
                    os.remove(f"{function_name}_v{version}_docstring.txt")
                    os.remove(f"{function_name}_v{version + 1}_docstring.txt")
                    os.remove(f"{function_name}_v{version}_code.txt")
                    os.remove(f"{function_name}_v{version + 1}_code.txt")

                if current_function['docstring'] != next_function['docstring']:
                    print(f"Docstring changed for function {function_name} between versions {version} and {version + 1}")
                    with open(docstring_differ_file, 'a') as diff_file:
                        diff_file.write(f"Docstring changed for function {function_name} between versions {version} and {version + 1}\n")
                    with open(f"{function_name}_v{version}_docstring.txt", 'w') as docstring_file:
                        docstring_file.write(current_function['docstring'])
                    with open(f"{function_name}_v{version + 1}_docstring.txt", 'w') as docstring_file:
                        docstring_file.write(next_function['docstring'])
                    # print the exact changes between the two versions like git diff
                    # print(f"Diff for function {function_name} between versions {version} and {version + 1}")
                    os.system(f"diff -u {function_name}_v{version}_docstring.txt {function_name}_v{version + 1}_docstring.txt")
                    with open(docstring_differ_file, 'a') as diff_file:
                        os.system(f"diff -u {function_name}_v{version}_docstring.txt {function_name}_v{version + 1}_docstring.txt >> {docstring_differ_file} ")
                        diff_file.write("\n")
                    # remove the temporary code files
                    os.remove(f"{function_name}_v{version}_docstring.txt")
                    os.remove(f"{function_name}_v{version + 1}_docstring.txt")

                if current_function['code'] != next_function['code']:
                    print(f"Code changed for function {function_name} between versions {version} and {version + 1}")
                    with open(code_differ_file, 'a') as diff_file:
                        diff_file.write(f"Code changed for function {function_name} between versions {version} and {version + 1}\n")
                    with open(f"{function_name}_v{version}_code.txt", 'w') as code_file:
                        code_file.write(current_function['code'])
                    with open(f"{function_name}_v{version + 1}_code.txt", 'w') as code_file:
                        code_file.write(next_function['code'])
                    # print the exact changes between the two versions like git diff
                    # print(f"Diff for function {function_name} between versions {version} and {version + 1}")
                    os.system(f"diff -u {function_name}_v{version}_code.txt {function_name}_v{version + 1}_code.txt")
                    with open(code_differ_file, 'a') as diff_file:
                        os.system(f"diff -u {function_name}_v{version}_code.txt {function_name}_v{version + 1}_code.txt >> {code_differ_file}")
                        diff_file.write("\n")
                    # remove the temporary code files
                    os.remove(f"{function_name}_v{version}_code.txt")
                    os.remove(f"{function_name}_v{version + 1}_code.txt")

        version += 1

def clean_up(repo_path, filename, last_commit):
    """
    This function cleans up the repository and moves the diff and JSON files to a unique directory named after the file and its project path
    It also deletes the cloned repository

    :param repo_path: Path to the cloned repository
    :param filename: Name of the file
    """
    filename = filename.replace('/', '_')
    # move all files to a directory
    if not os.path.exists('f{repo_path}_{filename}_files'):
        try:
            folder = f'{repo_path}_{filename}_files'
        except:
            # make the directory with a different name
            folder = f'{repo_path}_{filename}_files_1'
        os.makedirs(folder)

    # move all .txt files and .json files to the directory
    for file in os.listdir():
        if file.endswith('.txt') or file.endswith('.json'):
            shutil.move(file, folder)

    # reset the repo to the last commit
    repo = Repo(repo_path)
    repo.git.reset('--hard', last_commit)

def copy_files(matching_files):
    """
    This function copies the files to the differ_files directory
    To aggegrate all the diff files from all the projects into one directory

    :param matching_files: List of files to be copied
    """
    for file in matching_files:
        # copy the files to the directory
        os.system('cp '+file+' differ_files/')
        if file.split('/')[-1].startswith('differ_'):
            # also copy the json file in that directory
            os.system('cp ' +file.replace('differ_','').replace('txt','json')+' differ_files/')
        elif file.split('/')[-1].startswith('docstring_'):
            # also copy the json file in that directory
            os.system('cp ' +file.replace('docstring_diff_','').replace('txt','json')+' differ_files/')
        elif file.split('/')[-1].startswith('code_'):
            # also copy the json file in that directory
            os.system('cp ' +file.replace('code_diff_','').replace('txt','json')+' differ_files/')

def help():
    """
    This function prints the help message
    """
    print("Invalid number of arguments")
    print(f"Usage: python parse.py <username> <repository> <filename>")
    print("Example: python parse.py torvalds linux kernel/sched/core.py")
    print("This will process the file core.py from the linux repository owned by torvalds")
    print("Example: python parse.py torvalds linux")
    print("This will process all the Python files from the linux repository owned by torvalds")
    print("Example: python parse.py")
    print("This will process all the Python files in all the projects in the projects.csv file")
    sys.exit(1)

def main():
    """
    This is the main function
    It processes the projects and creates the differ files
    """
    if len(sys.argv) not in [1, 3, 4]:
        help()

    if len(sys.argv) == 1:
        process_projects()
    else:
        process_single_project()

    create_differ_files()

    # run whitespace only script on combined_diff_mapping_differ_.jsonl in the differ_files directory
    remove_all_whitespace('differ_files/combined_diff_mapping_differ_.jsonl')

    # use tree-sitter to fix associations
    assoc_fixer('differ_files/combined_diff_mapping_differ_.jsonl')

    # move fixed file to the differ_files directory
    os.system('mv fixed_combined_diff_mapping_differ_.jsonl differ_files/')

    # fix the keys in the fixed file
    fix_keys('./differ_files/fixed_combined_diff_mapping_differ_.jsonl', code=True)
    fix_keys('./differ_files/fixed_combined_diff_mapping_differ_.jsonl', code=False)

    # re-fix the diffs
    process_diffs('differ_files/fixed_combined_diff_mapping_differ_.jsonl')

    remove_all_whitespace_pass_2('differ_files/fixed_combined_diff_mapping_differ_.jsonl')

    common_info('differ_files/fixed_combined_diff_mapping_differ_.jsonl')

    # rename the fixed file to codocbench.jsonl
    os.system('mv differ_files/fixed_combined_diff_mapping_differ_.jsonl differ_files/codocbench.jsonl')

    fix_docstring_code_lines('differ_files/codocbench.jsonl')

    # remove the temporary files
    delete_repo_folders()

def process_projects():
    """
    In case no arguments are provided, this function processes all the projects in the projects.csv file
    All the files from the projects are processed
    """
    with open('projects.csv', 'r') as projects_file:
        projects = projects_file.readlines()[1:]
        for project in projects:
            username, repository = project.strip().split(',')
            print(f"Username: {username}")
            print(f"Repository: {repository}")
            repo_path = clone_repository(username, repository)
            all_PY_files = get_python_files(repo_path)
            print("Total number of python files: ", len(all_PY_files))
            for file in all_PY_files:
                print(f"We are at file number {all_PY_files.index(file)}")
                print(f"Number of files left: {len(all_PY_files) - all_PY_files.index(file)}")
                process_file(username, repository, file, repo_path)
            shutil.rmtree(repo_path, ignore_errors=True)

def process_single_project():
    """
    In case the arguments are provided, this function processes the single project
    If the filename is provided, only that file is processed
    Otherwise, all the files from the project are processed
    """
    username = sys.argv[1]
    repository = sys.argv[2]
    filename = sys.argv[3] if len(sys.argv) == 4 else None

    print(f"Username: {username}")
    print(f"Repository: {repository}")
    print(f"Filename: {filename}")

    repo_path = clone_repository(username, repository)

    if filename is None:
        all_PY_files = get_python_files(repo_path)
        print("Total number of python files: ", len(all_PY_files))
        for file in all_PY_files:
            print(f"We are at file number {all_PY_files.index(file)}")
            print(f"Number of files left: {len(all_PY_files) - all_PY_files.index(file)}")
            process_file(username, repository, file, repo_path)
    else:
        get_commits(username, repository, filename, repo_path)
    shutil.rmtree(repo_path, ignore_errors=True)

def delete_repo_folders():
    """
    Deletes all folders in the current directory that start with '<username>_<repository>'.
    """
    for folder in os.listdir('.'):  # List all items in the current directory
        if os.path.isdir(folder) and '_' in folder and 'differ' not in folder:  # Check if it is a folder and contains '_'
            parts = folder.split('_')
            if len(parts) >= 2:  # Ensure the name has at least two parts
                print(f"Deleting folder: {folder}")
                shutil.rmtree(folder, ignore_errors=True)
    print("Deletion process completed.")

def get_python_files(repo_path):
    """
    This function gets all the python files from the repository.

    :param repo_path: Path to the cloned repository
    """
    all_PY_files = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith('.py'):
                file = os.path.join(root, file).split(repo_path + '/')[1]
                all_PY_files.append(file)
    return [file for file in all_PY_files if file]

def process_file(username, repository, file, repo_path):
    """
    This function processes the file and gets the commits for the file

    :param username: Username of the repository owner
    :param repository: Name of the repository
    :param file: Name of the file
    :param repo_path: Path to the cloned repository
    """
    print(f"Getting commits for file: {file}")
    files_folder = f'{username}_{repository}_{file.replace("/", "_")}_files'
    if not os.path.exists(files_folder):
        try:
            get_commits(username, repository, file, repo_path)
        except Exception as e:
            print(f"Error: {e}")
            print(f"Retrying to process file: {file}")
            shutil.rmtree(repo_path, ignore_errors=True)
            while True:
                get_commits(username, repository, file, repo_path)
                if os.path.exists(files_folder):
                    break
    else:
        print(f"File: {file} already processed")

def create_differ_files():
    """
    This function creates the differ files
    It finds the files that start with the prefixes: docstring_, code_, differ_
    It copies the files to the differ_files directory
    It extracts the differences between the consecutive versions
    """
    os.mkdir('differ_files')
    for prefix in ['docstring_', 'code_', 'differ_']:
        matching_files = find_and_files('.', prefix)
        copy_files(matching_files)
        diff_extractor(prefix)

def fix_keys(filename, code=True):
    """
    This function fixes the keys in the fixed file
    The association fixer duplicated the keys
    So, the first instance of docstring and code is deleted (because they are the unfixed keys)
    """
    with open(filename) as f:
        data = f.readlines()
        data = [json.loads(d) for d in data]

    new_data = []

    for d in data:
        try:
            old_version = d['version_data'][0]
            new_version = d['version_data'][1]
            function_name = d['function'].split('.')[-1]

            for keys in old_version:
                for key in old_version[keys]:
                    # delete the first instance of docstring and code
                    if key == 'docstring' and not code:
                        del old_version[keys][key]
                        break
                    if key == 'code' and code:
                        del old_version[keys][key]
                        break

            for keys in new_version:
                for key in new_version[keys]:
                    # delete the first instance of docstring and code
                    if key == 'docstring' and not code:
                        del new_version[keys][key]
                        break
                    if key == 'code' and code:
                        del new_version[keys][key]
                        break

            # update version_data
            d['version_data'][0] = old_version
            d['version_data'][1] = new_version

            new_data.append(d)

        except:
            continue

    with open(filename, 'w') as f:
        for d in new_data:
            f.write(json.dumps(d) + '\n')


if __name__ == "__main__":
    main()
