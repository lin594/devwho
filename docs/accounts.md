# Accounts and authentication

[English](accounts.md) | [简体中文](zh-CN/accounts.md) · [Documentation](README.md)

Start here after the Git-only [first run](getting-started.md). Add only the integrations you use.

## Three different identities

| What you want to choose | What controls it | How to check |
|---|---|---|
| The name/email recorded on a Git commit | The profile's `[git]` settings | `devwho current --verbose` or `git var GIT_AUTHOR_IDENT` |
| The account used by `gh` commands | GitHub CLI login in the profile's config directory | `devwho doctor` or `gh api user --jq .login` |
| The account authorized to fetch/push | Your Git SSH key or HTTPS credential helper | Verify with that transport and a repository you have permission to use |

Changing the commit email does not log you into another account. A successful `gh` check does not prove that Git's SSH or HTTPS authentication uses that account.

## Use an existing GitHub CLI login

First, in a terminal where your existing `gh` login works, check its actual account:

```sh
gh api user --jq .login
```

If it is the account you want for `work`, point that profile to the existing configuration directory. The usual Linux/macOS directory is `~/.config/gh`; use the actual location if you already override `GH_CONFIG_DIR` or `XDG_CONFIG_HOME`.

```toml
[profiles.work.github]
hostname = "github.com"
expected_user = "your-work-login"
config_dir = "~/.config/gh"
```

Replace `your-work-login` with the account returned by GitHub. Then run:

```sh
setdev work
devwho doctor
```

You do not need to log in again if that directory already has a valid login for the expected account. Keep different people's profiles pointed at different directories; changing the active login in a shared directory affects every profile using it.

## Add another GitHub CLI account

For a new context, choose a separate location:

```toml
[profiles.personal.github]
hostname = "github.com"
expected_user = "your-personal-login"
config_dir = "~/.config/devwho/github/personal"
```

Then complete the one-time browser authorization as that person:

```sh
devwho exec personal -- gh auth login --hostname github.com --git-protocol https --web
devwho exec personal -- devwho doctor
```

If you already use GCM or another Git credential helper, choose **No** when gh asks whether to configure Git authentication. DevWho selects the gh context; gh manages its credentials. Tokens are not part of a DevWho profile.

Profiles containing GitHub settings reject inherited `GH_TOKEN` or `GITHUB_TOKEN`, since those can override the selected directory. See [Troubleshooting](troubleshooting.md) if the account differs or a login returns 401. The [GitHub CLI environment reference](https://cli.github.com/manual/gh_help_environment) describes these selectors.

## Select a key for Git over SSH

If your account already has an SSH key registered with the host:

```toml
[profiles.work.git_ssh]
identity_file = "~/.ssh/id_ed25519_work"
identities_only = true
```

Use an existing file's absolute path or a path beginning with `~/`. DevWho checks that the file exists and supplies it to Git's SSH command. It does not create/register keys, manage passphrases, or modify `~/.ssh/config`. A profile change does not affect standalone `ssh` commands. Other keys listed in your SSH configuration can also affect authentication, so check the account used by the transport itself.

## Use Git over HTTPS

Continue using a credential helper such as GCM. DevWho does not automatically reconfigure HTTPS authentication or convert saved remotes. A helper-specific selector can be added as a runtime Git setting:

```toml
[profiles.work.git.config]
"credential.https://github.com.username" = "your-work-login"
```

This example assumes GCM is already installed and configured. [GCM's multiple-account guide](https://github.com/git-ecosystem/git-credential-manager/blob/main/docs/multiple-users.md) explains its account selector. A username embedded in a saved remote, other helper configuration, or host policy may affect the result. Verify the actual transport before relying on it; use a test repository you control for a write check.

For repositories containing GitHub Actions workflow files, a gh OAuth login used as a Git credential helper also needs the `workflow` scope. Reuse an existing verified login with the required scope, or request it with `gh auth refresh --hostname github.com --scopes workflow` in the intended account context. This is a GitHub permission, separate from a commit's name and email.

## Check before working

```sh
setdev work
devwho current --verbose
devwho doctor
```

`OK` means the checks performed matched. `UNVERIFIED` means a required check could not complete, for example because a local tool is unavailable or an online check was skipped; `FAIL` means a mismatch or local configuration problem was found. For the exact checks and exit codes, see [Reference](reference.md).
