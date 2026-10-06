# Choose one compatibility core

[English](README.md) | [简体中文](README.zh-CN.md) · [Project overview](../README.md)

The compatibility core makes existing Git, SSH, and GitHub CLI workflows follow the context selected in a terminal. We want users to choose an implementation that fits their machine, while keeping the **same profile file, commands, and behavior**.

Only the Python core is implemented today. The rows marked planned are implementation work, not installable releases. The [native application convention](../spec/environment-v1.md) is an independent draft and does not require any of these cores.

## Implementation choices

| Implementation | Status / source | Intended end-user requirement | Why provide it? |
|---|---|---|---|
| Python | Available source: [`src/devwho`](../src/devwho); [`bin/devwho`](../bin/devwho) | Python 3.11+; no third-party runtime Python packages | Current complete implementation and regression baseline. |
| Go | Planned complete port; future source under `implementations/go/` | Matching prebuilt executable; no Python or Go compiler needed to run it | First priority for users missing Python and for simple binary distribution. |
| Rust | Planned complete port; future source under `implementations/rust/` | Matching prebuilt executable; no Python or Rust compiler needed to run it | An independent full implementation with its own build ecosystem. |
| Bash | Planned complete port; future source under `implementations/bash/` | Bash plus explicitly documented system utilities and consumer tools; no Python or compiler | Script-based installation for environments where Bash is available. |

Users install **one** core, not all languages. The producer language does not restrict the calling shell: every full port must provide both `init bash` and `init zsh`. Git 2.31+, and optional gh/OpenSSH, remain consumer dependencies where those features are used.

Go and Rust build executable applications; build tools belong on the builder, not necessarily the user's machine. Artifacts still need OS/CPU targets, checksums, and documented system-library requirements. A successful cross-compile is not proof the artifact works on that target. See the official [Go build guide](https://go.dev/doc/tutorial/compile-install) and [Rust build guide](https://doc.rust-lang.org/book/ch01-03-hello-cargo.html).

Bash has a harder parsing job: the current format is TOML, and reversible state has structured validation requirements. A full Bash port must implement these correctly, not translate a few `key=value` lines or invoke the Python core. Prefer Bash with standard utilities; any external parser/helper must be declared and assessed against the goal of easier installation. If a full parser is not finished, label the port experimental and leave its full-core issue open.

## The compatibility promise

All implementations target the [compatibility core v1 contract](../spec/compatibility-core-v1.md): configuration, transitions, Git/gh adapters, diagnostics, subprocess behavior, and safe real-shell integration. A port is complete only after common conformance tests and a runtime test with Python unavailable pass. Calling Python from a Go/Rust binary or a Bash function does not satisfy this goal.

The Python tree stays in its current location to preserve package/build compatibility. Specifications live in `spec/`; language implementations get their own directories as working code arrives. We do not add empty package skeletons that look installable or change users' existing workspace layouts.

File formats are a separate choice: [optional dotenv input](../docs/configuration-formats.md) can share the same normalized profile and transition engine. Every full port must still accept existing TOML profiles. A Bash core limited to dotenv would leave the full-core task incomplete.

## Delivery order and tracked work

1. Establish the shared contract and executable conformance fixtures. Keep the Python implementation passing so it remains a useful reference.
2. Prioritize the full Go core and tested downloadable binaries to remove the Python requirement for the widest initial group.
3. Develop the full Rust and Bash alternatives against the same suite. Each can land in reviewed stages; neither is considered complete as a wrapper or feature subset.
4. Add release packaging and install instructions only for artifacts that exist and pass their advertised target tests. Windows PowerShell/editor integration needs separate acceptance work even if a compiler can produce a Windows executable.

| Task | Tracking issue |
|---|---|
| Native context convention | [RFC #1](https://github.com/lin594/devwho/issues/1) |
| Shared complete-core conformance suite | [#2](https://github.com/lin594/devwho/issues/2) |
| Complete Go core | [#3](https://github.com/lin594/devwho/issues/3) |
| Complete Rust core | [#4](https://github.com/lin594/devwho/issues/4) |
| Complete Bash core | [#5](https://github.com/lin594/devwho/issues/5) |
| Optional dotenv input | [#6](https://github.com/lin594/devwho/issues/6) |

These are open tasks, not completed implementations. Contributions should keep behavior fixes and bilingual instructions aligned across implementations.
