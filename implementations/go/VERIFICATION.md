# Local verification evidence

Recorded 2026-10-06 against the working source derived from repository commit `415848ea7f5e76f0a7800be83dea57937c44f3b0`. This is development evidence, not a signed release artifact or a claim that every supported platform has been executed.

- Host: Linux x86-64; Bash 5.2.37; Zsh 5.9; Git 2.47.3.
- Build toolchain: official Go 1.27.1 `go1.27.1.linux-amd64.tar.gz`, obtained from https://go.dev/dl/?mode=json and https://dl.google.com/go/go1.27.1.linux-amd64.tar.gz.
- Archive SHA256 verified before the toolchain was used: `63d339f0da5ab53635a56f2490a7984dfe12dfcff22ad749f63edaf590168445`.
- Toolchain and caches stayed under `/tmp/devwho-toolchains/`; no shell startup or installed DevWho executable was changed.
- `go test ./...`: PASS, including true Git cherry-pick/rebase fixtures with distinct original author and new committer identities.
- `go mod verify`: PASS. External graph: `github.com/pelletier/go-toml/v2 v2.3.1` only. The TOML 1.0 version is intentionally pinned; v2.4.3 supports TOML 1.1 and would accept extra syntax rejected by the baseline.
- `python3 conformance/run.py --executable /tmp/devwho-toolchains/devwho-go --peer bin/devwho --report /tmp/devwho-go-conformance.json`: PASS, 62 tests with one intentional Bash skip of the Zsh-only attribute test. Includes shared literal dotenv/export/lifecycle cases, 55 configuration vectors, parsed cross-core state, runtime pair order and appendages, shell lifecycle, real Git/SSH, redacted doctor results, process argv/status/signals, private initialization, unchanged dirty repository/remotes/branches, and executable pinning.
- Fresh copied executable ran Bash and Zsh activate/switch/restore plus child execution with a dedicated PATH containing Bash, Zsh, Git, SSH and env, with Python, Python3 and Go absent.
- `CGO_ENABLED=0 go build -trimpath`: standalone static Linux executable; `ldd` reported `not a dynamic executable`. `go version -m` reported the pinned TOML module and checksum, `CGO_ENABLED=0`, `GOOS=linux`, and `GOARCH=amd64`.

No macOS/Bash 3.2, Linux ARM64, or live account authentication was executed locally. Those remain platform/integration coverage gaps until CI or an authorized environment verifies them. Independent Rust and Bash cores now exist. The final shared CI run exercises peer restoration state across all four implementations; check its recorded report for that revision. Development archives include checksums and full notices. A local Debian 13 container without Python or compilers passed the shared runtime fixtures, Bash/Zsh restoration, real Git replay, and the optional setup read/write operations. No tagged release is implied.

## Optional setup frontend

- `go test -tags setup ./...`: PASS, including true independent writer processes competing on one revision (one success, one stale rejection), exact backups and 0600/0700 modes, safe path refusals, missing-file creation, bilingual cancel/save, strict JSON/schema rejection, redaction, ordered special-string round trips, and retained advanced/unrelated fields.
- `go vet -tags setup ./...`: PASS.
- `CGO_ENABLED=0 go build -tags setup -trimpath -o /tmp/devwho-toolchains/devwho-setup .`: standalone optional binary. Runtime core excludes storage/UI code using build tags.
- Fresh copied setup binary performed JSON creation/replacement, redacted reads, Chinese cancellation, English save, and explicit value reads with PATH containing only Bash and the setup executable (Python/Python3/Go absent). Caller profile marker remained unchanged. `ldd` confirmed the setup binary is static.
