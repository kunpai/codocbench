#!/bin/bash
python3 -m venv codocbench-env
source codocbench-env/bin/activate
pip3 install -r requirements
build_grammars
cp language/tree-sitter-languages.so codocbench-env/lib/python3.10/site-packages/function_parser/tree_sitter_languages.so
