# DevWho Rust 兼容核心

[English](README.md) | [简体中文](README.zh-CN.md) · [通用安装、更新与卸载指南](../README.zh-CN.md#在-linux-或-macos-安装预编译-go-core)

这是独立的 Rust 实现。运行时是本机可执行文件，不调用 Python、Go、Bash 或其他 DevWho 核心。诊断时可调用 Git 和 GitHub CLI；`exec` 会运行指定子进程。

使用 Rust 1.85 或更新版本构建：

推荐的预编译 Go 安装步骤见[通用指南](../README.zh-CN.md#在-linux-或-macos-安装预编译-go-core)；Rust 归档会在各自的 `RUNTIME.txt` 中记录具体依赖。

```sh
cargo build --release --locked --manifest-path implementations/rust/Cargo.toml
```

运行 `implementations/rust/target/release/devwho --config /absolute/config.toml list`。在 Bash 或 Zsh 中执行 `init bash` 或 `init zsh` 的输出即可启用集成。生成的函数固定可执行文件和配置文件路径。`setdev [PROFILE]` 切换配置，`unsetdev` 恢复该终端原有环境。切换实现时请打开新终端。

可选的 dotenv 前端使用 `--env-file PATH [--env-profile NAME]`，与 `--config PATH` 互斥。文件中的 `DEVWHO_PROFILE=NAME` 或命令行的 `--env-profile NAME` 选择单个配置。其赋值是字面量通用环境变量。支持 LF/CRLF、注释、可选的 `export ` 前缀、未加引号的值、字面单引号及 JSON 转义双引号；拒绝重复键、无效键、错误引号、NUL 和语义配置。`config export-env PROFILE` 可导出仅包含通用环境变量的 TOML 配置；有 Git、SSH、GitHub 或 unset 设置时会拒绝导出。`config init` 仅适用于 TOML。

TOML 1.0 使用锁定版本的 `toml` 库解析，并保留重复 Git 设置的顺序。内部状态采用版本 1 JSON。Linux CI 二进制动态链接 glibc 与 `libgcc_s`，需要最高至 2.39 的 glibc 符号；RC1 不提供该二进制下载，Linux 推荐静态 Go 或 Rust 源码构建。不支持 Alpine/musl，目前也不宣传 Linux ARM64。请检查下载归档中的 `RUNTIME.txt`；不同构建的要求可能不同。诊断使用已安装的 `git` 及可选的 `gh`，切换本身离线。第三方许可详见 [LICENSES.md](LICENSES.md)。


## 更新与卸载

自行安装 Rust 二进制时，校验匹配的归档及其 `RUNTIME.txt` 后，只替换已安装的 `devwho` 文件。已初始化的 shell 会保留当前环境和恢复状态；打开新 shell，或重新运行 `devwho init` 并执行输出，以加载更新后的集成代码。配置、GitHub CLI 数据和配置前端备份不受影响。卸载时先从 shell 启动文件移除自行添加的 `devwho init` 行，再只删除自己安装的明确二进制路径，例如 `rm "$HOME/.local/bin/devwho"`；保留这些数据目录。通用新手说明见[安装指南](../README.zh-CN.md#在-linux-或-macos-安装预编译-go-core)。

## RC1 平台验收与下载范围

托管 Linux x86-64/macOS ARM64 已通过 71 项公共验收，包含真实 Bash/Zsh 和 macOS 系统 Bash 3.2。macOS 二进制声明最低 11.0，记录的实测宿主为 26.6.2；RUNTIME.txt 同时提供最低版本和测试宿主。RC1 仅发布 macOS ARM64 Rust 二进制；Linux 构建仍参加全部测试，但因 glibc 2.39 边界不提供预编译下载，推荐静态 Go 或源码构建。Windows、Linux ARM64、Alpine/musl 和真实远端多账号认证仍未验收。最新结果以最终提交 CI 为准。
