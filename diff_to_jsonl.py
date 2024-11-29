import os
import json


def diff_extractor(prefix):
    """
    Converts the diff txt files to a jsonl file.
    """
    # get the current working directory
    cwd = os.getcwd()

    # move into differ_files directory
    os.chdir('differ_files')

    # get all the files in the directory
    files = os.listdir()

    differ_files = [f for f in files if f.startswith(prefix) and f.endswith('.txt')]
    print("Number of files found:", len(differ_files))
    file_version_mapping = {}
    for file in differ_files:
        with open(file, 'r') as f:
            data = f.read()
            lines = data.split('\n')
            for line in lines:
                if prefix.startswith('differ_'):
                    if 'Docstring and code changed for function' in line:
                        try:
                            functions = line.split('Docstring and code changed for function')[1].rsplit('between', 1)[0].strip()
                            versions = line.rsplit('versions', 1)[1].rsplit('and', 1)
                            versions = [v.strip() for v in versions]
                            if file in file_version_mapping:
                                file_version_mapping[file].append({'functions': functions, 'versions': versions})
                            else:
                                file_version_mapping[file] = []
                                file_version_mapping[file].append({'functions': functions, 'versions': versions})
                        except:
                            print('Error in extracting versions')
                            print(line)
                            break
                elif prefix.startswith('code_'):
                    if 'Code changed for function' in line:
                        try:
                            functions = line.split('Code changed for function')[1].rsplit('between', 1)[0].strip()
                            versions = line.rsplit('versions', 1)[1].rsplit('and', 1)
                            versions = [v.strip() for v in versions]
                            if file in file_version_mapping:
                                file_version_mapping[file].append({'functions': functions, 'versions': versions})
                            else:
                                file_version_mapping[file] = []
                                file_version_mapping[file].append({'functions': functions, 'versions': versions})
                        except:
                            print('Error in extracting versions')
                            print(line)
                            break
                elif prefix.startswith('docstring_'):
                    if 'Docstring changed for function' in line:
                        try:
                            functions = line.split('Docstring changed for function')[1].rsplit('between', 1)[0].strip()
                            versions = line.rsplit('versions', 1)[1].rsplit('and', 1)
                            versions = [v.strip() for v in versions]
                            if file in file_version_mapping:
                                file_version_mapping[file].append({'functions': functions, 'versions': versions})
                            else:
                                file_version_mapping[file] = []
                                file_version_mapping[file].append({'functions': functions, 'versions': versions})
                        except:
                            print('Error in extracting versions')
                            print(line)
                            break

    diff_mapping = {}

    for file in file_version_mapping:
        if prefix.startswith('differ_'):
            corresponding_json_file = file.replace('differ_', '').replace('.txt', '.json')
        elif prefix.startswith('code_'):
            corresponding_json_file = file.replace('code_diff_', '').replace('.txt', '.json')
        elif prefix.startswith('docstring_'):
            corresponding_json_file = file.replace('docstring_diff_', '').replace('.txt', '.json')
        for entry in file_version_mapping[file]:
            functions = entry['functions']
            versions = entry['versions']
            try:
                with open(corresponding_json_file, 'r') as f:
                    data = json.load(f)
                    for version in versions:
                        key = corresponding_json_file.split('functions_')[1].split('.json')[0]
                        if key in diff_mapping:
                            if functions in data["v" + version]:
                                if functions in diff_mapping[key]:
                                    diff_mapping[key][functions].append({'v' + version: data["v" + version][functions], "commit_date_time": data["v" + version]["commit_date_time"], "commit_sha": data["v" + version]["commit_sha"], "project": data["v" + version]["project"], "owner": data["v" + version]["owner"], "filename": data["v" + version]["filename"], "file_path": data["v" + version]["file_path"], "commit_message": data["v" + version]["commit_message"]})
                                else:
                                    diff_mapping[key][functions] = [{'v' + version: data["v" + version][functions], "commit_date_time": data["v" + version]["commit_date_time"], "commit_sha": data["v" + version]["commit_sha"], "project": data["v" + version]["project"], "owner": data["v" + version]["owner"], "filename": data["v" + version]["filename"], "file_path": data["v" + version]["file_path"], "commit_message": data["v" + version]["commit_message"]}]
                            else:
                                print(f"Function '{functions}' not found in version 'v{version}' of file '{corresponding_json_file}'.")
                        else:
                            diff_mapping[key] = {}
                            if functions in data["v" + version]:
                                diff_mapping[key][functions] = [{'v' + version: data["v" + version][functions], "commit_date_time": data["v" + version]["commit_date_time"], "commit_sha": data["v" + version]["commit_sha"], "project": data["v" + version]["project"], "owner": data["v" + version]["owner"], "filename": data["v" + version]["filename"], "file_path": data["v" + version]["file_path"], "commit_message": data["v" + version]["commit_message"]}]
                            else:
                                print(f"Function '{functions}' not found in version 'v{version}' of file '{corresponding_json_file}'.")
            except:
                # skip the file if it doesn't exist
                print(f"File '{corresponding_json_file}' not found.")
                continue

    # write the diff_mapping to a .jsonl file
    with open('diff_mapping_' + prefix + '.jsonl', 'w') as f:
        for key in diff_mapping:
            for function, versions in diff_mapping[key].items():
                for version_data in versions:
                    json.dump({'file': key, 'function': function, 'version_data': version_data}, f)
                    f.write('\n')

    # reopen the jsonl file and print the contents
    with open('diff_mapping_' + prefix + '.jsonl', 'r') as f:
        # take two consecutive lines at a time
        for line1, line2 in zip(f, f):
            print(line1.strip())
            print(line2.strip())
            # combine the two lines' "version_data" dictionaries as two elements of a list and maintain other keys as is
            combined = []
            line1_data = json.loads(line1)
            line2_data = json.loads(line2)
            combined.append(line1_data['version_data'])
            combined.append(line2_data['version_data'])
            line1_data['version_data'] = combined
            print(combined)
            # write the new combined data to a new file
            with open('combined_diff_mapping_' + prefix + '.jsonl', 'a') as f2:
                json.dump(line1_data, f2)
                f2.write('\n')

    # delete the original diff_mapping.jsonl file
    os.remove('diff_mapping_' + prefix + '.jsonl')

    # move back to the original directory
    os.chdir(cwd)
