# DevWho Bash 实现

[English](README.md) | [简体中文](README.zh-CN.md) · [选择核心与预编译安装指南](../README.zh-CN.md)

本目录独立实现[兼容核心 v1](../../spec/compatibility-core-v1.zh-CN.md)：完整 TOML
配置、公共命令、Bash/Zsh 集成、可恢复 JSON 状态、有序 Git 运行时配置、SSH/GitHub
设置、启动默认环境、子进程执行和诊断。不会调用 Python 或其他语言的 DevWho 核心。

运行依赖为 **Bash 3.2+、jq 1.6+、Perl 5.18+ 和标准系统工具**。Perl 仅使用标准模块
与随附 TOML 解析器，无需 CPAN 安装。依赖、源码出处、校验值、许可证和解析器补丁见
[THIRD_PARTY.md](THIRD_PARTY.md)。

```bash
implementations/bash/devwho --config examples/config.toml list
eval "$(implementations/bash/devwho --config examples/config.toml init bash)"
setdev work
unsetdev
```

Zsh 使用 `init zsh`。`init` 只输出集成代码，不修改启动文件；生成代码固定可执行文件
与配置文件的绝对路径。配置文件及变量值不会作为 shell 代码执行。状态不导出，子 shell
继承选中的环境并把它作为自己的恢复基线。

通过系统包管理器安装依赖后，可运行：

```bash
bash implementations/bash/install.sh "$HOME/.local"
```

安装器复制完整目录到 `PREFIX/lib/devwho-bash`，创建 `PREFIX/bin/devwho` 链接，并拒绝
覆盖已有命令。也可直接运行源码目录中的命令。`config init` 以私有权限独占创建示例；
使用前请修改示例身份。

更新时，先确认 `PREFIX/bin/devwho` 是本安装器创建、且指向同一
`PREFIX/lib/devwho-bash` 目录的符号链接。只删除这个已确认的链接，再使用相同 prefix
重跑安装器；安装器会拒绝覆盖其他命令。已初始化的 shell 会保留当前环境和恢复状态；打开
新 shell，或重新运行 `devwho init` 并执行输出，以加载更新后的集成代码。配置、GitHub CLI
数据和配置前端备份单独保存。
卸载默认的 `$HOME/.local` 安装时，先从 shell 启动文件中移除自行添加的 `devwho init`
行，避免新终端调用已删除的命令；再删除已确认的链接和实现目录：

```bash
# 仅在默认安装的符号链接确实指向预期目标时更新。
test "$(readlink "$HOME/.local/bin/devwho")" = "$HOME/.local/lib/devwho-bash/devwho" &&
  rm "$HOME/.local/bin/devwho"
bash implementations/bash/install.sh "$HOME/.local"
```

完全卸载时，删除相同的已知路径：

```bash
rm "$HOME/.local/bin/devwho"
rm -r "$HOME/.local/lib/devwho-bash"
```

若使用其他 prefix，请替换为那个确切路径。除非另行决定清理，否则保留配置、GitHub CLI
数据和备份。核心选项及可选预编译 Go 安装方式见[通用指南](../README.zh-CN.md)。

命令与配置优先级遵循[公共参考](../../docs/zh-CN/reference.md)。激活始终离线。
`doctor` 返回 0（通过）、1（不匹配）或 2（未验证），隐藏通用变量值、令牌及外部工具
错误输出，并限制诊断等待时间。`exec` 保持参数、退出码和信号行为；不存在或不可执行的
命令分别返回 127 和 126。

缺失值、空值、非空值、有序重复 Git 配置、第三方后续追加项和孤立索引变量均可恢复。
状态校验及 shell 只读、数组、特殊属性检查在变更前完成。激活不修改 Git/SSH 持久配置、
凭据、远程地址、分支或工作文件。

开发验证（Python 仅用于测试）：

```bash
python3 -m unittest discover -s implementations/bash/tests -v
python3 conformance/run.py --executable implementations/bash/devwho --peer bin/devwho
```

公共测试覆盖真实 Bash/Zsh/Git/SSH、TOML 编码、错误配置、跨实现状态、字面参数、
退出与信号、诊断及原子恢复。源码测试不能替代无 Python 运行环境验证和完整发行平台矩阵；
RC1 已有成功的托管 Linux/macOS 和无 Python 隔离运行证据；具体目标以最终发行报告为准。

## 可选 dotenv 前端

TOML 仍是完整兼容格式。仅包含通用环境变量的配置可显式使用 dotenv：

```bash
eval "$(implementations/bash/devwho --env-file environment.env init bash)"
setdev
unsetdev
implementations/bash/devwho --env-file environment.env --env-profile work list
implementations/bash/devwho --config config.toml config export-env work > work.env
```

文件必须包含有效 `DEVWHO_PROFILE`，或显式传入 `--env-profile`；同时提供时必须相等。
标记用于配置元数据，不作为普通变量解析。单个配置自动作为快捷选择，不设启动默认配置。
`--env-file` 与 `--config` 互斥，初始化固定源文件和名称；`config init` 拒绝 dotenv 源。

支持 UTF-8、LF/CRLF、空行及整行注释、可选 `export ` 前缀、`=` 两侧空白、空值、
字面单引号和 JSON 双引号转义。非引号值去除两侧空白；只有空格或制表符之后的 `#`
开始注释。`$`、`${...}`、`$(...)` 永远是字面数据。重复键、裸键、物理多行、NUL、
单独 CR、无效 Unicode、保留变量和名称不匹配均拒绝。没有插值、source 或 unset 语法。
导出命令拒绝 Git/SSH/GitHub 语义设置及显式 unset，避免转换时丢失行为。

### 已记录的本地验证

Linux x86_64 上，Bash 5.2.37 / Zsh 5.9、jq 1.7、Perl 5.40.1 的公共测试 **63 项通过**
（Bash 中跳过一项仅适用于 Zsh 的检查），包括 Python 核心状态互操作。另行编译的
**Bash 3.2.0** 同时运行核心解释器及 Bash 集成时，同样通过 63 项公共测试。实现自身
**20 项测试通过**，并验证了新前缀安装、安装链接、Unicode、SHLVL/PWD、PATH/TMPDIR
及末尾含换行的配置文件名。这些早期 Linux 本地记录已补充托管 Linux x86-64/macOS ARM64 的 71 项公共验收，包括 macOS 系统 Bash 3.2 和 Bash/Zsh；FZ2/托管 Linux 的禁网、无 Python/编译器运行环境也通过。Windows 仍不支持。测试驱动依赖 Python，安装后的运行时不调用 Python。
