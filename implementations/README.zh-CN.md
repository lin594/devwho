# 选择一种兼容核心实现

[English](README.md) | [简体中文](README.zh-CN.md) · [项目概览](../README.zh-CN.md)

安装**一种** core 即可。RC1 推荐 Linux x86-64 使用静态 Go，macOS **13+ ARM64** 使用 Go；Rust macOS ARM64 二进制声明最低 macOS **11.0**。这些是部署最低版本，与实际托管 macOS 26.6.2 测试宿主不同。[已验证产物矩阵](../README.zh-CN.md#已验证候选产物)和归档的 `RUNTIME.txt` 分别记录目标、系统库、最低部署版本和实测宿主。

Python 要求 3.11+，无第三方运行时 Python 包；Bash 要求 Bash 3.2+、jq 1.6+、Perl 5.18+ 和标准工具。Go/Rust 二进制无需 Python/编译器。Git 2.31+、gh 和 OpenSSH 是各自功能的消费依赖。RC1 不发布需要 glibc 2.39 的 Linux Rust 二进制；它仍参加构建/测试，也可从源码自行构建。Linux ARM64、macOS x86-64、Alpine/musl、Windows/PowerShell 和编辑器身份绑定未验收。

[v0.1.0-rc.1 预发行](https://github.com/lin594/devwho/releases/tag/v0.1.0-rc.1)提供选定产物、完整 `SHA256SUMS`、`RELEASE-MANIFEST.json` 和 FZ2 下载产物验收证据。程序版本使用 `0.1.0-rc.1`，文件名采用等价的 PEP 440 `0.1.0rc1`。普通 Actions 下载仍是开发构建。[发行计划](../release-plan.json)指定八个完整产物和唯一 Python 来源；[手工发行步骤](../docs/zh-CN/releasing.md)强制检查完整性与来源。

### 在 Linux 或 macOS 安装预编译 Go core

1. 选择匹配归档：Linux x86-64 为 `devwho-0.1.0rc1-go-linux-x86_64.tar.gz`，macOS 13+ ARM64 为 `devwho-0.1.0rc1-go-darwin-arm64.tar.gz`。从[预发行](https://github.com/lin594/devwho/releases/tag/v0.1.0-rc.1)**只下载该归档和 SHA256SUMS**。例如：

   ```sh
   asset=devwho-0.1.0rc1-go-linux-x86_64.tar.gz  # macOS: devwho-0.1.0rc1-go-darwin-arm64.tar.gz
   base=https://github.com/lin594/devwho/releases/download/v0.1.0-rc.1
   curl -fLO "$base/$asset"
   curl -fLO "$base/SHA256SUMS"
   ```

2. 只核验所选文件的精确条目，无需其他平台产物：

   ```sh
   awk -v name="$asset" '$2 == name {print; found=1} END {if (!found) exit 1}' SHA256SUMS > selected.SHA256SUMS
   sha256sum -c selected.SHA256SUMS  # Linux
   # macOS: shasum -a 256 -c selected.SHA256SUMS
   ```

3. 解压、读取 `RUNTIME.txt`，安装到用户目录：

   ```sh
   tar -xzf "$asset"
   cd "${asset%.tar.gz}"
   cat RUNTIME.txt
   mkdir -p "$HOME/.local/bin"
   install -m 755 devwho "$HOME/.local/bin/devwho"
   install -m 755 devwho-setup "$HOME/.local/bin/devwho-setup"  # 可选配置编辑器
   export PATH="$HOME/.local/bin:$PATH"
   devwho --version
   ```

   无需编译器；PATH 修改只影响当前终端，需要时可加入启动文件。
4. 用 `devwho-setup --language zh-CN configure` 保存配置，或显式运行 `devwho --config /absolute/path/config.toml config init` 创建 TOML，修改示例身份，然后：

   ```sh
   eval "$(devwho --config /absolute/path/config.toml init bash)"  # Zsh: init zsh
   setdev PROFILE_NAME
   devwho doctor --offline
   unsetdev
   devwho --config /absolute/path/config.toml exec PROFILE_NAME -- git var GIT_AUTHOR_IDENT
   ```

   `unsetdev` 恢复初始环境。若配置了在线认证检查，doctor 离线退出 2 表示未验证，不是远端账号归属已获证明。

Rust macOS ARM64 用户选择 `devwho-0.1.0rc1-rust-darwin-arm64.tar.gz`，以相同方式校验、解压并安装 `devwho`；该包不附配置编辑器。程序声明最低 macOS 11.0，实测宿主记录为 26.6.2。Bash 安装/更新/卸载见[指南](bash/README.zh-CN.md)，Python 源码/zipapp 安装见[入门](../docs/zh-CN/getting-started.md)。

更新 Go/Rust 时核验新归档后只替换已安装程序。现有 shell 保留环境和恢复状态；新开 shell 或重新执行 `devwho init bash`/`zsh` 加载新集成。配置、gh 数据和编辑器备份保留。卸载时先移除自己添加的启动行，再只移除已安装的已知程序；除非明确另行删除，否则保留配置与凭据。

## 共同行为与格式

四种 core 都实现[兼容核心 v1 契约](../spec/compatibility-core-v1.zh-CN.md)，包括配置校验、profile 切换、Git/gh 适配器、诊断、子进程行为、真实 shell 集成和可恢复状态。[可执行的一致性 runner](../conformance/README.zh-CN.md)检查共用 fixture 及跨 core 的恢复状态互通。记录的结果和平台覆盖取决于具体实现与 runner；依赖某个平台前请查看相应记录。

所有 core 都支持完整 TOML profile 和可选的、显式选择的[字面量 dotenv 输入](../spec/dotenv-v1.zh-CN.md)。dotenv 只选择一个通用环境变量 profile，不与 TOML 合并，也不会被 source 或插值。如果导出会丢失 Git、SSH、GitHub 或 unset 语义，命令会拒绝导出。详见[配置格式指南](../docs/zh-CN/configuration-formats.md)。

可选的 [Go 配置前端](../docs/zh-CN/configuration-ui.md)提供中英文终端表单，以及带版本检查和私有备份的 read/replace 接口。它写入所有 core 共用的 TOML 格式，不是任何 core 的必需依赖。

拟议的[原生环境变量约定](../spec/environment-v1.zh-CN.md)是独立草案。本仓库提供了一个仅用标准库的原生参考使用方示例，位于 [`examples/native-notes`](../examples/native-notes)；但不声称已有第三方采用或 Git/gh 原生集成。示例自行管理应用配置和存储，不依赖兼容核心。

## 构建与贡献

各实现 README 说明安装方式、运行时依赖和该实现的验证情况。使用 [`scripts/package_cores.py`](../scripts/package_cores.py) 构建产物；CI 的 `cores` job 会构建并测试 Ubuntu 和 macOS runner 产物。请查看[实际工作流运行](https://github.com/lin594/devwho/actions/workflows/ci.yml)，不要把已配置的 job 当作通过证据。修改共同行为前，请参阅[共用契约](../spec/compatibility-core-v1.zh-CN.md)、[一致性测试套件](../conformance/README.zh-CN.md)和[贡献指南](../CONTRIBUTING.zh-CN.md)。
