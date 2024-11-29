import json

# Util file to create text files for each of the samples in the test set
# This is used to manually verify the samples

with open('dataset/test.jsonl') as f:
    ctr = 0
    for line in f:
        data = json.loads(line)
        old_version = data['version_data'][0]
        new_version = data['version_data'][1]
        old_code = old_version['code']
        new_code = new_version['code']
        old_docstring = old_version['docstring']
        new_docstring = new_version['docstring']
        diff_code = data['diff_code']
        diff_docstring = data['diff_docstring']

        func_txt = "OLD VERSION" + '\n'
        func_txt += "OLD DOCSTRING: " + old_docstring + '\n'
        func_txt += '\n'
        func_txt += "OLD CODE: " + old_code + '\n'
        func_txt += '\n'
        func_txt += "OLD CODE WITH DOCSTRING: " + '\n'
        func_txt += '"""' + '\n' + old_docstring + '"""' + '\n' + old_code
        func_txt += '\n'
        func_txt += "****************************************************************************************************" + '\n'
        func_txt += '\n'
        func_txt += "DIFF DOCSTRING: " + '\n'
        func_txt += diff_docstring + '\n'
        func_txt += '\n'
        func_txt += "DIFF CODE: " + '\n'
        func_txt += diff_code + '\n'
        func_txt += '\n'
        # func_txt += "NEW VERSION" + '\n'
        # func_txt += "NEW DOCSTRING: " + new_docstring + '\n'
        # func_txt += '\n'
        # func_txt += "NEW CODE: " + new_code + '\n'
        # func_txt += '\n'
        # func_txt += "NEW CODE WITH DOCSTRING: " + '\n'
        # func_txt += '"""' + '\n' + new_docstring + '"""' + '\n' + new_code

        with open(f'labeled_200_samples/{ctr+1}.txt', 'w') as f:
            f.write(func_txt)
        ctr += 1
