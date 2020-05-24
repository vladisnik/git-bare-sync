# Git bare sync

Small tool for the synchronization between two git repository.
But these repositories has type bare.

Can be used with configuration file, for non interactive use such as cron job.
And also as ad-hoc script with arguments from CLI.

> Written was for using with git server [Gitea](https://gitea.io).
It hasn't mirroring through ssh. Therefore tool has some things specific to that git server.
For example sub directory over root directory with repositories in configuration file.

## Dependencies

#### Requirements

- Python >= 3.4
- Git >= 1.7.0

Some python libs:
- [GitPython](https://github.com/gitpython-developers/GitPython)
- [PyYAML](https://github.com/yaml/pyyaml)

### Install

#### PIP way

1. Clone repository
```bash
git clone https://github.com/vladisnik/git-bare-sync.git
```
2. Install required libraries
```bash
pip install -r requirements.txt
```

#### OS package manager way

- **Ubuntu**

```bash
apt install python3-git python3-yaml
```

- **RedHat/Centos**

First install EPEL repository. [Instruction](https://fedoraproject.org/wiki/EPEL#Quickstart).

```bash
yum install GitPython PyYAML
```

## Usage

**First you need initialize git repository.**

```bash
git init --bare
```

Basic usage:

```bash
python git-bare-sync.py --local-repo $HOME/git-server/repository --remote-repo https://github.com/vladisnik/git-bare-sync.git
```

Remove deleted local branches which no longer exists in remote repository:

```bash
python git-bare-sync.py --local-repo $HOME/git-server/repository --remote-repo https://github.com/vladisnik/git-bare-sync.git --remove-branches
```

With configuration file:

> For more information about configuration see [section](#configuration) with this title.

```bash
python git-bare-sync.py -c config.yml
```

Use file where will writing status about fetching:

```bash
python git-bare-sync.py --local-repo $HOME/git-server/repository --remote-repo https://github.com/vladisnik/git-bare-sync.git --status-file /tmp/repo-sync.json
```

## Configuration

Script can read configuration file was written with YAML.
[Example](config-example.yml) is available in this project repo.

Specifies as argument for the script option `-c/--config` at startup.

Configuration file has following structure:
- `repo_root` — Local directory with repositories where stored git repositories subdirectories.
- `remote_server` — Main git server which will set as remote in repository
and where from will fetching updates.
- `remote_user` — User which will used for connect to git server through ssh.
- `metrics` — File where will write statuses about fetching.
- `remove_local_branches` - Flag in charge of removing local git branches which no longer exists in remote repository.
  It corresponds to git option `--prune`.
- `repos`
  - `subdirectory` — Directory which stored set of git repositories as list.
    - `git_repo` — Name of local git repository with value name of remote repository.


## License
This project uses the following license: [MIT](LICENSE.txt)
