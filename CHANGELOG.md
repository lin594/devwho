# Changelog

## 0.1.0 — Unreleased

- Environment-first TOML profiles with literal generic env and explicit unsets.
- Reversible Bash/Zsh `setdev` / `unsetdev` and process-scoped `devwho exec`.
- Git runtime identity, signing configuration, Git SSH command and GitHub CLI context.
- Explicit consumer diagnostics with mismatch and unverified results.
- Config bootstrap, optional startup default/shortcut and opt-in handoff notice.
- Isolated real-shell/Git regression tests, Linux/macOS CI, Python package and zipapp builds.
- Fixed SSH/GitHub semantic paths to stay independent of working-directory changes and resolve against the target profile's effective HOME.
- Effective Git identity in `current --verbose` and checksums covering all generated distributions.
- Compatible shell activation argument parsing on Python 3.11.

PowerShell and VS Code identity integration are deferred experiments. No release tag or package registry publication is provided yet.
