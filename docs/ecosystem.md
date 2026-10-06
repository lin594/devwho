# One identity context, two ways to support it

[English](ecosystem.md) | [简体中文](zh-CN/ecosystem.md) · [Overview](../README.md)

DevWho's goal is simple: choose a developer context once, and let the tools started from that terminal use it. The context could mean personal work, a client, or one person on a shared computer. Project directories and installed tools can stay where they are.

There are two independent parts to that goal:

| Part | How it works | Status |
|---|---|---|
| **Native environment convention** | An application reads the same small set of `DEVWHO_*` variables and selects its own configured account. Any launcher can provide those variables. | Proposed; no native application integration is shipped here. |
| **Compatibility core** | DevWho converts a saved profile into the interfaces existing applications already understand, such as Git runtime configuration and `GH_CONFIG_DIR`. | Independent Python, Go, Rust, and Bash implementations follow the shared contract. |

An application supporting the convention does not need to import a Python module, install DevWho, read DevWho's TOML file, or call a daemon. A user of the compatibility core will eventually choose **one implementation** suitable for their machine; they will not need all four languages installed.

## The convention comes first

Proxy environment variables are a useful model: an application reads a shared convention and implements the behavior itself. The convention and its implementations are separate. Exact spelling and precedence still matter—for example, curl deliberately accepts only lowercase `http_proxy` for HTTP. [curl's explanation](https://everything.curl.dev/usingcurl/proxies/env.html)

The initial DevWho draft uses just one variable:

| Variable | Meaning |
|---|---|
| `DEVWHO_PROFILE` | The selected local context, such as `personal` or `work`. |

Applications map that context to their own existing accounts. For example, `work` could select a company's Git hosting account in one tool and a company organization in another. Those mappings belong to the applications; passwords and tokens stay in their existing credential stores. The same profile label does not imply the same username at every service.

We do not introduce a separate `DEVWHO_<APP>_USER` family, a universal token, or a shared credentials directory. Git author name and email are not universal login identifiers. More fields should be added only when a concrete consumer needs them and their cross-application meaning is clear.

The [environment specification](../spec/environment-v1.md) defines spelling, validation, inheritance, missing values, precedence, and account-selection failures. **It is a draft.** All current cores export the profile marker; native consumers can read it directly. Actual support requires an application's own account mapping and normal authentication, not merely a marker in the environment.

One stable selector does not need a companion version variable. Keep its meaning stable, review extensions independently, and retain configuration-file versions only where a parser needs them. Neither TOML nor Python is required to supply the marker: an ordinary dotenv-aware launcher can load `DEVWHO_PROFILE=work`. All current cores read complete TOML profiles and support explicit [literal dotenv input](../spec/dotenv-v1.md); dotenv selects one generic-environment profile and does not merge with TOML.

## How existing tools work today

Git and GitHub CLI are supported through their existing interfaces. This repository does not claim that they read the proposed DevWho convention.

```text
Today
  saved TOML profile → compatibility core → Git / gh environment → existing tool

Proposed native support
  a context selector → shared DEVWHO_* variables → application's own account mapping
```

| Current adapter | What the core supplies |
|---|---|
| Git commit identity and signing | `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_*`, `GIT_CONFIG_VALUE_*` |
| Git SSH key selection | `GIT_SSH_COMMAND` |
| GitHub CLI context | `GH_CONFIG_DIR`, `GH_HOST`; `doctor` can verify the real login |
| Other existing applications | Literal, explicitly configured environment values and unsets |

These application-specific variables are compatibility outputs, not additions to the proposed shared convention. The core preserves unrelated settings, including proxy variables. It does not repeatedly rewrite repository or global configuration.

Native and adapted tools can coexist in one terminal. A launcher can provide the shared convention while existing adapters continue to serve applications that still need them. Removing an adapter requires actual consumer support and a migration path, not merely publishing a specification.

## The compatibility core has multiple implementations

Python 3.11+ remains one option. Independent Go, Rust, and Bash cores now implement the same compatibility contract, so users can choose one core for their machine. Go and Rust executables run without Python or a compiler; Bash requires Bash 3.2+, jq 1.6+, and Perl 5.18+. See the [implementation guide](../implementations/README.md) for source builds, CI artifacts, checksums, and current platform evidence. CI downloads require GitHub sign-in; artifacts are development builds, and there is no tagged release. The optional Go configuration frontend provides English/Chinese forms and writes the shared TOML configuration. It does not change shell identity.

The [compatibility contract](../spec/compatibility-core-v1.md) is separate from the native environment draft. Ports can deliver Python-free use of today's tools without waiting for applications to adopt the future convention.

## What can I do now?

- **Use DevWho:** follow [Getting started](getting-started.md) and choose one [core implementation](../implementations/README.md).
- **Use the configuration form:** see the optional [configuration frontend](configuration-ui.md).
- **Add native support to your application:** review the draft; the repository includes a reference consumer example, but it has no claim of third-party adoption.
- **Add native support to your application:** review the draft with us first. Use your language's environment API; no DevWho SDK is required. Resolve the profile through your own account configuration and verify authentication normally.
- **Propose a new shared variable:** explain its meaning across more than one application, its missing-value behavior, and how it avoids carrying secrets or creating conflicting sources of truth.
