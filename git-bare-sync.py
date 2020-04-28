#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from typing import TextIO
from os import path

from git import Repo, exc as GitException


def get_arguments() -> object:
    """
    Get and parse arguments which script was launched

    Returns:
        object: An ArgumentParser object which was parsed.
                Parsed arguments would accessible as object attributes.
    """

    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Script allow set remotes to a bare repository and "
                    "fetch an updates from remote git server.\n"
                    "Can work on the list from config and also with CLI arguments.",
    )
    parser.add_argument(
        'action', choices=['fetch', 'metric'], nargs='?', default='fetch',
        help="What need to process with script. "
             "Set remote and fetch from external git server (fetch), "
             "or just return content of file with metrics (metric). "
    )
    parser.add_argument(
        '-c', '--config', type=argparse.FileType('r'),
        help="Path to config where options defined. "
             "The following CLI options will be ignored."
    )
    parser.add_argument(
        '--local-repo', dest='local_repo',
        help="Path to local bare git repository. "
             "Used in executing script thru CLI."
    )
    parser.add_argument(
        '--remote-repo', dest='remote_repo',
        help="Full url to git repository on external server. "
             "Used in executing script thru CLI."
    )
    parser.add_argument(
        '--status-file', dest='status_file',
        help="Path to a file with statuses how the remote repos fetching went. "
             "Used in executing script thru CLI."
    )

    return parser.parse_args()


def read_config(config: TextIO) -> dict:
    """
    Read config and parse yaml in dict.

    Args:
        config (str): Path to config.

    Returns:
        dict: Yaml config which was parsed, as dict.
    """

    import yaml

    try:
        return yaml.load(config)
    except yaml.scanner.ScannerError as e:
        print(
            "Got error while parsing configuration file.\n{err}".format(err=e),
            file=sys.stderr
        )
        sys.exit(1)


def parse_config(config: dict) -> tuple:
    """
    Parse config into variables with test on a correctness.

    Args:
        config (dict): Readed to dict config.

    Returns:
        tuple: A set of variables from config
    """

    try:
        repo_root = config['repo_root']
        if not path.isdir(repo_root):
            raise FileNotFoundError(
                "Directory not found or permission denied "
                "from config field repo_root: {directory}".format(directory=repo_root)
            )

        remote_repo_base_url =            \
            config['remote_user'] + '@' + \
            config['remote_server'] + ':'

        # create dicts of local git repository with full paths
        # and remote urls
        repo_with_remotes = dict()
        for key, value in config['repos'].items():
            if value is not None:
                repo_sub_path = path.join(repo_root, key)
                if not path.isdir(repo_sub_path):
                    raise FileNotFoundError(
                        "Directory not found or permission denied "
                        "from config field repos -> {key}: "
                        "{directory}".format(key=key, directory=repo_sub_path)
                    )
                for repos in value:
                    for local, remote in repos.items():
                        repo_full_path = path.join(repo_sub_path, local)
                        if not path.isdir(repo_full_path):
                            raise FileNotFoundError(
                                "Directory not found or permission denied, "
                                "of git repository: {directory}".format(
                                    directory=repo_full_path
                                )
                            )
                        repo_with_remotes.update({repo_full_path: remote})

        status_file = config['metrics']
    except KeyError as e:
        print("Missing config field {field}".format(field=e), file=sys.stderr)
        sys.exit(1)
    except (FileNotFoundError, PermissionError) as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except TypeError as e:
        print(
            "Potential error in configuration file.\n"
            "Got exception while parsing it: {err}".format(err=e)
        )
        sys.exit(1)

    return (remote_repo_base_url, repo_with_remotes, status_file)


def parse_cli_arguments(args: object) -> tuple:
    """
    Parse arguments for executing script thru CLI
    Test their on a correctness

    Args:
        args (object): An ArgumentParser instance after executing parse_args function.
                       Contain script arguments values from CLI.

    Returns:
        tuple: A set of a variable from script arguments
    """

    try:
        local_repo = path.abspath(args.local_repo)
        remote_repo = args.remote_repo
        status_file = args.status_file

        if args.action == 'fetch':
            if local_repo is None or remote_repo is None:
                raise TypeError

            if not path.isdir(local_repo):
                print(
                    "Directory not found or permission denied, "
                    "of git repository: {directory}".format(directory=local_repo)
                )
                sys.exit(1)
        else:
            if status_file is None:
                print(
                    "Needs arguments --status-file "
                    "when script run without configuration file "
                    "and action 'metric'",
                    file=sys.stderr
                )
                sys.exit(1)
    except TypeError:
        print(
            "Needs arguments --local-repo and --remote-repo "
            "when script run without configuration file",
            file=sys.stderr
        )
        sys.exit(1)

    return (local_repo, remote_repo, status_file)


