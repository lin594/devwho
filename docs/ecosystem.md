# One identity context, two ways to support it

[English](ecosystem.md) | [简体中文](zh-CN/ecosystem.md) · [Overview](../README.md)

DevWho's goal is simple: choose a developer context once, and let the tools started from that terminal use it. The context could mean personal work, a client, or one person on a shared computer. Project directories and installed tools can stay where they are.

There are two independent parts to that goal:

| Part | How it works | Status |
|---|---|---|
| **Native environment convention** | An application reads the same small set of `DEVWHO_*` variables and selects its own configured account. Any launcher can provide those variables. | Proposed; no native application integration is shipped here. |
| **Compatibility core** | DevWho converts a saved profile into the interfaces existing applications already understand, such as Git runtime configuration and `GH_CONFIG_DIR`. | Implemented in Python; complete Go, Rust, and Bash alternatives are planned. |

An application supporting the convention does not need to import a Python module, install DevWho, read DevWho's TOML file, or call a daemon. A user of the compatibility core will eventually choose **one implementation** suitable for their machine; they will not need all four languages installed.

## The convention comes first

Proxy environment variables are a useful model: an application reads a shared convention and implements the behavior itself. The convention and its implementations are separate. Exact spelling and precedence still matter—for example, curl deliberately accepts only lowercase `http_proxy` for HTTP. [curl's explanation](https://everything.curl.dev/usingcurl/proxies/env.html)

The initial DevWho draft uses just one variable:

| Variable | Meaning |
|---|---|
| `DEVWHO_PROFILE` | The selected local context, such as `personal` or `work`. |

Applications map that context to their own existing accounts. For example, `work` could select a company's Git hosting account in one tool and a company organization in another. Those mappings belong to the applications; passwords and tokens stay in their existing credential stores. The same profile label does not imply the same username at every service.

We do not introduce a separate `DEVWHO_<APP>_USER` family, a universal token, or a shared credentials directory. Git author name and email are not universal login identifiers. More fields should be added only when a concrete consumer needs them and their cross-application meaning is clear.

The [environment specification](../spec/environment-v1.md) defines spelling, validation, inheritance, missing values, precedence, and account-selection failures. **It is a draft.** Current v0.1 already exports the profile marker; future native consumers can read it directly. Actual support requires an application's own account mapping and normal authentication, not merely a marker in the environment.

One stable selector does not need a companion version variable. Keep its meaning stable, review extensions independently, and retain configuration-file versions only where a parser needs them. Neither TOML nor Python is required to supply the marker: an ordinary dotenv-aware launcher can load `DEVWHO_PROFILE=work`. The current core still reads TOML; optional dotenv loading is a separate [input-format proposal](configuration-formats.md), not an implemented feature.

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

Native and adapted tools can coexist in one terminal. A future core can publish the shared convention and keep the existing adapters for applications that still need them. Removing an adapter requires actual consumer support and a migration path, not merely publishing a specification.

## Python is an implementation choice

The current Python implementation requires Python 3.11+. A zipapp bundles the application, not the Python interpreter. Users without Python cannot run it today.

Go, Rust, and Bash are planned as **independent implementations of the complete current compatibility core**. Each must read the same configuration, expose the same commands, and preserve the same switching and recovery behavior. They are not SDKs, frontends that invoke Python, or limited Git-name switchers.

Go and Rust will target downloadable executables so end users need neither Python nor a compiler. Bash will target a complete script implementation with its runtime requirements stated explicitly. In particular, it must handle the existing TOML syntax and state restoration correctly. See the [implementation plan](../implementations/README.md) for tradeoffs and tracked work.

The [compatibility contract](../spec/compatibility-core-v1.md) is separate from the native environment draft. Ports can deliver Python-free use of today's tools without waiting for applications to adopt the future convention.

## What can I do now?

- **Use DevWho:** follow [Getting started](getting-started.md); Python is currently required.
- **Work on a Python-free core:** choose a [full implementation task](../implementations/README.md) and use the common compatibility contract.
- **Add native support to your application:** review the draft with us first. Use your language's environment API; no DevWho SDK is required. Resolve the profile through your own account configuration and verify authentication normally.
- **Propose a new shared variable:** explain its meaning across more than one application, its missing-value behavior, and how it avoids carrying secrets or creating conflicting sources of truth.
