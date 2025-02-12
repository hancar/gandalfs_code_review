
import requests
from analyze_prs import HEADERS, REPO_NAME, REPO_OWNER

url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls"
response = requests.get(url, headers=HEADERS)
for pr in response.json():
    print(pr["number"])