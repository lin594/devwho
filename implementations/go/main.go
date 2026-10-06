package main

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

const version = "0.1.0-rc.1"

func environment() Env {
	e := Env{}
	for _, entry := range os.Environ() {
		k, v, ok := strings.Cut(entry, "=")
		if ok {
			e[k] = v
		}
	}
	return e
}
func envList(e Env) []string {
	a := []string{}
	for _, k := range sortedKeys(e) {
		a = append(a, k+"="+e[k])
	}
	return a
}
func runTool(timeout time.Duration, args ...string) (string, int, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, args[0], args[1:]...)
	out, e := cmd.Output()
	if ctx.Err() != nil {
		return "", -1, ctx.Err()
	}
	if e != nil {
		var ee *exec.ExitError
		if errors.As(e, &ee) {
			return string(out), ee.ExitCode(), nil
		}
		return "", -1, e
	}
	return string(out), 0, nil
}

var ident = regexp.MustCompile(`^([^\r\n]*<[^\r\n]*>) [0-9]+ [+-][0-9]+$`)

func doctor(cfg *Config, name string, offline bool, env Env) (int, error) {
	if name == "" {
		name = env["DEVWHO_PROFILE"]
	}
	if name == "" {
		fmt.Println("FAIL: no active profile; use setdev PROFILE or name a profile to diagnose")
		return 1, nil
	}
	p := cfg.Profiles[name]
	if p == nil {
		return 1, unknown(name)
	}
	fmt.Println("Profile: " + name)
	failed, unverified := false, false
	report := func(label, status, detail string) {
		line := label + ": " + status
		if detail != "" {
			line += " — " + detail
		}
		fmt.Println(line)
		failed = failed || status == "FAIL"
		unverified = unverified || status == "UNVERIFIED"
	}
	status := func(b bool) string {
		if b {
			return "OK"
		}
		return "FAIL"
	}
	report("Context", status(env["DEVWHO_PROFILE"] == name), "metadata is not proof of authentication")
	desired, e := compile(p, env)
	if e != nil {
		report("Configuration/environment", "FAIL", e.Error())
		return 1, nil
	}
	if n, ok := p.Git["name"]; ok {
		expected := n.(string) + " <" + p.Git["email"].(string) + ">"
		for _, check := range [][2]string{{"Git author", "GIT_AUTHOR_IDENT"}, {"Git committer", "GIT_COMMITTER_IDENT"}} {
			out, code, e := runTool(10*time.Second, "git", "var", check[1])
			actual := strings.TrimSpace(out)
			if e != nil {
				report(check[0], "UNVERIFIED", "Git unavailable or timed out")
			} else if code != 0 {
				report(check[0], "UNVERIFIED", "Git cannot resolve identity in this context")
			} else if strings.HasPrefix(actual, expected+" ") {
				report(check[0], "OK", expected)
			} else {
				safe := "unrecognized identity output"
				if m := ident.FindStringSubmatch(actual); m != nil {
					safe = m[1]
				}
				report(check[0], "FAIL", "expected "+expected+"; actual "+safe)
			}
		}
	}
	groups := map[string][]string{}
	order := []string{}
	for _, pair := range desired.Runtime {
		if _, ok := groups[pair[0]]; !ok {
			order = append(order, pair[0])
		}
		groups[pair[0]] = append(groups[pair[0]], pair[1])
	}
	mismatch, unavailable := false, false
	for _, key := range order {
		out, code, e := runTool(10*time.Second, "git", "config", "--null", "--get-all", key)
		if e != nil {
			unavailable = true
			continue
		}
		actual := strings.Split(out, "\x00")
		if len(actual) > 0 && actual[len(actual)-1] == "" {
			actual = actual[:len(actual)-1]
		}
		expected := groups[key]
		if code != 0 || len(actual) < len(expected) {
			mismatch = true
		} else {
			for i, v := range expected {
				if actual[len(actual)-len(expected)+i] != v {
					mismatch = true
				}
			}
		}
	}
	if len(groups) > 0 {
		s := "OK"
		if mismatch {
			s = "FAIL"
		} else if unavailable {
			s = "UNVERIFIED"
		}
		report("Git runtime configuration", s, "values hidden")
	}
	if len(p.SSH) > 0 {
		report("Git SSH command", status(env["GIT_SSH_COMMAND"] == desired.Values["GIT_SSH_COMMAND"]), "local command/key check only; remote authentication is unverified")
	}
	for _, k := range sortedKeys(p.Env) {
		v, ok := env[k]
		report("Environment "+k, status(ok && v == p.Env[k]), "value hidden")
	}
	for _, k := range p.Unset {
		_, ok := env[k]
		report("Unset "+k, status(!ok), "")
	}
	if len(p.GitHub) > 0 {
		expected := p.GitHub["expected_user"].(string)
		report("GitHub config directory", status(env["GH_CONFIG_DIR"] == desired.Values["GH_CONFIG_DIR"]), "")
		report("GitHub hostname", status(env["GH_HOST"] == desired.Values["GH_HOST"]), "")
		if offline {
			report("GitHub identity", "UNVERIFIED", "offline mode; expected "+expected)
		} else if _, e := exec.LookPath("gh"); e != nil {
			report("GitHub identity", "UNVERIFIED", "install GitHub CLI; expected "+expected)
		} else {
			out, code, e := runTool(15*time.Second, "gh", "api", "--hostname", desired.Values["GH_HOST"], "user", "--jq", ".login")
			actual := strings.TrimSpace(out)
			if e != nil {
				report("GitHub identity", "UNVERIFIED", "API unavailable; expected "+expected)
			} else if code != 0 || !regexp.MustCompile(`^[A-Za-z0-9_.-]{1,100}$`).MatchString(actual) {
				report("GitHub identity", "UNVERIFIED", "API/login unavailable; expected "+expected)
			} else {
				report("GitHub identity", status(actual == expected), "expected "+expected+"; actual "+actual)
			}
		}
	}
	if failed {
		return 1, nil
	}
	if unverified {
		return 2, nil
	}
	return 0, nil
}
func unknown(s string) error { return fmt.Errorf("Unknown profile %q; run devwho list", s) }

