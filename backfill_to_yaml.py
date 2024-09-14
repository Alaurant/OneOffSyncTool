import json
import logging
import re
import sys
from pathlib import Path

from github import GithubException
from ruamel.yaml import YAML, scalarstring

from yaml_definitions import AdditionalTeamDefinition, DeveloperInfo, \
    RepoYamlDefinition, SpecialYamlDefinition

logging.basicConfig(level=logging.DEBUG, format='%(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)


class SyncMain:
    def __init__(self, github_client):
        self.github_client = github_client

    def run(self, args):
        if len(args) == 0:
            raise ValueError("No file path provided.")

        for yaml_file_path in args:
            logger.info(f"Processing team for: {yaml_file_path}")
            team = YamlDataLoader.load_team(yaml_file_path)
            merger = TeamMerger(self.github_client)
            writer = YamlWriter()

            if isinstance(team, RepoYamlDefinition):
                if team.repo_name:
                    merger.sync_repository_team(team)
                writer.write_repo_team_to_yaml(team, yaml_file_path)
            elif isinstance(team, SpecialYamlDefinition):
                if team.team_name:
                    merger.sync_special_team(team)
                writer.write_special_team_to_yaml(team, yaml_file_path)


class YamlDataLoader:
    PERMISSIONS_PATH = Path('submodules/RPU/permissions').resolve()
    TEAMS_PATH = Path('submodules/RPU/teams').resolve()

    def __init__(self, file_path):
        self.resolved_path = self.resolve_file_path(file_path)
        self.load_yaml_configuration(self.resolved_path)

    @staticmethod
    def load_team(file_path):
        resolved_path = YamlDataLoader.resolve_file_path(file_path)
        team_config = YamlDataLoader.load_yaml_configuration(resolved_path)

        if file_path.startswith("submodules/RPU/permissions/"):
            return YamlDataLoader.parse_repo_team_definition(team_config)
        elif file_path.startswith("submodules/RPU/teams/"):
            return YamlDataLoader.parse_teams_team_definition(team_config)
        else:
            raise ValueError("Unsupported file path: " + file_path)

    @staticmethod
    def resolve_file_path(file_path):
        base_path = YamlDataLoader.PERMISSIONS_PATH if file_path.startswith(
            "submodules/RPU/permissions/") else YamlDataLoader.TEAMS_PATH
        resolved_path = base_path.joinpath(file_path.split("/", 3)[3]).resolve()

        if not resolved_path.exists():
            raise FileNotFoundError(f"File does not exist: {resolved_path}")
        if not str(resolved_path).endswith('.yml'):
            raise ValueError("Invalid file type")
        if not resolved_path.is_relative_to(base_path):
            raise PermissionError(
                "Attempted path traversal out of allowed directory")

        return resolved_path

    @staticmethod
    def load_yaml_configuration(path):
        yaml = YAML(typ='safe')
        try:
            with open(path, 'r') as file:
                return yaml.load(file)
        except Exception as e:
            logger.error(f"Failed to load YAML configuration: {path}")
            raise RuntimeError(
                f"Failed to load YAML configuration: {path}") from e

    @staticmethod
    def parse_repo_team_definition(team_config):
        team_path = team_config.get("github", "")
        developers = YamlDataLoader.extract_developers(team_config)
        if not team_path:
            logger.info("The 'github' field is missing or invalid")
            return RepoYamlDefinition(None, developers, None, None, set())

        repo_path = team_path.split('/')
        if len(repo_path) < 2:
            logger.info(f"Invalid GitHub path: {team_config['github']}")
            return RepoYamlDefinition(None, developers, None, None, set())
        else:
            org_name = repo_path[0]
            repo_name = repo_path[1]

        return RepoYamlDefinition(None, developers, org_name, repo_name, set())

    @staticmethod
    def parse_teams_team_definition(team_config):
        team_name = team_config.get("name", "")
        developers = YamlDataLoader.extract_developers(team_config)

        if not team_name or not team_name.strip():
            logger.info("The 'name' field is missing or invalid")
            return SpecialYamlDefinition(None, developers)
        else:
            logger.info(f"Team name: {team_name}")
            return SpecialYamlDefinition(team_name, developers)

    @staticmethod
    def extract_developers(team_config):
        developers = []
        if "developers" in team_config and isinstance(team_config["developers"],
                                                      list):

            for dev in team_config["developers"]:
                if isinstance(dev, str) and dev.strip():
                    developers.append(DeveloperInfo(dev, None))
                    logger.info(f"Adding new Yaml developer to list: {dev}")
                elif not dev.strip():
                    continue
                else:
                    logger.error(f"Invalid developer entry: {dev}")
                    raise ValueError("Expected a list of developer usernames.")
        return developers


def merge_github_developers(team, developers):
    if team:
        members = team.get_members()
        for member in members:
            github_username = member.login
            found = False
            for developer in developers:
                if developer.ldap == github_username:
                    logger.info(
                        f"Merging GitHub username for: {github_username}")
                    developer.github = github_username
                    found = True
                    break

            if not found:
                developers.append(DeveloperInfo(None, github_username))
                logger.info(
                    f"Adding new GitHub developer to list: {github_username}")

    else:
        if developers:
            logger.error(f"Team not found: {team}")


class TeamMerger:
    def __init__(self, github_client):
        self.github_client = github_client

    def sync_repository_team(self, repo_team):
        repo_name = repo_team.repo_name
        repo_team_name = repo_name + " Developers"
        org_name = repo_team.org_name
        developers = repo_team.developers
        additional_teams = repo_team.additional_teams

        with open('team_repo_roles.json', 'r') as file:
            # format: {"repo_name": [{"team": "team_name", "role": "role"}]}
            team_repo_roles = json.load(file)

        try:
            org = self.github_client.get_organization(org_name)
            team_slug = to_slug(repo_team_name)

            if repo_name in team_repo_roles:
                for team_info in team_repo_roles[repo_name]:
                    team_name = team_info['team']
                    role = team_info['role']
                    if team_name == repo_team_name:
                        matching_team = org.get_team_by_slug(team_slug)
                        merge_github_developers(matching_team, developers)
                        repo_team.team_name = repo_team_name
                        logger.info(f"Merging repo team: {repo_team.team_name}")
                    else:
                        logger.info(
                            f"Additional team: {team_name}, role: {role}")
                        additional_teams.add(
                            AdditionalTeamDefinition(team_name, role))

        except GithubException as e:
            logger.error(f"Failed to access GitHub API: {e}")
            raise

    def sync_special_team(self, special_team):
        logger.info(f"Merging special team: {special_team.team_name}")
        team_name = special_team.team_name
        org_name = special_team.org_name
        developers = special_team.developers

        with open('all_teams.json', 'r') as file:
            all_teams = json.load(file)

        try:
            org = self.github_client.get_organization(org_name)

            if team_name in all_teams:
                team = org.get_team_by_slug(to_slug(team_name))
                merge_github_developers(team, developers)

        except GithubException as e:
            logger.error(f"Failed to access GitHub API: {e}")
            raise


def update_developer_entries(team, data):
    developer_details = []
    if team.developers:
        for developer in team.developers:
            dev_map = {}
            if developer.ldap:
                dev_map["ldap"] = scalarstring.DoubleQuotedScalarString(
                    developer.ldap)

            if developer.github:
                dev_map["github"] = scalarstring.DoubleQuotedScalarString(
                    developer.github)

            developer_details.append(dev_map)

        data['developers'] = developer_details


class YamlWriter:
    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=4, sequence=4, offset=2)
        self.yaml.default_flow_style = False

    def write_repo_team_to_yaml(self, repo_team, file_path):
        yaml = self.yaml
        yaml.explicit_start = True

        with open(file_path, 'r') as f:
            data = yaml.load(f)

        # update developer usernames
        update_developer_entries(repo_team, data)

        # add repository team
        team_name = repo_team.team_name
        if team_name:
            data['repository_team'] = scalarstring.DoubleQuotedScalarString(
                team_name)

        # add additional teams
        additional_teams_details = []
        if repo_team.additional_teams:
            for team in repo_team.additional_teams:
                team_map = {
                    "team": scalarstring.DoubleQuotedScalarString(
                        team.team_name),
                    "role": scalarstring.DoubleQuotedScalarString(team.role)
                }
                additional_teams_details.append(team_map)
            data['additional_github_teams'] = additional_teams_details

        # write to yaml
        with open(file_path, 'w') as f:
            yaml.dump(data, f)
        logger.info("written finished.")

    def write_special_team_to_yaml(self, special_team, file_path):
        yaml = self.yaml
        yaml.explicit_start = True

        with open(file_path, 'r') as f:
            data = yaml.load(f)

        update_developer_entries(special_team, data)

        with open(file_path, 'w') as f:
            yaml.dump(data, f)


def to_slug(name):
    with open('all_teams.json', 'r') as file:
        all_teams = json.load(file)

    if name in all_teams:
        return all_teams[name]
    else:
        slug = name.lower()
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'[^\w-]', '', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        return slug
