# Project status

DevWho provides four independent implementations of a per-shell compatibility core: Python, Go, Rust, and Bash. The first tagged candidate is [v0.1.0-rc.1](https://github.com/lin594/devwho/releases/tag/v0.1.0-rc.1); package registry publication is deferred. Development artifacts are attached to CI runs; downloading them requires GitHub sign-in. Check the workflow run itself for hosted results.

## Separate tracks

| Track | Current status |
|---|---|
| [Native environment convention](../spec/environment-v1.md) | Draft with `DEVWHO_PROFILE` as its only shared selector. A native reference consumer example exists; no third-party adoption or Git/gh native integration is claimed. |
| Compatibility core | Python, Go, Rust, and Bash implementations follow the shared contract. Select one core; they share TOML profiles, commands, and restoration state. |
| [Shared executable conformance](../conformance/README.md) | Language-neutral fixtures and runner are implemented. The suite exercises shared CLI, shell, restoration-state, dotenv, and consumer-selection behavior; one shell-specific case may be intentionally skipped in runs under the other shell. Inspect each implementation's verification record for its own results. |
| [Dotenv input](../spec/dotenv-v1.md) | Implemented as an explicit, literal, single-profile input by all four cores. It does not merge with TOML; export rejects profiles whose semantics cannot be represented losslessly. |
| [Configuration frontend](configuration-ui.md) | Optional standalone Go tool provides English/Chinese terminal forms and a shared read/replace API with revision checks and private backups. |

## What DevWho provides

Each core compiles a full version 1 TOML profile, or explicitly selected generic-environment dotenv input, into environment settings for one shell or child process tree. Bash and Zsh initialization is explicit. Git identity, optional Git SSH settings, optional GitHub CLI context, and arbitrary literal environment variables are supported. `unsetdev` restores the baseline captured before the shell's first activation; `devwho exec` applies a profile only to the child process tree. Compatible cores can exchange restoration state.

Activation and inspection do not rewrite Git or SSH configuration, move credentials, or edit shell startup files. GitHub account checks are explicit `doctor` operations. The optional setup tool edits TOML but does not activate a profile. Review [the architecture](architecture.md), [configuration example](../examples/config.toml), and [dotenv contract](../spec/dotenv-v1.md) for details.

## Platform and release status

Python requires Python 3.11+. Go and Rust executable runtime does not require Python or a compiler. Bash requires Bash 3.2+, jq 1.6+, and Perl 5.18+. The `cores` CI job builds and tests Ubuntu/macOS artifacts; check [hosted workflow results](https://github.com/lin594/devwho/actions/workflows/ci.yml), and use each implementation's verification record for local evidence and coverage limitations. The workflow matrix alone is not evidence that every job passed.

Go/Rust candidate artifacts are attached to the pre-release; development artifacts are also available through CI; they target the actual runner platform and are checksummed. CI downloads require GitHub sign-in. The optional Go setup editor's local execution evidence covers Linux x86-64; Windows writes are unsupported. Windows PowerShell and VS Code identity integration remain experimental/deferred.
