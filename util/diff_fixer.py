import json
import difflib

def process_diffs(filename):
    """
    Processes a JSONL (JSON Lines) file containing code and docstring versions to compute their diffs.

    Args:
        filename (str): Path to the JSONL file containing the dataset. Each line is a JSON object with
                        the following structure:
                        {
                            "version_data": [
                                {"code": <str>, "docstring": <str>},
                                {"code": <str>, "docstring": <str>}
                            ]
                        }

    The function performs the following:
    1. Reads the dataset from the specified file.
    2. Computes line-by-line diffs for the code and docstrings between the old and new versions.
    3. Adds the computed diffs as new keys (`diff_code` and `diff_docstring`) in the JSON objects.
    4. Writes the updated dataset back to the file, replacing the original content.

    Notes:
        - If an entry in the dataset is invalid or processing fails for any reason, an error message is
          printed, and the entry is skipped.
        - The file content is overwritten with the processed data.

    Example:
        Input JSON line:
        {
            "version_data": [
                {"code": "def add(a, b):\\n    return a + b", "docstring": "Adds two numbers."},
                {"code": "def add(a, b):\\n    return a - b", "docstring": "Subtracts two numbers."}
            ]
        }

        Output JSON line:
        {
            "version_data": [
                {"code": "def add(a, b):\\n    return a + b", "docstring": "Adds two numbers."},
                {"code": "def add(a, b):\\n    return a - b", "docstring": "Subtracts two numbers."}
            ],
            "diff_code": "- def add(a, b):\\n?                ^\\n+ def add(a, b):\\n?                ^\\n-     return a + b\\n?                ^\\n+     return a - b\\n?                ^",
            "diff_docstring": "- Adds two numbers.\\n+ Subtracts two numbers.\\n"
        }

    Raises:
        FileNotFoundError: If the specified file does not exist.
        JSONDecodeError: If the file contains invalid JSON.
    """
    # Load dataset
    with open(filename) as f:
        data = f.readlines()  # Read all lines from the file
        data = [json.loads(d) for d in data]  # Parse each line as a JSON object

    new_data = []  # Initialize list to store processed data

    for d in data:
        try:
            # Extract old and new version information
            old_version = d['version_data'][0]
            new_version = d['version_data'][1]

            old_code = old_version['code']
            new_code = new_version['code']

            old_docstring = old_version['docstring']
            new_docstring = new_version['docstring']

            # Compute line-by-line diffs for code and docstrings
            diff_code = difflib.ndiff(old_code.splitlines(), new_code.splitlines())
            diff_docstring = difflib.ndiff(old_docstring.splitlines(), new_docstring.splitlines())

            # Add computed diffs to the current data entry
            d['diff_code'] = '\n'.join(diff_code)
            d['diff_docstring'] = '\n'.join(diff_docstring)

            new_data.append(d)  # Add processed entry to the new data list

        except Exception as e:
            print(f"Error processing entry: {e}")  # Log any errors and skip the current entry
            continue

    # Save processed data back to the file
    with open(filename, 'w') as f:
        for d in new_data:
            f.write(json.dumps(d) + '\n')  # Write each processed entry as a JSON line
