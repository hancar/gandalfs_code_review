import requests
import base64
import re
import sys

# GitHub API details
REPO_OWNER = 'pytorch'
REPO_NAME = 'pytorch'
TOKEN = ''  # Your GitHub personal access token
HEADERS = {'Authorization': f'token {TOKEN}'}

# Function to fetch PR details (for base and head commit SHAs)
def fetch_pr_details(pr_number):
    """Fetch PR details including base and head commit SHAs."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        pr_data = response.json()
        return pr_data['base']['sha'], pr_data['head']['sha']
    else:
        print(f"Error fetching PR details: {response.status_code}")
        return None, None

# Function to fetch the list of files modified in a PR
def fetch_pr_files(pr_number):
    """Fetch files changed in a pull request."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/files"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()  # List of files changed in the PR
    else:
        print(f"Error fetching PR files: {response.status_code}")
        return []

# Function to fetch a file content from a specific commit SHA
def fetch_file_from_commit(filename, commit_sha):
    """Fetch the content of a file from a specific commit SHA."""
    file_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filename}?ref={commit_sha}"
    response = requests.get(file_url, headers=HEADERS)
    
    if response.status_code == 200:
        content = response.json().get('content')
        return base64.b64decode(content).decode('utf-8') if content else None
    elif response.status_code == 404:
        return None  # File might have been added or removed
    else:
        print(f"Error fetching file {filename} at {commit_sha}: {response.status_code}")
        return None

class FuncMetadata:
    def __init__(self, name, header_indent):
        self.name = name
        self.header_indent = header_indent
        self.inner_indent = None
        self.num_lines = 1

def inc_stack(stack, long_functions):
    stack[-1].num_lines += 1
    if stack[-1].num_lines > 20:
        long_functions.add(stack[-1].name)


# Analyze the file content for long functions and missing docstrings
def analyze_full_source_code(file_content):
    """Analyze the full source code to find long functions and missing docstrings."""
    long_functions = set()
    missing_docstrings = set()

    function_pattern = re.compile(r"^(?P<indent>\s*)(?:async \s*)?def\s+(?P<fname>\w+)\s*\(.*\):")  
    docstring_pattern = re.compile(r'^\s*"""[^"]')
    indent_pattern = re.compile(r'^\s*')

    lines = file_content.split("\n")

    stack = []
    is_following_header = False
    for line in lines:
        if line.strip() == "":
            continue
        if is_following_header:
            stack[-1].inner_indent = indent_pattern.match(line).group(0)
            if stack and not docstring_pattern.match(line):
                missing_docstrings.add(stack[-1].name)
            is_following_header = False
        if match := function_pattern.match(line):
            # if the function is the first or a nested one
            if not stack or line.startswith(stack[-1].inner_indent):
                stack.append(FuncMetadata(match.group("fname"), match.group("indent")))
            # else if it starts on the same level as the previous function
            elif line.startswith(stack[-1].header_indent):
                stack[-1] = FuncMetadata(match.group("fname"), match.group("indent"))
            is_following_header = True
        elif stack and line.startswith(stack[-1].inner_indent):
            inc_stack(stack, long_functions)
        elif stack:
            while stack and not line.startswith(stack[-1].inner_indent):
                stack.pop()
            if stack:
                inc_stack(stack, long_functions)

    return long_functions, missing_docstrings

# Compare two versions of a file and find new problems
def find_new_issues(base_issues, head_issues):
    """Find functions that were fine before, but became problematic after the PR."""
    base_long, base_missing = base_issues
    head_long, head_missing = head_issues

    new_long = head_long - base_long  # Functions that became too long
    new_missing = head_missing - base_missing  # Functions that lost their docstrings

    return new_long, new_missing

# Main function to analyze all files touched by a PR
def analyze_pr(pr_number):
    """Analyze all Python files modified in a PR and find new issues introduced."""
    base_sha, head_sha = fetch_pr_details(pr_number)
    if not base_sha or not head_sha:
        print("Failed to fetch PR details.")
        return

    files = fetch_pr_files(pr_number)
    new_long_funcs = []
    new_missing_docs = []

    for file in files:
        filename = file['filename']
        
        if not filename.endswith(".py"):
            continue  # Skip non-Python files
        
        #print(f"Analyzing Python file: {filename}")

        # Fetch file versions
        base_content = fetch_file_from_commit(filename, base_sha)
        head_content = fetch_file_from_commit(filename, head_sha)

        if base_content is None and head_content is None:
            print(f"Skipping {filename} (couldn't fetch contents).")
            continue

        # Analyze both versions
        base_issues = analyze_full_source_code(base_content) if base_content else (set(), set())
        head_issues = analyze_full_source_code(head_content) if head_content else (set(), set())

        # Find new issues
        new_long, new_missing = find_new_issues(base_issues, head_issues)

        new_long_funcs.extend(new_long)
        new_missing_docs.extend(new_missing)

    print("PR: ", pr_number)
    if new_long_funcs:
        print("Newly introduced long functions (over 20 lines):", new_long_funcs)
    if new_missing_docs:
        print("Newly missing docstrings:", new_missing_docs)

# Start analyzing a PR (replace PR_NUMBER with the PR number you want to analyze)
if __name__ == "__main__":
    analyze_pr(sys.argv[1])
