# 字面量 dotenv 输入——第 1 版

[English](dotenv-v1.md) | [简体中文](dotenv-v1.zh-CN.md)

Python、Go、Rust、Bash 兼容性 core 均提供此可选输入格式。原生应用仍只读取 `DEVWHO_PROFILE`，无须打开生产者的配置文件。现有第 1 版 TOML 配置继续完整支持。

## 文件与身份选择

`devwho --env-file PATH [--env-profile NAME] COMMAND` 显式选择单个文件，不能同时使用 `--config`；`--env-profile` 必须配合 `--env-file`。不扫描当前目录、不合并 TOML、不插值、不执行 Shell、不访问网络。显式 dotenv 输入优先于 `DEVWHO_CONFIG`。

文件须包含合法且非空的 `DEVWHO_PROFILE`，或通过 `--env-profile` 指定名称。两者同时存在时必须相同；参数不能绕过文件中空的或非法的 marker。marker 被解析为 profile 名称，其余赋值成为普通 `profile.env`。输入生成一个 profile，以它作为 `setdev` 的快捷选择，但不设置启动默认身份。`unsetdev` 恢复切换前基线。Shell 初始化代码固定文件的绝对路径及 profile 名称。

## 语法

- 使用 UTF-8 和 LF/CRLF 换行；拒绝非法 UTF-8、NUL、孤立 CR、BOM 和跨物理行的值。
- 忽略空行及空格/制表符后的整行 `#` 注释；允许字面的 `export ` 前缀。
- 赋值为 `[A-Za-z_][A-Za-z0-9_]*=VALUE`，去掉键、等号两侧及无引号值两端的空格/制表符。重复键、只有键没有等号均报错。
- 无引号的 `$NAME`、`${NAME}`、命令替换和反引号均为字面量。无引号的 `#` 仅在前面有空格/制表符时开始注释，因此 `VALUE=#literal` 保留 `#literal`。
- 单引号内部全部按字面值读取，无转义。双引号使用 JSON 字符串转义，包括 `\n`、`\t`、`\r`、`\uXXXX` 和合法代理对；拒绝未知转义、未配对代理项及解码后的 NUL。
- 闭合引号后只允许空格、制表符及可选 `#` 注释；值不可跨越物理行。
- `KEY=` 表示显式空值；缺少键表示不管理该变量，不表示删除。需要显式删除时使用 TOML 的 `unset_env`。

这是 DevWho 约定的字面量子集，并非所有 dotenv 工具共用的标准。不要用 `source` 读取：字面值可能恰好是 Shell 代码。

## 校验与导出

现有 core 的变量名限制、作者变量冲突检查、只读变量预检、基线恢复和 Git 运行时配置所有权规则继续有效。拒绝原始 `GIT_CONFIG_*`、持久作者覆盖及保留的 DevWho/Shell 启动变量。普通 `GH_CONFIG_DIR` 仅是环境值，不代表验证过的 GitHub 账号。

`devwho [--config PATH] config export-env PROFILE` 输出 marker 和用 JSON 双引号包裹的普通环境赋值，也支持显式 dotenv 输入。若 profile 包含 Git/GitHub/SSH 语义设置或 `unset_env`，则在输出前报错，避免静默丢失功能。输出可能含私密值，保存时应使用严格权限，不要提交到仓库。

`config path` 显示所选输入路径，dotenv 模式下拒绝 `config init`。配置前端写入 TOML；dotenv 是简单的可选输入/导出，不是另一份隐藏的全局状态。

可执行验收见 [dotenv 数据](../conformance/fixtures/dotenv.json) 和 [公共测试](../conformance/test_dotenv.py)。
