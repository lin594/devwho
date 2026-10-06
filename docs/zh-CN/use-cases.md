# 日常工作流程

[English](../use-cases.md) | [简体中文](use-cases.md) · [文档首页](README.md)

以下示例假设你已完成[入门](getting-started.md)，并创建了 `personal` 和 `work` 两个 身份配置。

## 在同一个项目中使用个人和工作身份

打开已有项目目录，并在开始工作前选择身份：

```sh
setdev work
devwho current --verbose
git status
```

接下来的 Git 提交会使用该 身份配置 中的姓名和邮箱。另一个独立打开的终端可以运行 `setdev personal`，不会改变第一个终端。`workspace/owner/repo` 这样的文件夹路径不会决定提交者是谁。

完成后，`unsetdev` 会恢复这个 shell 首次激活 DevWho 前的设置。如果你先后切换 personal → work → personal，`unsetdev` 仍会回到最初状态；它不是“后退一步”。

## 为共用电脑设置简单的默认身份

在同一个配置文件中、各 身份配置 表之前，添加这个**顶层**配置表：

```toml
[settings]
default_profile = "personal"
shortcut_profile = "work"
handoff_warning = true
```

在文件顶部保留 `version = 1`，并保留两个 身份配置。打开一个全新的独立终端后：

| 操作 | 当前 身份配置 |
|---|---|
| 打开终端 | `personal` |
| 运行 `setdev` | `work` |
| 运行 `unsetdev` | `personal` |
| 运行 `setdev personal` | `personal` |

你可以用实际姓名替换 `personal` 和 `work`。熟悉命令的用户可以快速切换，默认用户则能直接开始工作。

可选的交接提醒会在切换后检查当前仓库是否有未提交改动。它不会 stash、清理文件、切换分支，也不会判断现有改动属于谁。共用一个工作副本前，请先处理或明确交接未提交的工作，并停止上一位使用者的编辑任务。使用不同副本也可以沿用相同命令。

## 只让一条命令使用指定 身份配置

```sh
devwho exec work -- git status
devwho exec work -- gh api user --jq .login
```

第二条命令需要配置 GitHub 身份配置 并完成登录，见[账号设置](accounts.md)。命令退出后，父终端仍使用原来的身份。该命令启动的子进程也会继承所选环境。

其他读取环境变量的开发工具也可以这样使用。它不会自动切换应用内部单独管理的账号。

## 启动子 shell

```sh
setdev work
bash
eval "$(devwho init bash)"
```

子 shell 启动时会继承 `work`。在子 shell 中运行 `unsetdev` 会恢复它继承到的环境，因此无法恢复父 shell 原先的 personal 身份配置。运行 `exit` 回到父 shell 后，再在那里运行 `unsetdev`；也可以在子 shell 中明确选择 `personal`。

独立打开的终端会使用配置的默认身份。这样既支持有意继承身份，也让互不相关的终端保持独立。

## 为其他工具选择环境设置

在 身份配置 中添加字面值：

```toml
[profiles.work.env]
TOOL_PROFILE = "work"
```

运行 `setdev work` 后，从当前 shell 启动的程序会看到 `TOOL_PROFILE=work`。只有当工具确实读取这个变量时，这种设置才有用。对于没有账号切换接口的工具，DevWho 不会凭空添加一个。

这些值会按原样传递：`"$HOME/work"` 仍是这段文本。只有专用的 Git SSH 和 GitHub 路径字段会展开相对于主目录的路径。显式取消设置和恢复规则见[配置参考](reference.md)。
