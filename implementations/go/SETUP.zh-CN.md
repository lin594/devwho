# 独立配置编辑器

[English](SETUP.md) | [简体中文](SETUP.zh-CN.md)

`devwho-setup` 是可选的独立 Go 可执行文件，用于创建和编辑标准 DevWho TOML。无需 Python，也无需运行中的 DevWho 核心。所有核心均可读取其输出。它复用核心模式校验器，存储和交互表单通过独立构建标签排除在运行时核心之外，不激活配置或修改当前 Shell。

```sh
go build -tags setup -trimpath -o devwho-setup .
go test -tags setup ./...
./devwho-setup --config /absolute/path/config.toml configure
./devwho-setup --config /absolute/path/config.toml --language zh-CN configure
```

每次表单编辑一个配置。留空保留现有值；`-` 删除可选 SSH/GitHub 映射或默认/快捷配置选择。支持 Git 姓名/邮箱、SSH 私钥路径、GitHub 目录/登录名/主机、默认和快捷配置。高级字段和其他配置保留。保存前显示隐藏自定义值的预览，需要明确输入 `save`/`cancel`（中文模式也支持 `保存`）。取消或输入结束不会写文件或改变会话。不指定命令时进入表单。

## 机器接口

```sh
./devwho-setup --config /absolute/path/config.toml read
./devwho-setup --config /absolute/path/config.toml read --show-values
./devwho-setup --config /absolute/path/config.toml replace --if-revision missing < configuration.json
./devwho-setup --config /absolute/path/config.toml replace --if-revision CURRENT_SHA256 < configuration.json
```

`read` 输出 `{ "revision": "SHA256", "configuration": { ... }, "redacted": true }`。版本哈希使用文件的原始字节。默认隐藏通用 env 和任意 `git.config` 的值；`--show-values` 显式显示这些值。文件不存在时返回版本 `missing`、配置 `null`。路径采用与核心相同的显式路径、配置环境变量、XDG、HOME 优先级。

`replace` 从 stdin 读取原始版本 1 模式对象，**不接受** read 输出的包装对象。输入最大 1 MiB。重复 JSON 键、多个文档、未知字段、无效配置、无效 Unicode 转义和非整数版本在写入前拒绝。JSON↔TOML 往返保留 Git 运行时表的插入顺序和多值，JSON 输出也保留该顺序。表单复用同一校验与保存 API。

## 保存行为

通过持久的相邻 `config.toml.lock` 和 Unix `flock` 协调合作编辑器。锁必须是常规文件，打开时不跟随符号链接。在锁内检查期望版本，把旧文件原始字节保存到相邻 `.devwho-backups/`（目录 0700、文件 0600），写入并同步私有临时文件，再原子重命名为 0600 配置文件，最后同步父目录。新文件没有虚构的旧版本备份。直接配置符号链接或备份目录符号链接写入均拒绝。

版本过期时，在备份和替换前失败。不使用同一锁的外部工具仍可能与保存竞争。保存会规范化格式和注释；保留支持的字段与 Git 配置顺序，备份则保留原始字节。编辑器不单独保存凭据、不访问远程服务。明确不支持 Windows 写入，目前本地执行证据覆盖 Linux x86-64。

测试覆盖真实跨进程竞争、精确备份字节和权限、双语取消、模式和重复 JSON 拒绝、默认隐藏值、缺失文件创建、符号链接拒绝、特殊字符串和有序 Git 往返。
