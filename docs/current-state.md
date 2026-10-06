# Project status

DevWho is a project for per-shell developer context: a proposed shared environment convention and a compatibility core for existing tools. Only the Python core is implemented today. Its source is public; version 0.1.0 has no tagged release or package registry publication yet.

## Separate tracks

| Track | Current status |
|---|---|
| [Native environment convention](../spec/environment-v1.md) | Draft using only `DEVWHO_PROFILE`, which the current core already exports. Native app mappings/integrations are not shipped or claimed. |
| Python compatibility core | Implemented in `src/devwho`, with Bash/Zsh and Git/gh adapters. |
| [Full Go, Rust, and Bash cores](../implementations/README.md) | Planned independent implementations of the same behavior; no working ports or downloadable binaries yet. |
| Shared executable conformance suite | Contract documented; language-neutral fixtures/runner still to be implemented. Existing Python regression tests are not a substitute. |
| [Dotenv core input](configuration-formats.md) | Proposed optional input. The current core still accepts TOML only; ordinary third-party dotenv launchers can already supply a context variable to future native consumers. |

## What DevWho provides

DevWho compiles a version 1 TOML profile into environment settings for one shell or child process tree. Bash and Zsh initialization is explicit. Git identity, optional Git SSH settings, optional GitHub CLI context, and arbitrary literal environment variables are supported. `unsetdev` restores the baseline captured before the shell's first activation; `devwho exec` applies a profile only to the child process tree.

Activation and inspection do not rewrite Git or SSH configuration, move credentials, or edit shell startup files. GitHub account checks are explicit `doctor` operations. Review [the architecture](architecture.md) and [the configuration example](../examples/config.toml) for details.

## Platform and release status

The current implementation requires Python 3.11 or newer. Linux/WSL Bash and Zsh have local integration coverage. GitHub Actions is configured for Ubuntu and macOS with Python 3.11 and 3.13; check the [workflow runs](https://github.com/lin594/devwho/actions/workflows/ci.yml) for hosted results. A configured workflow matrix is not itself evidence that every job has passed.

Windows PowerShell and editor identity integration are outside the supported v0.1 interface. No release, tag, or package publication is implied by the version in `pyproject.toml`.
