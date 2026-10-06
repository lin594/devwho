# 命令与配置参考

[English](../reference.md) | [简体中文](reference.md) · [文档首页](README.md)

本页用于查找配置项和精确行为。首次设置请从[入门指南](getting-started.md)开始。

## 命令

| 命令 | 用途 |
|---|---|
| `devwho list` | 列出已配置的 身份配置 名称。 |
| `devwho show PROFILE` | 显示 身份配置 元数据；自定义环境变量的值会隐藏。 |
| `devwho current [--verbose]` | 显示当前 身份配置；可选显示生效的 Git 身份和 CLI 路径。 |
| `devwho doctor [PROFILE] [--offline]` | 将实际工具身份与 身份配置 对照。 |
| `devwho exec PROFILE -- COMMAND ...` | 为一条命令及其子进程选择 身份配置。 |
| `devwho config path` | 打印当前选用的配置文件路径。 |
| `devwho config init` | 创建私有示例配置；若文件已存在则拒绝覆盖。 |
| `devwho init bash` / `devwho init zsh` | 打印供当前 shell 执行的集成代码。 |
| `setdev PROFILE` | 在已初始化的 shell 中激活 身份配置。 |
| `setdev` | 激活已配置的 `settings.shortcut_profile`。 |
| `unsetdev` | 恢复此 shell 的原始 初始状态。 |

使用 `devwho --config /absolute/path/config.toml COMMAND` 可为单条命令指定其他配置文件。

## 身份配置 配置

配置默认位于 `$XDG_CONFIG_HOME/devwho/config.toml`，或 `~/.config/devwho/config.toml`。`DEVWHO_CONFIG` 或 `devwho --config PATH ...` 可选择其他文件。

```toml
version = 1

[profiles.personal.git]
name = "Jane Doe"
email = "jane@example.com"

[profiles.personal.env]
TOOL_PROFILE = "personal"

[profiles.work.git]
name = "Jane Doe"
email = "jane@company.example"

[profiles.work.env]
TOOL_PROFILE = "work"
NEW_TOOL_ACCOUNT = "work"
```

`env` 中的值都是字面字符串：`$HOME`、反引号和 `$(...)` 都不会展开。也可以在 身份配置 层级使用 `unset_env = ["VARIABLE"]`。SSH 密钥和 GitHub 配置路径必须是绝对路径、`~` 或以 `~/` 开头；相对于主目录的路径会在切换后解析。相对路径和 `~other-user` 不接受。见[可运行示例](../../examples/config.toml)。

`show` 会显示身份元数据和自定义变量名称，但会隐藏自定义变量值。配置属于可信的本地输入：工具可能会执行环境变量或显式 Git 配置中指定的操作。DevWho 会为 shell 输出加引号，但不会沙盒化这些工具，也不会隔离共用的操作系统账号。

`current --verbose` 会显示生效的 Git author/committer 元数据和 GitHub CLI 配置目录。使用 `doctor` 可将这些信息与 身份配置 对照，并验证实际 GitHub 登录。

## 切换与恢复

`setdev PROFILE` 会影响当前 shell 及之后启动的子进程。其他终端和已经运行的应用保留各自环境。

`unsetdev` 会恢复首次激活前保存的 初始状态。未设置、空字符串和非空值会分别保留。A → B → C → unset 会回到原始 初始状态，而不是上一个 身份配置。新 身份配置 移除的变量会立即恢复。之后用户对该非受管变量所做的修改会保留。

Shell 状态保存在未导出的 `__DEVWHO_STATE` 变量中。子进程会继承当前活动环境，但不会继承父 shell 的恢复状态。在继承环境中启动的 shell 会把继承环境作为自己的 初始状态；初始化时会保留它的 `DEVWHO_PROFILE` 标记。

以下可选设置可让共用电脑更方便：

```toml
[settings]
default_profile = "personal"
shortcut_profile = "work"
handoff_warning = true
```

在全新且尚未激活的 shell 初始化时会应用默认 身份配置，并将其作为 初始状态。因此 `setdev` 选择 `work`，而 `unsetdev` 返回 `personal`。不设置这些选项时，初始化不会改变身份，切换时必须指定 身份配置。`handoff_warning` 是可选项：它会在切换后限时检查当前仓库是否有未提交改动，但绝不会认领、stash 或删除这些改动。

