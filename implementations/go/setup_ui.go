//go:build setup

package main

import (
	"bufio"
	"fmt"
	"io"
	"strings"
)

func configureForm(path, language string, in io.Reader, out io.Writer) (int, error) {
	zh := language == "zh-CN"
	say := func(en, cn string) string {
		if zh {
			return cn
		}
		return en
	}
	stored, e := storeRead(path)
	if e != nil {
		return 1, e
	}
	doc := stored.Document
	if doc == nil {
		doc = &Document{map[string]any{"version": int64(1), "profiles": map[string]any{}}, map[string][]string{}}
	}
	reader := bufio.NewReader(in)
	ask := func(en, cn, current string) (string, error) {
		prompt := say(en, cn)
		if current != "" {
			prompt += " [" + current + "]"
		}
		fmt.Fprint(out, prompt+": ")
		line, e := reader.ReadString('\n')
		if e != nil {
			return "", fmt.Errorf("Input ended; configuration was not saved")
		}
		line = strings.TrimSpace(strings.TrimSuffix(line, "\n"))
		return line, nil
	}
	fmt.Fprintln(out, say("DevWho configuration editor — blank keeps existing values; - clears optional settings.", "DevWho 配置编辑器 — 留空保留现有值；- 清除可选设置。"))
	profiles := doc.Data["profiles"].(map[string]any)
	fmt.Fprintln(out, say("Profiles: ", "配置列表：")+strings.Join(sortedKeys(profiles), ", "))
	name, e := ask("Profile to edit/add (blank cancels)", "编辑或添加的配置名称（留空取消）", "")
	if e != nil {
		return 1, e
	}
	if name == "" {
		fmt.Fprintln(out, say("Cancelled; no configuration changed.", "已取消；配置未修改。"))
		return 0, nil
	}
	if !profileName.MatchString(name) {
		return 1, fmt.Errorf("Invalid profile name")
	}
	p, ok := profiles[name].(map[string]any)
	if !ok {
		p = map[string]any{}
		profiles[name] = p
	}
	git, ok := p["git"].(map[string]any)
	if !ok {
		git = map[string]any{}
	}
	get := func(m map[string]any, k string) string { s, _ := m[k].(string); return s }
	n, e := ask("Git name", "Git 姓名", get(git, "name"))
	if e != nil {
		return 1, e
	}
	email, e := ask("Git email", "Git 邮箱", get(git, "email"))
	if e != nil {
		return 1, e
	}
	if n != "" {
		git["name"] = n
	}
	if email != "" {
		git["email"] = email
	}
	if len(git) > 0 {
		p["git"] = git
	}
	ssh, ok := p["git_ssh"].(map[string]any)
	if !ok {
		ssh = map[string]any{}
	}
	key, e := ask("SSH identity file (optional; - removes mapping)", "SSH 私钥文件（可选；- 删除映射）", get(ssh, "identity_file"))
	if e != nil {
		return 1, e
	}
	if key == "-" {
		delete(p, "git_ssh")
	} else if key != "" {
		ssh["identity_file"] = key
		p["git_ssh"] = ssh
	}
	gh, ok := p["github"].(map[string]any)
	if !ok {
		gh = map[string]any{}
	}
	dir, e := ask("GitHub config directory (optional; - removes mapping)", "GitHub 配置目录（可选；- 删除映射）", get(gh, "config_dir"))
	if e != nil {
		return 1, e
	}
	if dir == "-" {
		delete(p, "github")
	} else {
		user, e := ask("GitHub expected login (required with directory)", "GitHub 预期登录名（填写目录时必填）", get(gh, "expected_user"))
		if e != nil {
			return 1, e
		}
		host, e := ask("GitHub hostname (blank uses existing or github.com)", "GitHub 主机名（留空保留现有值或使用 github.com）", get(gh, "hostname"))
		if e != nil {
			return 1, e
		}
		if dir != "" {
			gh["config_dir"] = dir
		}
		if user != "" {
			gh["expected_user"] = user
		}
		if host != "" {
			gh["hostname"] = host
		}
		if len(gh) > 0 {
			p["github"] = gh
		}
	}
	settings, ok := doc.Data["settings"].(map[string]any)
	if !ok {
		settings = map[string]any{}
	}
	for _, field := range []string{"default_profile", "shortcut_profile"} {
		en, cn := "Default profile (- clears)", "默认配置（- 清除）"
		if field == "shortcut_profile" {
			en, cn = "Shortcut profile (- clears)", "快捷配置（- 清除）"
		}
		v, e := ask(en, cn, get(settings, field))
		if e != nil {
			return 1, e
		}
		if v == "-" {
			delete(settings, field)
		} else if v != "" {
			settings[field] = v
		}
	}
	if len(settings) > 0 {
		doc.Data["settings"] = settings
	} else {
		delete(doc.Data, "settings")
	}
	if _, e := validateDocument(doc.Data, path, doc.Orders); e != nil {
		return 1, e
	}
	preview := redactDocument(doc)
	fmt.Fprintln(out, say("Preview (custom values hidden):", "预览（隐藏自定义值）："))
	fmt.Fprintln(out, orderedJSON(preview.Data, nil, preview.Orders))
	decision, e := ask("Type save to write, or cancel", "输入 save 或 保存 写入，输入 cancel 或 取消 放弃", "")
	if e != nil {
		return 1, e
	}
	if decision != "save" && !(zh && decision == "保存") {
		fmt.Fprintln(out, say("Cancelled; no configuration changed.", "已取消；配置未修改。"))
		return 0, nil
	}
	next, e := storeSave(path, doc, stored.Revision)
	if e != nil {
		return 1, e
	}
	fmt.Fprintln(out, say("Saved configuration. Revision: ", "已保存配置。版本：")+next.Revision)
	return 0, nil
}