const help = `Usage: devwho [--config PATH | --env-file PATH [--env-profile NAME]] COMMAND
Per-shell developer identity through environment variables.
Commands: list, show PROFILE, current [--verbose], doctor [PROFILE] [--offline],
          exec PROFILE -- COMMAND ..., config path|init|export-env PROFILE, init bash|zsh
Options: --help, --version, --config PATH, --env-file PATH, --env-profile NAME
`

func usageError(s string) (int, error) { fmt.Fprintln(os.Stderr, "devwho: "+s); return 2, nil }
func mainArgs(args []string) (int, error) {
	env := environment()
	path, envFile, envProfile := "", "", ""
	configSet, envFileSet, envProfileSet := false, false, false
	for len(args) > 0 {
		a := args[0]
		if a == "--help" || a == "-h" {
			fmt.Print(help)
			return 0, nil
		}
		if a == "--version" {
			fmt.Println("devwho " + version)
			return 0, nil
		}
		key, value, inline := strings.Cut(a, "=")
		if key != "--config" && key != "--env-file" && key != "--env-profile" {
			break
		}
		if inline {
			args = args[1:]
		} else {
			if len(args) < 2 {
				return usageError(key + " requires a value")
			}
			value = args[1]
			args = args[2:]
		}
		switch key {
		case "--config":
			path = value
			configSet = true
		case "--env-file":
			envFile = value
			envFileSet = true
		case "--env-profile":
			envProfile = value
			envProfileSet = true
		}
	}
	if configSet && envFileSet {
		return usageError("--config and --env-file are mutually exclusive")
	}
	if envProfileSet && !envFileSet {
		return usageError("--env-profile requires --env-file")
	}
	if envProfileSet && !profileName.MatchString(envProfile) {
		return usageError("--env-profile must name a valid profile")
	}
	if len(args) == 0 {
		return usageError("a command is required")
	}
	command := args[0]
	args = args[1:]
	if command != "exec" {
		for _, a := range args {
			if a == "-h" || a == "--help" {
				fmt.Print(help)
				return 0, nil
			}
		}
	}
	switch command {
	case "list", "show", "current", "doctor", "exec", "config", "init", "internal":
	default:
		return usageError("unknown command")
	}
	if command == "current" {
		verbose := false
		if len(args) == 1 && args[0] == "--verbose" {
			verbose = true
		} else if len(args) != 0 {
			return usageError("current accepts only --verbose")
		}
		name := env["DEVWHO_PROFILE"]
		if name == "" {
			name = "none"
		}
		fmt.Println(name)
		if verbose {
			selected := path
			if envFileSet {
				selected = envFile
			}
			if selected == "" {
				selected = configPath(env)
			}
			fmt.Println("Configuration: " + selected)
			gh := env["GH_CONFIG_DIR"]
			if _, ok := env["GH_CONFIG_DIR"]; !ok {
				gh = "default"
			}
			host := env["GH_HOST"]
			if _, ok := env["GH_HOST"]; !ok {
				host = "github.com"
			}
			fmt.Println("GitHub config directory: " + gh)
			fmt.Println("GitHub hostname: " + host)
			for _, check := range [][2]string{{"Git author", "GIT_AUTHOR_IDENT"}, {"Git committer", "GIT_COMMITTER_IDENT"}} {
				out, code, e := runTool(10*time.Second, "git", "var", check[1])
				safe := "unavailable"
				if e == nil && code == 0 {
					if m := ident.FindStringSubmatch(strings.TrimSpace(out)); m != nil {
						safe = m[1]
					}
				}
				fmt.Println(check[0] + ": " + safe)
			}
			fmt.Println("Use devwho doctor to verify actual tool identity.")
		}
		return 0, nil
	}
	if command == "config" {
		if len(args) >= 1 && args[0] == "export-env" {
			if len(args) != 2 {
				return usageError("config export-env requires PROFILE")
			}
			var cfg *Config
			var e error
			if envFileSet {
				cfg, e = loadDotenv(envFile, envProfile, env)
			} else {
				cfg, e = loadConfig(path, env)
			}
			if e != nil {
				return 1, e
			}
			p := cfg.Profiles[args[1]]
			if p == nil {
				return 1, unknown(args[1])
			}
			text, e := exportDotenv(p)
			if e != nil {
				return 1, e
			}
			fmt.Print(text)
			return 0, nil
		}
		if len(args) != 1 || (args[0] != "path" && args[0] != "init") {
			return usageError("config requires path, init, or export-env PROFILE")
		}
		selected := path
		if envFileSet {
			selected = envFile
		}
		if selected == "" {
			selected = configPath(env)
		}
		if args[0] == "path" {
			fmt.Println(selected)
			return 0, nil
		}
		if envFileSet {
			return 1, fmt.Errorf("config init cannot initialize a dotenv source")
		}
		if e := os.MkdirAll(filepath.Dir(selected), 0700); e != nil {
			return 1, fmt.Errorf("local operation failed (OSError)")
		}
		f, e := os.OpenFile(selected, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
		if e != nil {
			return 1, fmt.Errorf("local operation failed (OSError)")
		}
		_, e = f.WriteString("version = 1\n\n[profiles.personal.git]\nname = \"Jane Doe\"\nemail = \"jane@example.com\"\n\n[profiles.work.git]\nname = \"Jane Doe\"\nemail = \"jane@company.example\"\n")
		ce := f.Close()
		if e != nil || ce != nil {
			return 1, fmt.Errorf("local operation failed (OSError)")
		}
		fmt.Println("Created " + selected + "; edit its example identities before use.")
		return 0, nil
	}
	var cfg *Config
	var e error
	if envFileSet {
		cfg, e = loadDotenv(envFile, envProfile, env)
	} else {
		cfg, e = loadConfig(path, env)
	}
	if e != nil {
		return 1, e
	}
	switch command {
	case "list":
		if len(args) != 0 {
			return usageError("list accepts no arguments")
		}
		for _, name := range sortedKeys(cfg.Profiles) {
			fmt.Println(name)
		}
		return 0, nil
	case "show":
		if len(args) != 1 {
			return usageError("show requires PROFILE")
		}
		p := cfg.Profiles[args[0]]
		if p == nil {
			return 1, unknown(args[0])
		}
		fmt.Println("Profile: " + p.Name)
		if n, ok := p.Git["name"]; ok {
			fmt.Printf("Git: %s <%s>\n", n, p.Git["email"])
		}
		if len(p.SSH) > 0 {
			fmt.Println("Git SSH key: " + p.SSH["identity_file"].(string))
		}
		if len(p.GitHub) > 0 {
			fmt.Println("GitHub expected user: " + p.GitHub["expected_user"].(string))
			fmt.Println("GitHub config: " + p.GitHub["config_dir"].(string))
		}
		fmt.Println("Custom environment keys: " + strings.Join(sortedKeys(p.Env), ", "))
		fmt.Println("Unset keys: " + strings.Join(p.Unset, ", "))
		return 0, nil
	case "doctor":
		name := ""
		offline := false
		for _, a := range args {
			if a == "--offline" {
				offline = true
			} else if strings.HasPrefix(a, "-") || name != "" {
				return usageError("doctor accepts PROFILE and --offline")
			} else {
				name = a
			}
		}
		return doctor(cfg, name, offline, env)
	case "init":
		if len(args) != 1 || (args[0] != "bash" && args[0] != "zsh") {
			return usageError("init requires bash or zsh")
		}
		if cfg.Default != "" && env["DEVWHO_PROFILE"] == "" {
			if _, e := compile(cfg.Profiles[cfg.Default], env); e != nil {
				return 1, e
			}
		}
		s, e := renderInit(args[0], cfg)
		if e != nil {
			return 1, e
		}
		fmt.Print(s)
		return 0, nil
	case "exec":
		if len(args) < 1 {
			return usageError("exec requires PROFILE")
		}
		name := args[0]
		child := args[1:]
		if len(child) > 0 && child[0] == "--" {
			child = child[1:]
		}
		if len(child) == 0 {
			return 1, fmt.Errorf("devwho exec needs a command after --")
		}
		if cfg.Profiles[name] == nil {
			return 1, unknown(name)
		}
		p, _, e := transition(cfg, &name, env, nil)
		if e != nil {
			return 1, e
		}
		return executeChild(child, p.Apply(env))
	case "internal":
		return internal(cfg, args, env)
	}
	return 1, nil
}
func internal(cfg *Config, args []string, env Env) (int, error) {
	if len(args) == 0 {
		return usageError("internal requires an action")
	}
	action := args[0]
	args = args[1:]
	if action != "transition" && action != "bootstrap" && action != "notice" {
		return usageError("unknown internal action")
	}
	shell, name := "", ""
	restore, activate := false, false
	for i := 0; i < len(args); i++ {
		option := args[i]
		value, inline := "", false
		if strings.HasPrefix(option, "--shell=") || strings.HasPrefix(option, "--activate=") {
			option, value, _ = strings.Cut(option, "=")
			inline = true
		}
		switch option {
		case "--shell":
			if inline {
				shell = value
			} else {
				i++
				if i >= len(args) {
					return usageError("--shell requires bash or zsh")
				}
				shell = args[i]
			}
			if shell != "bash" && shell != "zsh" {
				return usageError("--shell requires bash or zsh")
			}
		case "--restore":
			if activate {
				return usageError("--activate and --restore are exclusive")
			}
			restore = true
		case "--activate":
			if restore {
				return usageError("--activate and --restore are exclusive")
			}
			activate = true
			if inline {
				name = value
				continue
			}
			if i+1 < len(args) && !strings.HasPrefix(args[i+1], "-") {
				i++
				name = args[i]
			}
		default:
			return usageError("unexpected internal argument")
		}
	}
	if action == "notice" {
		if cfg.Handoff {
			out, code, e := runTool(2*time.Second, "git", "status", "--porcelain", "--untracked-files=normal")
			if e != nil {
				fmt.Fprintln(os.Stderr, "devwho: handoff check unavailable; check git status before taking over.")
			} else if code == 0 && out != "" {
				fmt.Fprintln(os.Stderr, "devwho: this repository has uncommitted changes; confirm the handoff before editing or committing. Switching identity does not assign those changes.")
			}
		}
		return 0, nil
	}
	if e := validShell(shell); e != nil {
		return 1, e
	}
	if action == "bootstrap" {
		if cfg.Default == "" {
			return 0, nil
		}
		p, _, e := transition(cfg, &cfg.Default, env, nil)
		if e != nil {
			return 1, e
		}
		fmt.Print(renderPatch(p, nil, shell))
		return 0, nil
	}
	raw, e := io.ReadAll(io.LimitReader(os.Stdin, 4*(1024*1024+1)))
	if e != nil {
		return 1, fmt.Errorf("Invalid DevWho shell state")
	}
	state, e := readState(raw)
	if e != nil {
		return 1, e
	}
	var selected *string
	if !restore {
		if name == "" {
			name = cfg.Shortcut
		}
		if name == "" {
			return 1, fmt.Errorf("setdev needs PROFILE or settings.shortcut_profile")
		}
		if cfg.Profiles[name] == nil {
			return 1, unknown(name)
		}
		selected = &name
	}
	p, next, e := transition(cfg, selected, env, state)
	if e != nil {
		return 1, e
	}
	fmt.Print(renderPatch(p, next, shell))
	return 0, nil
}
