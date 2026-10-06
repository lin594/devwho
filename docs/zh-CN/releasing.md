# 手工发布 RC1

[English](../releasing.md)

发布前完成 RC 阻塞；#11 自动发布属于后续工作。本轮不增加普通 CI 的写权限，继续保持 `contents: read`。

[发行计划](../../release-plan.json)指定八个完整产物和三个来源：唯一 Python 为 **`test (ubuntu-latest, 3.11)` / `devwho-ubuntu-latest-py3.11`**；其他三个 Python job 只用于验证。core 来源为 `cores (ubuntu-latest)` / `complete-cores-ubuntu-latest` 和 `cores (macos-latest)` / `complete-cores-macos-latest`。Linux Rust 继续构建/测试但 RC1 不生成下载归档。macOS Go/配置前端声明最低 13.0，Rust 11.0；最低部署版本与实测宿主分别记录在 RUNTIME.txt。

1. 合入已审查修改，确认最终提交，并要求该提交的七项 CI 全成功，覆盖 lint/测试/构建、最低编译器、跨 core/状态/原生示例、校验及无 Python 容器。核实选定 run 的 `head_sha` 与最终提交一致，并检查每个 job。
2. 只下载并组装指定来源：

   ```sh
   commit=FULL_FINAL_COMMIT_SHA
   run=SUCCESSFUL_FINAL_COMMIT_RUN_ID
   gh api "repos/lin594/devwho/actions/runs/$run" --jq '{head_sha,conclusion,event}'
   gh run download "$run" --repo lin594/devwho \
     -n complete-cores-ubuntu-latest -n complete-cores-macos-latest \
     -n devwho-ubuntu-latest-py3.11 --dir downloads
   python3 scripts/collect_release_assets.py \
     --source complete-cores-ubuntu-latest=downloads/complete-cores-ubuntu-latest/dist/cores \
     --source complete-cores-macos-latest=downloads/complete-cores-macos-latest/dist/cores \
     --source devwho-ubuntu-latest-py3.11=downloads/devwho-ubuntu-latest-py3.11 \
     --commit "$commit" --ci-run "https://github.com/lin594/devwho/actions/runs/$run" \
     --output release-assets
   (cd release-assets && sha256sum -c SHA256SUMS)
   ```

   集合器先检查来源、每项原始校验和、完整必需清单与同名冲突；缺少或意外产物/来源会在创建输出目录前失败。清单记录唯一 Python 来源、预期文件、各文件来源、CI job、原始校验清单 hash、省略目标、计划 hash 与最终提交。
3. 在 FZ2 新隔离前缀安装**下载的** Linux Go/Bash 包，运行版本、显式 config 初始化、Bash/Zsh init、setdev、离线 doctor、unsetdev、exec；测试 Go 配置前端和仓库外 wheel/zipapp。用下载包再次运行禁网、无 Python/编译器容器 fixture。核验 macOS ARM64 包头和最低部署版本，实际 macOS 执行以来源 CI 为证。保存去除私有路径的 FZ2-VALIDATION.json，关联同一提交、CI 与包 hash。
4. 核实运行版本 0.1.0-rc.1、Python 元数据等价写法 0.1.0rc1，以及计划/产物/文档的目标与运行要求一致；明确未验收架构和真实认证边界。新增证据文件时重新生成完整 SHA256SUMS，不修改分发包字节。
5. 将 `v0.1.0-rc.1` 标签指向精确最终提交，创建 GitHub **Pre-release**，上传八个分发包、校验和、清单及 FZ2 证据；维持 `prerelease=true`、`make_latest=false`，不发布软件包仓库。最后核验标签提交、预发行标记、公开下载校验，再关闭 #9/#12–#15。发行说明关联最终 CI、审查范围、安装矩阵和已知限制。

最终用户只需下载匹配归档和 SHA256SUMS，并按[安装指南](../../implementations/README.zh-CN.md)核验所选条目，无需其他平台产物。
