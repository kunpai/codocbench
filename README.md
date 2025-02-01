# CoDocBench: A Dataset for Code-Documentation Alignment in Software Maintenance

This repository contains the CoDocBench dataset, a dataset for code-documentation alignment in software maintenance. The dataset is composed of 4,573 code-documentation pairs extracted from 200 open-source Python projects.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14251623.svg)](https://doi.org/10.5281/zenodo.14251623)

## Dataset Description

To use the CoDocBench dataset mentioned in the paper, you can find the dataset in the `dataset` folder. The folder contains the following files:

1. `codocbench.jsonl`: The main dataset file containing 4573 code-documentation pairs.
2. `test.jsonl`: The test dataset file containing 2273 code-documentation pairs from a random selection of 50% of the projects.
3. `train.jsonl`: The training dataset file containing 2300 code-documentation pairs from the remaining 50% of the projects.

The dataset is in JSONL format, and each line contains a JSON file with the following fields:

``` json
{
  "file": "string",                // File name or path.
  "function": "string",            // Fully qualified function/method name.
  "version_data": [                // List of version-specific data.
    {
      "version1": "string",         // Version identifier.
      "docstring_lines": {         // Docstring line range.
        "start_line": "integer",
        "end_line": "integer"
      },
      "code_lines": {              // Code line range.
        "start_line": "integer",
        "end_line": "integer"
      },
      "commit_date_time": "string",// Timestamp of the commit.
      "commit_sha": "string",      // Commit hash.
      "commit_message": "string",  // Commit message.
      "docstring": "string",       // Function docstring.
      "code": "string"             // Function code.
    },
    {
      "version2": "string",         // Version identifier.
      "docstring_lines": {         // Docstring line range.
        "start_line": "integer",
        "end_line": "integer"
      },
      "code_lines": {              // Code line range.
        "start_line": "integer",
        "end_line": "integer"
      },
      "commit_date_time": "string",// Timestamp of the commit.
      "commit_sha": "string",      // Commit hash.
      "commit_message": "string",  // Commit message.
      "docstring": "string",       // Function docstring.
      "code": "string"             // Function code.
    }
  ],
  "diff_code": "string",           // Unified diff for the function code.
  "diff_docstring": "string",      // Unified diff for the docstring.
  "whitespace_only_code": "boolean",  // Indicates if code diff is whitespace-only.
  "whitespace_only_docstring": "boolean", // Indicates if docstring diff is whitespace-only.
  "file_path": "string",           // Full file path.
  "filename": "string",            // File name.
  "project": "string",             // Project name.
  "owner": "string"                // Owner of the repository.
}

```

## Extracting Your Own Dataset

To extract your own dataset, follow these steps:

1. Clone the repository:

    ``` bash
    git clone https://github.com/kunpai/codocbench.git
    ```

2. Install the required dependencies:

    ``` bash
    ./setup.sh
    ```

    NOTE: This script sets up a virtual environment and installs the required dependencies. It defaults to Python version 3.13.

    If you have a different Python version:
    ``` bash
    ./setup.sh <PYTHON_VERSION>
    ```
    where `<PYTHON_VERSION>` is the version of Python you want to use.
    
    If you prefer to use your own environment, you can install the dependencies manually by running:

    ``` bash
    pip install -r requirements
    ```

    (Be sure to give the appropriate permissions to the script by running `chmod +x setup.sh`)

3. Run the virtual environment:

    ``` bash
    source codocbench-env/bin/activate
    ```

4. To extract your own dataset, you can use the `parse.py` script. The script has a few variants that you can use to customize the extraction process.

    1. *Variant 1: Extracting from a single project*

        To extract code-documentation pairs from a single project, you can use the following command:

        ``` bash
        python parse.py owner repo
        ```

        where `owner` is the owner of the repository and `repo` is the name of the repository.

    2. *Variant 2: Extracting from multiple projects*

        To extract code-documentation pairs from multiple projects, you can use the following command:

        ``` bash
        python parse.py
        ```

        This command will extract code-documentation pairs from all the projects listed in the `projects.csv` file. Ensure that the `projects.csv` file contains the owner and repository name of the projects you want to extract, separated by a comma.

        The `projects.csv` file in this repository contains the owner and repository name of the projects used in the CoDocBench dataset.

    3. *Variant 3: Extracting from a specific file*

        To extract code-documentation pairs from a specific file, you can use the following command:

        ``` bash
        python parse.py owner repo path
        ```

        where `owner` is the owner of the repository, `repo` is the name of the repository, and `path` is the path to the file.

        NOTE: The path should be relative to the root of the repository, and it should exist in the latest commit of the repository.

5. The extracted code-documentation pairs will be saved in the `differ_files/` folder in JSONL format. The file name will be in the format `codocbench.jsonl`.

The `parse.py` script also records solitary docstring changes and solitary code changes in the `differ_files/` folder. The file name will be in the format `combined_diff_mapping_docstring_.jsonl` and `combined_diff_mapping_code_.jsonl`, respectively. However, these are not post-processed and may contain false positives.

## Examples

Example scripts of using the dataset are provided in the `examples` folder. The scripts demonstrate how to load the dataset and use it for various tasks.

For most of the examples, you can run the script using the following command:

``` bash
python examples/<FILENAME>.py <PATH_TO_DATASET>
```

where `<FILENAME>` is the name of the script and `<PATH_TO_DATASET>` is the path to the dataset file.

In case of the 3-shot learning examples, you can run the script using the following command:

``` bash
python examples/<FILENAME>.py <PATH_TO_DATASET> <PATH_TO_TRAIN_DATASET>
```

where `<FILENAME>` is the name of the script, `<PATH_TO_DATASET>` is the path to the dataset file, and `<PATH_TO_TRAIN_DATASET>` is the path to the training dataset file.

All these files load `meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo` as the default model. You can change the model by running the script with the `--model` flag:

``` bash
python examples/<FILENAME>.py <PATH_TO_DATASET> --model=<MODEL_NAME>
```

where `<MODEL_NAME>` is the name of the model you want to use.