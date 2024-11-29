import csv
import os
import sys

def find_done_projects():
    # open projects.csv
    projects = []
    with open('projects.csv', 'r') as f:
        reader = csv.reader(f)
        # skip header
        next(reader)
        for row in reader:
            projects.append(row)
    projects_done = []
    # list all the directories in the current directory
    for directory in os.listdir('.'):
        # check if the directory is a directory
        if os.path.isdir(directory):
            try:
                print('Checking {}'.format(directory))
                # check if any organization + repo in projects.csv is in the directory
                for project in projects:
                    if project[0] in directory and project[1] in directory:
                        projects_done.append(project)
                        break
            except Exception as e:
                print(e)
                continue

    # remove duplicates
    projects_done = list(set(tuple(project) for project in projects_done))

    # write to projects_done.csv
    with open('projects_done.csv', 'w') as f:
        writer = csv.writer(f)
        # write header
        writer.writerow(['organization', 'repo'])
        for project in projects_done:
            writer.writerow(project)

def main():
    # add command line argument for number of projects to extract
    if len(sys.argv) != 2:
        print('Usage: python project_extractor.py <number_of_projects>')
        sys.exit(1)

    num_projects = int(sys.argv[1])

    # find projects that have already been done
    # find_done_projects()
    projects_done = []
    projects_todo = []
    with open('projects_done.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            projects_done.append(row)

    with open('projects.csv', 'r') as f:
        # take first 1000 projects
        reader = csv.reader(f)
        for row in reader:
            projects_todo.append(row)

    # take only first 1000 projects of projects_todo
    projects_todo = projects_todo[:1001]

    # remove projects that have already been done
    projects_todo = [project for project in projects_todo if project not in projects_done]

    # extract the first num_projects projects
    projects_todo = projects_todo[:num_projects]

    # write to projects_todo.csv
    with open('projects_todo.csv', 'w') as f:
        writer = csv.writer(f)
        # write header
        writer.writerow(['organization', 'repo'])
        for project in projects_todo:
            writer.writerow(project)

if __name__ == '__main__':
    main()