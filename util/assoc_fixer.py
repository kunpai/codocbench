import json
import subprocess
import function_parser
import os
from function_parser.process import DataProcessor
from tree_sitter import Language
import argparse
import json
import functools
from multiprocessing import Pool
import pickle
from os import PathLike
from typing import Optional, Tuple, Type, List, Dict, Any

from docopt import docopt
from dpu_utils.codeutils.deduplication import DuplicateDetector
import pandas as pd
from tree_sitter import Language, Parser

from function_parser.language_data import LANGUAGE_METADATA
from function_parser.parsers.language_parser import LanguageParser, tokenize_docstring
from function_parser.utils import download, get_sha, flatten, remap_nwo, walk




LANGUAGE_METADATA = {
    'python': {
        'ext': ['py'],
        'language_parser': LANGUAGE_METADATA['python']['language_parser']
    },
}



class DataProcessor:

    PARSER = Parser()

    def __init__(self, language: str, language_parser: Type[LanguageParser]):
        self.language = language
        self.language_parser = language_parser
        self.proj_name=""

    def process_dee(self, nwo, ext) -> List[Dict[str, Any]]:
        # Process dependees (libraries) to get function implementations
        indexes = []
        _, nwo = remap_nwo(nwo)
        if nwo is None:
            return indexes

        tmp_dir = download(nwo)
        files = walk(tmp_dir, ext)
        # files = glob.iglob(tmp_dir.name + '/**/*.{}'.format(ext), recursive=True)
        sha = None

        for f in files:
            definitions = self.get_function_definitions(f)
            if definitions is None:
                continue
            if sha is None:
                sha = get_sha(tmp_dir, nwo)

            nwo, path, functions = definitions
            indexes.extend((self.extract_function_data(func, nwo, path, sha) for func in functions if len(func['function_tokens']) > 1))
        return indexes

    def process_dent(self, nwo, ext, library_candidates) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
        # Process dependents (applications) to get function calls
        dents = []
        edges = []
        _, nwo = remap_nwo(nwo)
        if nwo is None:
            return dents, edges

        tmp_dir = download(nwo)
        files = walk(tmp_dir, ext)
        sha = None

        for f in files:
            context_and_calls = self.get_context_and_function_calls(f)
            if context_and_calls is None:
                continue
            if sha is None:
                sha = get_sha(tmp_dir, nwo)

            nwo, path, context, calls = context_and_calls
            libraries = []
            for cxt in context:
                if type(cxt) == dict:
                    libraries.extend([v.split('.')[0] for v in cxt.values()])
                elif type(cxt) == list:
                    libraries.extend(cxt)

            match_scopes = {}
            for cxt in set(libraries):
                if cxt in library_candidates:
                    match_scopes[cxt] = library_candidates[cxt]

            for call in calls:
                for depended_library_name, dependend_library_functions in match_scopes.items():
                    for depended_library_function in dependend_library_functions:
                        # Other potential filters: len(call['identifier']) > 6 or len(call['identifier'].split('_')) > 1
                        if (call['identifier'] not in self.language_parser.STOPWORDS and
                            ((depended_library_function['identifier'].split('.')[-1] == '__init__' and
                              call['identifier'] == depended_library_function['identifier'].split('.')[0]) or
                             ((len(call['identifier']) > 9 or
                               (not call['identifier'].startswith('_') and len(call['identifier'].split('_')) > 1)) and
                              call['identifier'] == depended_library_function['identifier'])
                            )):
                            dent = {
                                'nwo': nwo,
                                'sha': sha,
                                'path': path,
                                'language': self.language,
                                'identifier': call['identifier'],
                                'argument_list': call['argument_list'],
                                'url': 'https://github.com/{}/blob/{}/{}#L{}-L{}'.format(nwo, sha, path,
                                                                                         call['start_point'][0] + 1,
                                                                                         call['end_point'][0] + 1)
                            }
                            dents.append(dent)
                            edges.append((dent['url'], depended_library_function['url']))
        return dents, edges

    def process_single_file(self, filepath: PathLike) -> List[Dict[str, Any]]:
        definitions = self.get_function_definitions(filepath)
        if definitions is None:
            return []
        _, _, functions = definitions
        # print("Functions: " + str(len(functions)))
        self.proj_name=filepath.split("/")[0]

        return [self.extract_function_data(func, '', '', '') for func in functions if len(func['function_tokens']) > 1]

    def extract_function_data(self, function: Dict[str, Any], nwo, path: str, sha: str):
        return {
            'nwo': self.proj_name,#nwo,
            'sha': sha,
            'path': path,
            'language': self.language,
            'identifier': function['identifier'],
            'parameters': function.get('parameters', ''),
            'argument_list': function.get('argument_list', ''),
            'return_statement': function.get('return_statement', ''),
            'docstring': function['docstring'].strip(),
            'docstring_summary': function['docstring_summary'].strip(),
            'docstring_tokens': tokenize_docstring(function['docstring_summary']),
            'function': function['function'].strip(),
            'function_tokens': function['function_tokens'],
            'url': 'https://github.com/{}/blob/{}/{}#L{}-L{}'.format(nwo, sha, path, function['start_point'][0] + 1,
                                                                     function['end_point'][0] + 1)
        }

    def get_context_and_function_calls(self, filepath: str) -> Optional[Tuple[str, str, List, List]]:
        nwo = '/'.join(filepath.split('/')[3:5])
        path = '/'.join(filepath.split('/')[5:])
        if any(fp in path.lower() for fp in self.language_parser.FILTER_PATHS):
            return None
        try:
            with open(filepath) as source_code:
                blob = source_code.read()
            tree = DataProcessor.PARSER.parse(blob.encode())
            return (nwo, path, self.language_parser.get_context(tree, blob), self.language_parser.get_calls(tree, blob))
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError, ValueError, OSError):
            return None

    def get_function_definitions(self, filepath: str) -> Optional[Tuple[str, str, List]]:
        nwo = '/'.join(filepath.split('/')[3:5])
        path = '/'.join(filepath.split('/')[5:])
        if any(fp in path.lower() for fp in self.language_parser.FILTER_PATHS):
            return None
        try:
            with open(filepath) as source_code:
                blob = source_code.read()
            tree = DataProcessor.PARSER.parse(blob.encode())
            print("Tree: " + str(tree))
            # print members of tree
            return (nwo, path, self.language_parser.get_definition(tree, blob))
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError, ValueError, OSError) as e:
            print(e)
            return None



