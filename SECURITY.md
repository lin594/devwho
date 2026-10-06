# Security

DevWho v0.1 is an unreleased project. No formal security audit or credential isolation is implied.

Profiles are trusted local configuration. Generic environment values are quoted as literal shell data. Nevertheless, a child tool can interpret environment variables or Git config as executable settings. DevWho does not sandbox commands, manage secrets, or protect two developers from each other within one OS account.

State stays in the calling shell; credentials stay with SSH agents, GitHub CLI and credential helpers. `show` hides custom env values. Doctor suppresses raw subprocess errors to avoid exposing credentials. Config initialization creates a private file exclusively and refuses an existing destination, including a symlink.

Treat shell quoting bugs, partial activation, environment leakage and unintended file mutation as security-relevant. Reproduce using fictional values and temporary files. Do not submit actual tokens or keys in issues, logs or pull requests.

Before public release, configure a private vulnerability reporting channel in the repository hosting service. Until one exists, avoid publicly disclosing a live exploit or secret; arrange a private contact with the repository maintainer. No maintainer email is invented here.
