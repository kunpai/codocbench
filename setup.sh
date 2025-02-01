#!/bin/bash

# Default to Python 3.13 if no argument is provided
PYTHON_VERSION=${1:-3.13}

# Create virtual environment
python$PYTHON_VERSION -m venv codocbench-env
source codocbench-env/bin/activate

# Install dependencies
pip install -r requirements

# Build grammars
build_grammars

# Copy the compiled language file to the appropriate site-packages directory
cp language/tree-sitter-languages.so codocbench-env/lib/python$PYTHON_VERSION/site-packages/function_parser/tree_sitter_languages.so
