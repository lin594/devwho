# DevWho

**在终端切换开发身份，项目目录照常使用。**

[English](README.md) | [简体中文](README.zh-CN.md)

[![CI](https://github.com/lin594/devwho/actions/workflows/ci.yml/badge.svg)](https://github.com/lin594/devwho/actions/workflows/ci.yml) · [MIT 许可证](LICENSE) · [文档](docs/zh-CN/README.md) · [获取帮助](https://github.com/lin594/devwho/issues)

DevWho 帮助需要使用多个开发身份的人：例如区分个人和工作账号、不同客户项目，或多人共用一台开发电脑。把每个身份保存一次，然后为当前终端选择要使用的身份。

下一次 Git 提交会使用所选的姓名和邮箱。你也可以为 Git 选择 SSH 密钥、为 GitHub CLI 选择账号配置，并设置其他工具使用的环境变量。现有项目目录和已安装的工具都不需要移动或重新安装。

## 哪些情况下适合使用？

| 使用情况 | DevWho 可以帮你做什么 |
|---|---|
| 你同时使用个人和工作 Git 身份。 | 开始工作前切换身份，并检查 Git 将使用的姓名和邮箱。 |
| 两个人共用一台开发电脑。 | 让新终端默认使用一个身份，也可以明确切换到另一个身份。 |
| 两个终端需要使用不同身份。 | 分别选择身份，即使两个终端位于同一个项目目录也可以。 |
| 某条命令需要特定工具配置。 | 为它指定一个身份配置，同时保留父终端原有状态。 |

如果 Git 的目录条件配置 `includeIf` 已经解决了你的问题，就不一定需要 DevWho。DevWho 更适合按**当前终端由谁使用**来选择身份，而不是按仓库所在目录选择。[比较不同方案 →](docs/alternatives.md)

## 已验证候选产物

| 下载文件 | 目标与实跑证据 | 运行要求 |
|---|---|---|
| `devwho-0.1.0rc1-go-linux-x86_64.tar.gz`（推荐） | Linux x86-64；Ubuntu CI 和 FZ2 Debian WSL | Go core/配置前端为静态程序；无需 Python、编译器或动态 libc |
| `devwho-0.1.0rc1-go-darwin-arm64.tar.gz`（推荐） | macOS ARM64；托管 macOS 26.6.2 | core/配置前端声明最低 macOS **13.0**；无需 Python/编译器 |
| `devwho-0.1.0rc1-rust-darwin-arm64.tar.gz` | macOS ARM64；托管 macOS 26.6.2 | 程序声明最低 macOS **11.0**；无需 Python/编译器 |
| `devwho-0.1.0rc1-bash-unix-source-linux-x86_64.tar.gz` / `devwho-0.1.0rc1-bash-unix-source-darwin-arm64.tar.gz` | 脚本归档；Linux x86-64、macOS ARM64 CI 的真实 Bash/Zsh | Bash 3.2+、jq 1.6+、Perl 5.18+ 与标准 Unix 工具 |
| `devwho-0.1.0rc1.pyz`、wheel 或 sdist | Python 分发；Linux x86-64/macOS ARM64 的 Python 3.11/3.13 CI | Python 3.11+；无需第三方运行时 Python 包 |

macOS 最低部署版本来自程序头，与实际 CI 测试宿主不同；`RUNTIME.txt` 同时记录两者。RC1 不发布 Linux Rust 二进制，因为其托管构建需要 glibc 2.39；Linux 推荐静态 Go，或自行从源码构建 Rust。源码可用不代表未经实测架构的预编译支持。Windows/PowerShell、VS Code 绑定、Linux ARM64、macOS x86-64、Alpine/musl 与真实双账号远端认证仍未验收。

从[预发行](https://github.com/lin594/devwho/releases/tag/v0.1.0-rc.1)只下载所选归档和 `SHA256SUMS`，选取该文件的精确条目后核验，无需下载其他平台产物：

```sh
asset=devwho-0.1.0rc1-go-linux-x86_64.tar.gz  # 按上表替换目标
awk -v name="$asset" '$2 == name {print; found=1} END {if (!found) exit 1}' SHA256SUMS > selected.SHA256SUMS
sha256sum -c selected.SHA256SUMS  # macOS: shasum -a 256 -c selected.SHA256SUMS
```

完整安装/更新/卸载步骤见[指南](implementations/README.zh-CN.md)。Git 2.31+、gh 和 SSH 仍是相应功能的可选消费工具。

## 统一的环境约定，以及面向现有工具的兼容层

我们的目标是：选择一次身份上下文，让应用自行读取并使用，就像应用读取代理环境变量一样。原生支持的应用可以读取 `DEVWHO_PROFILE`，再映射到自己的账号。它们无需导入 Python 模块、读取版本变量，也无需为每个应用另造一套 DevWho 变量。目前这份[环境变量约定](spec/environment-v1.zh-CN.md)仍是**草案**。

现在通过**兼容性 core**让现有工具可用：把身份配置转换成 Git 运行时配置、`GH_CONFIG_DIR` 等工具已有的接口。Python、Go、Rust、Bash 已分别实现相同切换契约的独立 core。按设备选择其中一种即可；Go/Rust 二进制运行时不需要 Python 或编译器。

[了解生态与兼容层的关系](docs/zh-CN/ecosystem.md) · [查看各实现的状态与路线](implementations/README.zh-CN.md)

运行时约定与文件格式无关。四种 core 都支持完整 TOML profile 和可选的[字面量 dotenv 输入](docs/zh-CN/configuration-formats.md)。可选的[配置前端](docs/zh-CN/configuration-ui.md)提供中英文提示和安全保存，初学者不必手写 TOML。原生应用只需读取最终环境，不必读取提供方的配置文件。

## 日常使用示例

完成下面的一次性设置后，`work` 和 `personal` 就是你为身份起的名字：

```sh
setdev work
git config user.email
# jane.work@example.test

setdev personal
git config user.email
# jane.personal@example.test

unsetdev                 # 恢复切换前此终端的身份设置
```

修改只会影响当前终端，以及之后从该终端启动的程序。其他终端和已经运行的应用仍使用各自原来的设置。在一个终端切换身份，**不会**切换已打开的 VS Code 窗口、Copilot 或浏览器登录账号。

## 当前版本需要什么？

| 条件 | 用途 |
|---|---|
| Linux、WSL 或 macOS，以及 Bash 或 Zsh | 使用终端集成。[CI](https://github.com/lin594/devwho/actions/workflows/ci.yml) 覆盖 Ubuntu/macOS 与 Python 3.11/3.13 组合；WSL 也经过本地检查。 |
| 选择一种 core | Go/Rust 二进制、Bash + jq + Perl，或 Python 3.11+。[选择指南](implementations/README.zh-CN.md)。 |
| Git **2.31 或更新版本** | 按本指南切换 Git 身份。 |
| GitHub CLI（`gh`） | 可选：仅在使用 GitHub CLI 账号配置或在线身份检查时需要。 |
| OpenSSH 和已有密钥 | 可选：仅在为 Git 选择 SSH 密钥时需要。 |

运行时**不需要第三方 Python 依赖**。安装步骤使用你已有的 Python；不需要 pipx、Node.js 或 Docker。Windows PowerShell 集成仍在计划中；目前 Windows 用户请使用 WSL。

**没有安装 Python？** 可以从 [v0.1.0-rc.1 预发行](https://github.com/lin594/devwho/releases/tag/v0.1.0-rc.1)下载经过测试的 Go/Rust 产物，也可以安装 [Bash core](implementations/bash/README.zh-CN.md)。详见[下载、构建与实际依赖](implementations/README.zh-CN.md)。发行产物附统一 SHA256SUMS 和提交清单；CI 产物仍是开发构建，下载需登录 GitHub。

## 开始使用

DevWho 目前处于早期 **v0.1** 阶段。首个标签候选版本为 [v0.1.0-rc.1](https://github.com/lin594/devwho/releases/tag/v0.1.0-rc.1)，暂未发布到软件包仓库。如果你已经能运行 `devwho --version`，可以直接跳到第 2 步。

### 1. 安装一次

先[选择一种 core](implementations/README.zh-CN.md)。以下源码安装示例适用于已有 Python 3.11+ 的用户；已安装 Go/Rust/Bash core 时，直接进入第 2 步。

在 Bash 或 Zsh 终端运行：

```sh
git clone https://github.com/lin594/devwho.git
cd devwho
python3 scripts/build_zipapp.py
mkdir -p "$HOME/.local/bin"
install -m 755 dist/devwho-0.1.0rc1.pyz "$HOME/.local/bin/devwho"
export PATH="$HOME/.local/bin:$PATH"
devwho --version
```

预期输出：`devwho 0.1.0-rc.1`。这会为当前操作系统用户安装一个可执行文件，所有身份配置共用它。版本检查、pipx 备用安装方式，以及更新或卸载方法请见[入门指南](docs/zh-CN/getting-started.md)。

### 2. 保存身份配置

安装可选的 Go 配置前端后，可运行 `devwho-setup --language zh-CN configure`，按提示填写。它写入的配置适用于全部 core。也可以使用下面的手动编辑方式。[交互配置与备份说明 →](docs/zh-CN/configuration-ui.md)

```sh
devwho config init
devwho config path
```

用文本编辑器打开命令显示的文件。如果是新建配置，就用下面的示例替换初始内容，再把 Jane 的姓名和邮箱改成你实际使用的身份信息。如果已经配置过身份，请保留已有内容，只添加或调整需要的身份。这些是 Git 提交显示的信息，不是密码或 GitHub 用户名。配置名称可以自行决定。

```toml
version = 1

[profiles.personal.git]
name = "Jane Doe"
email = "jane.personal@example.test"

[profiles.work.git]
name = "Jane Doe"
email = "jane.work@example.test"
```

如果已有配置文件，DevWho 会保留它：如果 `config init` 提示文件已存在，就直接编辑那个文件。大多数用户的默认路径是 `~/.config/devwho/config.toml`。

### 3. 切换并检查

在**当前终端**中选择一行初始化命令：

```sh
eval "$(devwho init bash)"    # Bash
# eval "$(devwho init zsh)"  # Zsh：请改用这一行
```

然后试试：

```sh
setdev work
devwho current              # 输出：work
git config user.email       # 输出你保存的工作邮箱
devwho doctor --offline     # 在本机检查当前 Git 身份
unsetdev
devwho current              # 使用此示例且在新终端中会输出：none
```

`none` 表示当前没有选择 DevWho 身份；Git 会恢复到切换前该终端已有的设置。试用不需要提交或推送任何内容。

若想在之后打开的终端中也使用这些命令，可以把 PATH 和对应的初始化命令加到 shell 启动文件中，只需设置一次。[查看具体步骤 →](docs/zh-CN/getting-started.md#让新终端也能使用)

## 常用命令

| 想做什么 | 命令 |
|---|---|
| 查看已保存的身份 | `devwho list` |
| 为当前终端切换身份 | `setdev work` |
| 查看当前身份和 Git 详情 | `devwho current --verbose` |
| 恢复终端原有设置 | `unsetdev` |
| 只为一条命令使用某个身份 | `devwho exec work -- git status` |
| 检查配置的 GitHub CLI 登录账号 | `devwho doctor` |

如果多人共用一台电脑，可以[设置默认身份和快捷身份](docs/zh-CN/use-cases.md)：新终端默认使用 `personal`，用 `setdev` 切换到 `work`，再用 `unsetdev` 恢复到 `personal`。

## 这会同时登录 GitHub 吗？

Git **提交身份信息**、**推送凭据**和 **GitHub CLI 登录**是彼此独立的。上面的示例只选择提交身份信息。若要选择 GitHub CLI 账号或 Git SSH 密钥，请阅读[账号与身份验证](docs/zh-CN/accounts.md)。DevWho 使用你已有的凭据工具；它不会创建账号，也不会代替你登录。

两个人共用同一份工作目录时，请先约定如何交接未提交的改动，并让上一位使用者停止正在进行的编辑任务。选择不同身份不会隔离文件，也不能避免同时修改造成的问题。

## 接下来读什么？

| 你想做什么 | 阅读内容 |
|---|---|
| 完成安装、更新或卸载 | [入门指南](docs/zh-CN/getting-started.md) |
| 了解个人/工作账号、共用电脑和单条命令的用法 | [日常使用场景](docs/zh-CN/use-cases.md) |
| 使用已有 GitHub CLI 登录或 Git SSH 密钥 | [账号与身份验证](docs/zh-CN/accounts.md) |
| 解决“找不到命令”、登录不匹配或恢复错误 | [故障排查](docs/zh-CN/troubleshooting.md) |
| 查询命令和 TOML 配置项 | [参考手册](docs/zh-CN/reference.md) |
| 理解原生环境约定与当前兼容层 | [生态设计](docs/zh-CN/ecosystem.md) |
| 参与完整的无 Python 依赖实现 | [Core 的多语言实现](implementations/README.zh-CN.md) |
| 报告问题或参与改进 | [贡献指南](CONTRIBUTING.zh-CN.md) |

更多信息：[文档索引](docs/zh-CN/README.md) · [更新记录](CHANGELOG.zh-CN.md) · [安全报告](SECURITY.zh-CN.md) · [MIT 许可证](LICENSE)