language = "python"
DataProcessor.PARSER.set_language(
    Language(os.path.join(function_parser.__path__[0], "tree-sitter-languages.so"), language)
)
processor = DataProcessor(
    language=language, language_parser=LANGUAGE_METADATA[language]["language_parser"]
)

def wget(old_version, new_version):
    owner_old = old_version['owner']
    project_old = old_version['project']
    sha_old = old_version['commit_sha']
    file_path_old = old_version['file_path']
    owner_new = new_version['owner']
    project_new = new_version['project']
    sha_new = new_version['commit_sha']
    file_path_new = new_version['file_path']
    print(owner_old, project_old)

    github_link_old = f'https://raw.githubusercontent.com/{owner_old}/{project_old}/{sha_old}/{file_path_old}'
    github_link_new = f'https://raw.githubusercontent.com/{owner_new}/{project_new}/{sha_new}/{file_path_new}'

    # wget github_link_old and github_link_new
    subprocess.run(['wget', github_link_old, '-O', 'old.py'])
    subprocess.run(['wget', github_link_new, '-O', 'new.py'])

def clean():
    subprocess.run(['rm', 'old.py'])
    subprocess.run(['rm', 'new.py'])
    subprocess.run(['rm', 'python_with_dup_old.jsonl'])
    subprocess.run(['rm', 'python_with_dup_new.jsonl'])

def which_one_to_use(old, new, old_version, new_version):
    with open(old) as f:
        old_data = f.readlines()
        old_data = old_data[1:]
        old_data = [json.loads(d) for d in old_data]
    with open(new) as f:
        new_data = f.readlines()
        new_data = new_data[1:]
        new_data = [json.loads(d) for d in new_data]

    # old_data and new_data intersection based on "identifier" field so that we can compare the same functions
    old_data = sorted(old_data, key=lambda x: x['identifier'])
    new_data = sorted(new_data, key=lambda x: x['identifier'])

    # take the intersection of the two lists
    old_data = [x for x in old_data if x['identifier'] in [y['identifier'] for y in new_data]]
    new_data = [x for x in new_data if x['identifier'] in [y['identifier'] for y in old_data]]

    ctr = 0
    func_change = False
    docstring_change = False
    both_change = False
    function_old = "No function changed"
    for i in range(len(old_data)):
        func_change = False
        docstring_change = False
        both_change = False
        if old_data[i]!=new_data[i]:
            for k1, v1 in old_data[i].items():
                for k2, v2 in new_data[i].items():
                    if k1=="function" and k2=="function":
                        # we need to remove the docstring from the function
                        v1 = v1.replace(old_data[i]['docstring'], '')
                        v2 = v2.replace(new_data[i]['docstring'], '')
                        v1 = v1.replace('"""', '')
                        v2 = v2.replace('"""', '')
                    if k1==k2 and v1!=v2 and (k1=="function" or k1=="docstring"):
                        if k1=="function":
                            func_change = True
                        if k1=="docstring":
                            docstring_change = True
                    else:
                        continue
            if func_change and docstring_change:
                both_change = True
                print("Both function and docstring changed")
                function_old = old_data[i]['identifier']
                print(function_old)
                old_code = old_data[i]['function'].replace(old_data[i]['docstring'], '').replace('"""', '')
                new_code = new_data[i]['function'].replace(new_data[i]['docstring'], '').replace('"""', '')
                old_version['docstring'] = old_data[i]['docstring']
                new_version['docstring'] = new_data[i]['docstring']
                old_version['code'] = old_code
                new_version['code'] = new_code
                print(old_version['code'])
                break
        else:
            continue
    print(old_version)
    print("Function changed: ", function_old)
    return old_version, new_version, function_old


