# Go compatibility core

[English](README.md) | [简体中文](README.zh-CN.md) · [Common prebuilt install/update/remove guide](../README.md#install-the-prebuilt-go-core-on-linux-or-macos)

An independent implementation of [compatibility core v1](../../spec/compatibility-core-v1.md). It parses profiles, validates and compiles adapters, manages reversible shell state, renders Bash/Zsh integration, executes child commands, and diagnoses consumers. Its runtime does not invoke Python or another DevWho core.

Unix process execution uses `exec`, preserving argv, process exit status, and signals. Windows process execution is explicitly unsupported; use a supported Unix environment. CI runs provide development artifacts; there is no tagged release. Check a successful target run for platform validation.

Hosted binaries are platform-specific, not universal. Go Linux builds may be static or dynamically linked depending on build configuration; inspect the artifact's `RUNTIME.txt` for its exact system requirements rather than assuming all builds share one linkage model. Linux ARM64 is not advertised. macOS ARM64 binaries use the actual runner architecture; check the target run and its runtime note.

## Build and use

Go 1.23 or newer is the build dependency; no Go toolchain or TOML package is required by the resulting executable. Git, SSH, and gh are optional consumer tools used only by their corresponding features. Bash/Zsh integration uses the same functions and profile files as Python. Beginner-friendly artifact installation steps are in the [common guide](../README.md#install-the-prebuilt-go-core-on-linux-or-macos).

```sh
cd implementations/go
go mod download
go mod verify
go test ./...
# Linux: build without cgo for a static Linux executable.
CGO_ENABLED=0 go build -trimpath -o devwho .
# macOS: use platform toolchain defaults instead.
# go build -trimpath -o devwho .
./devwho --config /absolute/path/config.toml list
./devwho --config /absolute/path/config.toml exec work -- git status
eval "$(./devwho --config /absolute/path/config.toml init bash)"
setdev work
unsetdev
```

The executable supports `--help`, `--version`, `--config PATH`, `list`, `show`, `current --verbose`, `doctor [PROFILE] [--offline]`, `exec`, `config path/init`, `init bash/zsh`, and the internal transition/bootstrap/notice endpoints. Configuration initialization is explicit, exclusive, and private (0600 file and 0700 new directories). Initialization prints integration without editing startup files and pins the executable and resolved configuration path. State stays in non-exported `__DEVWHO_STATE` and interoperates with Python's version 1 JSON state.

Generic env values are literal. SSH and gh semantic paths resolve against restored/target HOME. Author/committer override and semantic GitHub token conflicts fail before restoration. Git runtime blocks preserve pair order and third-party appendages, and tampering fails atomically. Shell renderers preflight readonly, array, and unsupported attributes before applying a patch. Runtime Git identity configuration preserves original replay authors; no persistent `GIT_AUTHOR_*` or `GIT_COMMITTER_*` exports are used.

## Optional dotenv frontend

Keep existing TOML configurations, or explicitly select one dotenv file:

```sh
./devwho --env-file /absolute/path/work.env list
./devwho --env-file /absolute/path/work.env exec work -- git status
eval "$(./devwho --env-file /absolute/path/work.env init bash)"
setdev
unsetdev
./devwho --config /absolute/path/config.toml config export-env env-only-profile
```

The file needs a valid `DEVWHO_PROFILE=work` marker or explicit `--env-profile work`. If both exist they must agree. `--env-file` is exclusive with `--config`; `--env-profile` requires it. There is no source merging, cwd discovery, or automatic activation. The frontend normalizes one env-only profile, consuming the marker as metadata and setting the shortcut. Init pins the source path and profile. `config init` refuses dotenv sources.

The literal grammar accepts UTF-8 LF/CRLF, comments, `export KEY=VALUE`, unquoted values, literal single quotes, and JSON-escaped double quotes. Duplicate keys, bare keys, NUL/lone CR, invalid Unicode, reserved author/runtime variables and unsafe keys fail. Dollar expressions remain literal. `config export-env PROFILE` explicitly emits values with a marker, and refuses semantic or unset settings to avoid data loss. Ordinary read commands continue hiding custom values. See the repository's dotenv convention for the full grammar.

## Optional standalone editor

Build the Python-free configuration form and revision-checked JSON API with `go build -tags setup -o devwho-setup .`. It writes standard TOML for all cores, preserves advanced fields and ordered Git values, and uses private backups and atomic revision-checked saves. [Editor instructions](SETUP.md) / [中文说明](SETUP.zh-CN.md).

## Update and uninstall

To update a prebuilt install at `~/.local/bin/devwho`, verify the matching artifact as described in the [common guide](../README.md#install-the-prebuilt-go-core-on-linux-or-macos) and replace that file. Replace `~/.local/bin/devwho-setup` only if updating that optional tool. An initialized shell keeps its current environment and restoration state; open a fresh shell or re-run `devwho init` and evaluate its output to load the updated integration. Configuration, GitHub CLI data, and `.devwho-backups` remain in place. To uninstall, first remove any `devwho init` line you added to a shell startup file, then remove only the known installed binaries, for example `rm "$HOME/.local/bin/devwho"` and, if installed, `rm "$HOME/.local/bin/devwho-setup"`.

## Verification and limitations

`core_test.go` exercises equivalent TOML encodings and ordering, schema rejection, missing/empty/nonempty baselines, switching, idempotence, state validation/limits, runtime corruption and appendages, inherited conflicts, HOME paths, and actual Git cherry-pick/rebase authors. The repository's executable-target acceptance runner and CLI/shell tests provide broader cross-language coverage.

Local evidence and toolchain provenance are recorded in `VERIFICATION.md`. Platforms not listed there, including real macOS Bash 3.2, are coverage gaps until CI or an authorized test environment exercises them. The integration renderer uses Bash 3.2-compatible syntax but this is not a claim that a current-Bash run verifies Bash 3.2. Fake gh responses test local diagnostics; they do not verify live authentication. No activation network calls or persistent Git/SSH/credential writes occur.

## Dependencies

`go.mod` and `go.sum` pin the full build module graph. The sole external runtime code dependency is [pelletier/go-toml/v2 v2.3.1](https://github.com/pelletier/go-toml/tree/v2.3.1), MIT licensed. Its [AST parser](https://pkg.go.dev/github.com/pelletier/go-toml/v2/unstable) preserves runtime table insertion order; standard Go map iteration is deliberately not used for that order. The unstable API is protected by the exact version pin and equivalence tests. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [license](licenses/go-toml-LICENSE). Only the Go standard library is used otherwise.
