# Project status

DevWho is a Python command-line project for per-shell developer identity. Its source is public; version 0.1.0 has no tagged release or package registry publication yet.

## What DevWho provides

DevWho compiles a version 1 TOML profile into environment settings for one shell or child process tree. Bash and Zsh initialization is explicit. Git identity, optional Git SSH settings, optional GitHub CLI context, and arbitrary literal environment variables are supported. `unsetdev` restores the baseline captured before the shell's first activation; `devwho exec` applies a profile only to the child process tree.

Activation and inspection do not rewrite Git or SSH configuration, move credentials, or edit shell startup files. GitHub account checks are explicit `doctor` operations. Review [the architecture](architecture.md) and [the configuration example](../examples/config.toml) for details.

## Platform and release status

The project requires Python 3.11 or newer. Linux/WSL Bash and Zsh have local integration coverage. GitHub Actions is configured for Ubuntu and macOS with Python 3.11 and 3.13; check the [workflow runs](https://github.com/lin594/devwho/actions/workflows/ci.yml) for hosted results. A configured workflow matrix is not itself evidence that every job has passed.

Windows PowerShell and editor identity integration are outside the supported v0.1 interface. No release, tag, or package publication is implied by the version in `pyproject.toml`.
