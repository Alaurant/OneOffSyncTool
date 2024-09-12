import logging
import os
import sys

from github import Github

from backfill_to_yaml import SyncMain


logging.basicConfig(level=logging.DEBUG, format='%(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)


def main():
    directories = ["teams", "submodules/RPU/permissions"]

    github_token = os.getenv("GITHUB_OAUTH")
    if not github_token:
        raise EnvironmentError(
            "GitHub OAuth token is not set in the environment variables.")

    github_client = Github(github_token)

    sync_main = SyncMain(github_client)

    for directory in directories:
        if not os.path.exists(directory):
            logger.info(f"Directory not found: {directory}")
            continue

        files = [f for f in os.listdir(directory) if f.endswith('.yml')]
        if not files:
            logger.info(f"No YAML files found in {directory}.")
            continue

        args = [os.path.join(directory, f) for f in files]
        sync_main.run(args)


if __name__ == "__main__":
    main()