共用一个工作副本时，接手前请完成或明确交接未提交的改动，并停止上一位使用者的编辑任务。进程环境隔离不能阻止多人同时写入同一个仓库。

## 为子进程选择 身份配置

```bash
devwho exec work -- git status
devwho exec work -- bash
devwho exec work -- codex --version
```

命令及其子进程会获得所选 身份配置，父进程环境保持不变。身份配置 未设置的现有变量仍会继承；`exec` 不是环境沙盒。在 POSIX 系统上，命令会替代 DevWho 进程，因此信号和退出状态保持正常。DevWho 不管理可执行文件本身或各工具专属的登录设置。

## Git 行为

Git 姓名和邮箱会编译为 `GIT_CONFIG_COUNT` 及其索引运行时配置，涵盖 `user`、`author` 和 `committer`。它们会覆盖配置文件，包括仓库中过时的身份字段；显式 Git `-c` 选项和 author 参数仍遵循 Git 原有优先级。DevWho 不会改写 `.gitconfig` 或仓库配置。

DevWho 刻意不长期设置 `GIT_AUTHOR_*` 和 `GIT_COMMITTER_*`，因此 cherry-pick 和 rebase 会保留原作者。继承到的非空直接身份覆盖变量会导致激活失败；其值既不会打印，也不会被悄悄清除。

已有运行时配置条目会保留。激活期间由第三方追加的条目在切换和恢复时也会保留。如果已有配置前缀或 DevWho 管理的部分被改动，恢复会失败，而不会删除无法识别的配置；请打开新 shell 或撤销外部修改。这是有意采用的保守限制。

基础签名设置 `signing_key`、`signing_format` 和 `sign_commits` 会编译为 Git 运行时配置。DevWho 不生成密钥，也不验证签名是否可信。其他运行时设置示例：

```toml
[profiles.work.git.config]
"commit.gpgSign" = "false"
```

值可以是字符串或字符串数组，从而保留重复配置键。单独配置签名不要求提供 Git 姓名和邮箱。

## Git SSH

```toml
[profiles.work.git_ssh]
identity_file = "~/.ssh/id_ed25519_work"
identities_only = true
```

密钥文件必须存在。DevWho 会安全引用路径，并通过 `GIT_SSH_COMMAND` 传给 Git；Git fetch/pull/push 会继承该命令。它不会改写 `~/.ssh/config`、创建密钥、管理 agent，也不会为单独运行的 `ssh` 选择身份。现有的独立 agent 可以通过通用变量 `SSH_AUTH_SOCK` 选择。

本地 doctor 会检查配置的命令和密钥，但不会确认远端 SSH 账号归属。远端认证需要另外验证。

## GitHub CLI

```toml
[profiles.work.github]
hostname = "github.com"
expected_user = "jane-work"
config_dir = "~/.config/devwho/github/work"
```

DevWho 会导出 `GH_CONFIG_DIR` 和 `GH_HOST`。请在每个上下文中用 `devwho exec work -- gh auth login` 完成一次登录。DevWho 不会复制或打印令牌；凭据由 GitHub CLI 管理。非空的 `GH_TOKEN` 或 `GITHUB_TOKEN` 与 GitHub 身份配置 冲突，会导致本地激活失败。

Git 提交身份、Git 传输凭据和 GitHub CLI 登录彼此独立。gh 登录匹配不代表 Git HTTPS/GCM 使用同一账号。请分别配置并验证传输；普通 身份配置 激活不会改写 remote，也不会自动将 SSH 转换为 HTTPS。

## 诊断

```bash
devwho doctor
devwho doctor work --offline
```

Doctor 会检查当前环境与指定 身份配置 是否匹配；它不会先切换环境。Git 身份通过实际 Git 命令检查。已配置 GitHub 身份时，会调用 `gh api user` 检查。发现不匹配时会报告预期和实际账号元数据。API 请求失败会标记为 `UNVERIFIED`，绝不会被当作成功。`--offline` 会跳过该请求。

退出码：`0` 表示验证通过；`1` 表示失败或不匹配；`2` 表示所需检查无法完成或已跳过。Exec 保留子命令退出码；命令不存在时返回 `127`，命令不可执行时返回 `126`。激活和普通检查都离线进行；只有显式执行在线 doctor 检查时才会发起网络请求。可选的交接提醒只检查本地仓库。
