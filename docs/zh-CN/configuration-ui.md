# 按提示配置身份

[English](../configuration-ui.md) | [简体中文](configuration-ui.md)

`devwho-setup` 是 Go 发行物附带的可选独立程序。不需要 Python，也不需要先运行 core；它保存的 profile 适用于**任意一种** DevWho core。

```sh
devwho-setup --language zh-CN configure
```

选择已有 profile 或输入新名称，填写 Git 姓名/邮箱，可选填写 GitHub CLI/SSH 设置，再选择默认与快捷身份。空白保留已有值，`-` 清除可选设置。预览后明确保存；取消或输入结束都不会写入文件。每次编辑一个 profile，其他 profile 与高级设置会保留。

保存后，在已初始化的终端运行 `setdev PROFILE`。配置前端不会改变当前 Shell 或已经打开的窗口。

## 文件、备份及其他编辑器

默认路径与 core 相同，也可用 `--config PATH` 指定。保存时校验完整 profile 格式、比较最初读取的修订值，再原子写入私有文件。同目录 `.devwho-backups/` 保留保存前文件的完整原始字节。新文件会重新排版且不保留注释，备份保留原注释，高级字段与 Git 配置顺序仍然保留。

两个 DevWho 配置前端不会静默覆盖对方刚保存的内容；不遵守协作锁的外部编辑器仍可能竞争，因此应先关闭它或重新读取配置。拒绝直接写入配置符号链接。

恢复时，先另存当前文件，选定对应的私有备份，再用 0600 权限复制回原位置。已有 Shell 持有自己的环境，恢复文件后应打开新终端或重新切换身份。

## 接入其他界面或自动化

`read` 返回修订值和脱敏配置，`read --show-values` 才会明确显示值。`replace --if-revision HASH|missing` 从标准输入读取原始 schema JSON，与交互界面使用同一套校验和保存操作。脱敏读取结果的外层对象不能直接当作 profile 文档写回。详见[机器接口与构建方式](../../implementations/go/SETUP.zh-CN.md)。

首个前端使用通用的终端表单。后续更丰富的 TUI/GUI 可以调用相同操作，不会成为 core 的强制依赖，也无需守护进程。
