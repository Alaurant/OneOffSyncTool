from unittest import TestCase

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from ruamel.yaml import YAML
from backfill_to_yaml import YamlDataLoader, TeamMerger, YamlWriter, SyncMain
from yaml_definitions import RepoYamlDefinition, SpecialYamlDefinition, \
    AdditionalTeamDefinition, DeveloperInfo


class TestYamlDataLoader(unittest.TestCase):

    @patch('ruamel.yaml.YAML.load')
    @patch('backfill_to_yaml.Path.exists', return_value=True)
    def test_permissions_team_name_extraction(self, mock_exists, mock_load_yaml):
        mock_load_yaml.return_value = {
            'github': 'org/repo',
            'developers': ['Alice', 'Bob']
        }
        result = YamlDataLoader.parse_repo_team_definition({
            'github': 'org/repo',
            'developers': ['Alice', 'Bob']
        })
        self.assertIsInstance(result, RepoYamlDefinition)
        self.assertEqual(result.team_name, None)
        self.assertEqual(result.repo_name, 'repo')
        self.assertEqual([dev.ldap for dev in result.developers], ['Alice', 'Bob'])

    @patch('ruamel.yaml.YAML.load')
    @patch('backfill_to_yaml.Path.exists', return_value=True)
    def test_teams_team_name_extraction(self, mock_exists, mock_load_yaml):
        mock_load_yaml.return_value = {
            'name': 'Dev Team',
            'developers': ['Alice', 'Bob']}
        result = YamlDataLoader.parse_teams_team_definition({
            'name': 'Dev Team',
            'developers': ['Alice', 'Bob']})
        self.assertIsInstance(result, SpecialYamlDefinition)
        self.assertEqual(result.team_name, 'Dev Team')
        self.assertEqual(result.org_name, 'jenkinsci')
        self.assertEqual([dev.ldap for dev in result.developers], ['Alice', 'Bob'])


class TestTeamMerger(unittest.TestCase):
    def test_update_developers_with_complete_list(self):
        github_client = MagicMock()
        team = MagicMock()

        team.get_members.return_value = [
            MagicMock(login='Bob'),
            MagicMock(login='Charlie')
        ]

        developers = [
            DeveloperInfo('Alice', None),
            DeveloperInfo('Bob', None)
        ]
        merger = TeamMerger(github_client)
        merger.update_developers(team, developers)

        expected_developers = [
            DeveloperInfo('Alice', None),
            DeveloperInfo('Bob', 'Bob'),
            DeveloperInfo(None, 'Charlie')
        ]

        self.assertEqual(len(developers), len(expected_developers))

        for expected_dev in expected_developers:
            found = any(
                dev.ldap == expected_dev.ldap and dev.github == expected_dev.github
                for dev in developers)
            self.assertTrue(found,
                            f"Developer {expected_dev.ldap} with GitHub {expected_dev.github} not found")


if __name__ == '__main__':
    unittest.main()
