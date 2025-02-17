import requests

GITHUB_TOKEN = ""
REPO_OWNER = "hancar"
REPO_NAME = "python-mini-projects"
PR_NUMBER = 1  # Example: 42


HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_latest_commit_id():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{PR_NUMBER}/commits"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        commits = response.json()
        return commits[-1]["sha"]  # Get the latest commit SHA
    else:
        print(f"❌ Failed to fetch commits: {response.status_code}, {response.text}")
        return None

def post_comment_on_pr(file_path, position, message):
    commit_id = get_latest_commit_id()
    if not commit_id:
        return
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{PR_NUMBER}/comments"
    
    payload = {
        "body": message,
        "commit_id": commit_id,
        "path": file_path,
        "side": "RIGHT",
        "position": position  # User-defined position in the diff
    }
    
    response = requests.post(url, json=payload, headers=HEADERS)
    
    if response.status_code == 201:
        print(f"✅ Comment posted on {file_path} at position {position}")
    else:
        print(f"❌ Failed to post comment: {response.status_code}, {response.text}")

# Example usage:
post_comment_on_pr("projects/chatbot/bot.py", 15, "Gandalf says: This function is too long! Consider refactoring.")
