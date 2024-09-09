class TeamDefinition:
    DEFAULT_ORG_NAME = "jenkinsci"

    def __init__(self, team_name, developers, org_name=None):
        self.org_name = org_name if org_name is not None else self.DEFAULT_ORG_NAME
        self.team_name = team_name
        self.developers = developers if developers is not None else []

    def get_org_name(self):
        return self.org_name

    def get_team_name(self):
        return self.team_name

    def get_developers(self):
        return self.developers

    def set_developers(self, developers):
        self.developers = developers


class RepoYamlDefinition(TeamDefinition):
    def __init__(self, team_name, developers, org_name, repo_name,
                 additional_teams):
        super().__init__(team_name, developers, org_name)
        self.repo_name = repo_name
        self.additional_teams = additional_teams

    def get_additional_teams(self):
        return self.additional_teams

    def set_additional_teams(self, additional_teams):
        self.additional_teams = additional_teams


class SpecialYamlDefinition(TeamDefinition):
    def __init__(self, team_name, developers, org_name=None):
        super().__init__(team_name, developers, org_name)


class AdditionalTeamDefinition:
    def __init__(self, team_name, role):
        self.team_name = team_name
        self.role = role

    def get_name(self):
        return self.team_name

    def set_name(self, team_name):
        self.team_name = team_name

    def get_role(self):
        return self.role

    def set_role(self, role):
        self.role = role


class DeveloperInfo:
    def __init__(self, ldap, github):
        self.ldap = ldap
        self.github = github

    def get_ldap_username(self):
        return self.ldap

    def set_ldap_username(self, ldap):
        self.ldap = ldap

    def get_github_username(self):
        return self.github

    def set_github_username(self, github):
        self.github = github

from enum import Enum

class Role(Enum):
    Read = 'Read'
    Triage = 'Triage'
    Write = 'Write'
    Maintain = 'Maintain'
    Admin = 'Admin'


class Permissions:
    def __init__(self, triage=False, push=False, pull=False, maintain=False,
                 admin=False):
        self.triage = triage
        self.push = push
        self.pull = pull
        self.maintain = maintain
        self.admin = admin


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
