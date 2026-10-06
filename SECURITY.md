# Security

[简体中文](SECURITY.zh-CN.md)

DevWho v0.1.0-rc.1 is an early pre-release candidate. No formal security audit or credential isolation is implied.

Profiles are trusted local configuration. Generic environment values are quoted as literal shell data. A child tool can still interpret environment variables or Git config as executable settings. DevWho does not sandbox commands, manage secrets, or protect two developers from each other within one OS account.

State stays in the calling shell; credentials stay with SSH agents, GitHub CLI and credential helpers. `show` hides custom environment values. Doctor suppresses raw subprocess errors to avoid exposing credentials. Config initialization creates a private file exclusively and refuses an existing destination, including a symlink.

## Report a vulnerability

Private vulnerability reporting is enabled for this repository. Use the [private vulnerability reporting page](https://github.com/lin594/devwho/security/advisories/new) to share a report with the maintainers.

If GitHub says private reporting is unavailable, open an issue that contains no vulnerability details and ask the maintainers for a private reporting channel. Do not put exploit steps, affected secrets, tokens, or keys in that issue. The maintainers are responsible for enabling private reporting and responding through a private channel.

For ordinary bugs and feature requests, use the [issue tracker](https://github.com/lin594/devwho/issues).
