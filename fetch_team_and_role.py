import os
import sys

from github import Github
import json
import logging

logging.basicConfig(level=logging.DEBUG, format='%(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)


class FetchAdditionalTeams:
    def __init__(self):
        global github_token
        self.github_client = Github(github_token)

    def get_teams_and_roles(self, org_name="jenkinsci"):
        org = self.github_client.get_organization(org_name)
        all_teams = org.get_teams()

        additional_teams = {}

        for team in all_teams:
            for repo in team.get_repos():
                repo_name = repo.name
                if repo_name not in additional_teams:
                    additional_teams[repo_name] = []

                permission = team.get_repo_permission(repo)
                role = permissions_to_role(permission)
                additional_teams[repo_name].append({
                    'team': team.name,
                    'role': role
                })
                logger.info(f" team of repo {repo_name}:"
                            f"team: {team.name}, role: {role}")

        with open('team_repo_roles.json', 'w') as f:
            json.dump(additional_teams, f, indent=4)


def permissions_to_role(permissions):
    if permissions.admin:
        return "Admin"
    elif permissions.maintain:
        return "Maintain"
    elif permissions.push:
        return "Write"
    elif permissions.triage:
        return "Triage"
    elif permissions.pull:
        return "Read"
    return None


if __name__ == "__main__":
    github_token = os.getenv("GITHUB_OAUTH")
    if not github_token:
        raise EnvironmentError(
            "GitHub OAuth token is not set in the environment variables.")

    fetcher = FetchAdditionalTeams()
    fetcher.get_teams_and_roles()
