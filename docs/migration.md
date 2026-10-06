# Use existing Git and GitHub CLI accounts

DevWho does not import or rewrite existing Git, SSH, or GitHub CLI configuration. Add profiles that point to the identities and credentials you already use, then activate them in a shell or child process.

## 1. Install and locate the configuration

Install DevWho from a checkout using the instructions in the [README](../README.md), then create a starter file:

```bash
devwho config init
devwho config path
```

The configuration is TOML. Edit the file created by `config init`, or add a profile to your existing configuration file.

## 2. Move Git identity values into profiles

Copy the name and email you currently use from `~/.gitconfig` or repository-local Git config into `[profiles.<name>.git]`:

```toml
version = 1

[profiles.personal.git]
name = "Jane Doe"
email = "jane.personal@example.test"

[profiles.work.git]
name = "Jane Doe"
email = "jane.work@example.test"
```

DevWho does not modify the old Git settings. While a profile is active, its Git runtime settings take precedence over saved config for identity. After `unsetdev`, Git again sees the shell baseline and the existing repository/global config. Explicit Git command-line settings retain Git's normal precedence.

Do not set persistent `GIT_AUTHOR_*` or `GIT_COMMITTER_*` variables for these profiles. Direct author or committer identity variables inherited by the shell can conflict with activation; DevWho reports the variable name and leaves it untouched. Remove such overrides from their source if you want profile activation to manage Git identity.

## 3. Reuse GitHub CLI credentials

GitHub CLI keeps authentication in its own config directory. Create a separate directory for each profile and log in through that profile:

```toml
[profiles.work.github]
hostname = "github.com"
expected_user = "your-work-login"
config_dir = "~/.config/devwho/github/work"
```

```bash
devwho exec work -- gh auth login --hostname github.com
devwho exec work -- gh auth status
```

Repeat with the appropriate profile and directory for each account. DevWho does not copy tokens or move an existing `gh` login. If you want to retain credentials already stored in the default GitHub CLI directory, keep using that directory for the corresponding profile or authenticate into the profile's configured directory. `GH_TOKEN` or `GITHUB_TOKEN` inherited by the shell conflicts with a GitHub profile and is not cleared by DevWho.

A successful `gh` account check verifies GitHub CLI identity only. It does not prove that Git HTTPS or SSH transport uses the same account.

## 4. Reuse an existing SSH key

If each Git account already has a separate SSH key, add the selected key path to that profile:

```toml
[profiles.work.git_ssh]
identity_file = "~/.ssh/id_ed25519_work"
identities_only = true
```

The referenced file must exist. DevWho uses this setting for Git operations through `GIT_SSH_COMMAND`; it does not alter `~/.ssh/config`, create keys, or manage an SSH agent. Existing standalone SSH workflows continue to use their existing configuration.

## 5. Initialize, activate, and verify

Choose the shell initialization line for the current shell:

```bash
eval "$(devwho init bash)"
# or: eval "$(devwho init zsh)"
```

Then activate and inspect the profile:

```bash
setdev work
devwho current
devwho doctor work --offline
```

`setdev` is local and does not authenticate over the network. Run `devwho doctor work` when you want DevWho to check the configured GitHub CLI login. `unsetdev` restores the baseline from before the shell's first DevWho activation; it does not switch to the previous profile. `devwho exec work -- COMMAND` applies the profile only to that command and its descendants, leaving the parent shell unchanged.

Keep your old Git and SSH configuration until you have tested the new profile in a disposable repository and confirmed that `unsetdev` restores the expected behavior.
