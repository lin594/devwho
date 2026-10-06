# Troubleshooting

[English](troubleshooting.md) | [简体中文](zh-CN/troubleshooting.md) · [Documentation](README.md)

Start with `devwho --version`, `devwho current --verbose`, and `devwho doctor --offline`. When asking for help, share the command and relevant error with fictional names and paths. Do not paste credentials or your whole environment.

## `devwho: command not found`

For the single-file installation, try `~/.local/bin/devwho --version`. If that works, add `export PATH="$HOME/.local/bin:$PATH"` to your current shell and its startup file. If the file does not exist, complete [installation](getting-started.md). For pipx, check the directory reported by `pipx environment`.

## `setdev: command not found`, but `devwho` works

`setdev` changes the current shell, so it must be loaded as a shell function. Run `eval "$(devwho init bash)"` in Bash, or `eval "$(devwho init zsh)"` in Zsh. If initialization reports a missing configuration, run `devwho config init`, edit the file, then initialize again. For future terminals, follow the [startup steps](getting-started.md#make-it-available-in-new-terminals).

## `config init` says the file already exists

That prevents overwriting your settings. Run `devwho config path` and edit the existing file. Do not delete a working configuration just to repeat the tutorial.

## Unknown profile, or `setdev` needs a profile

Run `devwho list` and use one of those names. `setdev work` selects an explicit profile; bare `setdev` needs `settings.shortcut_profile`. The shared-machine example is in [Everyday workflows](use-cases.md).

## `current` says `none`, or `unsetdev` returns an unexpected identity

`none` means DevWho has no active profile marker. Git can still have a name and email in its existing configuration. `unsetdev` restores the environment from before this shell's first activation. A configured default becomes that baseline; a child shell's baseline is the environment it inherited. See [child shells](use-cases.md#start-a-child-shell).

## GitHub login returns 401, or the account is different

Check the GitHub config directory shown by `devwho current --verbose`. A fresh per-profile directory does not contain the login you used in a different directory. Verify your existing `gh api user --jq .login` context, then either point the profile to that directory or log into its separate directory. [Account setup](accounts.md) explains both options.

`devwho doctor work` checks the current environment against `work`; it does not switch first. Run `setdev work` before the check.

## `doctor --offline` reports `UNVERIFIED` and exits with code 2

This is expected for a profile containing GitHub settings: the account needs an API request to be verified. Run `devwho doctor` when online. For a Git-only profile, no GitHub API check is needed. Exit code 1 means a failure or mismatch; 0 means all configured checks passed.

## A conflicting environment variable blocks activation

Persistent `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, or `GIT_COMMITTER_EMAIL` can override commit identity. `GH_TOKEN` and `GITHUB_TOKEN` can override a gh profile. Find where the named variable is set and decide whether that override is still intended; DevWho leaves it untouched and reports only its name. Avoid putting those identity overrides in startup files when using DevWho profiles.

Readonly or specially typed shell variables can also prevent a switch. Use a normal exported string for a managed setting, or open a fresh shell with the conflicting customization removed. Failed preflight checks leave the identity unchanged.

## SSH key or GitHub config path is rejected

Use an absolute path, `~`, or a path beginning with `~/`. Relative paths depend on the working directory and are rejected, as are `~other-user` paths. The selected SSH key must be an existing file. Home-relative paths use the effective HOME after switching, which must itself be nonempty and absolute.

## Git still shows an unexpected name or email

Check `devwho current --verbose` and `devwho doctor --offline` in the same terminal that runs Git. Check `git --version` is at least 2.31. Explicit `git -c ...`, an explicit author option, or tool-specific environment settings can override a profile. Rebase and cherry-pick intentionally keep the original commit author while using your current identity as committer.

## `unsetdev` refuses to restore Git runtime configuration

Another tool changed the original runtime configuration or DevWho's managed portion. DevWho refuses to guess which values to remove. Undo that external edit if you know it, or open a fresh, independent terminal. Runtime settings appended after activation are supported; arbitrary rewrites of existing entries are not.

## VS Code, Copilot, or another application still uses the old account

Already-running applications keep their existing environment and may have their own login system. v0.1 has no VS Code window/account isolation integration. Use Git commands in the selected terminal; do not assume `code .` switches Source Control, Copilot, or browser sessions.

## GitHub rejects a workflow-file push

If Git uses gh credentials and GitHub reports a missing `workflow` scope, check or refresh the intended gh login's permissions. This is separate from selecting a Git author. See [HTTPS authentication](accounts.md#use-git-over-https).

Still stuck? [Open an issue](https://github.com/lin594/devwho/issues) with your OS, shell, Python/Git versions, the command, and a minimal example. For a security issue, use [private reporting](../SECURITY.md).
