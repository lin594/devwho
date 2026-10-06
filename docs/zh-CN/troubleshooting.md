# 故障排查

[English](../troubleshooting.md) | [简体中文](troubleshooting.md) · [文档首页](README.md)

先运行 `devwho --version`、`devwho current --verbose` 和 `devwho doctor --offline`。求助时，请提供执行的命令和相关报错，并将姓名和路径换成虚构内容。不要粘贴凭据或完整环境变量。

## 提示 `devwho: command not found`

如果是单文件安装，试试 `~/.local/bin/devwho --version`。如果能运行，请在当前 shell 和启动文件中加入 `export PATH="$HOME/.local/bin:$PATH"`。如果文件不存在，请完成[安装步骤](getting-started.md)。使用 pipx 时，请检查 `pipx environment` 报告的目录。

## `devwho` 可用，但提示 `setdev: command not found`

`setdev` 会修改当前 shell，因此必须作为 shell 函数加载。在 Bash 中运行 `eval "$(devwho init bash)"`，在 Zsh 中运行 `eval "$(devwho init zsh)"`。如果初始化提示找不到配置，请运行 `devwho config init`，编辑生成的文件，再重新初始化。让后续终端自动加载的步骤见[配置新终端](getting-started.md#让新终端也能使用)。

## `config init` 提示文件已存在

这是为了避免覆盖你的设置。运行 `devwho config path` 并编辑现有文件。不要只为重走教程就删除可用配置。

## 身份配置 未知，或 `setdev` 要求指定 身份配置

运行 `devwho list` 并选择列出的名称。`setdev work` 会选择指定 身份配置；不带参数的 `setdev` 需要设置 `settings.shortcut_profile`。共用电脑的示例见[日常工作流程](use-cases.md)。

## `current` 显示 `none`，或 `unsetdev` 恢复到意外身份

`none` 表示 DevWho 当前没有活动 身份配置 标记。Git 仍可能从原有配置中读到姓名和邮箱。`unsetdev` 会恢复此 shell 首次激活前保存的环境。已配置的默认 身份配置 会成为这个 初始状态；子 shell 的 初始状态 则是它继承到的环境。参见[子 shell](use-cases.md#启动子-shell)。

## GitHub 登录返回 401，或显示了另一个账号

检查 `devwho current --verbose` 显示的 GitHub 配置目录。新的 身份配置 专属目录不会包含你在另一个目录中使用的登录。先检查现有上下文中的 `gh api user --jq .login`，然后让 身份配置 指向那个目录，或在它自己的目录中登录。[账号设置](accounts.md)说明了这两种做法。

`devwho doctor work` 会用当前环境对照 `work`；它不会先切换身份。检查前请先运行 `setdev work`。

## `doctor --offline` 报告 `UNVERIFIED` 并以代码 2 退出

对于包含 GitHub 设置的 身份配置，这是预期结果：验证账号需要请求 API。联网后运行 `devwho doctor`。纯 Git 身份配置 不需要调用 GitHub API。退出码 1 表示检查失败或不匹配；0 表示所有配置检查通过。

## 环境变量冲突导致无法激活

持久设置的 `GIT_AUTHOR_NAME`、`GIT_AUTHOR_EMAIL`、`GIT_COMMITTER_NAME` 或 `GIT_COMMITTER_EMAIL` 可能覆盖提交身份。`GH_TOKEN` 和 `GITHUB_TOKEN` 可能覆盖 gh 身份配置。请查明该变量在哪里设置，并决定是否仍需要此覆盖；DevWho 不会更改它，也只报告变量名。使用 DevWho 身份配置 时，避免把这些身份覆盖写进启动文件。

只读或带特殊类型的 shell 变量也可能阻止切换。请将受管理的设置改为普通的导出字符串，或在移除冲突设置后打开新 shell。预检失败时身份不会改变。

## SSH 密钥或 GitHub 配置路径被拒绝

请使用绝对路径、`~` 或 `~/` 开头的路径。相对路径会随当前工作目录变化，因此不接受；`~other-user` 路径也不接受。所选 SSH 密钥必须是现存文件。相对于主目录的路径使用切换后的有效 `HOME`，该值必须非空且为绝对路径。

## Git 仍显示意外的姓名或邮箱

在运行 Git 的同一个终端中检查 `devwho current --verbose` 和 `devwho doctor --offline`。检查 `git --version` 至少为 2.31。显式的 `git -c ...`、显式 author 参数或工具专属环境设置都可能覆盖 身份配置。Rebase 和 cherry-pick 会保留原提交作者，同时将当前身份用作 committer。

## `unsetdev` 拒绝恢复 Git 运行时配置

其他工具可能修改了原有运行时配置或 DevWho 管理的部分。DevWho 不会猜测应该删除哪些值。若你清楚外部修改内容，可以撤销它；也可以打开一个全新的独立终端。激活后追加的运行时设置可以保留，但不支持任意改写已有条目。

## VS Code、Copilot 或其他应用仍使用旧账号

已经运行的应用会保留原环境，也可能有自己的登录系统。v0.1 不提供 VS Code 窗口或账号隔离集成。请在所选终端中运行 Git 命令；不要假设 `code .` 会切换 Source Control、Copilot 或浏览器会话。

## GitHub 拒绝推送 workflow 文件

如果 Git 使用 gh 凭据且 GitHub 报告缺少 `workflow` scope，请检查或刷新目标 gh 登录的权限。这与选择 Git author 不同。参见[HTTPS 认证](accounts.md#使用-git-https)。

仍无法解决？请在[问题跟踪页](https://github.com/lin594/devwho/issues)提供操作系统、shell、Python/Git 版本、执行命令和最小复现。安全问题请使用[私密报告渠道](../../SECURITY.zh-CN.md)。
