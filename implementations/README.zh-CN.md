# 选择一种兼容核心实现

[English](README.md) | [简体中文](README.zh-CN.md) · [项目概览](../README.zh-CN.md)

兼容核心让现有 Git、SSH 和 GitHub CLI 工作流程使用终端当前选择的上下文。Python、Go、Rust、Bash 实现现在都遵循相同的 profile、命令、切换和恢复契约。按设备安装或构建**一种**核心即可。

## 实现选项

| 实现 | 源码与分发 | 最终用户所需环境 | 说明 |
|---|---|---|---|
| Python | [`src/devwho`](../src/devwho)、[`bin/devwho`](../bin/devwho) | Python 3.11 或更高版本；运行时不需要第三方 Python 包 | 参考实现；保留现有 Python 安装说明。 |
| Go | [`implementations/go`](go/README.md) | 预编译可执行文件运行时无需 Python 或编译器；源码构建需要 Go | 推荐初学者使用；`complete-cores-ubuntu-latest` 和 `complete-cores-macos-latest` 工作流运行中附有开发构建产物，下载需登录 GitHub。 |
| Rust | [`implementations/rust`](rust/README.md) | 预编译可执行文件运行时无需 Python 或编译器；源码构建需要 Rust | 独立实现；构建和平台覆盖请参阅其 README。 |
| Bash | [`implementations/bash`](bash/README.md) | Bash 3.2+、jq 1.6+、Perl 5.18+ 和标准系统工具 | 独立脚本实现；Perl 和 jq 是运行时依赖。 |

CI 产物是开发构建，不是正式标签发布。每次工作流运行会提供归档名称和校验和，归档目标对应实际运行平台。仓库尚未发布标签或托管发行版。Go/Rust 可执行文件运行时不需要 Python 或编译器；Bash 运行时不会调用 Python core。二进制归档含 `RUNTIME.txt`，记录该构建的实际操作系统、架构和系统库要求。Linux Rust 产物需要最高至 2.39 的 glibc 符号及 `libgcc_s`，不支持 Alpine/musl。Go Linux 构建会因构建配置而静态链接或动态链接。安装前请检查对应归档的 `RUNTIME.txt`。目前不宣传 Linux ARM64 支持。

### 在 Linux 或 macOS 安装预编译 Go core

