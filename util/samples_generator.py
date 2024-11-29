import json
import random

# Specify the input and output file paths
input_file_path = 'dataset/test.jsonl'
output_file_path = 'dataset/test_sampled.jsonl'

# Read the JSONL file
with open(input_file_path, 'r') as f:
    data = [json.loads(line) for line in f]

# Sample 100 entries randomly
sampled_data = random.sample(data, 100)

# Write the sampled data to a new JSONL file
with open(output_file_path, 'w') as f:
    for entry in sampled_data:
        f.write(json.dumps(entry) + '\n')

print(f"Sampled 100 entries and saved to {output_file_path}")
