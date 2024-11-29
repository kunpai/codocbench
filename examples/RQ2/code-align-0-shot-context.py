import sys
import os
import json
import argparse
import requests
from typing import List, Dict, Any
from time import sleep
from dotenv import load_dotenv

load_dotenv()

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
TOGETHER_API_URL = "https://api.together.xyz/inference"

def load_data(file_path: str) -> List[Dict[str, Any]]:
    with open(file_path, 'r') as f:
        return [json.loads(line) for line in f]

def extract_versions(entry: Dict[str, Any]) -> Dict[str, str]:
    version_old = entry['version_data'][0]
    version_new = entry['version_data'][1]
    return {
        'old_code': version_old['code'],
        'old_docstring': version_old['docstring'],
        'new_code': version_new['code'],
        'new_docstring': version_new['docstring']
    }

def create_prompt(entries: List[Dict[str, Any]], target_index: int) -> str:
    prompt = f"A function-docstring pair has undergone changes. This function is from the project {entries[target_index]['owner']}/{entries[target_index]['project']}. The function is located in {entries[target_index]['file_path']}.\n\n Given the old code, the old commit message, the old docstring and the new docstring and the new commit message, your task is to generate the new code, based on the new docstring, taking into account how it differs from the old docstring and the old code:\n\n"

    target_version = extract_versions(entries[target_index])
    prompt += f"Old Docstring: {target_version['old_docstring']}\n"
    prompt += f"Old Commit Message: {entries[target_index]['version_data'][0]['commit_message']}\n"
    prompt += f"Old Code: {target_version['old_code']}\n"
    prompt += f"New Docstring: {target_version['new_docstring']}\n"
    prompt += f"New Commit Message: {entries[target_index]['version_data'][1]['commit_message']}\n\n"
    prompt += "[INST] Generate the code and return only the code [/INST]:"

    return prompt

def generate_code(prompt: str, model: str = "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo") -> str:
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "prompt": f"{prompt}",
        "max_tokens": 1000,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "repetition_penalty": 1,
        "stop": ["[/INST]", "</s>"]
    }

    for attempt in range(5):
        try:
            response = requests.post(TOGETHER_API_URL, headers=headers, json=data)
            response.raise_for_status()
            return response.json()['output']['choices'][0]['text'].strip()
        except (requests.RequestException, KeyError) as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 4:  # Only sleep if there are remaining attempts
                print("Retrying in 10 seconds...")
                sleep(10)
            else:
                print("Max retries reached. Exiting.")
                sys.exit(1)


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def main():
    parser = argparse.ArgumentParser(description="Generate docstrings using Together.AI model.")
    parser.add_argument("file_path", help="Path to the JSON file containing entries")
    parser.add_argument("--model", default="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", help="Together.AI model to use")
    args = parser.parse_args()

    entries = load_data(args.file_path)

    json_filename = "generated_new_code_summary.json"
    results = []

    # if generated_new_code_summary.json exists, calculate the starting index
    try:
        with open(json_filename, 'r') as jsonfile:
            results = json.load(jsonfile)
            start_index = len(results)
    except FileNotFoundError:
        start_index = 0

    for i in range(start_index, len(entries)):
        # Create two prompts: one for old code and one for new code
        prompt = create_prompt(entries, i)

        # Generate code for both
        generated_response = generate_code(prompt, args.model)
        sleep(2)

        # Extract reference code from both old and new
        new_reference = extract_versions(entries[i])['new_code']
        old_reference = extract_versions(entries[i])['old_code']

        # Calculate distances
        distances = {
            'generated_with_new': levenshtein_distance(generated_response, new_reference),
            'generated_with_old': levenshtein_distance(generated_response, old_reference)
        }
        avg_distance = sum(distances.values()) / len(distances)

        results.append({
            'entry': f"Entry {i+1}",
            'generated_new': generated_response,
            'new_reference': new_reference,
            'old_reference': old_reference,
            'avg_levenshtein_distance': avg_distance,
            'distances': distances
        })

        print(f"Entry {i+1} - Average Levenshtein Distance: {avg_distance}")
        print("="*50 + "\n")
        print(len(results))

        # WRITE current results to json file
        with open(json_filename, 'w') as jsonfile:
            json.dump(results, jsonfile, indent=4)

    print(f"Results have been written to {json_filename}")

if __name__ == "__main__":
    main()
