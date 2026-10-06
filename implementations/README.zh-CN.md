# 选择一种兼容核心实现

[English](README.md) | [简体中文](README.zh-CN.md) · [项目概览](../README.zh-CN.md)

兼容核心让现有 Git、SSH 和 GitHub CLI 工作流程使用终端当前选择的上下文。我们希望用户可以选择适合自己机器的实现，同时保留**相同的 profile 文件、命令和行为**。

目前只有 Python 核心已经实现。标记为“规划中”的项目仍是实现工作，不是可安装的发行版。[原生应用约定](../spec/environment-v1.zh-CN.md)是独立草案，不依赖任何一种兼容核心。

## 实现选项

| 实现 | 状态/源码 | 最终用户所需环境 | 提供它的原因 |
|---|---|---|---|
| Python | 可用源码：[`src/devwho`](../src/devwho)；[`bin/devwho`](../bin/devwho) | Python 3.11 或更高版本；运行时不需要第三方 Python 包 | 当前完整实现和回归测试基准。 |
| Go | 规划中的完整移植；未来源码位于 `implementations/go/` | 匹配平台的预编译可执行文件；运行时无需 Python 或 Go 编译器 | 优先满足没有 Python 的用户，并便于分发单个二进制文件。 |
| Rust | 规划中的完整移植；未来源码位于 `implementations/rust/` | 匹配平台的预编译可执行文件；运行时无需 Python 或 Rust 编译器 | 基于独立构建生态的完整实现。 |
| Bash | 规划中的完整移植；未来源码位于 `implementations/bash/` | Bash，以及明确记录的系统工具和使用方工具；无需 Python 或编译器 | 为已有 Bash 的环境提供脚本安装方式。 |

用户只安装**一种**核心，而不是全部语言版本。核心使用哪种语言不限制调用它的 shell：每个完整移植版都必须提供 `init bash` 和 `init zsh`。在使用相应功能时，Git 2.31 或更高版本以及可选的 gh/OpenSSH 仍是使用方依赖。

Go 和 Rust 会构建可执行应用；构建工具只需安装在构建机器上，不一定要装到用户机器。发行制品仍需明确操作系统/CPU 目标、校验和及系统库要求。交叉编译成功不能证明制品在目标环境能运行。参见官方 [Go 构建指南](https://go.dev/doc/tutorial/compile-install)和 [Rust 构建指南](https://doc.rust-lang.org/book/ch01-03-hello-cargo.html)。

Bash 面临更复杂的解析工作：当前配置格式是 TOML，可恢复状态也需要结构化校验。完整 Bash 移植版必须正确实现这些要求，不能只转换几行 `key=value`，也不能调用 Python 核心。优先使用 Bash 和标准系统工具；如果需要外部解析器或辅助程序，必须明确说明并评估它是否符合简化安装的目标。完整解析器尚未完成时，应标记为实验版，并保持完整核心事项开放。

## 兼容承诺

所有实现都以[兼容核心 v1 契约](../spec/compatibility-core-v1.zh-CN.md)为目标：配置、切换、Git/gh 适配器、诊断、子进程行为以及安全的真实 shell 集成。只有通过通用一致性测试，并在 Python 不可用时通过运行时测试，移植版才算完成。Go/Rust 二进制文件或 Bash 函数调用 Python 不符合这一目标。

Python 源码树保留在现有位置，以维持包和构建兼容性。规范放在 `spec/`；语言实现会在有可工作的代码时分别放入各自目录。我们不会添加看起来可安装的空包骨架，也不会更改用户现有的工作区布局。

文件格式是另一个选择：[可选的 dotenv 输入](../docs/zh-CN/configuration-formats.md)可以规范化为相同 profile 和切换引擎。每个完整移植版仍必须接受现有 TOML profile。Bash 核心如果只支持 dotenv，就不能算完成完整核心任务。

## 交付顺序与跟踪工作

1. 建立共用契约和可执行的一致性 fixture。继续让 Python 实现通过测试，使其保留为参考实现。
2. 优先完成 Go 核心，并测试可下载二进制文件，让最多用户摆脱 Python 依赖。
3. 以相同测试套件开发完整的 Rust 和 Bash 替代实现。两者都可以分阶段提交并评审，但包装器或功能子集都不算完成。
4. 只为实际存在且通过所声明目标平台测试的制品编写发布打包和安装说明。即使编译器能够生成 Windows 可执行文件，PowerShell/编辑器集成仍需单独验收。

| 任务 | 跟踪问题 |
|---|---|
| 原生上下文约定 | [RFC #1](https://github.com/lin594/devwho/issues/1) |
| 完整核心共用一致性测试套件 | [#2](https://github.com/lin594/devwho/issues/2) |
| Go 完整核心 | [#3](https://github.com/lin594/devwho/issues/3) |
| Rust 完整核心 | [#4](https://github.com/lin594/devwho/issues/4) |
| Bash 完整核心 | [#5](https://github.com/lin594/devwho/issues/5) |
| 可选 dotenv 输入 | [#6](https://github.com/lin594/devwho/issues/6) |

以上都是待完成事项，不代表实现已经完成。贡献时请让行为修复和双语说明在各实现之间保持一致。
