# 参与 DevWho

[English](CONTRIBUTING.md)

感谢你关注 DevWho。我们欢迎范围清晰的小改动，包括问题反馈、文档修正和代码贡献。

## 从哪里开始

- **发现问题？** 先查看[已有问题](https://github.com/lin594/devwho/issues)。如果还没人报告，请新建 issue，说明你原本预期的结果、实际发生的情况，以及简短的复现方法。请使用虚构身份信息，并删除令牌、私人路径等敏感内容。
- **想改进文档？** 修改相关的 Markdown 页面或示例，然后提交拉取请求。只改文档时，请检查链接是否有效，命令和配置示例是否准确。无需为了文字改动而机械地增加测试。
- **想修改代码？** 从一个明确的问题开始，或在拉取请求中说明要解决什么。行为变化应补充或更新测试，尤其是涉及 shell 切换、Git 身份和子进程执行时。
- **想参与 core 开发？** Python、Go、Rust、Bash 实现共用[兼容契约](spec/compatibility-core-v1.zh-CN.md)和[可执行一致性测试套件](conformance/README.zh-CN.md)。构建要求和验证记录见[实现指南](implementations/README.zh-CN.md)。Go/Rust 运行时不依赖 Python/编译器；Bash 需要 jq 和 Perl。可选的 [Go 配置前端](docs/zh-CN/configuration-ui.md)与运行时 core 行为分开维护。
- **想让应用原生支持？** 请先讨论[环境约定草案](spec/environment-v1.zh-CN.md)。应用用自身语言读取统一环境变量，无需依赖 DevWho 库或 core 的配置解析器。

## 开发现有 Python core

目前的 Python 实现需要 Python 3.11 或更新版本。运行完整的 shell 集成测试还需要 Git 2.31 或更新版本、Bash 和 Zsh。其他实现将说明各自的构建要求，并运行相同的一致性用例。开发 Python 版本时，创建虚拟环境并安装项目及开发工具：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e . build ruff
```

## 运行相关检查

修改代码或 Python 测试时，请运行 CI 使用的检查：

```bash
.venv/bin/ruff format --check src tests scripts
.venv/bin/ruff check src tests scripts
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m build
.venv/bin/python scripts/build_zipapp.py
```

Shell 测试会使用真实的 Bash、Zsh 和 Git，并在临时 HOME 目录及仓库中运行；不需要 GitHub 账号或在线凭据。只修改说明文字时可以跳过测试套件，改为检查链接，并验证本次改动涉及的命令和配置示例。

[CI 工作流](https://github.com/lin594/devwho/actions/workflows/ci.yml)会在 Ubuntu、macOS 和 Python 3.11、3.13 组合上运行。macOS 使用系统自带的 `/bin/bash`。请查看工作流的实际运行结果，不要把配置好的任务当成已通过。

## 提交拉取请求

1. 保持改动聚焦；行为改变时同步更新相关文档。
   修改共用说明或示例时，请同步更新英文和简体中文版，保持命令和配置键一致。
2. 运行适用于本次改动的检查，并在拉取请求说明中列出结果。如果某项检查无法运行，请如实说明。
3. 向仓库提交拉取请求。用几句话说明问题和改动后的行为；如有关联 issue，请附上链接。

请勿提交个人身份配置、凭据、编辑器生成状态、构建产物或私人绝对路径。Shell 初始化命令的标准输出应只包含可执行的 shell 代码，诊断信息写入标准错误。日常贡献不要改写 Git 历史，也不要发布软件包或标签。

Windows/PowerShell 和编辑器身份集成不属于 v0.1 的支持范围。在对外宣称支持前，必须有真实的集成测试。
