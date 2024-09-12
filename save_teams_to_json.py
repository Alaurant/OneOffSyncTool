import os

from github import Github
import json


class SaveTeamsToJson:
    def __init__(self):
        global github_token
        self.github_client = Github(github_token)

    def save_teams_to_json(self):
        org_name = "jenkinsci"
        org = self.github_client.get_organization(org_name)
        teams = org.get_teams()
        teams_data = {team.name: team.slug for team in teams}

        with open("all_teams.json", 'w') as f:
            json.dump(teams_data, f, indent=4)


if __name__ == "__main__":
    github_token = os.getenv("GITHUB_OAUTH")
    if not github_token:
        raise EnvironmentError(
            "GitHub OAuth token is not set in the environment variables.")

    saver = SaveTeamsToJson()
    saver.save_teams_to_json()
