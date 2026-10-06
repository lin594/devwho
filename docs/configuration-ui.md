# Configure through prompts

[English](configuration-ui.md) | [简体中文](zh-CN/configuration-ui.md)

`devwho-setup` is an optional standalone Go program included in the Go distribution. It works without Python or a running core, and its saved profiles work with **any** DevWho core.

```sh
devwho-setup configure
# Chinese prompts:
devwho-setup --language zh-CN configure
```

Choose an existing profile or name a new one, enter Git name/email, optionally add GitHub CLI/SSH settings, and select defaults. Blank keeps an existing value. `-` clears an optional setting. Review the preview and explicitly save; cancelling or reaching end-of-input leaves the file untouched. The terminal form edits one profile at a time and retains unrelated profiles and advanced settings.

After saving, run `setdev PROFILE` in an initialized terminal. The editor does not change the current shell or any open window.

## Files, backups and other editors

The default file follows the core's configuration-path rules; `--config PATH` chooses another file. Saves validate the full profile schema, compare the revision originally read, and atomically write a private file. A sibling `.devwho-backups/` directory retains the exact previous bytes. The new file uses normalized formatting and drops comments; advanced values and Git pair ordering remain intact.

Two DevWho editors cannot silently overwrite each other's saved revision. External editors that ignore the cooperative lock can still race; close them or reread before saving. Configuration symlink writes are refused.

To restore, first retain the current file, select the intended private backup, then copy it back with mode 0600. Existing shell sessions continue to hold their own environment; initialize a fresh terminal or switch again after restoring.

## For another UI or automation

`read` returns a revision plus redacted configuration; `read --show-values` explicitly exposes values. `replace --if-revision HASH|missing` accepts raw schema JSON from stdin and uses the same validation/save operation as the form. It does not accept the redacted read envelope as a profile document. See the [complete machine interface and build instructions](../implementations/go/SETUP.md).

This is the first frontend, implemented as a portable terminal form. A richer TUI or GUI can call the same operations without becoming a mandatory runtime dependency or introducing a daemon.
