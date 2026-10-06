# DevWho environment convention — draft revision 1

[English](environment-v1.md) | [简体中文](environment-v1.zh-CN.md) · [Why this exists](../docs/ecosystem.md)

**Status: proposal, not an established industry standard or a claim of native application adoption.** This is a language-independent interface between a context producer and an application. The revision number versions this document; it is not an environment variable or a value applications negotiate.

Discussion: [RFC #1](https://github.com/lin594/devwho/issues/1).

## 1. Scope and terms

A **producer** selects a context and places it in a process environment. It could be a shell function, an IDE, a CI runner, a dotenv loader, or any implementation of DevWho. No particular language, file format, SDK, daemon, or core installation is required.

A **consumer** is an application that explicitly implements this convention. It maps the context to its own account or organization configuration. This repository's Git and gh adapters are not native consumption of the draft.

A **profile** is a case-sensitive local context label, not a globally unique identity, service username, OS user, or proof of authentication. Producers sharing one user's application mappings must agree on label meanings: `work` must not mean two different people in that same scope. Renaming a label requires updating the relevant mappings.

## 2. Complete initial variable set

| Variable | Value | Meaning |
|---|---|---|
| `DEVWHO_PROFILE` | Nonempty ASCII label matching `[A-Za-z0-9][A-Za-z0-9_.-]*`, case-sensitive | Selected local context, such as `personal`, `work`, or `client-a`. |

Use canonical uppercase spelling. There are no aliases, shell expansions, lists, or interpolation rules. The label is literal data; consumers must not interpret it as a pathname, command, URL, or request to create an account.

A future native consumer could receive the value through an ordinary environment:

```sh
export DEVWHO_PROFILE=work
```

All four compatibility cores export this marker on activation. A native consumer can use it without another marker. Exporting it manually does not invoke today's Git/gh adapters, and this repository does not claim that those tools already read it.

| Additional candidate | Decision |
|---|---|
| `DEVWHO_SPEC_VERSION` | Unnecessary for one stable opaque selector. Document revisions and file-format versions are separate from the process interface. |
| `DEVWHO_CONTEXT` | Duplicates the profile selector; a second identifier needs a demonstrated use case. |
| Universal name/email | Commit authors, display names, and authenticated accounts are different concepts. Keep attribution in the relevant app/adapter configuration. |
| Provider-specific usernames | Keep them in application mappings or adapter settings rather than inventing a variable family per app. |
| Tokens, passwords, private keys | Never part of this convention. |
| Shared app data/config directory | Apps retain their own configuration and credential stores. |

## 3. Reading and selecting

For operations needing an account, a native consumer follows these rules:

1. An explicit account choice for the operation, such as a command-line option or deliberate in-app selection, takes precedence. Do not mix that account with another profile's credentials or metadata.
2. Otherwise, read `DEVWHO_PROFILE`. Missing or empty means no shared context is selected: preserve the application's ordinary behavior. This agrees with the current CLI's `none` display. Whitespace-only or otherwise malformed nonempty labels are invalid selections, not empty values.
3. Resolve a valid nonempty label through the application's own mapping. A missing mapping or malformed label requires an explicit user choice or a clear error before an identity-dependent operation. Never silently choose a default account because the requested profile is unknown. Unrelated help/read-only commands need not be blocked.
4. Use the application's normal authentication flow and verify the actual account as appropriate. The marker is never authentication proof or authorization to gain extra privileges.

For example, an app might configure `work → existing-account-entry-42`. This is illustrative data, not a prescribed mapping-file format. Different apps can map the same label to different providers and hosts without another environment-variable family.

Show the resolved account in the application's usual status UI or diagnostics. Echoing the profile does not verify a login. Reading a producer's TOML or dotenv file to discover a protocol version must not be required.

## 4. Inheritance and restoration

Normal process inheritance applies. A producer changes its environment or that of a process it launches. Existing sibling processes and editor windows do not change. An application captures the context at startup unless it offers its own explicit account-switching UI; this draft defines no IPC, polling, or global current user.

Validate before activation. A reversible shell producer records missing, empty, and nonempty values distinctly, even though consumers treat the first two as no selection. On deactivation, restore exactly those previous values. Restore adapter outputs or future fields dropped by a new context instead of leaving stale identity information behind. Readonly/unwritable variables must cause failure before any managed variable changes.

Manually exporting a variable or loading dotenv supplies environment data. It does not automatically provide baseline snapshots, atomic switching, startup defaults/shortcuts, or adapter checks.

## 5. Adapters and explicit overrides

The convention selects context; it does not replace explicit application flags, authenticate users, or mandate changing Git authors during rebase/cherry-pick. Preserve normal authorship and replay behavior.

When native support and adapters coexist, applications must document their environment-override precedence. A conflicting token or account-specific setting must be diagnosed or resolved through an explicit account choice, not silently mixed with the context. The current core's exact rules are in the [compatibility contract](compatibility-core-v1.md).

## 6. Evolution without a mandatory version variable

Keep `DEVWHO_PROFILE` an opaque local selector. Do not later reinterpret it as JSON, a path, a service username, or serialized credentials. This narrow stable meaning makes an unversioned interface reasonable.

New optional features need documented names, value grammar, absence behavior, conflict rules, and consumer tests. Unknown optional variables may be ignored only when that cannot change required identity or security behavior. A producer cannot assume consumer support merely because it set a variable.

A genuinely incompatible or required capability needs a separately reviewed interface and explicit support detection. Do not overload the selector or hide a breaking process-interface change behind a local file version. This draft does not preallocate speculative capability flags.

| Version domain | Where it belongs |
|---|---|
| Convention documentation | Specification revision and change history. |
| Current TOML profile schema | Existing `version = 1`, interpreted only by its core/parser. |
| Internal restoration transport | Private state version used by compatible cores. |
| Optional dotenv core input | Its separate parser contract; plain key/value input need not export a version key. |

Docker Compose's top-level `version` is now obsolete and does not select its validation schema. A version field alone does not define compatibility. DevWho retains its existing TOML version because its parser actually validates it; removing that requirement needs a separate migration. [Docker documentation](https://docs.docker.com/reference/compose-file/version-and-name/)

## 7. Trust and privacy

Treat environment input as untrusted selection metadata. Parse data; never evaluate/source it or automatically open files/load code from a label. Elevated processes and services follow their own environment trust policy rather than trusting a client-supplied marker.

Labels inherit into children and can appear in diagnostics; keep secrets and sensitive personal data out of them. Shared OS accounts are not isolated by this convention. Consumers still enforce their own access controls.

## 8. Variables outside the convention

| Name | Current role |
|---|---|
| `DEVWHO_CONFIG` | Selects the compatibility CLI's TOML file. Native apps must not need it. |
| `__DEVWHO_STATE` | Non-exported internal shell restoration state, not an app integration API. |
| `GIT_CONFIG_*`, `GIT_SSH_COMMAND`, `GH_CONFIG_DIR`, `GH_HOST` | Adapter outputs defined by the corresponding tools. |
| `HTTP_PROXY`, `http_proxy`, other unrelated variables | Preserved unless explicitly configured otherwise. |

The current core reserves `DEVWHO_*` in generic profile env settings and supplies the marker itself. This draft is separate from the installed runtime and its file loaders. The four cores implement explicit [dotenv v1 input](dotenv-v1.md), which does not change the native convention.

## 9. Review and adoption gates

- Agree on stable selector meaning, grammar, absence/error behavior, explicit-account precedence, and unknown mappings.
- Add language-neutral consumer cases, including environments from today's core and ordinary dotenv loaders.
- The repository now includes a stdlib-only [reference consumer example](../examples/native-notes/); it is illustrative and does not establish third-party adoption. Continue to validate independently maintained consumers without importing a core or reading its private state/config files.
- Publish adoption status backed by actual integrations; adapter support alone is not native adoption.
- Assess extensions against real consumer needs, with tests and a compatibility rationale.

Full core ports and producer file formats can evolve independently of native application adoption.
