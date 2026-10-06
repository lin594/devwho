# Third-party notices

The compiled Go core includes code from the Go standard library (Go project BSD-style license) and the following module:

| Module | Pinned version | License | Source |
|---|---|---|---|
| github.com/pelletier/go-toml/v2 | v2.3.1 | MIT | https://github.com/pelletier/go-toml/tree/v2.3.1 |

The TOML license is reproduced in `licenses/go-toml-LICENSE`. The Go license is reproduced in `licenses/Go-LICENSE` and available at https://go.dev/LICENSE. Go is a build dependency, not an interpreter required at runtime. `go.mod`/`go.sum` contain the complete external module graph; this module has no transitive module requirements. `go mod verify` checks downloaded source against recorded sums and Go's checksum database verifies module downloads by default.

The pinned TOML parser is maintained upstream and supports TOML 1.0 syntax, duplicate detection, and complete parsing. We first decode and validate the schema, then iterate its AST to preserve insertion order, including nested inline and dotted-key encodings.
