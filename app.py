import os
from flask import Flask, request
from github import Github, GithubIntegration

app = Flask(__name__)

app_id = 311895

# Read the bot certificate
with open(
        os.path.normpath(os.path.expanduser('hugovent-bot.2023-03-30.private-key.pem')),
        'r'
) as cert_file:
    app_key = cert_file.read()
    
# Create an GitHub integration instance
git_integration = GithubIntegration(
    app_id,
    app_key,
)

def issue_opened_event(repo, payload):
    issue = repo.get_issue(number=payload['issue']['number'])
    author = issue.user.login

    issue.add_to_labels("needs triage")
    
    response = f"Thanks for opening this issue, @{author}! " \
                f"The repository maintainers will look into it ASAP! :speech_balloon:"
    issue.create_comment(f"{response}")

"""Exercise 2. Say thanks when a pull request has been merged.
Make the bot post a comment to say thanks whenever a pull request has been merged.
For this case, you will want to subscribe to the pull_request event, specifically when the action to the event is closed.
For reference, the relevant GitHub API documentation for the pull request event is here:
https://docs.github.com/en/webhooks-and-events/webhooks/webhook-events-and-payloads?actionType=closed#pull_request
Note: A pull request can be closed without it getting merged. You will need to find out how to determine whether the pull
request was merged or closed."""

def pull_request_closed_event(repo, payload):
    pull_request = repo.get_pull(payload['pull_request']['number'])
    author = pull_request.user.login

    response = f"Thanks for your contribution, @{author}! " \
                f"Your pull request has been merged! :tada:"
    pull_request.create_issue_comment(f"{response}")


"""Exercise 3. Automatically delete a merged branch.
Automate even more tedious tasks whenever a pull request has been merged. Make the bot automatically delete a merged
branch. The branch name can be found in the pull request webhook event.
As for the previous exercise, you will want to subscribe to the pull_request event, specifically when the action to the event is
closed.
For reference, the relevant GitHub documentation for references is here: https://docs.github.com/en/rest/git/refs
Relevant PyGitHub documentation: https://pygithub.readthedocs.io/en/latest/github_objects/GitRef.html#github.GitRef.GitRef"""

def delete_merged_branch(repo, payload):
    pull_request = repo.get_pull(payload['pull_request']['number'])
    branch_name = pull_request.head.ref

    repo.get_git_ref(f"heads/{branch_name}").delete()

""" Exercise 4. Prevent merging of pull requests with "WIP" in the title.
Make the bot set a pull request status to pending if it finds one of the following terms in the pull request titles: “wip,” “work in
progress,” or “do not merge.” Developers might update the pull request title at any time, so consider it and update the pull
request status accordingly. For example, once the pull request is updated and the term removed, set back the pull request
status to success.
For this case, you will want to subscribe to the pull_request event, specifically when the action to the event is edited.
For reference, the relevant GitHub documentation for the commit statuses is here:
https://docs.github.com/en/rest/commits/statuses
Examples using PyGitHub: https://pygithub.readthedocs.io/en/latest/examples/Commit.html#create-commit-status-check
Note: Commit statuses can determine the overall status of a pull request. You must find out how to change the pull request
status based on a commit status. Read the documentation for reference."""

def pull_request_opened_event(repo, payload):
    pull_request = repo.get_pull(payload['pull_request']['number'])
    author = pull_request.user.login

    if "wip" in pull_request.title.lower() or "work in progress" in pull_request.title.lower() or "do not merge" in pull_request.title.lower():
        repo.get_commit(sha=pull_request.head.sha).create_status(state="pending", description="Work in progress", context="review")
        response = f"Your pull request is currently marked as a work in progress @{author}!"
        pull_request.create_issue_comment(f"{response}")
        
def pull_request_edited_event(repo, payload):
    pull_request = repo.get_pull(payload['pull_request']['number'])
    author = pull_request.user.login

    if "wip" in pull_request.title.lower() or "work in progress" in pull_request.title.lower() or "do not merge" in pull_request.title.lower():
        repo.get_commit(sha=pull_request.head.sha).create_status(state="pending", description="Work in progress", context="review")
        response = f"Your pull request is currently marked as a work in progress @{author}!"
        pull_request.create_issue_comment(f"{response}")
    else:
        repo.get_commit(sha=pull_request.head.sha).create_status(state="success", description="Ready for review", context="review")
        response = f"Your pull request is ready for review @{author}!"
        pull_request.create_issue_comment(f"{response}")

@app.route("/", methods=['POST'])
def bot():
    payload = request.json

    if not 'repository' in payload.keys():
        return "", 204

    owner = payload['repository']['owner']['login']
    repo_name = payload['repository']['name']

    git_connection = Github(
        login_or_token=git_integration.get_access_token(
            git_integration.get_installation(owner, repo_name).id
        ).token
    )
    repo = git_connection.get_repo(f"{owner}/{repo_name}")

    # Check if the event is a GitHub issue creation event
    if all(k in payload.keys() for k in ['action', 'issue']) and payload['action'] == 'opened':
        issue_opened_event(repo, payload)

    # Check if the event is a GitHub pull request closed event
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'closed':
        pull_request_closed_event(repo, payload)

    # Check if the event is a GitHub pull request closed event
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'closed':
        delete_merged_branch(repo, payload)

    #  Check if the event is a GitHub pull request opened event
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'opened':
        pull_request_opened_event(repo, payload)

    # Check if the event is a GitHub pull request edited event
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'edited':
        pull_request_edited_event(repo, payload)

    

    return "", 204

if __name__ == "__main__":
    app.run(debug=True, port=5000)