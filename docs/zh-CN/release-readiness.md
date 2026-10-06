# 首个预发行候选版本验收

候选版本为 `v0.1.0-rc.1`；Python 包元数据和产物文件名采用等价的 PEP 440 写法 `0.1.0rc1`。完整范围和限制见[英文验收清单](../release-readiness.md)。

FZ2 Debian WSL、Linux x86-64 上已运行真实 Bash/Zsh/Git：

- Python 回归 84 项通过；Bash 分组中一个 Zsh 专属用例按预期跳过。
- Python、Go、Rust、Bash 各通过 71 项公共合同测试，包括跨 core 状态互换；上述预期跳过同样适用。
- Go core/配置前端单元测试与 vet、Rust 锁定依赖测试与构建、Bash 20 项实现测试、原生示例 9 项选择用例和四种 producer 集成通过。
- Ruff 格式/静态检查、Python 编译通过；wheel/sdist/zipapp 和 core 归档已构建并核验校验和。
- Go、Rust、Bash 在禁网、无 Python、无语言编译器的 Debian 运行容器内通过验收；Go 配置前端读写也通过。
- 本机工具为 Python 3.13.5、Go 1.27.1、Cargo 1.90.0、rustc 1.95.0。本地 Rust 产物与 Ubuntu CI 产物不同，发行物以其 CI 记录和 RUNTIME.txt 为准。

所有 core 归档名包含版本与实际验证目标，Bash 也区分 runner，避免重名覆盖。发行集合器核验来源校验和，拒绝损坏下载和同名异内容，生成统一 SHA256SUMS 和最终提交清单。

发布前仍须核实最终提交的完整托管 CI，下载并在 FZ2 安装运行托管产物，核对最终审查结论，再附提交/CI/校验证据发布明确标记的预发行。本机 Linux 验收不能替代 macOS CI 证据。

已知限制：Windows PowerShell/VS Code 身份绑定不在支持范围；真实双账号 GitHub/SSH/GCM 远端认证尚未验收。Linux ARM64、Alpine/musl、未实测的 macOS CPU 不作支持声明。Bash 依赖 jq、Perl；Rust 系统库要求以归档 RUNTIME.txt 为准。原生环境约定仍为草案，不宣称第三方采纳。

## RC1 产物计划

[明确的八产物计划](../../release-plan.json)选择 Linux x86-64 Go/Bash、macOS ARM64 Go/Rust/Bash 和唯一 Ubuntu/Python3.11 的 wheel/sdist/zipapp。Linux Rust 保留测试但因 glibc 2.39 不提供下载；RUNTIME.txt 区分 macOS 最低部署版本与测试宿主。[手工发行步骤](releasing.md)拒绝不完整/意外产物，并记录来源校验和及 CI 证据。
