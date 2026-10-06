# Open-source readiness

Assessment: 2026-10-06. Candidate: v0.1.0-rc.1. This checklist defines the RC1 release gates. Source hosting does not constitute a tagged or packaged release. The [CI workflow](https://github.com/lin594/devwho/actions/workflows/ci.yml) records hosted validation for each revision. The `cores` job builds and tests Ubuntu/macOS artifacts; inspect that run for its actual result before release decisions. The [candidate release](https://github.com/lin594/devwho/releases/tag/v0.1.0-rc.1) records its final commit, verified CI run, and tested artifact checksums.

## First candidate verification on FZ2

The v0.1.0-rc.1 candidate was built and exercised on FZ2 under Debian WSL, Linux x86-64, with real Bash/Zsh/Git:

- Python regression: 84 tests passed, with one expected Zsh-only case skipped in the Bash group.
- Python, Go, Rust and Bash: each passed 71 shared contract cases, including peer-state interchange; the same expected Bash-group skip applies.
- Go core/setup unit tests and vet, Rust locked unit tests/build, Bash's 20 implementation tests, and the native example's 9 selection cases plus four producer integrations passed.
- Ruff lint/format and Python compilation passed. Python wheel/sdist/zipapp and core archives built and their checksums verified.
- Go, Rust and Bash ran in a network-disabled Debian runtime container with no Python or language compilers. The Go setup frontend passed its read/replace fixture there.
- Local build tools were Python 3.13.5, Go 1.27.1, Cargo 1.90.0 and rustc 1.95.0. The locally tested Rust binary is source-build evidence; RC1 omits its Linux archive and records hosted runtime inventories for shipped packages.

The candidate version is 0.1.0-rc.1; Python metadata and asset names use the equivalent PEP 440 spelling 0.1.0rc1. Core archive names include version and tested target, including Bash, to avoid cross-runner collisions. The release assembly script verifies input checksums and rejects differing duplicates, then produces one checksum list and final-commit manifest.

Before publishing, the final revision must pass the complete hosted matrix; download and install the selected hosted artifacts on FZ2, inspect the final audit outcome, and attach the final commit/CI/checksum evidence to an explicitly marked pre-release. Local validation does not establish macOS support. The originating macOS CI run must supply that evidence.

[简体中文候选验收](zh-CN/release-readiness.md)
## Product and architecture

Per-shell developer identity through environment variables. Independent Python, Go, Rust, and Bash cores compile TOML profiles (or explicit dotenv input) to a set/unset environment patch consumed by one shell or child process tree. No global active-profile file exists. Python requires Python 3.11+; Go/Rust executables have no Python/compiler runtime requirement; Bash requires Bash 3.2+, jq 1.6+, and Perl 5.18+.

Generic env is first-class and literal. Git name/email, basic signing configuration, Git SSH key selection, and GitHub CLI directory/host selection share the compiler. Bash/Zsh rendering keeps restoration state non-exported and preflights variable attributes before applying any assignments. Git replay authors retain native semantics through runtime config rather than persistent author environment variables.

## Python regression evidence

The following local evidence summarizes the Python regression suite. For Go, Rust and Bash implementation-specific results and gaps, see each [implementation README](../implementations/README.md); the [common runner](../conformance/README.md) results should be checked per target and revision.

- The unified Python unittest suite passes locally. One Zsh-only string-attribute test is intentionally skipped under Bash, not because a supported shell is missing. Run the commands in [CONTRIBUTING.md](../CONTRIBUTING.md) for the current count and results.
- Real independent Bash/Zsh processes remain alive while the other profile changes.
- Missing, empty and nonempty baselines restore; different key sets, idempotence and child inheritance are covered.
- Actual Git commits override stale local names; nonempty cherry-pick and rebase preserve original authors and select the current committer.
- Actual Git SSH invocation is observed through a local mock executable, including a quoted key path with spaces/Unicode/command-like characters; no remote SSH authentication is claimed.
- Relative SSH/GitHub semantic paths are rejected. Home-relative paths resolve against the destination profile's effective HOME, including restoration of variables dropped during a switch.
- Actual Git identities and runtime configuration are diagnosed. GitHub login match/mismatch, wrong host, API failure and offline results use deterministic mock gh fixtures.
- Injection characters are round-tripped in real Bash/Zsh without creating marker files; readonly, integer/nameref and Zsh transformation attributes fail before partial changes.
- Repository/global Git config bytes remain unchanged. Existing proxies and appended third-party runtime pairs survive switching.
- Relocated zipapps, including an executable renamed without .pyz, support actual shell activation/restoration.
- Ruff lint and format checks passed. Wheel, sdist and zipapp build/install checks are performed locally; final artifact checksums accompany the build.

## Supported scope

Python local verification covers Linux/WSL, Python 3.13, Bash 5.2, and installed Zsh/Git. Implementation-specific READMEs record other local targets and limitations. Bash integration avoids Bash 4-only constructs. CI includes Ubuntu/macOS and Python 3.11/3.13, selecting `/bin/bash` on macOS to test its system Bash. Refer to actual workflow runs for hosted platform evidence.

Windows PowerShell and VS Code identity binding are deferred experimental work and are outside this package's supported interface.

## Security and credentials

Config initialization is explicit, exclusive and mode 0600. Activation/exec/inspection do not modify Git, SSH, credentials or startup files. The optional handoff warning only reads the current repository. Custom env values and raw subprocess errors are not displayed by inspection/doctor.

Profiles are trusted local input; DevWho is not a security boundary between OS-account users, a secret manager or a command sandbox. Git transport authentication and gh login remain distinct from commit identity. No credential contents are copied into source or automatically moved between gh config directories.

Source/examples use fictional identities. Local design notes, profiles and backups are excluded from tracked source and packages. A working-tree/package/history scan is part of the source-publication review. Findings must be resolved before publishing affected content.

## Alternatives

[Comparison](alternatives.md) uses current primary documentation for Git includeIf, git-profile, git-persona, gitch, DevSwitch, gh, direnv and git-context. Environment management substantially overlaps with direnv; DevWho's contribution is the explicit profile/restore/exec/doctor developer interface. No verified evidence in that bounded review establishes a mature identical contract. Some latest-release endpoints could not be retrieved, and no maintenance claims are invented.

## Limits and release decisions

- Verify the target revision's hosted Ubuntu/macOS matrix before tagging a release. Local Linux evidence cannot substitute for hosted platform results.
- Live two-account GitHub/SSH/GCM authorization and pushing to a test repository require authenticated account setup and a separate operator check. Mock consumer routing is not proof of remote account ownership.
- Runtime prefix/managed-block changes during activation make restoration fail conservatively; tail appendages are supported.
- Inherited shells restore their inherited baseline; they do not know a parent's earlier baseline.
- No directory auto-switching, daemon, GUI, remote identity guard, previous-profile stack or secret-provider integration is included.
- The project uses MIT licensing. Private vulnerability reports use the entry point in [SECURITY.md](../SECURITY.md).
- The first release is explicitly marked as a pre-release. Package registry publication is deferred.

The Python, Go, Rust, and Bash shell/process models have recorded local acceptance coverage; each implementation README identifies its own limits. Confirm hosted CI and transport authentication separately before relying on an additional platform or live account setup. The optional native Go setup frontend has Linux x86-64 local evidence; Windows writes are unsupported. A native reference consumer example exists, but it does not establish third-party adoption.

## RC1 asset plan

The [explicit eight-asset plan](../release-plan.json) selects Linux x86-64 Go/Bash, macOS ARM64 Go/Rust/Bash, and one canonical Ubuntu/Python3.11 wheel/sdist/zipapp set. Rust Linux remains tested but is omitted from downloads because of glibc 2.39. macOS core/setup minimum deployment versions are recorded in RUNTIME.txt separately from the hosted test OS. The [manual procedure](releasing.md) rejects incomplete/unexpected assets and preserves source checksums and provenance.
