# 兼容核心 v1——跨语言契约

[English](compatibility-core-v1.md) | [简体中文](compatibility-core-v1.zh-CN.md) · [各语言实现](../implementations/README.zh-CN.md)

**状态：**Python、Go、Rust、Bash 均已实现，并有[共用可执行一致性 runner](../conformance/README.zh-CN.md)。本契约与拟议的[原生环境约定](environment-v1.zh-CN.md)相互独立。

基准行为以 [946ad9e](https://github.com/lin594/devwho/tree/946ad9ef771750aab9570992f8af77575a69570b) 中的 Python 核心、[命令参考](../docs/zh-CN/reference.md)和回归测试为准。对此基准的修正必须作为明确且有文档记录的契约变更提出，不能成为不同语言实现间的意外差异。只通过少数切换示例不足以证明完整兼容。

## 1. 完整实现的含义

每个 Go、Rust 或 Bash 实现都要自行负责配置解析、校验、环境编译、可恢复切换、CLI 执行、诊断以及 Bash/Zsh 代码生成。运行时不得调用 Python、由 Python 构建的辅助程序或另一个核心实现。语言绑定、启动器、SDK 或仅支持 Git 的子集都不算完成移植。

用户选择一种实现，并继续使用现有 profile 文件和公开命令。开发和测试依赖可以不同于运行时依赖。可以用 Python 编写测试驱动，但新移植版的运行时验收环境中不得有 Python。

## 2. 公开命令和行为

支持 `--help`、`--version`、全局选项 `--config PATH` 和以下命令：

| 接口 | 必需行为 |
|---|---|
| `list`、`show PROFILE` | 列出名称；显示支持的 profile 元数据，但不泄露通用环境变量值或凭据。 |
| `current [--verbose]` | 显示所选标记或 `none`；verbose 模式还要显示生效的 Git 身份和配置位置。 |
| `doctor [PROFILE] [--offline]` | 检查当前环境，但不激活指定 profile。检查实际 Git author/committer 和已配置的值；仅在明确执行在线诊断时查询 gh。 |
| `exec PROFILE -- COMMAND ...` | 为子进程树应用 profile，保留 argv、退出状态和信号，并确保调用方不变。命令不存在时返回 127；命令不可执行时返回 126。 |
| `config path`、`config init` | 解析同一个配置文件路径；显式、私密且独占地初始化，不覆盖已有文件。 |
| `init bash`、`init zsh` | 输出集成代码，不编辑启动文件。固定所选可执行文件和配置路径。 |
| `setdev [PROFILE]`、`unsetdev` | 提供 shell 函数，以激活显式/快捷 profile 并恢复 shell baseline。 |

`doctor` 只有在所有请求的检查均通过时才返回 0；遇到失败或不匹配时返回 1；检查未完成/无法验证时返回 2，包括本地工具不可用或跳过网络检查。若同时存在失败和未验证，失败优先。诊断信息不得泄露任意环境变量值、令牌或子进程原始错误输出。

命令输出语义和退出码必须匹配。帮助信息排版、JSON 空格和正确加引号的 shell 代码格式不要求逐字节相同。生成的初始化输出必须是有效且可执行的 shell 代码；诊断信息写入 stderr。

## 3. 配置兼容性

遵守版本 1 架构和查找优先级：显式 `--config`，然后 `DEVWHO_CONFIG`，再 `$XDG_CONFIG_HOME/devwho/config.toml`，最后 `~/.config/devwho/config.toml`。原生应用不必读取此文件。

TOML 是必须继续支持的**现有兼容格式**，但不是整个生态永久只能使用的格式。已提供可选的 [dotenv 输入](dotenv-v1.zh-CN.md)，规范化为相同的 profile/切换模型。该格式使用独立的语法和选择规则，同时保留完整 TOML 支持。

所有实现都必须接受基准架构可接受的 TOML 1.0 配置编码，包括带引号键、点分键、内联表、多行字符串、Unicode 转义和多行数组。无效 TOML、重复定义、未知字段、类型错误和无效 profile 都必须拒绝。逐行读取键值的近似解析器不算兼容的 TOML 解析器。[TOML 1.0 规范](https://toml.io/en/v1.0.0)

必需覆盖的架构内容：

- `settings.default_profile`、`shortcut_profile` 和 `handoff_warning`。
- Git 姓名/邮箱必须成对；签名密钥、格式、布尔开关，以及保持顺序和多值的 `git.config` 条目。
- `git_ssh.identity_file` 和 `identities_only`。
- `github.hostname`、`expected_user` 和 `config_dir`。
- 通用环境变量字面值和显式 `unset_env`；拒绝保留/不安全键以及语义重叠设置。

字面值绝不执行 shell 展开。语义化 SSH 和 gh 路径必须是绝对路径、`~` 或以 `~/` 开头；路径应在恢复先前受管值、应用目标环境变量和取消设置项之后，根据目标环境中的有效 `HOME` 解析。主目录路径遇到缺失/相对 `HOME` 时必须拒绝，并要求所选 SSH 密钥文件存在。切换工作目录不得改变已选密钥或 gh 上下文。

## 4. 切换与适配器兼容性

1. 应用切换前，必须校验完整 profile、继承到的冲突、状态和 shell 可写性。只有当切换要新增或此前由 DevWho 管理 Git 运行时配置时，才校验 Git 运行时配置对；不管理运行时配置的纯 env profile 会原样保留无关的格式错误 `GIT_CONFIG_COUNT`。未知 profile 或任何必要校验失败，都必须让环境和状态保持不变。
2. 分别保留 baseline 中缺失、空值和非空值。重复激活必须幂等。A→B→C→unset 应恢复原始 baseline，而非 B 或一叠旧 profile。切到 B 后 A 独有的值必须恢复。
3. 保留现有 Git 运行时配置和重复值的顺序。追加受管的身份/签名/配置区块。保留之后由其他程序追加的无关条目；若已有前缀或受管区块被改动，则拒绝移除，不能误删无关配置。按 baseline 恢复被覆盖/孤立的索引变量；遵守无效输入和大小限制。
4. Git 身份通过运行时 `user`、`author` 和 `committer` 姓名/邮箱配置编译。不得长期导出 `GIT_AUTHOR_*` 或 `GIT_COMMITTER_*`。Cherry-pick 和 rebase 必须保留原作者。
5. 在恢复操作可能掩盖冲突前，拒绝继承到的非空 `GIT_AUTHOR_NAME`、`GIT_AUTHOR_EMAIL`、`GIT_COMMITTER_NAME` 和 `GIT_COMMITTER_EMAIL`。若设置了语义化 GitHub 配置，还要拒绝继承环境或目标通用环境变量中的 `GH_TOKEN`/`GITHUB_TOKEN`。绝不静默清除冲突。
6. Git SSH 和 GitHub 设置通过现有适配器变量编译。身份选择不代表认证成功；普通激活保持离线。必须区分提交身份、登录身份和推送凭据。
7. 保留无关配置和代理设置。激活不得修改全局/仓库 Git 配置、已保存的 remote、SSH 配置、凭据、文件或分支。可选交接提醒不得 stash、清理、认领改动或关闭窗口。

## 5. Shell 生命周期与内部状态

支持真实 Bash 和 Zsh，包括当前 macOS 测试覆盖使用的 Bash 3.2。若要求更高版本，必须明确披露，并记录为测试覆盖缺口，不得宣称平台支持程度相同。

新打开的独立 shell 可以将配置的默认 profile 作为 baseline 启动。明确继承到的 profile 应继续生效；子 shell 会把继承环境作为自己的 baseline。恢复状态必须保持未导出。其他终端和窗口不会因另一个终端切换而改变。

正确地将引号、美元符号、命令替换、反引号、换行、控制字符、Unicode 和空字符串都作为数据引用。修改任何受管变量前，先检查只读变量、数组和不受支持的 shell 属性。所有核心语言都必须做到这一点；使用编译语言本身不会令输出安全。

核心间一致性必须保留基准实现版本 1 JSON 状态语义（`version`、`profile`、`baseline`、`managed`、`runtime`）和内部切换请求行为。不能只检查 JSON 语法，还必须检查结构和限制。状态通过 stdin 与未导出的 shell 变量在内部传递；它不属于原生应用 API。比较解析后的状态和环境结果，不比较 JSON 空格。

使用 fixture 和内部接口测试 Python→Go→Rust→Bash 的切换。公开 `init` 会固定到一种可执行程序；核心间状态测试不代表改变 PATH 就能热切换已经初始化的 shell。要使用另一种实现，请开新终端，或在兼容状态下有意重新初始化。

## 6. 通用验收套件

提取与语言无关的输入和预期结果，然后对每个实现运行。通用测试运行器必须针对可执行文件路径，不能导入 Python 核心类。现有 Python 单元测试仍有价值，但不足以证明其他语言的实现符合要求。

| 类别 | 必需证据 |
|---|---|
| 解析 | 等价 TOML 格式、有效/无效架构、重复定义、Unicode/字面值/空值/多行值、保留键、路径和 HOME 案例。 |
| 切换 | 无 baseline/空值/既有 baseline；重复切换；A→B→C→unset；未知 profile；状态损坏；运行时前缀/受管区块冲突；第三方追加条目。 |
| Shell | 真实 Bash 3.2/当前 Bash 和 Zsh；只读/数组/属性失败；启动默认值、快捷切换、子进程继承、独立终端；没有命令注入。 |
| Git | 实际提交身份覆盖旧仓库设置；签名设置；rebase/cherry-pick 原作者保留；配置、remote、分支、未提交文件和代理状态不变。 |
| SSH/gh | 路径安全引用、密钥缺失、主机/配置隔离、冲突的 author/token 变量；用确定性模拟响应覆盖 gh 匹配/不匹配/不可用。CI 不要求凭据。 |
| 进程/诊断 | argv 原样传递、父进程隔离、子进程状态/信号、126/127 情况；doctor 的 0/1/2 和敏感信息屏蔽；激活期间不联网。 |
| 分发 | 在无 Python 环境中全新安装并运行完整验收；检查可执行文件/脚本依赖；实际支持的操作系统/架构任务和校验和。 |
| 互操作 | 所有实现使用相同配置/示例；解析后的状态和切换输出一致，包括跨实现恢复。 |

实际账号或远端推送验证应作为独立、自愿参加且使用授权测试账号的集成测试。模拟响应不能报告为真实认证已验证。

## 7. 发布和兼容性声明

发布时应说明实现的核心契约、运行环境要求、已测试平台矩阵、已知缺口和制品来源。可以分阶段合入移植，但完整契约测试通过前必须保持实验状态。不支持的功能必须清楚报错；子集不能静默成功，也不能关闭完整核心实现事项。

原生环境草案必须保持独立。任何移植都不得自行发明一套 `DEVWHO_*` 变量词汇、改变现有 profile 标记的含义，也不得要求用户把 profile 文件转换为特定语言格式。
