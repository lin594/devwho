# 更新记录

[English](CHANGELOG.md)

## 0.1.0 — 尚未发布

- 支持以 TOML 配置文件管理开发身份，并将配置编译为环境变量；任意环境变量按字面值处理，也可显式清除变量。
- 支持 Bash/Zsh 中可恢复的 `setdev` / `unsetdev`，以及仅对指定进程树生效的 `devwho exec`。
- 支持通过 Git 运行时配置设置 Git 身份、签名选项、Git SSH 命令和 GitHub CLI 配置目录。
- 提供显式身份检查，可报告不匹配或暂时无法验证的情况。
- 支持初始化配置文件、可选启动默认身份/快捷身份，以及选择启用的工作区交接提醒。
- 增加真实 shell 和 Git 回归测试、Linux/macOS CI、Python 软件包和 zipapp 构建。
- 修正 SSH/GitHub 语义路径，使其不受工作目录变化影响，并依据目标配置中的有效 HOME 解析。
- `current --verbose` 显示生效的 Git 身份；为所有生成的软件包添加校验和。
- 修复 Python 3.11 下 shell 激活参数的兼容性。
- 新增贡献指南、安全说明和更新记录的简体中文版。
- 将原生环境约定草案与现有兼容性 core 分开说明，新增双语规范和完整 Go/Rust/Bash 实现计划。这些移植和原生应用集成尚未实现。
- 定义单变量上下文接口草案，单独说明可选 dotenv 输入与当前 TOML 格式的关系；dotenv 加载尚未实现。

PowerShell 和 VS Code 身份集成仍是后续实验功能。本版本尚无正式发布标签，也未发布到软件包仓库。
