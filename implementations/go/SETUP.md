# Standalone configuration editor

[English](SETUP.md) | [简体中文](SETUP.zh-CN.md)

`devwho-setup` is an optional, independent Go executable for creating and editing standard DevWho TOML. Python and a running DevWho core are not required. Every core can read its output. It shares the core schema validator, but its storage and form code are excluded from the runtime executable through a separate build tag. It does not activate a profile or change the current shell.

```sh
go build -tags setup -trimpath -o devwho-setup .
go test -tags setup ./...
./devwho-setup --config /absolute/path/config.toml configure
./devwho-setup --config /absolute/path/config.toml --language zh-CN configure
```

The form edits one selected profile per invocation. Blank keeps an existing value; `-` removes an optional SSH/GitHub mapping or default/shortcut selection. It supports Git name/email, SSH key path, GitHub directory/login/hostname, default and shortcut selection. Advanced fields and unrelated profiles stay intact. A redacted preview precedes an explicit `save`/`cancel` decision (`保存` also saves in Chinese mode). Cancellation and EOF do not write configuration or change a session. When no command is given, the editor starts the form.

## Machine interface

```sh
./devwho-setup --config /absolute/path/config.toml read
./devwho-setup --config /absolute/path/config.toml read --show-values
./devwho-setup --config /absolute/path/config.toml replace --if-revision missing < configuration.json
./devwho-setup --config /absolute/path/config.toml replace --if-revision CURRENT_SHA256 < configuration.json
```

`read` prints `{ "revision": "SHA256", "configuration": { ... }, "redacted": true }`. The revision hashes the exact file bytes. Generic env values and arbitrary `git.config` values are hidden by default; `--show-values` explicitly reveals them. An absent file reports revision `missing`, configuration `null`. Paths use the same explicit/config-environment/XDG/HOME precedence as the runtime core.

`replace` accepts the raw version 1 schema object, **not** the read envelope, on stdin. Its maximum input size is 1 MiB. Duplicate JSON keys, multiple documents, unknown fields, invalid profiles, invalid Unicode escapes, and a noninteger version are rejected before writing. Git runtime table insertion order and repeated values survive JSON↔TOML round trips. JSON output preserves that order. Form editing uses the same validator and save API.

For example, a new `configuration.json` can contain:

```json
{"version":1,"profiles":{"work":{"git":{"name":"Work User","email":"work@example.test","config":{"credential.helper":["","custom"]}}}}}
```

## Save behavior

A persistent sibling `config.toml.lock` coordinates cooperating editors through Unix `flock`. The lock must be a regular file and is opened without following symlinks. Inside the lock, the editor checks the expected revision, saves the previous exact bytes privately under sibling `.devwho-backups/` (0700 directory, 0600 files), writes and syncs a private temporary file, and atomically renames it over the selected configuration as 0600. The containing directory is synced. A new file has no invented prior backup. Direct configuration symlink writes and unsafe backup-directory symlinks fail.

A stale revision fails before backup or replacement. Tools that do not use this lock can still race with a save. Source formatting and comments are normalized on save; all supported fields and Git pair order are retained, while the backup retains the original exact bytes. The editor stores no credentials separately and contacts no remote service. Windows writes are explicitly unsupported; local execution evidence currently covers Linux x86-64.

Tests cover true cross-process stale-save contention, exact backup bytes and modes, cancellation in both languages, schema/duplicate-JSON rejection, redaction, missing-file creation, symlink refusals, special strings and ordered Git round trips.
