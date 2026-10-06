# DevWho 需要 TOML 吗？dotenv 应放在哪里？

[English](../configuration-formats.md) | [简体中文](configuration-formats.md) · [生态概览](ecosystem.md)

**建议：**让运行时约定与文件格式无关，保留现有 TOML profile，并在解析和切换规则确定后，将 dotenv 作为可选的简单输入格式。DevWho 核心加载 dotenv 目前只是提案，尚未实现。跟踪事项见 [issue #6](https://github.com/lin594/devwho/issues/6)。

## 三个不同的问题

| 关注点 | 契约 |
|---|---|
| 原生应用读取什么 | 从进程环境读取 `DEVWHO_PROFILE`。应用不必打开配置文件，也不需要知道值是如何保存的。 |
| 提供方如何保存用户选择 | 由提供方决定：现有 TOML、拟议的 dotenv、IDE 设置或其他表示方式。 |
| 兼容核心如何切换现有工具 | 将经过校验的 profile 转为可恢复的环境补丁和有序 Git 运行时配置。所有核心实现都保留这些语义。 |

```text
现有 TOML ───────────┐
拟议的 dotenv 输入 ──┼→ 规范化 profile → 共用校验/切换规则
其他提供方输入 ─────┘                    → 当前工具适配器

任意上下文提供方 → DEVWHO_PROFILE → 原生应用自己的账号映射
```

与其要求未来每个提供方都使用 TOML，不如确保共用模型和行为一致。当前文件格式仍是现有兼容契约的一部分，因此不能让现有用户失去可用配置。

## 普通 dotenv 文件可以提供原生上下文

对于已经支持 dotenv 的启动器，文件可以只有这一行：

```dotenv
DEVWHO_PROFILE=work
```

启动器加载后，未来的原生使用方就能从环境读取该值。它不需要 `version` 行、Python 依赖或 dotenv 文件本身。这不是新增的 `devwho` 命令；如果没有适配器，今天的 Git 或 gh 也不会因此自动选账号。

Dotenv 也可以保存现有工具使用的字面设置。例如：

```dotenv
GH_HOST=github.com
GH_CONFIG_DIR=/home/jane/.config/gh-work
EDITOR=vim
```

这些是现有工具接口，不是新增的通用 DevWho 变量。未来核心的加载器应通过同一套可恢复引擎应用这些值，而不是 source 文件后丢失 baseline 和冲突检查。仅选择 gh 目录并不能验证其登录。

## 为什么保留现有结构化格式？

| 需求 | 普通 `KEY=value` | 现有 TOML profile |
|---|---|---|
| 字面环境设置 | 很自然。 | `env` 支持。 |
| 空值 | 可以用 `KEY=` 表示。 | 使用空字符串。 |
| 明确移除变量 | dotenv 没有通用表示；缺少某个键不等于移除变量。 | 使用 `unset_env`。 |
| Git author、签名、SSH 和预期 gh 账号 | 可以设置原始工具变量，但无法表达所有语义校验。 | 使用有类型的字段，并执行冲突检查和诊断预期校验。 |
| 重复且有序的 Git 配置 | 扁平映射很难自然地保留重复项。 | `git.config` 下的值数组可以保留顺序。 |
| 多个 profile 和启动默认值/快捷方式 | 还需选择文件，并另定元数据约定。 | 现有命名 profile 和 `settings` 已支持。 |

把 JSON 数组塞进环境变量字符串，或设计一堆带编号的键，只会以更不清晰的方式重造结构化格式。我们应支持范围明确的简单 dotenv 用例，而不是假装它能表达所有现有功能。高级用户可以继续使用 TOML；未来完整的扁平格式需要单独设计并配套共用测试，不能悄悄丢失功能。

## 拟议的核心 dotenv 加载规则

Dotenv 并没有一种普遍适用的统一语法：Node 明确记录了自己的语法，而 Docker Compose 会在未加引号和双引号的值中执行插值。DevWho 必须自行选择并测试行为，不能让每种语言的实现各自继承所用库的语法。[Node 文档](https://nodejs.org/api/environment_variables.html#dotenv)、[Compose 插值规则](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)

实现可选输入格式前，必须：

1. 定义精简的字面语法，并为 UTF-8、LF/CRLF、空白、注释、引号、转义、重复键和无效/NUL 输入准备共用 fixture。不得使用 `source`、`eval`、命令替换或隐式 `$VAR` 插值。明确拒绝不支持的语法。
2. 区分键缺失、空值和显式移除。不要意外发明 unset 语法。在明确规定扩展前，移除变量仍使用现有结构化格式。
3. 明确如何在输入中指定 profile、用户如何显式选择文件，以及输入值如何与 TOML/默认值合并。拒绝歧义，或明确给出优先级。不得根据当前目录自动加载仓库里的 `.env`。
4. 将 `DEVWHO_PROFILE` 选择元数据与任意环境赋值分开。如果所选 profile 名称与文件中的标记冲突，必须在改动环境前解决。继续保留现有的保留键、author/token 和 shell 属性检查。
5. 复用规范化、校验、原子性、恢复和诊断逻辑。如果未来接受原始 `GIT_CONFIG_*` 区块，就必须明确管理区块的规范化和索引校验；直接赋值 count/index 变量会覆盖无关运行时设置。持久设置 `GIT_AUTHOR_*` 不能替代 Git 适配器。
6. 继续明确执行预期账号验证。通用 env-only profile 不得声称可以执行依赖 `expected_user` 和 GitHub 适配器冲突规则的语义化 GitHub 检查。
7. 为每个声称支持 dotenv 的实现添加等价测试。完整 Go/Rust/Bash 移植版仍须兼容 TOML；只提供 dotenv 不能算完整核心移植。

首个 dotenv 实现应解决范围清晰的字面环境变量使用场景。原生应用和其他提供方都不应被迫实现 DevWho 的 TOML 解析器才能加入生态。在有明确且兼容的迁移方案前，现有核心会继续支持 TOML。
