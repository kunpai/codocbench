#!/usr/bin/env python3
import json
import sys
import subprocess
import ast
import os

# --- Function to remove the first occurrence of docstring_lines and code_lines ---
def remove_first_occurrence(version):
    """
    Iterates over keys in the version dict. If a key starting with 'v' (e.g., 'v11' or 'v12') is found and its value is a dict,
    removes the keys 'docstring_lines' and 'code_lines' from that nested dict.
    If the nested dict becomes empty, it is removed entirely.
    Only the first such occurrence is processed.
    """
    for key in list(version.keys()):
        if key.startswith('v') and isinstance(version[key], dict):
            subdict = version[key]
            subdict.pop('docstring_lines', None)
            subdict.pop('code_lines', None)
            if not subdict:
                del version[key]
            break  # Only process the first occurrence

# --- Functions to compute and extract line numbers for a function ---

def compute_line_numbers(func_start, docstring_text="", code_text=""):
    """
    Given the starting line number for a function along with the docstring and code text,
    compute and return the line ranges for the docstring and code blocks.
    
    - If a docstring exists, its end_line is: start_line + (number of docstring lines) - 1.
    - The code block’s end_line is: start_line + (number of docstring lines) + (number of code lines) - 1.
    """
    doc_lines = len(docstring_text.splitlines()) if docstring_text else 0
    code_lines = len(code_text.splitlines()) if code_text else 0

    docstring_lines = {"start_line": func_start, "end_line": func_start + doc_lines - 1} if doc_lines > 0 else {}
    code_lines_dict = {"start_line": func_start, "end_line": func_start + doc_lines + code_lines - 1} if code_lines > 0 else {}

    return {
        "docstring_lines": docstring_lines,
        "code_lines": code_lines_dict
    }

def extract_function_data_naive(file_path, function_name, docstring_text="", code_text=""):
    """
    A fallback extraction function that accepts the docstring and code text as parameters.
    It scans the file line-by-line for a function definition matching the function_name and then computes the line ranges.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    func_start = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("def ") and stripped[4:].startswith(function_name + "("):
            func_start = i + 1  # Convert to 1-indexed line number
            break

    if func_start is None:
        return {"error": f"Function {function_name} not found in {file_path}"}

    return compute_line_numbers(func_start, docstring_text, code_text)

def extract_function_data(file_path, function_name):
    """
    Uses AST to extract the docstring and code line numbers for the given function.
    If successful, returns a dictionary with keys 'docstring_lines' and 'code_lines'.
    If AST parsing fails or the function is not found, an error key is returned.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=file_path)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                docstring = ast.get_docstring(node, clean=False)
                docstring_start = (
                    node.body[0].lineno
                    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str)
                    else None
                )
                docstring_end = docstring_start + len(docstring.split('\n')) - 1 if docstring and docstring_start else None

                return {
                    "docstring_lines": {"start_line": docstring_start, "end_line": docstring_end} if docstring else {},
                    "code_lines": {"start_line": node.lineno, "end_line": node.end_lineno}
                }
    except Exception as e:
        return {"error": str(e)}

    return {"docstring_lines": {}, "code_lines": {}}  # Function not found


def fix_docstring_code_lines(file_path):
    input_file = file_path
    with open(input_file, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f]

    print(f"Processing {len(data)} entries from {input_file}")

    new_data = []
    errors = []

    for d in data:
        try:
            # Retrieve the two version entries from the JSON data
            old_version = d['version_data'][0]
            new_version = d['version_data'][1]
            
            # Optional: Print keys for debugging
            print(old_version.keys())
            print(new_version.keys())

            # Remove any preexisting nested docstring_lines and code_lines in the first occurrence (if any)
            remove_first_occurrence(old_version)
            remove_first_occurrence(new_version)
            
            # Extract metadata needed for GitHub file download and function extraction
            owner = d['owner']
            project = d['project']
            sha_old = old_version['commit_sha']
            sha_new = new_version['commit_sha']
            file_path = d['file_path']
            # Get the function name (assumes the 'function' field may be namespaced; take the last part)
            function = d['function'].split('.')[-1]
            old_docstring = old_version['docstring']
            old_code = old_version['code']
            new_docstring = new_version['docstring']
            new_code = new_version['code']

            # Build raw GitHub URLs for both versions
            github_link_old = f'https://raw.githubusercontent.com/{owner}/{project}/{sha_old}/{file_path}'
            github_link_new = f'https://raw.githubusercontent.com/{owner}/{project}/{sha_new}/{file_path}'

            # Download the files using wget
            result_old = subprocess.run(['wget', '-q', github_link_old, '-O', 'old.py'], check=False)
            result_new = subprocess.run(['wget', '-q', github_link_new, '-O', 'new.py'], check=False)

            if result_old.returncode != 0 or result_new.returncode != 0:
                errors.append(f"Failed to download files for {owner}/{project} at {file_path}")
                continue

            # First try using AST-based extraction.
            old_data = extract_function_data('old.py', function)
            new_data_extracted = extract_function_data('new.py', function)

            # If AST parsing failed, fall back to the naive extraction approach.
            if "error" in old_data:
                old_data = extract_function_data_naive('old.py', function, docstring_text=old_docstring, code_text=old_code)
            if "error" in new_data_extracted:
                new_data_extracted = extract_function_data_naive('new.py', function, docstring_text=new_docstring, code_text=new_code)

            # Update the version dictionaries with the newly extracted line information
            old_version['docstring_lines'] = old_data['docstring_lines']
            old_version['code_lines'] = old_data['code_lines']
            new_version['docstring_lines'] = new_data_extracted['docstring_lines']
            new_version['code_lines'] = new_data_extracted['code_lines']

            # Save the updated versions back into the data object
            d['version_data'][0] = old_version
            d['version_data'][1] = new_version

            new_data.append(d)

        except Exception as e:
            errors.append(f"Error processing {d.get('owner','unknown')}/{d.get('project','unknown')} at {d.get('file_path','unknown')}: {str(e)}. File is {sys.argv[1]}")
        finally:
            # Clean up downloaded files
            for file in ['old.py', 'new.py']:
                try:
                    os.remove(file)
                except FileNotFoundError:
                    pass

    # Write the updated data back to a new JSONL file
    output_file = input_file
    print(f"Writing updated data to {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in new_data:
            f.write(json.dumps(entry) + '\n')

    # Write any error logs to a separate file
    if errors:
        with open('error_log.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(errors) + '\n')

    print(f"Processing completed. Updated data saved in {output_file}")
    if errors:
        print("Some errors occurred. Check 'error_log.txt' for details.")
