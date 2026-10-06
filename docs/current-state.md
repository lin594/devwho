# Initial implementation audit

Audit date: 2026-10-06. This page records the starting point; current acceptance evidence belongs in [release readiness](../OPEN_SOURCE_READINESS.md).

The requested WSL checkout initially contained only an untracked implementation-guide Markdown file and an empty Git repository on `master`, with no commits. There was no existing package manager, executable, test suite, CI or release in that checkout. No applicable AGENTS.md was found in its parent directories.

A prior local implementation package existed outside this checkout. It was read directly during the audit: Python standard-library `dev_accounts.py`, `setup.py`, Bash/Zsh and PowerShell initialization scripts, an editor extension and unittest fixtures. It selected identity using a runtime Git include plus a per-account GH_CONFIG_DIR. There was no published-release evidence in the local checkout.

The old activation code did not mutate repository configuration. Its installer did write machine-specific identity files, copy gh login state, install editor integration, and modify shell/editor configuration with backup manifests. Its `unsetdev` selected a fixed default, rather than restoring an arbitrary shell baseline. It lacked the new generic-env profile model, process-scoped exec interface and real independent-shell integration coverage.

The useful pieces retained conceptually are the Python language/standard library approach, argparse CLI, Git runtime precedence, separate gh config directories, safe shell quoting and real disposable Git tests. Core transition logic was separated and extended to represent environment patches and shell-local baseline state. Machine-specific installation/editor logic and credentials were deliberately excluded from the public package.

Python 3.13, Bash 5.2, Zsh, Git, gh and Codex were available locally. Build tooling was installed only into a temporary Python virtual environment, using the existing interpreter. Availability here does not establish macOS/Windows support.

Public CLI activation, restoration, scoped exec and inspection do not write Git config, SSH config, credentials or shell rc files. `devwho init` emits functions; `devwho config init` is an explicit exclusive file creation. Optional handoff notices read the current repository. The separate, user-authorized local setup is machine configuration and is not part of the release source or an automatic installer behavior.