def create_git_remote(repo: object, url: str) -> bool:
    """
    Create remote to external git server in git repository for future fetching.
    Recreate remote "origin" if it exists.

    Args:
        repo (object): A GitPython Repo instance.
                       It is git repository over that will proceed works.
        url (str): Remote URL. Typically is a ssh link.

    Returns:
        bool: True if remote was added successfully. Otherwise False.
    """

    try:
        if len(repo.remotes) > 1:
            print(
                "Unexpected amount of repo {repo} remotes.\n"
                "You need to solve "
                "the conflict on your own.".format(repo=repo.working_dir),
                file=sys.stderr
            )
            return False

        # check that remote exists and not changed
        if len(repo.remotes) != 0:
            # get url value from remote.urls iterator
            # usually there one value anyway
            remote_url = next(repo.remotes[0].urls)
            if remote_url == url:
                return True

        repo.create_remote('origin', url=url)
        return True
    except GitException.GitCommandError as e:
        # recreate remote if it exists but urls doesn't concide
        if 'remote origin already exists' in e.stderr:
            repo.delete_remote('origin')
            return create_git_remote(repo, url)
        else:
            print(e.stderr, file=sys.stderr)
            return False


def fetch_remote_repository(remote: object) -> bool:
    """
    Fetch repository update from external git server.
    Used force update branches by specified refs with "+".
    Clean deleted branches. That the responsibility of parameter "prune".

    Args:
        remote (object): A GitPython Remote instance.
                         Got from instance of Repo remotes objects.

    Returns:
        bool: True if update fetching successfully. Otherwise, False.
    """

    try:
        remote.fetch(refspec='+refs/heads/*:refs/heads/*', prune=True)
        return True
    except GitException.GitCommandError as e:
        if 'Could not read from remote repository' in e.stderr:
            print(
                'Could not read from remote repository: '
                '{repo}'.format(repo=next(remote.urls)),
                file=sys.stderr
            )
        else:
            print(e.stderr, file=sys.stderr)
        return False


def write_status_file(metrics: dict, status_file: str):
    """
    Write collected metrics to status file as json.

    Args:
        metrics (dict): Collected metrics. Formatted as 'repo: status'.
        status_file (str): Path to a file with statuses.
    """

    import json
    import time

    try:
        full_status = {
            'updated_at': int(time.time()),
            'statuses': metrics
        }
        with open(status_file, 'w') as status_file_fh:
            status_file_fh.write(json.dumps(full_status, indent=2))
    except PermissionError as e:
        print(e, file=sys.stderr)


def read_status_file(status_file: str):
    """
    Read collected metrics from status file.

    Args:
        status_file (str): Path to a file with statuses.
    """

    try:
        with open(status_file, 'r') as status_file_fh:
            print(status_file_fh.read())
    except (PermissionError, FileNotFoundError) as e:
        print(e, file=sys.stderr)
        sys.exit(1)


def main():
    arguments = get_arguments()

    # assign config/CLI variables with their verification
    if arguments.config is not None:
        config = read_config(arguments.config)
        base_remote_url, repos, status_file = parse_config(config)
    else:
        local_repo, remote_repo, status_file = parse_cli_arguments(arguments)
        repos = {local_repo: remote_repo}

    if arguments.action == 'metric':
        read_status_file(status_file)
        sys.exit(0)

    fetch_states = dict()
    try:
        for repo_path, remote_url in repos.items():
            try:
                full_remote_url = base_remote_url + remote_url
            except UnboundLocalError:
                full_remote_url = remote_url
            repo = Repo(repo_path)
            create_res = create_git_remote(repo, full_remote_url)
            if create_res:
                remote = repo.remotes[0]
                fetch_res = fetch_remote_repository(remote)
            else:
                print(
                    "Failed while creatig remote for repository {repository}. "
                    "Skipping".format(repository=full_remote_url),
                    file=sys.stderr
                )
            fetch_states.update({
                path.basename(repo_path) + ':' + full_remote_url.split(':')[-1]:
                1 if (fetch_res and create_res) else 0
            })
    except GitException.InvalidGitRepositoryError as e:
        print("Invalid repository {repo}".format(repo=e), file=sys.stderr)

    if status_file is not None:
        write_status_file(fetch_states, status_file)


if __name__ == '__main__':
    main()
