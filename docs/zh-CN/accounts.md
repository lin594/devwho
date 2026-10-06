# 账号与身份验证

[English](../accounts.md) | [简体中文](accounts.md) · [文档首页](README.md)

先按[入门指南](getting-started.md)完成 Git 署名配置，再按需添加本页的账号认证功能。

## 三种不同的身份

| 你要选择的身份 | 控制它的设置 | 检查方法 |
|---|---|---|
| Git 提交中记录的姓名和邮箱 | 身份配置 的 `[git]` 设置 | `devwho current --verbose` 或 `git var GIT_AUTHOR_IDENT` |
| `gh` 命令使用的账号 | 身份配置 配置目录中的 GitHub CLI 登录 | `devwho doctor` 或 `gh api user --jq .login` |
| 拉取或推送时授权的账号 | Git SSH 密钥或 HTTPS 凭据助手 | 使用相应传输方式，并在有权限的仓库中核实 |

修改提交邮箱不会登录到另一个账号。`gh` 检查成功也不能证明 Git 的 SSH 或 HTTPS 认证使用了该账号。

## 使用已有的 GitHub CLI 登录

先在已有 `gh` 登录可用的终端中检查实际账号：

```sh
gh api user --jq .login
```

如果返回的是你希望 `work` 使用的账号，就让该 身份配置 指向已有配置目录。Linux/macOS 通常使用 `~/.config/gh`；如果你已设置 `GH_CONFIG_DIR` 或 `XDG_CONFIG_HOME`，请填写实际目录。

```toml
[profiles.work.github]
hostname = "github.com"
expected_user = "your-work-login"
config_dir = "~/.config/gh"
```

将 `your-work-login` 替换为 GitHub 返回的账号，然后运行：

```sh
setdev work
devwho doctor
```

如果该目录已有预期账号的有效登录，就不必再次登录。不同使用者的 身份配置 应指向不同目录；在共用目录中更换当前登录，会影响使用该目录的所有 身份配置。

## 添加另一个 GitHub CLI 账号

为新的使用场景选择单独的目录：

```toml
[profiles.personal.github]
hostname = "github.com"
expected_user = "your-personal-login"
config_dir = "~/.config/devwho/github/personal"
```

然后以对应使用者身份完成一次浏览器授权：

```sh
devwho exec personal -- gh auth login --hostname github.com --git-protocol https --web
devwho exec personal -- devwho doctor
```

如果你已使用 GCM 或其他 Git 凭据助手，当 `gh` 询问是否配置 Git 认证时请选择 **No**。DevWho 负责选用 gh 配置目录，凭据仍由 gh 管理。令牌不属于 DevWho 身份配置 的内容。

包含 GitHub 设置的 身份配置 会拒绝继承到的 `GH_TOKEN` 或 `GITHUB_TOKEN`，因为它们可能覆盖所选目录。账号不匹配或登录返回 401 时，请查看[故障排查](troubleshooting.md)。GitHub CLI 的[环境变量说明](https://cli.github.com/manual/gh_help_environment)介绍了这些选择变量。

## 为 Git SSH 选择密钥

如果你的账号已在 Git 托管平台登记了 SSH 密钥：

```toml
[profiles.work.git_ssh]
identity_file = "~/.ssh/id_ed25519_work"
identities_only = true
```

请使用现存文件的绝对路径或 `~/` 开头的路径。DevWho 会检查文件是否存在，并将其交给 Git 使用的 SSH 命令。它不会创建或登记密钥、管理密钥口令，也不会修改 `~/.ssh/config`。身份配置 切换不影响单独运行的 `ssh` 命令。SSH 配置中列出的其他密钥也可能影响认证，请核实传输实际使用的账号。

## 使用 Git HTTPS

继续使用 GCM 这类凭据助手。DevWho 不会自动重新配置 HTTPS 认证，也不会转换已保存的 remote。可以将凭据助手需要的账号选择器设为 Git 运行时配置：

```toml
[profiles.work.git.config]
"credential.https://github.com.username" = "your-work-login"
```

此示例假设 GCM 已安装并配置。[GCM 的多账号指南](https://github.com/git-ecosystem/git-credential-manager/blob/main/docs/multiple-users.md)介绍了它的账号选择器。已写入 remote 的用户名、其他凭据助手配置或托管平台策略都可能改变结果。依赖该设置前，请在自己有权限的测试仓库中验证实际传输；写入测试也应使用你控制的仓库。

如果仓库包含 GitHub Actions 工作流文件，并且 Git 使用 gh OAuth 登录作为凭据助手，登录还需要 `workflow` 权限。请在目标账号上下文中复用已核实且包含该权限的登录，或运行 `gh auth refresh --hostname github.com --scopes workflow` 申请权限。这是 GitHub 权限，与提交姓名和邮箱相互独立。

## 开始工作前检查

```sh
setdev work
devwho current --verbose
devwho doctor
```

`OK` 表示已执行的检查均匹配。`UNVERIFIED` 表示所需检查未能完成，例如工具不可用或在线检查被跳过；`FAIL` 表示发现不匹配或本地配置问题。具体检查项目和退出码见[命令参考](reference.md)。
