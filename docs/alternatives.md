# Alternatives

Reviewed on 2026-10-06 against primary project documentation. Project names can be ambiguous; the linked repositories identify the specific implementations compared. Features absent from their documentation are not assumed impossible.

| Tool | Documented application model | File mutation / binding | Generic env and child execution | Verification / guard |
|---|---|---|---|---|
| [Git includeIf](https://git-scm.com/docs/git-config) | Conditional Git config | Config files, commonly gitdir/repository binding | Git settings only; no developer-profile shell restoration | Git itself does not verify hosting login |
| [b4nd/git-profile](https://github.com/b4nd/git-profile) | Named Git identities | Local/global Git configuration; its README references v0.1.5 downloads | No generic developer env/exec interface documented | Current profile inspection |
| [erbilnas/git-persona](https://github.com/erbilnas/git-persona) | macOS menu-bar personas | Applies repository/global Git name/email/signing key | Git-specific GUI | Read-only Git previews; public repo is archived and points to Glaze |
| [orzazade/gitch](https://github.com/orzazade/gitch) | Git identities, SSH/signing and auto-switch rules | Repository/global settings, directory/remote rules | Shell prompt integration documented, rather than reversible developer env profiles | Audit, pre-commit identity guards and editor integration |
| [DevSwitch](https://devswitch.in/docs) / [repository](https://github.com/umesh-saini/DevSwitch) | Desktop/CLI profile and key management | Generated SSH host aliases, shared profile store | Profile-specific clone operation documented | SSH test, doctor and OAuth integration |
| [gh auth switch](https://cli.github.com/manual/gh_auth_switch) | Changes active account for a host | Authentication configuration in the selected gh config context | GH_CONFIG_DIR can separate contexts; Git author and generic env not managed | [gh auth status](https://cli.github.com/manual/gh_auth_status) |
| [direnv](https://github.com/direnv/direnv/blob/master/man/direnv.1.md) | Directory-bound environment loading | Approved .envrc files, shell hook | Arbitrary env, reversible unload and `direnv exec` | Trust/allow model for executable .envrc, not developer login checks |
| [git-context](https://github.com/techquestsdev/git-context) | YAML Git profiles, including GitLab-style transport configuration | Documentation says it owns ~/.gitconfig via include/includeIf | Arbitrary Git settings, rather than arbitrary process environment | Git-focused context inspection |

The release pages for some projects were not accessible during this review; no latest-version or maintenance claim is made from README download examples alone. Git Persona's archived status is explicitly stated by its repository. DevSwitch's public changelog search result references v1.0.3, but the changelog page could not be retrieved, so that is not treated as a verified latest release.

## DevWho capability boundary

| Dimension | v0.1 behavior |
|---|---|
| Git author / committer | Runtime config, actual Git checks; replay preserves original authors |
| Git SSH identity | Safely quoted GIT_SSH_COMMAND; no standalone SSH identity manager |
| GitHub account | Separate GH_CONFIG_DIR/GH_HOST; explicit live login verification |
| Commit signing | Runtime configuration only; no key lifecycle or trust verification |
| Repository / directory binding | None; folders and saved remotes are retained |
| Per-shell / simultaneous profiles | Explicit profiles in independent process environments |
| Global mutation | None during activation, exec or inspection; explicit config init creates a file |
| Arbitrary env | Literal strings and explicit unsets |
| Child execution | Profile-scoped exec with parent unchanged |
| Identity verification | Git consumers and optional gh API; transport authentication separate |
| Wrong-identity guard | Deferred; an optional local dirty-work handoff notice is not a policy guard |

## Differentiation

Environment scoping is not a new primitive: direnv and hand-written shell functions already provide substantial overlap. DevWho's narrower contribution is a small, explicit developer-profile interface combining shell baseline restoration, semantic Git/GitHub compilation, scoped execution and consumer diagnostics. It does not compete on key generation, GUI menus or directory automation.

The reviewed documentation does not establish a mature, widely adopted tool with precisely the same manual profile/restore/exec/doctor contract. This is a scoped observation, not a claim of uniqueness or an exhaustive market survey. Continued implementation is reasonable; evidence of a closer alternative should be recorded honestly.
