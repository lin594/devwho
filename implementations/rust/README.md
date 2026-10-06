# DevWho Rust compatibility core

This is an independent Rust implementation of the DevWho v0.1 compatibility core. Its runtime is one native executable; it does not invoke Python, Go, Bash, or another core as an implementation helper. It invokes Git and optionally GitHub CLI for diagnostics, and the requested child command for `exec`.

Build with Rust 1.85 or later:

For the recommended prebuilt Go installation steps, see the [common guide](../README.md#install-the-prebuilt-go-core-on-linux-or-macos). Rust archive requirements are recorded per build in `RUNTIME.txt`.

```sh
cargo build --release --locked --manifest-path implementations/rust/Cargo.toml
```

Run `implementations/rust/target/release/devwho --config /absolute/config.toml list`. To integrate a shell, evaluate its `init bash` or `init zsh` output in that shell. The generated functions pin the executable and configuration path. `setdev [PROFILE]` activates a profile; `unsetdev` restores the shell baseline. Start a fresh shell to choose another implementation.

The optional dotenv frontend accepts `--env-file PATH [--env-profile NAME]` in place of `--config PATH`. The file selects one profile with `DEVWHO_PROFILE=NAME`, or the caller supplies `--env-profile NAME`. The file's assignments become literal generic environment values. It supports LF/CRLF, comments, optional `export `, unquoted values, literal single quotes, and JSON-escaped double quotes. It rejects duplicates, invalid keys, malformed quoting, NUL, and semantic settings. `config export-env PROFILE` writes a lossless dotenv representation of a profile that has only generic environment values; it rejects Git, SSH, GitHub, or unset settings. `config init` applies only to TOML.

TOML 1.0 is parsed by the locked `toml` crate with insertion order preserved for repeated Git settings. Internal shell state uses version 1 JSON. Linux artifacts dynamically link to glibc and `libgcc_s`; the current Linux x86_64 CI build requires glibc symbols through 2.39. Alpine/musl is not supported, and Linux ARM64 is not advertised. Check the downloaded archive's `RUNTIME.txt`; requirements may differ between builds. Diagnostics use installed `git` and optional `gh`; switching is offline. See [LICENSES.md](LICENSES.md) for the exact third-party license inventory.

Validation on Linux x86_64: Rust 1.85.1 compiled and passed the unit tests; Rust 1.95.0 built the release binary; the common runner passed on the built binary with one shell-specific skip. Current Bash and Zsh integration passed. Bash 3.2 and macOS have not been run here and remain coverage gaps. This port remains experimental until distribution and platform CI complete. It does not edit global Git configuration, remotes, credentials, or shell startup files.

## Update and uninstall

For a self-installed Rust binary, verify the matching artifact and its `RUNTIME.txt`, then replace only the installed `devwho` file. An initialized shell keeps its current environment and restoration state; open a fresh shell or re-run `devwho init` and evaluate its output to load updated integration code. Configuration, GitHub CLI data, and setup-editor backups are unchanged. To uninstall, first remove any `devwho init` line you added to a shell startup file, then remove only the known binary path you installed, such as `rm "$HOME/.local/bin/devwho"`. Keep those data directories. The common beginner install guide is [here](../README.md#install-the-prebuilt-go-core-on-linux-or-macos).