def assoc_fixer(filename):
    # Load dataset
    with open(filename) as f:
        data = f.readlines()
        data = [json.loads(d) for d in data]

    filename = filename.split('/')[-1]

    for i, d in enumerate(data):
        try:
            old_version = d['version_data'][0]
            new_version = d['version_data'][1]

            print(old_version)
            print("Processing: ", i)

            wget(old_version, new_version)
            py_files = ['old.py', 'new.py']
            definitions_old = []
            definitions_new = []

            # Process the old version
            for file_path in [py_files[0]]:
                print("processing:", file_path)
                defs = processor.process_single_file(file_path)
                for w in defs:
                    w['func_token_count'] = str(len(w['function_tokens']))
                    w['docstring_token_count'] = str(len(w['docstring_tokens']))
                    w['code_tokens'] = w['function_tokens']
                    definitions_old.append(w)

            with open('python_with_dup_old.jsonl', 'a') as fp:
                fp.write('\n'.join(json.dumps(i) for i in definitions_old) + '\n')

            # Process the new version
            for file_path in [py_files[1]]:
                print("processing:", file_path)
                defs = processor.process_single_file(file_path)
                for w in defs:
                    w['func_token_count'] = str(len(w['function_tokens']))
                    w['docstring_token_count'] = str(len(w['docstring_tokens']))
                    w['code_tokens'] = w['function_tokens']
                    definitions_new.append(w)

            with open('python_with_dup_new.jsonl', 'a') as fp:
                fp.write('\n'.join(json.dumps(i) for i in definitions_new) + '\n')

            updated_old_version, updated_new_version, func = which_one_to_use(
                'python_with_dup_old.jsonl', 'python_with_dup_new.jsonl', old_version, new_version
            )

            # Update dataset entry
            d['version_data'][0] = updated_old_version
            d['version_data'][1] = updated_new_version
            d['function'] = func

            if func != "No function changed":
                with open(f'fixed_{filename}', 'a') as f:
                    f.write(json.dumps(d) + '\n')

            clean()

        except Exception as e:
            print("Error:", e)
            clean()
            continue


if __name__ == '__main__':
    # load dataset
    with open('dataset/dataset.jsonl') as f:
        data = f.readlines()
        data = [json.loads(d) for d in data]

    i = 0
    for d in data:
        try:
            old_version = d['version_data'][0]
            new_version = d['version_data'][1]
            print(old_version)

            wget(old_version, new_version)
            py_files = ['old.py', 'new.py']
            definitions_old = []
            definitions_new = []
            for file_path in [py_files[0]]:
                print("processing: ")
                defs = processor.process_single_file(file_path)
                for w in defs:
                    definitions_old.append(w)

            for w in definitions_old:
                w['func_token_count'] = str(len(w['function_tokens']))
                w['docstring_token_count'] = str(len(w['docstring_tokens']))
                w['code_tokens'] = w['function_tokens']

            with open('python_with_dup_old.jsonl', 'a') as fp:
                fp.write('\n'.join(json.dumps(i) for i in definitions_old) +'\n')

            for file_path in [py_files[1]]:
                print("processing: ")
                defs = processor.process_single_file(file_path)
                for w in defs:
                    definitions_new.append(w)

            for w in definitions_new:
                w['func_token_count'] = str(len(w['function_tokens']))
                w['docstring_token_count'] = str(len(w['docstring_tokens']))
                w['code_tokens'] = w['function_tokens']

            with open('python_with_dup_new.jsonl', 'a') as fp:
                fp.write('\n'.join(json.dumps(i) for i in definitions_new) +'\n')

            updated_old_version, updated_new_version, func = which_one_to_use('python_with_dup_old.jsonl', 'python_with_dup_new.jsonl', old_version, new_version)
            # write new data to a file
            d['version_data'][0] = updated_old_version
            d['version_data'][1] = updated_new_version
            d['function'] = func

            if func != "No function changed":
                with open('dataset/fixed_dataset.jsonl', 'a') as f:
                    f.write(json.dumps(d) + '\n')

            clean()

        except:
            print("Error")
            clean()
            continue

        with open('dataset/fixed_dataset.jsonl') as f:
            data = f.readlines()
            data = [json.loads(d) for d in data]

