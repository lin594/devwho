# Test an implementation

[English](README.md) | [简体中文](README.zh-CN.md)

The common runner treats a core as an executable. It never imports that core's parser, state engine or adapters. Python is a **test-driver** requirement, not a runtime dependency of Go, Rust or Bash.

```sh
python3 conformance/run.py --executable /path/to/devwho --peer ./bin/devwho --report report.json
```

Use `--peer` repeatedly to check restoration-state interchange with other cores. The runner covers complete TOML profiles, shared JSON fixtures, ordered Git pairs, real Bash/Zsh sessions, readonly-variable atomicity, proxy/baseline preservation, explicit diagnostics, subprocess behavior, dotenv and literal SSH arguments. It reuses the existing black-box CLI/shell tests; Python-specific package tests remain in `tests/`.

For Bash 3.2, set `DEVWHO_TEST_BASH=/path/to/bash-3.2`; macOS CI uses `/bin/bash`. Missing shell coverage must be reported rather than described as a pass.

## Prove Python-free runtime operation

```sh
docker build -f conformance/Dockerfile -t devwho-runtime-check conformance
docker run --rm --network none \
  -v "$PWD/conformance:/checks:ro" \
  -v /absolute/path/to/artifacts:/artifacts:ro \
  devwho-runtime-check /artifacts/devwho
```

Mount only the selected distribution (including Bash's companion files), not a Python installation or another source core. The image contains Bash, Zsh, Git, jq and Perl, but no Python or language compiler. `runtime.sh` verifies this, consumes the same TOML/dotenv vectors, tests installation bootstrap and shell restoration, and performs real Git rebase/cherry-pick author preservation. Networking is disabled during runtime tests. Docker is only a contributor test dependency.

The container run complements the larger host suite; it does not replace all cross-platform checks. CI retains JSON reports and tested distributions. No live credential or remote-write test runs in this suite.
