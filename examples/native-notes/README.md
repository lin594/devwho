# Native notes consumer (Go)

This is a small, real consumer of the proposed `DEVWHO_PROFILE` convention. It reads the process environment directly and implements its own account mapping and local notebook operation. It does not import DevWho code, read DevWho configuration/private state, or claim that the marker authenticates a user.

Adoption status: **reference consumer; no third-party adoption asserted.**

## Run

Use Go 1.23 or newer:

```sh
go run . --config ./notes.json status
go run . --config ./notes.json add 'remember this'
go run . --config ./notes.json list
DEVWHO_PROFILE=work go run . --config ./notes.json add 'work note'
```

`notes.json` is application-owned. Relative notebook paths are resolved beside that file; absolute paths are also accepted. Example:

```json
{
  "default_account": "personal",
  "accounts": {
    "personal": "personal-notes.txt",
    "work-account": "work-notes.txt"
  },
  "profiles": {
    "work": "work-account"
  }
}
```

An explicit `--account ID` takes precedence over `DEVWHO_PROFILE`, including a malformed or unmapped environment value. Otherwise missing or empty values use the app's configured default, while malformed labels and unknown mappings fail before a notebook operation. `status` reports the selected app account; it does not verify login or identity. Notes are plain local files and are written with owner-only initial permissions subject to the host OS policy. The profile label is treated as literal data, never as a path or command.

A dotenv loader can provide ordinary process environment data. For example, after creating a trusted `.env` containing `DEVWHO_PROFILE=work`, a host CLI can invoke:

```sh
../../bin/devwho --env-file .env --env-profile work exec work -- go run . --config ./notes.json add 'from dotenv'
```

The producer's dotenv file is not read by this app. Only the resulting process environment is consumed. The consumer test suite exercises the same language-neutral selection cases in [`conformance/native/selection.json`](../../conformance/native/selection.json).
