import json
import argparse

def load_data(file_path):
    """
    Loads JSONL (JSON Lines) data from a file.

    Args:
        file_path (str): Path to the JSONL file.

    Returns:
        list: A list of Python dictionaries loaded from the JSONL file.
    """
    with open(file_path, 'r') as file:
        data = file.readlines()
        data = [json.loads(d) for d in data]
    return data

def process_entries(entries):
    """
    Processes a list of JSON entries to extract and restructure common metadata.

    Args:
        entries (list): A list of JSON objects, where each object contains:
                        - `version_data`: A list of two dictionaries (old and new versions).
                          Each dictionary may have keys such as `file_path`, `filename`, `project`, and `owner`.

    Returns:
        list: A list of updated entries with:
              - Top-level keys `file_path`, `filename`, `project`, and `owner` extracted from the old version.
              - These keys removed from the `version_data` dictionaries.
    """
    new_data = []
    for entry in entries:
        try:
            old_version = entry['version_data'][0]
            new_version = entry['version_data'][1]

            # Extract and add top-level metadata
            entry['file_path'] = old_version.get('file_path', '')
            entry['filename'] = old_version.get('filename', '').split('/')[-1]
            entry['project'] = old_version.get('project', '')
            entry['owner'] = old_version.get('owner', '')

            # Remove the extracted keys from both versions
            for version in (old_version, new_version):
                for key in ['file_path', 'filename', 'project', 'owner']:
                    version.pop(key, None)

            # Update the entry with processed version data
            entry['version_data'] = [old_version, new_version]
            new_data.append(entry)
        except Exception as e:
            print(f"Error processing entry: {e}")
            continue
    return new_data

def write_data(file_path, data):
    """
    Writes processed JSON data back to a JSONL file.

    Args:
        file_path (str): Path to the output file.
        data (list): A list of JSON objects to write to the file.
    """
    with open(file_path, 'w') as file:
        for entry in data:
            file.write(json.dumps(entry) + '\n')

def common_info(file_path):
    """
    Reads, processes, and writes back JSONL data with extracted common metadata.

    Args:
        file_path (str): Path to the JSONL file to process.
    """
    entries = load_data(file_path)
    new_data = process_entries(entries)
    write_data(file_path, new_data)

# Main script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract common information from JSON entries.")
    parser.add_argument("file_path", help="Path to the JSON file containing entries.")
    args = parser.parse_args()
    common_info(args.file_path)
