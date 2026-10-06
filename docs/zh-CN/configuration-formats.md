# 配置文件与应用读取的环境

[English](../configuration-formats.md) | [简体中文](configuration-formats.md) · [生态](ecosystem.md)

原生应用只需读取 `DEVWHO_PROFILE`，无须 TOML 解析器、dotenv 库、DevWho SDK，也不需要访问其他程序的配置文件。用户如何编辑和保存 profile 是另一层的问题。

## 按需求选择输入方式

| 需求 | 使用方式 |
|---|---|
| 按提示配置 Git、账号及默认身份 | 可选的[中英文配置前端](configuration-ui.md)，保存所有 core 共用的普通 TOML。 |
| 完整 Git/GitHub/SSH 设置、多 profile、有序 Git 配置或显式删除变量 | 保留现有第 1 版 TOML 格式与校验规则。 |
| 少量字面量环境设置 | 显式 dotenv 输入，Python、Go、Rust、Bash 均支持。 |
| 为应用增加原生支持 | 读取进程环境，再使用应用自己的账号映射；不需要读取提供方的文件。 |

```text
交互配置 / 机器写入接口 → 校验后的 profile 存储（目前为 TOML）
字面量 dotenv 输入 ────→ 校验后的 profile
                                  ↓
                             当前会话切换
                                  ↓
                    DEVWHO_PROFILE + 现有工具适配器

原生应用 → 读取 DEVWHO_PROFILE → 应用自己的账号映射
```

不需要守护进程，也没有全局“当前账号”文件。保存配置与激活身份是两件事。未来可以更换存储后端，继续使用相同的校验和会话模型，而不改变应用约定。

## 试用 dotenv profile

把以下内容保存为私有的 `work.env`：

```dotenv
DEVWHO_PROFILE=work
EDITOR=vim
APP_ACCOUNT=work
```

```sh
devwho --env-file ./work.env exec work -- env
eval "$(devwho --env-file ./work.env init bash)"  # Zsh 改用 zsh
setdev
unsetdev
```

第一条命令会打印子进程环境，请在适合显示环境内容的场合使用。`setdev` 通过同一套可恢复引擎应用配置。文件中没有 marker 时，必须添加 `--env-profile work`。不会自动查找 `.env`，也不会与 TOML 合并；`$HOME` 和看似命令的内容均按字面值保留。

仅含普通环境设置的 TOML profile 可用 `devwho config export-env PROFILE` 导出。简单 dotenv 无法完整表达的 Git/GitHub/SSH 语义设置或显式删除操作，会让导出明确失败，而不是静默丢失。缺少键与空值含义不同。详见[完整语法、选择及导出契约](../../spec/dotenv-v1.zh-CN.md)。

## 为什么 profile 存储仍使用 TOML

普通环境赋值无法完整描述有序重复 Git 配置、默认/快捷 profile、显式删除及预期 GitHub 账号。把它们塞入编号变量或 JSON 字符串，实际上是在再造一种结构化协议。配置界面让初学者不必处理这些细节；原生应用则始终不必解析它。

TOML 是当前可替换的存储格式，也是对已有用户的兼容承诺，不是整个生态的硬性要求。dotenv 则适合它能够完整表达的简单输入。两者都无需 `DEVWHO_SPEC_VERSION` 环境变量；文件格式版本与规范文档修订号各有用途。
