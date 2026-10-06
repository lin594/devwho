# Choose one compatibility core

[English](README.md) | [简体中文](README.zh-CN.md) · [Project overview](../README.md)

The compatibility core makes existing Git, SSH, and GitHub CLI workflows follow the context selected in a terminal. Python, Go, Rust, and Bash implementations now target the same profile, command, transition, and restoration contract. Install or build **one** core for your machine.

## Implementation choices

| Implementation | Source and distribution | End-user requirements | Notes |
|---|---|---|---|
| Python | [`src/devwho`](../src/devwho), [`bin/devwho`](../bin/devwho) | Python 3.11+; no third-party runtime Python packages | Reference implementation; existing Python installation instructions remain available. |
| Go | [`implementations/go`](go/README.md) | Prebuilt executable needs no Python or compiler; source build needs Go | Recommended for beginners; development artifacts are attached to `complete-cores-ubuntu-latest` and `complete-cores-macos-latest` workflow runs; download requires GitHub sign-in. |
| Rust | [`implementations/rust`](rust/README.md) | Prebuilt executable needs no Python or compiler; source build needs Rust | Independent implementation; consult its README for build and platform coverage. |
| Bash | [`implementations/bash`](bash/README.md) | Bash 3.2+, jq 1.6+, Perl 5.18+, standard OS utilities | Independent script implementation; Perl and jq are runtime requirements. |

CI artifacts are development builds, not tagged releases. Their archive names and checksums are published with each workflow run; the archive targets the actual runner platform. No tag or hosted release is published. Go and Rust executables run without Python or a compiler at runtime. The Bash runtime invokes no Python core. Binary archives include `RUNTIME.txt` with the actual OS, architecture, and system-library requirements for that build. Linux Rust artifacts require glibc symbols through 2.39 and `libgcc_s`; Alpine/musl is unsupported. Go Linux builds may be static or dynamically linked depending on the build. Check each archive's `RUNTIME.txt` before installing. Linux ARM64 is not advertised.

### Install the prebuilt Go core on Linux or macOS

1. Open the repository’s [Actions workflow](https://github.com/lin594/devwho/actions/workflows/ci.yml), choose a successful CI run for the desired commit, then download its `complete-cores-[OS]` artifact. Extract the downloaded GitHub artifact ZIP.
2. In the extracted directory, verify the archive checksum before unpacking it:

   ```sh
   cd /path/to/extracted-artifact/dist/cores
   sha256sum -c SHA256SUMS       # Linux
   shasum -a 256 -c SHA256SUMS  # macOS
   ```

3. Unpack the Go archive for your runner. Linux x86-64 uses `devwho-go-linux-x86_64.tar.gz`; macOS uses the exact `devwho-go-darwin-ARCH.tar.gz` filename listed in `SHA256SUMS` for that runner. For example:

   ```sh
   tar -xzf devwho-go-linux-x86_64.tar.gz
   cd devwho-go-linux-x86_64
   # On macOS, substitute its matching archive and cd into devwho-go-darwin-ARCH.
   ```

   The archive contains `devwho` and the optional `devwho-setup` standalone editor. Install either or both into a user-owned directory:

   ```sh
   mkdir -p "$HOME/.local/bin"
   install -m 755 devwho "$HOME/.local/bin/devwho"
   install -m 755 devwho-setup "$HOME/.local/bin/devwho-setup"
   export PATH="$HOME/.local/bin:$PATH"
   ```

   The `install devwho-setup` line is optional if you want to edit TOML by hand. The PATH command applies to this terminal; add the same directory to your shell startup file if you want it in future terminals. No compiler is needed on the user machine.
4. Optionally run `devwho-setup configure` and follow the form to save a profile. Then initialize the shell and activate it:

   ```sh
   eval "$(devwho init bash)"  # use `zsh` instead of `bash` in Zsh
   setdev PROFILE_NAME
   ```

   `unsetdev` restores the shell baseline. The command pins this installed executable and the default configuration path for the current shell.

For source-build instructions and verification, see the [Go guide](go/README.md). To update Go or Rust, verify and extract the newer matching artifact, then replace only `~/.local/bin/devwho`; replace `devwho-setup` only if you are updating that optional tool too. An initialized shell keeps its current environment and restoration state. Open a fresh shell or re-run `devwho init bash`/`zsh` and evaluate the output to load updated integration code. Configuration, GitHub CLI data, and setup-editor backups remain in place. For Bash updates and removal, follow the [Bash guide](bash/README.md).

To remove a Go/Rust installation, first remove any `devwho init` line you added to a shell startup file, then remove only the executable(s) you placed in `~/.local/bin` (for example, `devwho` and optionally `devwho-setup`). Keep configuration and GitHub CLI data if you may use them again.


The core language does not limit the calling shell: all implementations provide `init bash` and `init zsh`. Git 2.31+ and optional `gh`/OpenSSH remain consumer dependencies for the features that use them. Windows/PowerShell and editor identity integration remain experimental or deferred.

## Shared behavior and format

All four cores implement the [compatibility core v1 contract](../spec/compatibility-core-v1.md), including configuration validation, profile transitions, Git/gh adapters, diagnostics, subprocess behavior, real shell integration, and reversible state. The [executable conformance runner](../conformance/README.md) checks common fixtures and cross-core restoration-state interchange. Its recorded results and platform coverage are implementation- and runner-specific; consult those records before relying on a target.

Every core supports full TOML profiles and the optional, explicit [literal dotenv input](../spec/dotenv-v1.md). Dotenv selects a single generic-environment profile and does not merge with TOML. It is not sourced or interpolated. Export to dotenv is rejected when it would lose Git, SSH, GitHub, or unset semantics. See the [configuration format guide](../docs/configuration-formats.md).

The optional [Go configuration frontend](../docs/configuration-ui.md) provides English and Chinese terminal forms, plus a read/replace interface with revision checks and private backups. It writes the shared TOML format and is not required by any core.

The proposed [native environment convention](../spec/environment-v1.md) is a separate draft. The repository includes a stdlib-only native reference consumer example in [`examples/native-notes`](../examples/native-notes), but does not claim third-party adoption or native integrations in Git/gh. The example owns its application configuration and storage and has no core dependency.

## Build and contribute

Install instructions, runtime dependencies, and implementation-specific validation are in each implementation README. Build artifacts with [`scripts/package_cores.py`](../scripts/package_cores.py); the CI `cores` job builds and tests Ubuntu and macOS runner artifacts. Check the actual [workflow run](https://github.com/lin594/devwho/actions/workflows/ci.yml) for results rather than treating a configured job as a pass. See the [common contract](../spec/compatibility-core-v1.md), [conformance suite](../conformance/README.md), and [contributing guide](../CONTRIBUTING.md) before changing shared behavior.
