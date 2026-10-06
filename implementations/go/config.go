package main

import (
	"fmt"
	"os"
	"os/user"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"unicode"

	"github.com/pelletier/go-toml/v2"
	"github.com/pelletier/go-toml/v2/unstable"
)

type Env map[string]string
type Pair [2]string
type Profile struct {
	Name             string
	Git, SSH, GitHub map[string]any
	Env              Env
	Unset            []string
	GitOrder         []string
}
type Config struct {
	Path              string
	Profiles          map[string]*Profile
	Default, Shortcut string
	Handoff           bool
	EnvFile           bool
}

var profileName = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_.-]*$`)
var envName = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]*$`)
var runtimeName = regexp.MustCompile(`^GIT_CONFIG_(COUNT|KEY_[0-9]+|VALUE_[0-9]+)$`)
var gitKey = regexp.MustCompile(`^[A-Za-z][A-Za-z0-9-]*\.([^\n\r\x00]+\.)?[A-Za-z][A-Za-z0-9-]*$`)
var loginName = regexp.MustCompile(`^[A-Za-z0-9]([A-Za-z0-9_-]{0,98}[A-Za-z0-9])?$`)
var hostName = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9.-]*$`)
var unsafeEnv = map[string]bool{}

func init() {
	for _, k := range strings.Fields("BASH_ENV ENV BASHOPTS SHELLOPTS IFS CDPATH ZDOTDIR PS4 PROMPT_COMMAND GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL") {
		unsafeEnv[k] = true
	}
}
func validateEnv(k string, internal bool) error {
	if !envName.MatchString(k) {
		return fmt.Errorf("Invalid environment variable name")
	}
	if unsafeEnv[k] || strings.HasPrefix(k, "__DEVWHO") || strings.HasPrefix(k, "__devwho") || (strings.HasPrefix(k, "DEVWHO_") && !(internal && k == "DEVWHO_PROFILE")) || ((k == "GIT_CONFIG_COUNT" || strings.HasPrefix(k, "GIT_CONFIG_KEY_") || strings.HasPrefix(k, "GIT_CONFIG_VALUE_")) && !(internal && runtimeName.MatchString(k))) {
		return fmt.Errorf("Reserved environment variable: %s", k)
	}
	return nil
}

// Python str.strip includes the four ASCII information separators in addition
// to Unicode White_Space; identity validation follows that baseline exactly.
func trimSpace(s string) string {
	return strings.TrimFunc(s, func(r rune) bool { return unicode.IsSpace(r) || (r >= 0x1c && r <= 0x1f) })
}

func str(v any, field string, nonempty bool) (string, error) {
	s, ok := v.(string)
	if !ok || strings.ContainsRune(s, 0) || (nonempty && trimSpace(s) == "") {
		adjective := "a"
		if nonempty {
			adjective = "a nonempty"
		}
		return "", fmt.Errorf("%s must be %s string without NUL", field, adjective)
	}
	return s, nil
}
func table(v any, field string, allowed ...string) (map[string]any, error) {
	m, ok := v.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("%s must be a table", field)
	}
	if allowed != nil {
		known := map[string]bool{}
		for _, k := range allowed {
			known[k] = true
		}
		for _, k := range sortedKeys(m) {
			if !known[k] {
				return nil, fmt.Errorf("Unknown field in %s: %s", field, k)
			}
		}
	}
	return m, nil
}
func getTable(m map[string]any, k string, allowed ...string) (map[string]any, error) {
	v, ok := m[k]
	if !ok {
		v = map[string]any{}
	}
	return table(v, k, allowed...)
}
func sortedKeys[V any](m map[string]V) []string {
	k := make([]string, 0, len(m))
	for s := range m {
		k = append(k, s)
	}
	sort.Strings(k)
	return k
}
func fallbackHome() string {
	if u, e := user.Current(); e == nil {
		return u.HomeDir
	}
	s, _ := os.UserHomeDir()
	return s
}
func expandPath(s string, env Env) string {
	if s == "~" || strings.HasPrefix(s, "~/") {
		h := env["HOME"]
		if h == "" {
			h = fallbackHome()
		}
		return h + s[1:]
	}
	if strings.HasPrefix(s, "~") {
		head, tail, _ := strings.Cut(s, "/")
		if u, e := user.Lookup(head[1:]); e == nil {
			if tail != "" {
				return u.HomeDir + "/" + tail
			}
			return u.HomeDir
		}
	}
	return s
}
func configPath(env Env) string {
	if s := env["DEVWHO_CONFIG"]; s != "" {
		return expandPath(s, env)
	}
	root := env["XDG_CONFIG_HOME"]
	if root == "" {
		root = filepath.Join(expandPath("~", env), ".config")
	}
	return filepath.Join(root, "devwho", "config.toml")
}
func parseProfile(name string, raw any, order []string) (*Profile, error) {
	if !profileName.MatchString(name) {
		return nil, fmt.Errorf("Invalid profile name")
	}
	d, e := table(raw, "profiles."+name, "git", "git_ssh", "github", "env", "unset_env")
	if e != nil {
		return nil, e
	}
	g, e := getTable(d, "git", "name", "email", "signing_key", "signing_format", "sign_commits", "config")
	if e != nil {
		return nil, e
	}
	_, n := g["name"]
	_, em := g["email"]
	if n != em {
		return nil, fmt.Errorf("git.name and git.email must be provided together")
	}
	for _, k := range []string{"name", "email", "signing_key", "signing_format"} {
		if v, ok := g[k]; ok {
			s, err := str(v, "git."+k, true)
			if err != nil {
				return nil, err
			}
			if (k == "name" || k == "email") && (trimSpace(s) != s || strings.ContainsAny(s, "\r\n<>")) {
				return nil, fmt.Errorf("git.%s must not contain identity delimiters or surrounding whitespace", k)
			}
		}
	}
	if v, ok := g["signing_format"]; ok && v != "ssh" && v != "openpgp" && v != "x509" {
		return nil, fmt.Errorf("Unsupported git.signing_format")
	}
	if v, ok := g["sign_commits"]; ok {
		if _, ok := v.(bool); !ok {
			return nil, fmt.Errorf("git.sign_commits must be a boolean")
		}
	}
	runtime, e := getTable(g, "config")
	if e != nil {
		return nil, e
	}
	for k, v := range runtime {
		if !gitKey.MatchString(k) {
			return nil, fmt.Errorf("Invalid Git runtime configuration key")
		}
		values := []any{v}
		if a, ok := v.([]any); ok {
			values = a
		}
		if len(values) == 0 {
			return nil, fmt.Errorf("git.config lists must not be empty")
		}
		for _, v := range values {
			if _, e := str(v, "git.config value", false); e != nil {
				return nil, e
			}
		}
	}
	ssh, e := getTable(d, "git_ssh", "identity_file", "identities_only")
	if e != nil {
		return nil, e
	}
	if len(ssh) > 0 {
		if _, e := str(ssh["identity_file"], "git_ssh.identity_file", true); e != nil {
			return nil, e
		}
		if v, ok := ssh["identities_only"]; ok {
			if _, ok := v.(bool); !ok {
				return nil, fmt.Errorf("git_ssh.identities_only must be a boolean")
			}
		}
	}
	gh, e := getTable(d, "github", "hostname", "expected_user", "config_dir")
	if e != nil {
		return nil, e
	}
	if len(gh) > 0 {
		if _, e := str(gh["config_dir"], "github.config_dir", true); e != nil {
			return nil, e
		}
		s, e := str(gh["expected_user"], "github.expected_user", true)
		if e != nil {
			return nil, e
		}
		if !loginName.MatchString(s) {
			return nil, fmt.Errorf("Invalid github.expected_user")
		}
		if v, ok := gh["hostname"]; ok {
			s, e := str(v, "github.hostname", true)
			if e != nil {
				return nil, e
			}
			if !hostName.MatchString(s) {
				return nil, fmt.Errorf("Invalid github.hostname")
			}
		}
	}
	en, e := getTable(d, "env")
	if e != nil {
		return nil, e
	}
	env := Env{}
	for k, v := range en {
		if e := validateEnv(k, false); e != nil {
			return nil, e
		}
		s, e := str(v, "env."+k, false)
		if e != nil {
			return nil, e
		}
		env[k] = s
	}
	unset := []string{}
	if v, ok := d["unset_env"]; ok {
		a, ok := v.([]any)
		if !ok {
			return nil, fmt.Errorf("unset_env must be an array of environment variable names")
		}
		seen := map[string]bool{}
		for _, v := range a {
			k, ok := v.(string)
			if !ok {
				return nil, fmt.Errorf("unset_env must be an array of environment variable names")
			}
			if e := validateEnv(k, false); e != nil {
				return nil, e
			}
			if _, ok := env[k]; ok {
				return nil, fmt.Errorf("An environment variable cannot be both set and unset")
			}
			if !seen[k] {
				unset = append(unset, k)
				seen[k] = true
			}
		}
	}
	semantic := map[string]bool{}
	if len(ssh) > 0 {
		semantic["GIT_SSH_COMMAND"] = true
	}
	if len(gh) > 0 {
		semantic["GH_CONFIG_DIR"] = true
		semantic["GH_HOST"] = true
	}
	for k := range env {
		if semantic[k] {
			return nil, fmt.Errorf("Generic environment conflicts with semantic configuration")
		}
	}
	for _, k := range unset {
		if semantic[k] {
			return nil, fmt.Errorf("Generic environment conflicts with semantic configuration")
		}
	}
	// AST ordering is mandatory: map iteration cannot model repeated Git values.
	ordered := []string{}
	seen := map[string]bool{}
	for _, k := range order {
		if _, ok := runtime[k]; ok && !seen[k] {
			ordered = append(ordered, k)
			seen[k] = true
		}
	}
	for _, k := range sortedKeys(runtime) {
		if !seen[k] {
			ordered = append(ordered, k)
		}
	}
	return &Profile{name, g, ssh, gh, env, unset, ordered}, nil
}
func keyPath(n *unstable.Node) []string {
	r := []string{}
	it := n.Key()
	for it.Next() {
		r = append(r, string(it.Node().Data))
	}
	return r
}
func collectInline(n *unstable.Node, path []string, record func([]string)) {
	if n.Kind != unstable.InlineTable {
		return
	}
	it := n.Children()
	for it.Next() {
		kv := it.Node()
		p := append(append([]string{}, path...), keyPath(kv)...)
		record(p)
		collectInline(kv.Value(), p, record)
	}
}
func runtimeOrders(data []byte) (map[string][]string, error) {
	out := map[string][]string{}
	record := func(p []string) {
		if len(p) >= 5 && p[0] == "profiles" && p[2] == "git" && p[3] == "config" {
			out[p[1]] = append(out[p[1]], p[4])
		}
	}
	var p unstable.Parser
	p.Reset(data)
	prefix := []string{}
	for p.NextExpression() {
		n := p.Expression()
		switch n.Kind {
		case unstable.Table, unstable.ArrayTable:
			prefix = keyPath(n)
			record(prefix)
		case unstable.KeyValue:
			path := append(append([]string{}, prefix...), keyPath(n)...)
			record(path)
			collectInline(n.Value(), path, record)
		}
	}
	return out, p.Error()
}
func loadConfig(path string, env Env) (*Config, error) {
	if path == "" {
		path = configPath(env)
	}
	path = expandPath(path, env)
	selected, e := filepath.Abs(path)
	if e != nil {
		return nil, e
	}
	if resolved, e := filepath.EvalSymlinks(selected); e == nil {
		selected = resolved
	}
	data, e := os.ReadFile(selected)
	if e != nil {
		return nil, fmt.Errorf("Cannot read configuration: %s", selected)
	}
	var d map[string]any
	if e = toml.Unmarshal(data, &d); e != nil {
		return nil, fmt.Errorf("Invalid TOML configuration")
	}
	orders, e := runtimeOrders(data)
	if e != nil {
		return nil, fmt.Errorf("Invalid TOML configuration")
	}
	return validateDocument(d, selected, orders)
}
func validateDocument(d map[string]any, path string, orders map[string][]string) (*Config, error) {
	var e error
	if _, e = table(d, "configuration", "version", "settings", "profiles"); e != nil {
		return nil, e
	}
	if v, ok := d["version"].(int64); !ok || v != 1 {
		return nil, fmt.Errorf("Configuration version must be 1")
	}
	raw, e := getTable(d, "profiles")
	if e != nil {
		return nil, e
	}
	if len(raw) == 0 {
		return nil, fmt.Errorf("Configuration must contain at least one profile")
	}
	cfg := &Config{Path: path, Profiles: map[string]*Profile{}}
	for n, r := range raw {
		p, e := parseProfile(n, r, orders[n])
		if e != nil {
			return nil, e
		}
		cfg.Profiles[n] = p
	}
	settings, e := getTable(d, "settings", "default_profile", "shortcut_profile", "handoff_warning")
	if e != nil {
		return nil, e
	}
	if v, ok := settings["handoff_warning"]; ok {
		b, ok := v.(bool)
		if !ok {
			return nil, fmt.Errorf("settings.handoff_warning must be a boolean")
		}
		cfg.Handoff = b
	}
	for _, k := range []string{"default_profile", "shortcut_profile"} {
		if v, ok := settings[k]; ok {
			s, ok := v.(string)
			if !ok || cfg.Profiles[s] == nil {
				return nil, fmt.Errorf("settings.%s must name an existing profile", k)
			}
			if k == "default_profile" {
				cfg.Default = s
			} else {
				cfg.Shortcut = s
			}
		}
	}
	return cfg, nil
}
