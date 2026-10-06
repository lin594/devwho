# Open-source readiness

Assessment: 2026-10-06. Version: 0.1.0, unreleased. **Linux/WSL core is locally validated; public release awaits hosted CI and the maintainer's publication decision.**

## Product and architecture

Per-shell developer identity through environment variables. TOML profiles compile to a set/unset EnvironmentPatch, consumed by one shell or child process tree. No global active-profile file exists. Python 3.11+, standard library only at runtime.

Generic env is first-class and literal. Git name/email, basic signing configuration, Git SSH key selection, and GitHub CLI directory/host selection share the compiler. Bash/Zsh rendering keeps restoration state non-exported and preflights variable attributes before applying any assignments. Git replay authors retain native semantics through runtime config rather than persistent author environment variables.

## Local acceptance evidence

- Unified unittest run: **71 tests, 70 passed, 1 skipped**. The skip is the Zsh-only string-attribute test under Bash, not a missing supported shell.
- Real independent Bash/Zsh processes remain alive while the other profile changes.
- Missing, empty and nonempty baselines restore; different key sets, idempotence and child inheritance are covered.
- Actual Git commits override stale local names; nonempty cherry-pick and rebase preserve original authors and select the current committer.
- Actual Git SSH invocation is observed through a local mock executable, including a quoted key path with spaces/Unicode/command-like characters; no remote SSH authentication is claimed.
- Actual Git identities and runtime configuration are diagnosed. GitHub login match/mismatch, wrong host, API failure and offline results use deterministic mock gh fixtures.
- Injection characters are round-tripped in real Bash/Zsh without creating marker files; readonly, integer/nameref and Zsh transformation attributes fail before partial changes.
- Repository/global Git config bytes remain unchanged. Existing proxies and appended third-party runtime pairs survive switching.
- Relocated zipapps, including an executable renamed without .pyz, support actual shell activation/restoration.
- Ruff lint and format checks passed. Wheel, sdist and zipapp build/install checks are performed locally; final artifact checksums accompany the build.

## Supported scope

Locally verified: Linux/WSL, Python 3.13, Bash 5.2 and installed Zsh/Git. Bash integration avoids Bash 4-only constructs. CI includes Ubuntu/macOS and Python 3.11/3.13, selecting /bin/bash on macOS to test its system Bash. Hosted CI has not yet run in this local repository.

Windows PowerShell and VS Code identity binding are deferred experimental work. Their earlier private prototype is retained separately and is not advertised as tested support in this public package.

## Security and credentials

Config initialization is explicit, exclusive and mode 0600. Activation/exec/inspection do not modify Git, SSH, credentials or startup files. The optional handoff warning only reads the current repository. Custom env values and raw subprocess errors are not displayed by inspection/doctor.

Profiles are trusted local input; DevWho is not a security boundary between OS-account users, a secret manager or a command sandbox. Git transport authentication and gh login remain distinct from commit identity. No credential contents are copied into source or automatically moved between gh config directories.

Source/examples use fictional identities. The supplied discussion guide is ignored, and real local profiles/build backups stay outside the repository. A working-tree/package/history scan precedes delivery; findings, if any, are release blockers rather than silently removed secrets.

## Alternatives

[Comparison](docs/alternatives.md) uses current primary documentation for Git includeIf, git-profile, git-persona, gitch, DevSwitch, gh, direnv and git-context. Environment management substantially overlaps with direnv; DevWho's contribution is the explicit profile/restore/exec/doctor developer interface. No verified evidence in that bounded review establishes a mature identical contract. Some latest-release endpoints could not be retrieved, and no maintenance claims are invented.

## Limits and release decisions

- Hosted Ubuntu/macOS CI and macOS system Bash acceptance remain pending. Local Linux evidence cannot substitute for those results.
- Live two-account GitHub/SSH/GCM authorization and pushing to a test repository require authenticated account setup and a separate operator check. Mock consumer routing is not proof of remote account ownership.
- Runtime prefix/managed-block changes during activation make restoration fail conservatively; tail appendages are supported.
- Inherited shells restore their inherited baseline; they do not know a parent's earlier baseline.
- No directory auto-switching, daemon, GUI, remote identity guard, previous-profile stack or secret-provider integration is included.
- Review MIT ownership and configure private security reporting before public publication. The license does not invent a maintainer's real name or email.
- No repository visibility change, remote push, release tag, hosted release or package publication has been performed.

The shell/process model meets local v0.1 acceptance. The project is a locally tested release candidate, **not an already published release or a claim that pending platform/authentication checks have passed**.
