import re
from github import GithubException
from ruamel.yaml import YAML, scalarstring
from pathlib import Path
import sys
import logging

from yaml_definitions import AdditionalTeamDefinition, DeveloperInfo, \
    RepoYamlDefinition, SpecialYamlDefinition, permissions_to_role

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
                merger.sync_repository_team(team)
                writer.write_repo_team_to_yaml(team, yaml_file_path)
            elif isinstance(team, SpecialYamlDefinition):
                merger.sync_special_team(team)
                writer.write_special_team_to_yaml(team, yaml_file_path)


class YamlDataLoader:
    PERMISSIONS_PATH = Path('permissions').resolve()
    TEAMS_PATH = Path('teams').resolve()

    def __init__(self, file_path):
        self.resolved_path = self.resolve_file_path(file_path)
        self.load_yaml_configuration(self.resolved_path)

    @staticmethod
    def load_team(file_path):
        resolved_path = YamlDataLoader.resolve_file_path(file_path)
        team_config = YamlDataLoader.load_yaml_configuration(resolved_path)

        if file_path.startswith("permissions/"):
            return YamlDataLoader.parse_repo_team_definition(team_config)
        elif file_path.startswith("teams/"):
            return YamlDataLoader.parse_teams_team_definition(team_config)
        else:
            raise ValueError("Unsupported file path: " + file_path)

    @staticmethod
    def resolve_file_path(file_path):
        base_path = YamlDataLoader.PERMISSIONS_PATH if file_path.startswith(
            "permissions/") else YamlDataLoader.TEAMS_PATH
        resolved_path = base_path.joinpath(file_path.split("/", 1)[1]).resolve()

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
        print(team_path)
        developers = YamlDataLoader.extract_developers(team_config)
        if not team_path:
            logger.error("The 'github' field is missing or invalid")
            return None

        repo_path = team_path.split('/')
        if len(repo_path) < 2:
            logger.error(f"Invalid GitHub path: {team_config['github']}")
            return None
        else:
            org_name = repo_path[0]
            repo_name = repo_path[1]
        print(org_name,repo_name)

        return RepoYamlDefinition(None, developers, org_name, repo_name, set())

    @staticmethod
    def parse_teams_team_definition(team_config):
        team_name = team_config.get("name", "")
        developers = YamlDataLoader.extract_developers(team_config)

        if not team_name:
            if developers:
                raise ValueError("No valid team name found.")
            else:
                logger.error("No valid team name provided.")
                return None
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
        elif not team_config["developers"]:
                return developers
        else:
            logger.error("Developer data is missing or incorrect")
            raise ValueError("Expected a list of developer usernames.")

        return developers


class TeamMerger:
    def __init__(self, github_client):
        self.github_client = github_client

    def update_developers(self, team, developers):
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

    def sync_repository_team(self, repo_team):
        logger.info(f"Merging repo team: {repo_team.team_name}")
        repo_name = repo_team.repo_name
        team_name = repo_name + " Developers"
        org_name = repo_team.org_name
        developers = repo_team.developers
        additional_teams = repo_team.additional_teams

        try:
            org = self.github_client.get_organization(org_name)
            repo = org.get_repo(repo_name)
            all_teams = repo.get_teams()
            matching_team = next((team for team in all_teams if team.name == team_name), None)
            self.update_developers(matching_team, developers)

            if matching_team:
                self.update_developers(matching_team, developers)
                repo_team.team_name = team_name
            else:
                # No matching team found
                if repo_team.developers:
                    logger.info(
                        f"Need a new team for the repository: {repo_name}")

            # update additional teams
            additional_teams_details = [team for team in all_teams if
                                        team.name.lower() != repo_team.team_name]
            for additional_team in additional_teams_details:
                team_name = additional_team.name
                permission = additional_team.get_repo_permission(repo)
                role = permissions_to_role(permission)
                logger.info(f"Additional team: {team_name}, role: {role}")
                additional_teams.add(AdditionalTeamDefinition(team_name, role))

        except GithubException as e:
            logger.error(f"Failed to access GitHub API: {e}")
            raise

    def sync_special_team(self, special_team):
        logger.info(f"Merging special team: {special_team.team_name}")
        team_name = special_team.team_name
        org_name = special_team.org_name
        developers = special_team.developers

        try:
            org = self.github_client.get_organization(org_name)
            team = org.get_team_by_slug(to_slug(team_name))
            self.update_developers(team, developers)

        except GithubException as e:
            logger.error(f"Failed to access GitHub API: {e}")
            raise


class YamlWriter:
    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=4, sequence=4, offset=2)
        self.yaml.default_flow_style = False

    def update_developers(self, team, data):
        developer_details = []
        for developer in team.developers:
            dev_map = {
                "ldap": scalarstring.DoubleQuotedScalarString(
                    developer.ldap if developer.ldap else ""),
                "github": scalarstring.DoubleQuotedScalarString(
                    developer.github if developer.github else "")
            }
            developer_details.append(dev_map)

        data['developers'] = developer_details

    def write_repo_team_to_yaml(self, repo_team, file_path):
        yaml = self.yaml

        with open(file_path, 'r') as f:
            data = yaml.load(f)

        # update developer usernames
        self.update_developers(repo_team, data)

        # add repository team
        data['repository_team'] = repo_team.team_name

        # add additional teams
        additional_teams_details = []
        if not repo_team.additional_teams:
            data['additional_github_teams'] = None
        else:
            for team in repo_team.additional_teams:
                team_map = {
                    "team": team.team_name,
                    "role": team.role
                }
                additional_teams_details.append(team_map)
            data['additional_github_teams'] = additional_teams_details

        # write to yaml
        with open(file_path, 'w') as f:
            yaml.dump(data, f)

    def write_special_team_to_yaml(self, special_team, file_path):
        yaml = self.yaml
        yaml.explicit_start = True

        with open(file_path, 'r') as f:
            data = yaml.load(f)

        self.update_developers(special_team, data)

        with open(file_path, 'w') as f:
            yaml.dump(data, f)


def to_slug(name):
    slug = name.lower()

    slug = re.sub(r'\s+', '-', slug)

    slug = re.sub(r'[^\w-]', '', slug)

    slug = re.sub(r'-+', '-', slug)

    slug = slug.strip('-')
    return slug
