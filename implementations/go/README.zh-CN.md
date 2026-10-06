# Go 兼容核心

[English](README.md) | [简体中文](README.zh-CN.md) · [通用预编译安装、更新与卸载指南](../README.zh-CN.md#在-linux-或-macos-安装预编译-go-core)

这是 [compatibility core v1](../../spec/compatibility-core-v1.zh-CN.md) 的独立实现，负责配置解析、校验、环境编译、可恢复切换、Bash/Zsh 渲染、子进程执行与诊断。运行时不调用 Python 或其他 DevWho 核心。

Unix 使用 `exec` 保留 argv、退出状态和信号。Windows 进程执行明确不支持，请使用受支持的 Unix 环境。CI 运行会提供开发构建产物，目前没有正式标签发布；请查看成功的目标运行及其平台验证结果。

托管二进制按平台构建，不是通用二进制。Go Linux 构建会因构建配置而静态链接或动态链接；请检查对应归档的 `RUNTIME.txt`，不要假设所有构建使用相同链接方式。目前不宣传 Linux ARM64 支持。macOS ARM64 二进制按实际 runner 架构构建；请确认对应目标运行及其 runtime 说明。

## 构建与使用

构建需要 Go 1.23 或更新版本；编译后的可执行文件不需要 Go 或独立 TOML 包。Git、SSH、gh 仅在相应功能中作为可选工具使用。新手下载和安装步骤见[通用指南](../README.zh-CN.md#在-linux-或-macos-安装预编译-go-core)。

```sh
cd implementations/go
go mod download
go mod verify
go test ./...
# Linux：禁用 cgo 构建静态 Linux 可执行文件。
CGO_ENABLED=0 go build -trimpath -o devwho .
# macOS：使用平台工具链默认设置。
# go build -trimpath -o devwho .
./devwho --config /absolute/path/config.toml list
./devwho --config /absolute/path/config.toml exec work -- git status
eval "$(./devwho --config /absolute/path/config.toml init bash)"
setdev work
unsetdev
```

支持 `--help`、`--version`、`--config PATH`、`list`、`show`、`current --verbose`、`doctor [PROFILE] [--offline]`、`exec`、`config path/init`、`init bash/zsh` 以及内部 transition/bootstrap/notice 接口。配置初始化是显式、排他、私有的（文件 0600，新目录 0700）。Shell 初始化只输出代码，固定可执行文件和解析后的配置路径，不编辑启动文件。`__DEVWHO_STATE` 不导出，其 JSON v1 状态可与 Python 核心互操作。

通用环境值为字面值。SSH/gh 语义路径使用恢复后并应用目标配置的 HOME。作者/提交者覆盖变量以及 GitHub 令牌冲突在恢复前检查。Git 运行时配置保持顺序与第三方追加项，篡改导致原子失败。Shell 渲染器先检查只读、数组与不支持的属性，再应用补丁。通过 Git 运行时配置设置身份，cherry-pick/rebase 保留原作者，不持续导出 `GIT_AUTHOR_*` 或 `GIT_COMMITTER_*`。

## 可选 dotenv 前端

保留现有 TOML，或显式使用 `--env-file /absolute/path/work.env`。文件需要有效的 `DEVWHO_PROFILE=work` 标记或 `--env-profile work`；两者同时存在时必须一致。`--env-file` 与 `--config` 互斥，`--env-profile` 需要前者。不合并来源、不发现当前目录文件、不自动激活。文件规范化为一个通用 env 配置，标记作为元数据消费，并设置快捷配置。Shell 初始化固定文件和配置名称；`config init` 拒绝 dotenv 来源。

支持 UTF-8 LF/CRLF、注释、`export KEY=VALUE`、无引号值、字面单引号和 JSON 转义双引号。拒绝重复键、裸键、NUL/孤立 CR、无效 Unicode、保留作者/运行时变量及危险键。美元表达式保持字面含义。`config export-env PROFILE` 显式输出标记和值，并拒绝语义设置或 unset 设置，避免有损导出。常规读取命令仍隐藏自定义值。

```sh
./devwho --env-file /absolute/path/work.env list
eval "$(./devwho --env-file /absolute/path/work.env init bash)"
setdev
unsetdev
```

## 可选独立编辑器

通过 `go build -tags setup -o devwho-setup .` 构建无需 Python 的配置表单和版本检查 JSON API。它为所有核心输出标准 TOML，保留高级字段和有序 Git 值，并使用私有备份和原子保存。详见 [中文说明](SETUP.zh-CN.md) / [English](SETUP.md)。

## 更新与卸载

更新 `~/.local/bin/devwho` 中的预编译程序时，按[通用指南](../README.zh-CN.md#在-linux-或-macos-安装预编译-go-core)校验匹配归档并替换该文件；只有需要更新可选工具时才替换 `~/.local/bin/devwho-setup`。已初始化的 shell 会保留当前环境和恢复状态；打开新 shell，或重新运行 `devwho init` 并执行输出，以加载更新后的集成。配置、GitHub CLI 数据和 `.devwho-backups` 会保留。卸载时先从 shell 启动文件移除自行添加的 `devwho init` 行，再只删除已知安装程序，例如 `rm "$HOME/.local/bin/devwho"`；若已安装可选工具，再删除 `rm "$HOME/.local/bin/devwho-setup"`。

## 验证与限制

`core_test.go` 覆盖等价 TOML 编码与顺序、模式拒绝、缺失/空/非空基线、连续切换、幂等性、状态结构与大小限制、运行时篡改和追加项、继承冲突、HOME 路径，以及真实 Git cherry-pick/rebase 作者。仓库的可执行文件验收工具和 CLI/Shell 测试提供更广泛的跨语言验证。

本地证据及工具链来源见 `VERIFICATION.md`。其中没有列出的平台仍为覆盖缺口，包括真实 macOS Bash 3.2。渲染器使用兼容 Bash 3.2 的语法，但当前 Bash 的测试不等于 Bash 3.2 验证。模拟 gh 测试仅验证本地诊断，不代表真实认证。激活不访问网络，也不持久修改 Git/SSH 配置或凭据。

## 依赖

`go.mod` 与 `go.sum` 固定全部构建模块图。唯一外部代码依赖是 MIT 许可的 [pelletier/go-toml/v2 v2.3.1](https://github.com/pelletier/go-toml/tree/v2.3.1)。通过其 [AST API](https://pkg.go.dev/github.com/pelletier/go-toml/v2/unstable) 保留 Git 配置插入顺序，避免 Go map 的无序迭代。该不稳定 API 通过精确版本固定和等价测试保护。详见 [第三方声明](THIRD_PARTY_NOTICES.md) 和 [许可证](licenses/go-toml-LICENSE)。除此之外仅使用 Go 标准库。
