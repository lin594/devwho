# Contributing

[简体中文](CONTRIBUTING.zh-CN.md)

Thanks for taking an interest in DevWho. Small, focused contributions are welcome, including bug reports, documentation fixes, and code changes.

## Where to start

- **Found a problem?** Search the [existing issues](https://github.com/lin594/devwho/issues) first. If it has not been reported, open an issue with what you expected, what happened, and a short way to reproduce it. Use fictional identities and remove tokens, private paths, and other sensitive details.
- **Improving the docs?** Fix the relevant Markdown page or example and open a pull request. For documentation-only changes, check that links work and commands or configuration examples are accurate. You do not need to add tests just to add tests for prose.
- **Changing code?** Start with a focused issue or explain the problem in your pull request. Add or update tests for behavior changes, especially shell transitions, Git identity, and child-process execution.
- **Working on a core?** Python, Go, Rust, and Bash implementations share the [compatibility contract](spec/compatibility-core-v1.md) and [executable conformance suite](conformance/README.md). See the [implementation guide](implementations/README.md) for build requirements and evidence. Go/Rust have no Python/compiler runtime dependency; Bash requires jq and Perl. The optional [Go configuration frontend](docs/configuration-ui.md) is maintained separately from runtime core behavior.
- **Adding native application support?** Review the [environment convention draft](spec/environment-v1.md). Consumers read shared environment variables using their own language; they do not need a DevWho library or the core's profile parser.

## Develop the current Python core

The current Python implementation requires Python 3.11 or newer, Git 2.31 or newer, Bash, and Zsh for the full shell integration suite. Other implementations will document their own build requirements and run the same conformance cases. Create a virtual environment for Python development and install the project plus its development tools:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e . build ruff
```

## Run the relevant checks

For code or Python test changes, run the same checks used by CI:

```bash
.venv/bin/ruff format --check src tests scripts
.venv/bin/ruff check src tests scripts
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m build
.venv/bin/python scripts/build_zipapp.py
```

The shell tests use real Bash, Zsh, and Git with temporary HOME directories and repositories. They do not need your GitHub account or live credentials. If a change only edits prose, skip the test suite; check links and verify any changed commands or configuration examples instead.

The [CI workflow](https://github.com/lin594/devwho/actions/workflows/ci.yml) runs on Ubuntu and macOS with Python 3.11 and 3.13. macOS selects `/bin/bash` to exercise the system Bash. Check its current results rather than assuming a configured job has passed.

## Open a pull request

1. Keep the change focused and update the relevant docs when behavior changes.
   Update both English and Simplified Chinese counterparts when changing shared instructions or examples; keep commands and configuration keys identical.
2. Run the checks that apply to your change and note them in the pull request description. If a check could not run, say so.
3. Open a pull request against the repository. Explain the problem and the resulting behavior in a few sentences; link the related issue if there is one.

Do not include personal profiles, credentials, generated editor state, build outputs, or private absolute paths. Keep shell-rendering command output limited to executable shell code and send diagnostics to stderr. Do not rewrite history or publish packages or tags as part of routine contributions.

Windows/PowerShell and editor identity integration are outside the supported v0.1 interface. They need real integration tests before support can be advertised.
