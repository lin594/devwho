# DevWho Bash implementation

[English](README.md) | [简体中文](README.zh-CN.md) · [Choose a core and prebuilt Go install guide](../README.md)

Independent implementation of the [compatibility core v1](../../spec/compatibility-core-v1.md).
It includes strict TOML configuration, all public CLI commands, Bash/Zsh
integration, reversible JSON state, ordered Git runtime configuration, semantic
SSH/GitHub settings, startup defaults, subprocess execution and diagnostics.

The runtime is **Bash 3.2+, jq 1.6+, Perl 5.18+ and standard OS utilities**.
Perl uses only standard modules and the included TOML decoder. No Python,
Go/Rust DevWho core, CPAN install, network service, or runtime build is needed. A small Perl launcher captures the environment before Bash startup normalizes special variables; Bash/jq still own the core. The exec transport preserves the calculated environment even for SHLVL, PWD and names Bash cannot export.
See [dependency versions, license and parser changes](THIRD_PARTY.md).

## Run and install

From a checkout:

```bash
implementations/bash/devwho --config examples/config.toml list
implementations/bash/devwho --config examples/config.toml exec personal -- git var GIT_AUTHOR_IDENT
# Evaluate only generated integration code, never the TOML file itself.
eval "$(implementations/bash/devwho --config examples/config.toml init bash)"
setdev work
unsetdev
```

Use `init zsh` in Zsh. `init` prints code and never edits startup files. It pins the
resolved executable and configuration path. Profile selection and literal values
are local to the current shell; restoration state is not exported to children.

Install prerequisites with your OS package manager, then:

```bash
bash implementations/bash/install.sh "$HOME/.local"
"$HOME/.local/bin/devwho" --config /absolute/path/config.toml list
```

The installer copies the complete implementation to `PREFIX/lib/devwho-bash` and
creates `PREFIX/bin/devwho`. It refuses to replace an existing `devwho` symlink or
file. Keep all installed files together. `config init` creates an example privately
and exclusively; edit example identities before use. The executable can also be
run directly without installation.

To update, first confirm `PREFIX/bin/devwho` is the symlink created by this
installer and points into that same `PREFIX/lib/devwho-bash` directory. Remove only
that known symlink, then rerun the installer with the same prefix; it refuses to
overwrite an unrelated command. An initialized shell keeps its current environment
and restoration state; open a fresh shell or re-run `devwho init` and evaluate its
output to load updated integration code. Configuration,
GitHub CLI data, and setup-editor backups remain separate. To uninstall a default
`$HOME/.local` install, remove the known symlink and then the known implementation
directory. If you added a `devwho init` line to a shell startup file, remove that
line first so new terminals do not call a removed command:

```bash
# Update the default install only if this is its expected symlink target.
test "$(readlink "$HOME/.local/bin/devwho")" = "$HOME/.local/lib/devwho-bash/devwho" &&
  rm "$HOME/.local/bin/devwho"
bash implementations/bash/install.sh "$HOME/.local"
```

For a full uninstall, remove those same known paths instead:

```bash
rm "$HOME/.local/bin/devwho"
rm -r "$HOME/.local/lib/devwho-bash"
```

If you used another prefix, substitute that exact prefix. Keep configuration,
GitHub CLI data, and backups unless you intend to remove those separately. See the
[common guide](../README.md) to compare core options and the optional prebuilt Go path.

## Behavior and validation

Configuration precedence, schema, commands and workflow match the
[common reference](../../docs/reference.md). Activation is offline. `doctor`
returns 0 for passing checks, 1 for mismatches, and 2 when checks are unverified.
It hides generic values/tokens and tool stderr. Diagnostics have bounded timeouts.
`exec` replaces its process, preserving literal argv, child status and signals;
missing/nonexecutable commands return 127/126.

The state model preserves absent, empty and nonempty baseline values, appended
third-party Git pairs, original author behavior in replay operations, and orphan
runtime variables. State structure/size and shell readonly/array/attribute checks
run before changes are applied. Every value is rendered as literal shell data.

Development validation (Python is a **test-only** dependency):

```bash
python3 -m unittest discover -s implementations/bash/tests -v
python3 conformance/run.py --executable implementations/bash/devwho --peer bin/devwho
```

The shared runner exercises real Bash/Zsh/Git/SSH, TOML encodings and invalid
schema, cross-implementation state, literal argv, exit/signals, diagnostics and
atomic restoration. Source-tree tests do not by themselves prove every supported
OS or a Python-free deployment. This port remains experimental until the common
release matrix and isolated runtime checks pass; consult the report from the
specific release rather than assuming coverage from a source commit.

No startup/profile files, saved Git/SSH config, credentials, remotes, branches or
working files are changed by activation.

## Optional dotenv frontend

TOML remains the full compatibility format. A generic-environment-only profile may
also come from an explicit dotenv file:

```bash
# environment.env contains DEVWHO_PROFILE=work and ordinary KEY=value assignments.
eval "$(implementations/bash/devwho --env-file environment.env init bash)"
setdev                         # shortcut selects the file's one profile
unsetdev
# When the file omits DEVWHO_PROFILE, supply its name explicitly:
implementations/bash/devwho --env-file environment.env --env-profile work list
# Export a TOML profile containing only generic env values:
implementations/bash/devwho --config config.toml config export-env work > work.env
```

`--env-file` and `--config` are mutually exclusive; `--env-profile` requires an
explicit dotenv file. A file marker and explicit name must match. The marker is
consumed as profile metadata. The single profile is a shortcut, not a startup
default. Generated initialization pins the file and profile name. `config path`
reports the selected source; `config init` refuses dotenv files.

Files use UTF-8 with LF or CRLF. Assignments accept whitespace around `=`, an
optional literal `export ` prefix, blank/full-comment lines, empty values, literal
single quotes, and JSON double-quoted strings (including escaped newlines).
Unquoted values are trimmed; `#` starts a comment only after space/tab. Dollar
signs, `${...}` and `$(...)` always stay literal. Duplicate keys, bare keys,
physical multiline values, NUL, lone CR, invalid Unicode escapes, unsafe/reserved
keys and profile mismatches fail. There is no interpolation, sourcing or unset
syntax. `config export-env` rejects Git, SSH, GitHub settings and explicit unsets
so none can be silently lost during conversion.

### Recorded local validation

On Linux x86_64, the common suite passed **63 tests** (one intentional Zsh-only
check skipped for Bash) with Bash **5.2.37** and Zsh **5.9**, jq **1.7**, Perl
**5.40.1**, and a Python-core state peer. The same 63-test suite also passed with
an independently built **Bash 3.2.0** selected for both the core interpreter and
Bash integration. The implementation-specific suite passed **20 tests**. A fresh
prefix install, installed symlink, inherited/target Unicode and SHLVL/PWD,
PATH/TMPDIR changes, and a newline-suffixed configuration filename were checked.

These are Linux results. Actual macOS/Windows and clean runtime filesystem
acceptance remain responsibilities of the shared release matrix. Python here is
only the development test driver; it is not invoked by the installed runtime.
