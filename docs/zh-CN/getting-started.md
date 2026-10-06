# 入门指南

[English](../getting-started.md) | [简体中文](getting-started.md) · [文档索引](README.md)

本指南将带你完成安装，并检查 Git 将使用的身份信息。首次运行不需要 GitHub 登录，也不需要创建测试提交。

## 检查终端和工具

请在 Linux、WSL 或 macOS 上使用 Bash 或 Zsh。Windows 用户请打开 WSL 终端，并在 WSL 中完成全部步骤。v0.1 不支持原生 PowerShell 或 VS Code 账号切换。

```sh
python3 --version
git --version
```

Git 身份配置流程需要 Python 3.11 或更新版本，以及 Git 2.31 或更新版本。Git 2.31 开始支持这里用到的[基于环境变量的配置](https://github.com/git/git/blob/master/Documentation/RelNotes/2.31.0.adoc)。如果缺少命令或版本过旧，请使用操作系统常用的软件包管理器安装或更新，然后重新检查。DevWho 使用这些已有工具，不会为每个身份另装一份 Python 或 Git。

不确定当前用的是哪种 shell？在 Bash 中运行 `echo "$BASH_VERSION"` 会显示版本；在 Zsh 中运行 `echo "$ZSH_VERSION"` 会显示版本。稍后选择对应的初始化命令。

## 安装单文件版本

如果 `devwho --version` 已能正常运行，可以跳到配置步骤。否则，在你存放工具或源码的目录中运行：

```sh
git clone https://github.com/lin594/devwho.git
cd devwho
python3 scripts/build_zipapp.py
mkdir -p "$HOME/.local/bin"
install -m 755 dist/devwho-0.1.0.pyz "$HOME/.local/bin/devwho"
export PATH="$HOME/.local/bin:$PATH"
devwho --version
```

你应该会看到 `devwho 0.1.0`。安装文件中包含 DevWho，但运行时仍使用系统中的 Python 3.11 或更新版本。运行时不需要第三方依赖。如果之后想自行更新，请保留这份源码目录。

如果你已经在使用 pipx，也可以在源码目录中运行 `pipx install .`。确保 pipx 的可执行文件目录已加入 PATH，然后运行 `devwho --version` 检查。请选择一种安装方式，以便清楚之后要更新哪个可执行文件。目前尚无 PyPI 正式版本；以上步骤安装的是本仓库中的代码。

## 创建两个身份配置

**身份配置（profile）**是一组有名字的设置。`personal` 和 `work` 只是示例名称，你可以自行命名。

```sh
devwho config init
devwho config path
```

用常用文本编辑器打开命令显示的路径。默认位置是 `~/.config/devwho/config.toml`；如果设置了 `XDG_CONFIG_HOME` 或 `DEVWHO_CONFIG`，请以命令显示的路径为准。`config init` 不会覆盖已有文件。

如果是新建配置，将初始内容替换为下面的示例，并填入你希望显示在提交记录中的姓名和邮箱。如果文件已经包含你的身份配置，请保留已有内容，只添加或调整需要的配置：

```toml
version = 1

[profiles.personal.git]
name = "Jane Doe"
email = "jane.personal@example.test"

[profiles.work.git]
name = "Jane Doe"
email = "jane.work@example.test"
```

TOML 是一种文本配置格式：保留方括号和引号，只修改引号中的值。`name` 是提交中显示的姓名。`email` 是你希望显示在提交中的邮箱，也可以使用 GitHub noreply 邮箱。这两项都不会验证或登录 GitHub。

## 激活并验证

使用 Bash 时运行：

```sh
eval "$(devwho init bash)"
```

使用 Zsh 时运行：

```sh
eval "$(devwho init zsh)"
```

只运行与当前 shell 对应的一行。这会在当前 shell 中定义 `setdev` 和 `unsetdev`。现在试试：

```sh
devwho list
setdev work
devwho current
git config user.email
devwho doctor --offline
unsetdev
devwho current
```

`list` 会显示 `personal` 和 `work`。切换后，`current` 会显示 `work`，Git 会显示你设置的工作邮箱。对于这个仅配置 Git 的示例，`doctor --offline` 应报告 `OK`。在新终端中恢复后，`current` 会显示 `none`，并重新使用原有 Git 配置。如果终端继承了身份或设置了默认身份，恢复结果可能不同，详见[日常使用场景](use-cases.md)。

## 让新终端也能使用

确认当前终端试用正常后，打开**一个** shell 启动文件：Bash 使用 `~/.bashrc`，Zsh 使用 `~/.zshrc`。把对应的代码块添加一次。

Bash：

```sh
export PATH="$HOME/.local/bin:$PATH"
eval "$(devwho init bash)"
```

Zsh：

```sh
export PATH="$HOME/.local/bin:$PATH"
eval "$(devwho init zsh)"
```

如果通过 pipx 安装，且其可执行文件目录不是 `~/.local/bin`，请改用实际目录。打开新终端，运行 `devwho list`，然后运行 `setdev work`。

有些 Bash 终端（包括常见的 macOS 配置）会启动登录 shell，并读取 `~/.bash_profile`。如果现有登录配置没有加载 `~/.bashrc`，可在 `~/.bash_profile` 中添加以下代码一次：

```sh
if [ -f "$HOME/.bashrc" ]; then
    . "$HOME/.bashrc"
fi
```

DevWho 只会输出初始化代码，不会自行修改 shell 启动文件。保留原有 shell 设置，并将简短的集成代码加入其中。

## 更新或卸载

使用单文件安装时，在源码目录中运行：

```sh
git pull --ff-only
python3 scripts/build_zipapp.py
install -m 755 dist/devwho-0.1.0.pyz "$HOME/.local/bin/devwho"
```

然后打开新终端并运行 `devwho --version`。使用 pipx 时，在更新后的源码目录中运行 `pipx install --force .`。

卸载前，先从 shell 启动文件中删除 DevWho 初始化行。单文件安装请删除 `~/.local/bin/devwho`；pipx 安装请运行 `pipx uninstall devwho`。然后打开新终端。如果其他工具也使用 PATH 设置，可以保留 PATH 那一行。DevWho 配置文件和 gh 登录目录仍可使用；是否删除由你决定。

接下来：[选择日常工作方式](use-cases.md)、[连接已有账号](accounts.md)，或[排查问题](troubleshooting.md)。
