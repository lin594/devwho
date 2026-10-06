# Choose one compatibility core

[English](README.md) | [简体中文](README.zh-CN.md) · [Project overview](../README.md)

Install **one** core. RC1 recommends static Go for Linux x86-64 and Go for macOS **13+ ARM64**. The Rust macOS ARM64 binary declares macOS **11.0** minimum. These are deployment requirements, distinct from the actual hosted macOS 26.6.2 test host. See the [tested artifact matrix](../README.md#tested-candidate-artifacts) and each archive's `RUNTIME.txt` for target, libraries, deployment minimum and test host.

Python requires 3.11+ and no third-party runtime Python packages. Bash requires Bash 3.2+, jq 1.6+, Perl 5.18+ and standard utilities. Go/Rust binaries require no Python/compiler. Git 2.31+, gh and OpenSSH are consumer dependencies for their respective features. RC1 omits the Linux Rust binary because the hosted build requires glibc 2.39; it is still built/tested, and source builds remain available. Linux ARM64, macOS x86-64, Alpine/musl, Windows/PowerShell and editor identity binding remain unverified.

The [v0.1.0-rc.1 pre-release](https://github.com/lin594/devwho/releases/tag/v0.1.0-rc.1) provides selected tested assets, the complete `SHA256SUMS`, `RELEASE-MANIFEST.json`, and FZ2 downloaded-artifact validation evidence. Product versions use `0.1.0-rc.1`; package filenames use equivalent PEP 440 `0.1.0rc1`. Ordinary Actions downloads remain development artifacts. The [release plan](../release-plan.json) defines the exact eight distributions and canonical Python source; the [manual procedure](../docs/releasing.md) enforces completeness and provenance.

### Install the prebuilt Go core on Linux or macOS

1. Select the matching archive: Linux x86-64 uses `devwho-0.1.0rc1-go-linux-x86_64.tar.gz`; macOS 13+ ARM64 uses `devwho-0.1.0rc1-go-darwin-arm64.tar.gz`. Download **that archive and SHA256SUMS only** from the [pre-release](https://github.com/lin594/devwho/releases/tag/v0.1.0-rc.1). For example:

   ```sh
   asset=devwho-0.1.0rc1-go-linux-x86_64.tar.gz  # macOS: devwho-0.1.0rc1-go-darwin-arm64.tar.gz
   base=https://github.com/lin594/devwho/releases/download/v0.1.0-rc.1
   curl -fLO "$base/$asset"
   curl -fLO "$base/SHA256SUMS"
   ```

2. Verify the exact selected entry; unrelated distributions are not needed:

   ```sh
   awk -v name="$asset" '$2 == name {print; found=1} END {if (!found) exit 1}' SHA256SUMS > selected.SHA256SUMS
   sha256sum -c selected.SHA256SUMS  # Linux
   # macOS: shasum -a 256 -c selected.SHA256SUMS
   ```

3. Unpack, inspect `RUNTIME.txt`, and install into a user-owned directory:

   ```sh
   tar -xzf "$asset"
   cd "${asset%.tar.gz}"
   cat RUNTIME.txt
   mkdir -p "$HOME/.local/bin"
   install -m 755 devwho "$HOME/.local/bin/devwho"
   install -m 755 devwho-setup "$HOME/.local/bin/devwho-setup"  # optional configuration editor
   export PATH="$HOME/.local/bin:$PATH"
   devwho --version
   ```

   No compiler is required. The PATH change applies to this terminal; add the directory to your startup file if desired.
4. Save profiles with `devwho-setup configure` or initialize TOML explicitly with `devwho --config /absolute/path/config.toml config init`. Edit the example identities, then:

   ```sh
   eval "$(devwho --config /absolute/path/config.toml init bash)"  # Zsh: init zsh
   setdev PROFILE_NAME
   devwho doctor --offline
   unsetdev
   devwho --config /absolute/path/config.toml exec PROFILE_NAME -- git var GIT_AUTHOR_IDENT
   ```

   `unsetdev` restores the shell baseline. Doctor exit 2 means a configured online authentication check is unverified offline; it does not prove live account ownership.

For a Rust macOS ARM64 installation, choose `devwho-0.1.0rc1-rust-darwin-arm64.tar.gz`, verify/extract it the same way and install its `devwho`; it does not bundle `devwho-setup`. Its declared macOS minimum is 11.0, and the actual recorded test host is 26.6.2. Bash installation/update/removal is in the [Bash guide](bash/README.md). Python source/zipapp installation is in [Getting started](../docs/getting-started.md).

To update Go/Rust, verify the newer matching archive and replace only the installed executables. An initialized shell retains its environment/restoration state; open a fresh shell or re-evaluate `devwho init bash`/`zsh` for updated integration. Configuration, gh data and setup backups remain in place. To uninstall, remove any startup line you added, then only the known executables you installed; retain configuration and credentials unless deliberately removing them separately.

## Shared behavior and format

All four cores implement the [compatibility core v1 contract](../spec/compatibility-core-v1.md), including configuration validation, profile transitions, Git/gh adapters, diagnostics, subprocess behavior, real shell integration, and reversible state. The [executable conformance runner](../conformance/README.md) checks common fixtures and cross-core restoration-state interchange. Its recorded results and platform coverage are implementation- and runner-specific; consult those records before relying on a target.

Every core supports full TOML profiles and the optional, explicit [literal dotenv input](../spec/dotenv-v1.md). Dotenv selects a single generic-environment profile and does not merge with TOML. It is not sourced or interpolated. Export to dotenv is rejected when it would lose Git, SSH, GitHub, or unset semantics. See the [configuration format guide](../docs/configuration-formats.md).

The optional [Go configuration frontend](../docs/configuration-ui.md) provides English and Chinese terminal forms, plus a read/replace interface with revision checks and private backups. It writes the shared TOML format and is not required by any core.

The proposed [native environment convention](../spec/environment-v1.md) is a separate draft. The repository includes a stdlib-only native reference consumer example in [`examples/native-notes`](../examples/native-notes), but does not claim third-party adoption or native integrations in Git/gh. The example owns its application configuration and storage and has no core dependency.

## Build and contribute

Install instructions, runtime dependencies, and implementation-specific validation are in each implementation README. Build artifacts with [`scripts/package_cores.py`](../scripts/package_cores.py); the CI `cores` job builds and tests Ubuntu and macOS runner artifacts. Check the actual [workflow run](https://github.com/lin594/devwho/actions/workflows/ci.yml) for results rather than treating a configured job as a pass. See the [common contract](../spec/compatibility-core-v1.md), [conformance suite](../conformance/README.md), and [contributing guide](../CONTRIBUTING.md) before changing shared behavior.
