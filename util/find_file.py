import os

def find_files(directory, prefix):
    """
    Recursively search for files that begin with the given prefix in the specified directory.
    """
    matching_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.startswith(prefix):
                matching_files.append(os.path.join(root, file))
    return matching_files

# Example usage:
directory_to_search = "."
prefix_to_match = "differ_"
matching_files = find_files(directory_to_search, prefix_to_match)
print("Matching files:")
# create a directory to store the files
os.mkdir('differ_files')
for file in matching_files:
    print(file)
    print(file.replace('differ_','').replace('txt','json'))
    # copy the files to the directory
    os.system('cp '+file+' differ_files/')
    # also copy the json file in that directory
    os.system('cp ' +file.replace('differ_','').replace('txt','json')+' differ_files/')
