# Contributing

Use Python 3.11+ and installed Bash, Zsh and Git. Keep changes centered on profile → environment patch → process tree. Activation must remain local, reversible and independent of other shells.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e . build ruff
.venv/bin/ruff format --check src tests scripts
.venv/bin/ruff check src tests scripts
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m build
.venv/bin/python scripts/build_zipapp.py
```

Add regression tests for behavior changes. Security tests must exercise real shell evaluation and Git consumers, rather than only comparing emitted text. Use temporary HOME/config/repositories and fictional identities; never require live credentials for tests. macOS CI selects `/bin/bash` to exercise the system's older Bash.

Do not commit personal profiles, credentials, generated editor state, build outputs or private absolute paths. Keep stdout from shell-rendering commands strictly executable shell text, and diagnostics on stderr. Do not rewrite history or publish packages/tags as part of routine changes.

Windows/PowerShell and editor identity isolation need their own actual integration tests before support is advertised.
