# 原生 notes 消费端（Go）

这是一个小型但可实际运行的 `DEVWHO_PROFILE` 提案消费端。它直接读取进程环境，并自行维护账户映射和本地笔记文件操作。它不导入 DevWho 代码、不读取 DevWho 配置或私有状态，也不声称该标记可以验证用户身份。

采用状态：**参考消费端；没有声称任何第三方已采用。**

## 运行

需要 Go 1.23 或更新版本：

```sh
go run . --config ./notes.json status
go run . --config ./notes.json add '记下这件事'
go run . --config ./notes.json list
DEVWHO_PROFILE=work go run . --config ./notes.json add '工作笔记'
```

`notes.json` 由应用管理。相对笔记路径相对于该文件所在目录解析，也可以使用绝对路径。示例：

```json
{
  "default_account": "personal",
  "accounts": {
    "personal": "personal-notes.txt",
    "work-account": "work-notes.txt"
  },
  "profiles": {
    "work": "work-account"
  }
}
```

显式 `--account ID` 优先于 `DEVWHO_PROFILE`，即使环境值格式错误或没有映射也是如此。否则，变量缺失或为空时使用应用配置的默认账户；格式错误的标签和未知映射会在笔记操作前报错。`status` 显示选中的应用账户，但不会验证登录或身份。笔记是本地纯文本文件；新文件初始权限为仅所有者可访问，最终受主机操作系统策略约束。profile 标签作为字面数据处理，绝不会用作路径或命令。

dotenv 加载器可以提供普通的进程环境数据。例如，创建一个可信的 `.env` 文件并写入 `DEVWHO_PROFILE=work` 后，可由主机 CLI 启动：

```sh
../../bin/devwho --env-file .env --env-profile work exec work -- go run . --config ./notes.json add '来自 dotenv'
```

消费端不会读取生产者的 dotenv 文件，只使用最终进程环境。测试会使用 [`conformance/native/selection.json`](../../conformance/native/selection.json) 中相同的跨语言选择用例。
