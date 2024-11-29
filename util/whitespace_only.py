import json
import re

def remove_whitespace(text):
    """
    Removes all whitespace characters (spaces, tabs, newlines) from a given string.

    Args:
        text (str): The input string.

    Returns:
        str: The string with all whitespace characters removed.
    """
    return re.sub(r'\s+', '', text)

def remove_all_whitespace(file_path):
    """
    Processes a JSONL file to determine if changes between versions are solely due to whitespace differences.
    Removes entries from the dataset if the only changes are whitespace-related.

    Args:
        file_path (str): The path to the JSONL file.
    """
    new_lines = []
    with open(file_path) as f:
        for line in f:
            data = json.loads(line)
            old_version = data['version_data'][0]
            new_version = data['version_data'][1]

            # Extract code and docstring from old and new versions
            old_code = ""
            new_code = ""
            old_docstring = ""
            new_docstring = ""
            for keys in old_version:
                    for key in old_version[keys]:
                        if key == 'code':
                            old_code = old_version[keys]['code']
                            old_docstring = old_version[keys]['docstring']
                            #old_versions.append(old_version[keys])
                            # print(old_version[keys]['code'])
            for keys in new_version:
                for key in new_version[keys]:
                    if key == 'code':
                        new_code = new_version[keys]['code']
                        new_docstring = new_version[keys]['docstring']
            # Remove all whitespace from code and docstrings
            old_code = remove_whitespace(old_code)
            new_code = remove_whitespace(new_code)
            old_docstring = remove_whitespace(old_docstring)
            new_docstring = remove_whitespace(new_docstring)

            # Compare whitespace-normalized versions
            whitespace_only_code = old_code == new_code
            whitespace_only_docstring = old_docstring == new_docstring

            # Update flags in the data
            data['whitespace_only_code'] = whitespace_only_code
            data['whitespace_only_docstring'] = whitespace_only_docstring

            # Skip entries where changes are solely whitespace-related
            if whitespace_only_code or whitespace_only_docstring:
                continue

            new_lines.append(data)
    # Write the filtered data back to the file
    with open(file_path, 'w') as f:
        for line in new_lines:
            f.write(json.dumps(line) + '\n')

def remove_all_whitespace_pass_2(file_path):
    """
    Secondary pass to further refine entries by removing whitespace-related changes.
    Processes a JSONL file similarly to `remove_all_whitespace`.

    Args:
        file_path (str): The path to the JSONL file.
    """
    new_lines = []
    with open(file_path) as f:
        for line in f:
            data = json.loads(line)
            old_version = data['version_data'][0]
            new_version = data['version_data'][1]

            # Remove whitespace and compare versions
            old_code = remove_whitespace(old_version.get('code', ''))
            new_code = remove_whitespace(new_version.get('code', ''))
            old_docstring = remove_whitespace(old_version.get('docstring', ''))
            new_docstring = remove_whitespace(new_version.get('docstring', ''))

            whitespace_only_code = old_code == new_code
            whitespace_only_docstring = old_docstring == new_docstring

            # Update flags and skip irrelevant entries
            data['whitespace_only_code'] = whitespace_only_code
            data['whitespace_only_docstring'] = whitespace_only_docstring

            if whitespace_only_code or whitespace_only_docstring:
                continue

            new_lines.append(data)

    # Write filtered data back to the file
    with open(file_path, 'w') as f:
        for line in new_lines:
            f.write(json.dumps(line) + '\n')

if __name__ == '__main__':
    """
    Main script to process a JSONL dataset. Removes whitespace-only differences from code and docstring
    entries and outputs the cleaned dataset to a new file.
    """
    new_lines = []
    with open('dataset/fixed_dataset.jsonl') as f:
        for line in f:
            data = json.loads(line)
            old_version = data['version_data'][0]
            new_version = data['version_data'][1]

            # Extract code and docstring
            old_code = old_version.get('code', '')
            new_code = new_version.get('code', '')
            old_docstring = old_version.get('docstring', '')
            new_docstring = new_version.get('docstring', '')

            # Remove all whitespace
            old_code = remove_whitespace(old_code)
            new_code = remove_whitespace(new_code)
            old_docstring = remove_whitespace(old_docstring)
            new_docstring = remove_whitespace(new_docstring)

            # Compare versions and set flags
            whitespace_only_code = old_code == new_code
            whitespace_only_docstring = old_docstring == new_docstring

            data['whitespace_only_code'] = whitespace_only_code
            data['whitespace_only_docstring'] = whitespace_only_docstring

            new_lines.append(data)

    # Write the updated dataset to a new file
    with open('dataset/fixed_dataset_with_whitespace.jsonl', 'w') as f:
        for line in new_lines:
            f.write(json.dumps(line) + '\n')
