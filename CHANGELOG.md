# Changelog

[简体中文](CHANGELOG.zh-CN.md)

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
- Added a Chinese version of the contributing guide, security policy, and changelog.
- Separated the draft native environment convention from the existing compatibility core, with bilingual specifications and complete Go/Rust/Bash implementation plans. These ports and native integrations are not implemented yet.
- Defined a draft single-variable context interface and documented optional dotenv input separately from the current TOML format; dotenv loading is not implemented yet.

PowerShell and VS Code identity integration are deferred experiments. No release tag or package registry publication is provided yet.
