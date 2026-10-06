package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func configFrom(t *testing.T, s string) *Config {
	t.Helper()
	p := filepath.Join(t.TempDir(), "config.toml")
	if e := os.WriteFile(p, []byte(s), 0600); e != nil {
		t.Fatal(e)
	}
	cfg, e := loadConfig(p, Env{})
	if e != nil {
		t.Fatal(e)
	}
	return cfg
}
func activate(t *testing.T, cfg *Config, name string, env Env, state *State) (Env, *State) {
	t.Helper()
	var n *string
	if name != "" {
		n = &name
	}
	patch, next, e := transition(cfg, n, env, state)
	if e != nil {
		t.Fatal(e)
	}
	return patch.Apply(env), next
}
func TestTOMLFormsAndRuntimeOrder(t *testing.T) {
	forms := []string{
		`version = 1
[profiles.a.git.config]
"credential.helper" = ["", "custom"]
"user.name" = "quoted"
"core.editor" = "vim"
[profiles.a.env]
VALUE = "\u96ea"
EMPTY = ''
MULTI = '''line
second'''
`,
		`version=1
profiles.a={git={config={"credential.helper"=["","custom"],"user.name"="quoted","core.editor"="vim"}},env={VALUE="雪",EMPTY='',MULTI="line\nsecond"}}
`,
		`version=1
"profiles"."a".git.config."credential.helper" = [
 "",
 "custom",
]
profiles.a.git.config."user.name"="quoted"
profiles.a.git.config."core.editor"="vim"
profiles.a.env={VALUE="雪",EMPTY='',MULTI="line\nsecond"}
`,
	}
	for i, s := range forms {
		t.Run(fmt.Sprint(i), func(t *testing.T) {
			cfg := configFrom(t, s)
			c, e := compile(cfg.Profiles["a"], Env{})
			if e != nil {
				t.Fatal(e)
			}
			want := []Pair{{"credential.helper", ""}, {"credential.helper", "custom"}, {"user.name", "quoted"}, {"core.editor", "vim"}}
			if !reflect.DeepEqual(c.Runtime, want) {
				t.Fatalf("ordered pairs: %#v", c.Runtime)
			}
			if c.Values["VALUE"] != "雪" || c.Values["EMPTY"] != "" || c.Values["MULTI"] != "line\nsecond" {
				t.Fatalf("literal values: %#v", c.Values)
			}
		})
	}
}
func TestRejectSchemaAndInvalidTOML(t *testing.T) {
	cases := []string{"version=true\n[profiles.a]", "version=1\nversion=1\n[profiles.a]", "version=1\n[profiles.a]\nunknown=true", "version=1\n[profiles.a.git]\nname='Jane'", "version=1\n[profiles.a.env]\nX=1", "version=1\n[profiles.a.git.config]\n'credential.helper'=[]", "version=1\n[profiles.a.git]\nsign_commits=1", "version=1\n[profiles.a.github]\nconfig_dir='/tmp'\nexpected_user='bad user'", "version=1\n[profiles.a.git_ssh]\nidentities_only=true", "version=1\n[settings]\nshortcut_profile='missing'\n[profiles.a]"}
	for _, key := range []string{"DEVWHO_PROFILE", "DEVWHO_OTHER", "__DEVWHO_STATE", "__devwho_data", "BASH_ENV", "IFS", "GIT_AUTHOR_NAME", "GIT_CONFIG_KEY_x", "GIT_CONFIG_COUNT"} {
		cases = append(cases, "version=1\n[profiles.a.env]\n"+key+"='hidden'")
	}
	for i, s := range cases {
		t.Run(fmt.Sprint(i), func(t *testing.T) {
			p := filepath.Join(t.TempDir(), "config.toml")
			os.WriteFile(p, []byte(s), 0600)
			if _, e := loadConfig(p, Env{}); e == nil {
				t.Fatal("invalid configuration accepted")
			}
		})
	}
}
func TestRestoreBaselineSwitchesAndAppendages(t *testing.T) {
	cfg := configFrom(t, `version=1
[profiles.a]
unset_env=['DELETE']
[profiles.a.env]
ABSENT='a'
EMPTY='a'
PRESENT='a'
[profiles.a.git]
name='Jane'
email='jane@example.test'
[profiles.b.env]
PRESENT='b'
B_ONLY='b'
[profiles.c.git.config]
'credential.helper'=['','custom']
`)
	for _, base := range []Env{{"EMPTY": "", "PRESENT": "old", "DELETE": "old", "HTTP_PROXY": "proxy"}, {"GIT_CONFIG_COUNT": "000", "GIT_CONFIG_KEY_0": "orphan", "GIT_CONFIG_VALUE_0": "unused"}, {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.proxy", "GIT_CONFIG_VALUE_0": "proxy", "GIT_CONFIG_KEY_12": "orphan", "GIT_CONFIG_VALUE_12": "old"}} {
		env, state := activate(t, cfg, "a", base, nil)
		patch, next, e := transition(cfg, ptr("a"), env, state)
		if e != nil || len(patch.Set) != 0 || len(patch.Unset) != 0 || !reflect.DeepEqual(state, next) {
			t.Fatalf("idempotence: %#v %v", patch, e)
		}
		env, state = activate(t, cfg, "b", env, state)
		env, state = activate(t, cfg, "c", env, state)
		raw, _ := json.Marshal(state)
		decoded, e := readState(raw)
		if e != nil {
			t.Fatal(e)
		}
		env, _ = activate(t, cfg, "", env, decoded)
		if !reflect.DeepEqual(base, env) {
			t.Fatalf("restore want %#v got %#v", base, env)
		}
	}
	env, state := activate(t, cfg, "a", Env{}, nil)
	env["GIT_CONFIG_COUNT"] = "7"
	env["GIT_CONFIG_KEY_6"] = "credential.helper"
	env["GIT_CONFIG_VALUE_6"] = "external"
	env, state = activate(t, cfg, "b", env, state)
	env, state = activate(t, cfg, "a", env, state)
	env, _ = activate(t, cfg, "", env, state)
	want := Env{"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "credential.helper", "GIT_CONFIG_VALUE_0": "external"}
	if !reflect.DeepEqual(env, want) {
		t.Fatalf("appendage restore: %#v", env)
	}
}
func ptr(s string) *string { return &s }
func TestAtomicRuntimeAndInheritedConflicts(t *testing.T) {
	cfg := configFrom(t, `version=1
[profiles.a.git]
name='Jane'
email='jane@example.test'
[profiles.token.env]
GH_TOKEN='fictional-secret'
[profiles.gh.github]
config_dir='/tmp/gh'
expected_user='jane_work'
[profiles.env.env]
VALUE='x'
`)
	for _, base := range []Env{{"GIT_CONFIG_COUNT": ""}, {"GIT_CONFIG_COUNT": "-1"}, {"GIT_CONFIG_COUNT": "1"}, {"GIT_CONFIG_COUNT": "4097"}} {
		saved := Env(clone(base))
		if _, _, e := transition(cfg, ptr("a"), base, nil); e == nil {
			t.Fatal("malformed pairs accepted")
		}
		if !reflect.DeepEqual(base, saved) {
			t.Fatal("input mutated")
		}
	}
	base := Env{"GIT_CONFIG_COUNT": "broken"}
	env, state := activate(t, cfg, "env", base, nil)
	env, _ = activate(t, cfg, "", env, state)
	if !reflect.DeepEqual(base, env) {
		t.Fatal("env profile touched unowned count")
	}
	env, state = activate(t, cfg, "a", Env{}, nil)
	env["GIT_CONFIG_VALUE_0"] = "tampered"
	before, _ := json.Marshal(state)
	saved := Env(clone(env))
	if _, _, e := transition(cfg, nil, env, state); e == nil {
		t.Fatal("tampered owned block accepted")
	}
	after, _ := json.Marshal(state)
	if !reflect.DeepEqual(saved, env) || string(before) != string(after) {
		t.Fatal("atomic failure mutated state")
	}
	env, state = activate(t, cfg, "token", Env{}, nil)
	if _, _, e := transition(cfg, ptr("gh"), env, state); e == nil || strings.Contains(e.Error(), "fictional-secret") {
		t.Fatal("inherited token conflict unreported or leaked")
	}
	for _, k := range []string{"GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"} {
		if _, _, e := transition(cfg, ptr("env"), Env{k: "private"}, nil); e == nil || strings.Contains(e.Error(), "private") {
			t.Fatal("author conflict unreported or leaked")
		}
	}
}
func TestStateStructureAndLimits(t *testing.T) {
	cfg := configFrom(t, "version=1\n[profiles.a.env]\nVALUE='a'")
	_, state := activate(t, cfg, "a", Env{}, nil)
	raw, _ := json.Marshal(state)
	for _, s := range []string{"{}", "[]", strings.Replace(string(raw), `"version":1`, `"version":true`, 1), strings.Replace(string(raw), `"version":1`, `"version":1.0`, 1), strings.Replace(string(raw), `"VALUE":null`, `"BASH_ENV":"bad"`, 1), string(raw) + " {}", strings.Repeat(" ", 1024*1024+1)} {
		if _, e := readState([]byte(s)); e == nil {
			t.Fatalf("accepted invalid state: %.100s", s)
		}
	}
	if _, e := readState([]byte(`null`)); e != nil {
		t.Fatal(e)
	}
}
func TestEffectiveHomeAndLiteralShellPaths(t *testing.T) {
	root := t.TempDir()
	for _, dir := range []string{"original", "previous", "destination"} {
		os.Mkdir(filepath.Join(root, dir), 0700)
		os.WriteFile(filepath.Join(root, dir, "key ' $(false)"), nil, 0600)
	}
	cfg := configFrom(t, fmt.Sprintf(`version=1
[profiles.a.env]
HOME=%q
[profiles.b.git_ssh]
identity_file="~/key ' $(false)"
[profiles.b.github]
config_dir='~/github/$HOME'
expected_user='jane_work'
[profiles.c.env]
HOME=%q
[profiles.c.git_ssh]
identity_file="~/key ' $(false)"
[profiles.c.github]
config_dir='~'
expected_user='jane_work'
`, filepath.Join(root, "previous"), filepath.Join(root, "destination")))
	base := Env{"HOME": filepath.Join(root, "original")}
	env, state := activate(t, cfg, "a", base, nil)
	env, state = activate(t, cfg, "b", env, state)
	if env["GH_CONFIG_DIR"] != base["HOME"]+"/github/$HOME" || !strings.Contains(env["GIT_SSH_COMMAND"], "original") {
		t.Fatal("path uses previous managed HOME")
	}
	env, state = activate(t, cfg, "c", env, state)
	if env["GH_CONFIG_DIR"] != filepath.Join(root, "destination") {
		t.Fatal("target HOME ignored")
	}
	env, _ = activate(t, cfg, "", env, state)
	if !reflect.DeepEqual(env, base) {
		t.Fatal("HOME failed restore")
	}
	for _, home := range []string{"", "relative"} {
		if _, e := compile(cfg.Profiles["b"], Env{"HOME": home}); e == nil {
			t.Fatal("missing/relative home accepted")
		}
	}
}
func TestActualGitReplayAuthors(t *testing.T) {
	if _, e := exec.LookPath("git"); e != nil {
		t.Skip("git unavailable")
	}
	cfg := configFrom(t, `version=1
[profiles.a.git]
name='Work User'
email='work@example.test'
[profiles.b.git]
name='Personal User'
email='personal@example.test'
`)
	for _, operation := range []string{"cherry-pick", "rebase"} {
		t.Run(operation, func(t *testing.T) {
			root := t.TempDir()
			base := environment()
			for k := range base {
				if strings.HasPrefix(k, "GIT_") || strings.HasPrefix(k, "DEVWHO_") {
					delete(base, k)
				}
			}
			base["HOME"] = root
			base["GIT_CONFIG_NOSYSTEM"] = "1"
			base["GIT_CONFIG_GLOBAL"] = "/dev/null"
			env, state := activate(t, cfg, "a", base, nil)
			git := func(args ...string) string {
				t.Helper()
				c := exec.Command("git", args...)
				c.Dir = root
				c.Env = envList(env)
				o, e := c.CombinedOutput()
				if e != nil {
					t.Fatalf("git %v: %v %s", args, e, o)
				}
				return strings.TrimSpace(string(o))
			}
			git("init", "-q")
			git("checkout", "-qb", "main")
			git("config", "user.name", "Wrong Local")
			git("config", "user.email", "wrong@example.test")
			git("commit", "--allow-empty", "-qm", "base")
			git("checkout", "-qb", "source")
			os.WriteFile(filepath.Join(root, "source.txt"), []byte("source"), 0600)
			git("add", "source.txt")
			git("commit", "--author=Original Author <original@example.test>", "-qm", "source")
			commit := git("rev-parse", "HEAD")
			git("checkout", "-q", "main")
			env, state = activate(t, cfg, "b", env, state)
			os.WriteFile(filepath.Join(root, "main.txt"), []byte("main"), 0600)
			git("add", "main.txt")
			git("commit", "-qm", "diverged")
			if operation == "cherry-pick" {
				git("cherry-pick", commit)
			} else {
				git("rebase", "main", "source")
			}
			if got := git("log", "-1", "--format=%an <%ae>|%cn <%ce>"); got != "Original Author <original@example.test>|Personal User <personal@example.test>" {
				t.Fatalf("author replay: %s", got)
			}
		})
	}
}

func TestUnicodeStateBudgetAndIdentityWhitespace(t *testing.T) {
	cfg := configFrom(t, "version=1\n[profiles.a.env]\nVALUE='a'")
	_, state := activate(t, cfg, "a", Env{}, nil)
	// The baseline limits stdin characters, not UTF-8 bytes.
	state.Baseline["VALUE"] = ptr(strings.Repeat("雪", 400000))
	raw, _ := json.Marshal(state)
	if len(raw) <= 1024*1024 {
		t.Fatal("fixture must exceed the byte budget")
	}
	if _, e := readState(raw); e != nil {
		t.Fatalf("valid Unicode state rejected: %v", e)
	}
	for _, value := range []string{"\x1cJane", "Jane\x1f", "\u0085Jane", "Jane\u3000"} {
		raw := map[string]any{"git": map[string]any{"name": value, "email": "jane@example.test"}}
		if _, e := parseProfile("a", raw, nil); e == nil {
			t.Fatal("identity boundary whitespace accepted")
		}
	}
}
