# DevWho Rust 兼容核心

这是独立的 Rust 实现。运行时是本机可执行文件，不调用 Python、Go、Bash 或其他 DevWho 核心。诊断时可调用 Git 和 GitHub CLI；`exec` 会运行指定子进程。

使用 Rust 1.85 或更新版本构建：

```sh
cargo build --release --locked --manifest-path implementations/rust/Cargo.toml
```

运行 `implementations/rust/target/release/devwho --config /absolute/config.toml list`。在 Bash 或 Zsh 中执行 `init bash` 或 `init zsh` 的输出即可启用集成。生成的函数固定可执行文件和配置文件路径。`setdev [PROFILE]` 切换配置，`unsetdev` 恢复该终端原有环境。切换实现时请打开新终端。

可选的 dotenv 前端使用 `--env-file PATH [--env-profile NAME]`，与 `--config PATH` 互斥。文件中的 `DEVWHO_PROFILE=NAME` 或命令行的 `--env-profile NAME` 选择单个配置。其赋值是字面量通用环境变量。支持 LF/CRLF、注释、可选的 `export ` 前缀、未加引号的值、字面单引号及 JSON 转义双引号；拒绝重复键、无效键、错误引号、NUL 和语义配置。`config export-env PROFILE` 可导出仅包含通用环境变量的 TOML 配置；有 Git、SSH、GitHub 或 unset 设置时会拒绝导出。`config init` 仅适用于 TOML。

TOML 1.0 使用锁定版本的 `toml` 库解析，并保留重复 Git 设置的顺序。内部状态采用版本 1 JSON。Linux 二进制文件动态链接 glibc 与 libgcc_s。诊断使用已安装的 `git` 及可选的 `gh`，切换本身离线。第三方许可详见 [LICENSES.md](LICENSES.md)。

Linux x86_64 验证：Rust 1.85.1 编译并通过单元测试；Rust 1.95.0 构建发布二进制文件；共享验收测试在该二进制文件上通过，1 项因只适用于特定 shell 而跳过。当前 Bash 与 Zsh 集成均通过。此处未测试 Bash 3.2 和 macOS，仍属覆盖缺口。发行与平台 CI 完成前，本实现保持实验状态。它不会修改全局 Git 配置、远端、凭据或 shell 启动文件。
