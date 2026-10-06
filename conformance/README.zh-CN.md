# 验收一个实现

[English](README.md) | [简体中文](README.zh-CN.md)

公共验收只把 core 当作可执行程序调用，不导入被测实现的解析器、状态引擎或适配器。Python 是**测试驱动器**的依赖，不是 Go、Rust、Bash core 的运行依赖。

```sh
python3 conformance/run.py --executable /path/to/devwho --peer ./bin/devwho --report report.json
```

重复传入 `--peer` 可验证与其他 core 的恢复状态互通。验收覆盖完整 TOML profile、公共 JSON 数据、Git 配置顺序、真实 Bash/Zsh 会话、只读变量原子性、代理与基线恢复、诊断、子进程、dotenv 和字面量 SSH 参数。复用现有 CLI/Shell 黑盒测试；Python 专属打包测试仍位于 `tests/`。

测试 Bash 3.2 时设置 `DEVWHO_TEST_BASH=/path/to/bash-3.2`；macOS CI 使用 `/bin/bash`。缺少某 Shell 的覆盖必须明确报告，不能记作通过。

## 验证运行环境确实没有 Python

```sh
docker build -f conformance/Dockerfile -t devwho-runtime-check conformance
docker run --rm --network none \
  -v "$PWD/conformance:/checks:ro" \
  -v /absolute/path/to/artifacts:/artifacts:ro \
  devwho-runtime-check /artifacts/devwho
```

仅挂载所选发行物（Bash 包含配套文件），不挂载 Python 安装目录或另一个 core 的源码。镜像含 Bash、Zsh、Git、jq、Perl，没有 Python 或语言编译器。`runtime.sh` 检查这一点，使用相同 TOML/dotenv 数据，检查配置初始化、Shell 恢复，并执行真实 Git rebase/cherry-pick 作者保留测试。运行验收时禁用网络。Docker 只供贡献者验收使用。

容器验收补充主机上的完整测试，不代替跨平台覆盖。CI 保存 JSON 报告和经过测试的发行物。测试不读取真实登录凭据，也不向远端写入。