1. 打开仓库的 [Actions 工作流](https://github.com/lin594/devwho/actions/workflows/ci.yml)，选择对应提交成功的 CI 运行，再下载 `complete-cores-ubuntu-latest` 或 `complete-cores-macos-latest` artifact。解压下载的 GitHub artifact ZIP。
2. 在解压后的目录中，先校验归档文件，再解包：

   ```sh
   cd /path/to/extracted-artifact/dist/cores
   sha256sum -c SHA256SUMS       # Linux
   shasum -a 256 -c SHA256SUMS  # macOS
   ```

3. 解包与 runner 对应的 Go 归档。Linux x86-64 使用 `devwho-go-linux-x86_64.tar.gz`；macOS 请使用 `SHA256SUMS` 中该 runner 对应的确切 `devwho-go-darwin-ARCH.tar.gz` 文件名。例如：

   ```sh
   tar -xzf devwho-go-linux-x86_64.tar.gz
   cd devwho-go-linux-x86_64
   # macOS 请替换为匹配的归档名，并 cd 到 devwho-go-darwin-ARCH 目录。
   ```

   归档中包含 `devwho` 和可选的独立配置编辑器 `devwho-setup`。可将其中一个或两者安装到用户目录：

   ```sh
   mkdir -p "$HOME/.local/bin"
   install -m 755 devwho "$HOME/.local/bin/devwho"
   install -m 755 devwho-setup "$HOME/.local/bin/devwho-setup"
   export PATH="$HOME/.local/bin:$PATH"
   ```

   如果准备手动编辑 TOML，可以跳过安装 `devwho-setup`。PATH 命令只对当前终端生效；如需在新终端中使用，请把该目录加入 shell 启动文件。用户机器不需要编译器。
4. 可选：运行 `devwho-setup --language zh-CN configure` 并按表单填写 profile。然后初始化 shell 并激活身份：

   ```sh
   eval "$(devwho init bash)"  # 使用 Zsh 时将 `bash` 换成 `zsh`
   setdev PROFILE_NAME
   ```

   `unsetdev` 会恢复 shell 初始环境。该命令会为当前 shell 固定此可执行文件和默认配置路径。

源码构建和验证说明见 [Go 指南](go/README.md)。更新 Go/Rust 时，校验并解压与平台匹配的新归档，然后只替换 `~/.local/bin/devwho`；只有同时更新可选工具时才替换 `devwho-setup`。已初始化的 shell 会保留当前环境和恢复状态。打开新 shell，或重新运行 `devwho init bash`/`zsh` 并执行输出，即可加载更新后的集成代码。配置、GitHub CLI 数据和配置前端备份会保留。Bash 的更新和卸载见 [Bash 指南](bash/README.zh-CN.md)。

卸载 Go/Rust 时，先从 shell 启动文件中移除自行添加的 `devwho init` 行，再只删除安装在 `~/.local/bin` 的可执行文件（例如 `devwho`，以及可选的 `devwho-setup`）。如果以后还会使用，请保留配置和 GitHub CLI 数据。


核心的实现语言不限制调用它的 shell：所有实现都提供 `init bash` 和 `init zsh`。使用相应功能时仍需 Git 2.31 或更高版本以及可选的 `gh`/OpenSSH。Windows/PowerShell 和编辑器身份集成仍属实验或后续工作。

## 共同行为与格式

四种 core 都实现[兼容核心 v1 契约](../spec/compatibility-core-v1.zh-CN.md)，包括配置校验、profile 切换、Git/gh 适配器、诊断、子进程行为、真实 shell 集成和可恢复状态。[可执行的一致性 runner](../conformance/README.zh-CN.md)检查共用 fixture 及跨 core 的恢复状态互通。记录的结果和平台覆盖取决于具体实现与 runner；依赖某个平台前请查看相应记录。

所有 core 都支持完整 TOML profile 和可选的、显式选择的[字面量 dotenv 输入](../spec/dotenv-v1.zh-CN.md)。dotenv 只选择一个通用环境变量 profile，不与 TOML 合并，也不会被 source 或插值。如果导出会丢失 Git、SSH、GitHub 或 unset 语义，命令会拒绝导出。详见[配置格式指南](../docs/zh-CN/configuration-formats.md)。

可选的 [Go 配置前端](../docs/zh-CN/configuration-ui.md)提供中英文终端表单，以及带版本检查和私有备份的 read/replace 接口。它写入所有 core 共用的 TOML 格式，不是任何 core 的必需依赖。

拟议的[原生环境变量约定](../spec/environment-v1.zh-CN.md)是独立草案。本仓库提供了一个仅用标准库的原生参考使用方示例，位于 [`examples/native-notes`](../examples/native-notes)；但不声称已有第三方采用或 Git/gh 原生集成。示例自行管理应用配置和存储，不依赖兼容核心。

## 构建与贡献

各实现 README 说明安装方式、运行时依赖和该实现的验证情况。使用 [`scripts/package_cores.py`](../scripts/package_cores.py) 构建产物；CI 的 `cores` job 会构建并测试 Ubuntu 和 macOS runner 产物。请查看[实际工作流运行](https://github.com/lin594/devwho/actions/workflows/ci.yml)，不要把已配置的 job 当作通过证据。修改共同行为前，请参阅[共用契约](../spec/compatibility-core-v1.zh-CN.md)、[一致性测试套件](../conformance/README.zh-CN.md)和[贡献指南](../CONTRIBUTING.zh-CN.md)。
