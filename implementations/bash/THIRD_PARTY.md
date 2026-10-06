# Third-party source and runtime inventory

This implementation invokes no Python, Python-built helper, or other DevWho
implementation. Bash owns process execution, CLI and shell integration; `core.jq`
owns the independently maintained schema, compilation, state and transition rules.
Perl adapters decode TOML/JSON/dotenv and canonicalize filesystem paths. The small launcher also captures the original OS environment through an unlinked private descriptor before Bash can normalize SHLVL/PWD; a child-exec adapter transports the calculated complete environment and argv to exec, preserving unusual variable names and exit/signals. These adapters contain no profile/transition policy. No profile
file or profile value is sourced or evaluated.

## Runtime

- Bash >= 3.2, installed at `/bin/bash`; generated integration supports Bash and Zsh.
- jq >= 1.6 (MIT), for JSON values, validation, reversible transformations and
  shell quoting. Install from your OS package manager (`apt install jq`,
  `brew install jq`, or equivalent).
- Perl >= 5.18 (`/usr/bin/perl` for the direct launcher, or explicitly invoke it
  with your Perl interpreter) and its standard modules: JSON::PP, Cwd, File::Spec, FindBin,
  Scalar::Util, Encode, Carp, Data::Dumper, Math::BigInt, Math::BigFloat, charnames,
  Exporter, File::Temp, Fcntl, File::Path, File::Basename, Errno. No CPAN installation is needed.
- Standard OS utilities: `cat`, `dirname`, `chmod` (installer), `cp` (installer), `head`,
  `ln` (installer), `mkdir`, `mktemp`, `mv`, `rm`, `sleep`, `wc`.
- Git is required by Git consumers and Git diagnostics. Missing Git is an
  unverified doctor result; ordinary environment activation works without Git.
- `gh` is optional and is called only by explicit online `doctor`. SSH is a
  consumer of the generated `GIT_SSH_COMMAND`, never called by activation.

## Vendored TOML parser

`vendor/TOML/Tiny/{Parser,Tokenizer,Grammar}.pm` derives from **TOML::Tiny 0.22**,
by Jeff Ober and contributors, published by Olaf Alders.

- Upstream: <https://github.com/sysread/TOML-Tiny>
- Source archive: <https://cpan.metacpan.org/authors/id/O/OA/OALDERS/TOML-Tiny-0.22.tar.gz>
- SHA-256: `d48064476740f2e9232afba2e0f61a82641b8c3b66a71c398ba1632fa4614b65`
- License: Artistic-1.0-Perl OR GPL-1.0-or-later (the same terms as Perl 5).
  Complete upstream license: [`vendor/LICENSE.TOML-Tiny`](vendor/LICENSE.TOML-Tiny).

Only the decoder modules are included; the writer and optional DateTime modules
are unnecessary. The wrapper rejects TOML dates and floats because no field in
DevWho's v1 schema permits either type. Booleans retain JSON boolean type.

Local modifications are maintained in-tree and reviewed with the parser source:

1. Insertion-ordered table hashes (`vendor/DevWho/Ordered.pm`) preserve Git config
   key order when encoding JSON. jq uses `to_entries` without sorting runtime keys.
2. Reject duplicate empty keys, mutation of inline tables, dotted-table
   redefinitions, and arrays of tables (not permitted anywhere by this schema).
3. Restrict Unicode escapes to hexadecimal digits and Unicode scalar values;
   permit unassigned code points/noncharacters as TOML does; restrict bare keys
   to ASCII.
4. Correct multiline literal handling, the immediately following opening newline,
   line-continuation whitespace, and CRLF normalization.

The small `DevWho::Ordered` module and the parser adapter scripts are DevWho project
code, covered by the repository license. jq and Perl are system dependencies,
not bundled binary artifacts. Release provenance and platform coverage must be
reported separately from a source-tree conformance run.
