package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"strconv"
	"strings"
	"unicode/utf8"
)

type Compiled struct {
	Values  Env
	Unset   []string
	Runtime []Pair
}
type Patch struct {
	Set   Env
	Unset []string
}
type Runtime struct {
	Baseline Env    `json:"baseline"`
	Before   []Pair `json:"before"`
	Owned    []Pair `json:"owned"`
}
type State struct {
	Version  int                `json:"version"`
	Profile  string             `json:"profile"`
	Baseline map[string]*string `json:"baseline"`
	Managed  []string           `json:"managed"`
	Runtime  *Runtime           `json:"runtime"`
}

func clone[V any](m map[string]V) map[string]V {
	r := map[string]V{}
	for k, v := range m {
		r[k] = v
	}
	return r
}
func (p Patch) Apply(env Env) Env {
	r := Env(clone(env))
	for _, k := range p.Unset {
		delete(r, k)
	}
	for k, v := range p.Set {
		r[k] = v
	}
	return r
}
func conflicts(p *Profile, env Env) error {
	for _, k := range []string{"GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"} {
		if env[k] != "" {
			return fmt.Errorf("Conflicting environment variable: %s", k)
		}
	}
	if len(p.GitHub) > 0 {
		for _, k := range []string{"GH_TOKEN", "GITHUB_TOKEN"} {
			if env[k] != "" || p.Env[k] != "" {
				return fmt.Errorf("Conflicting environment variable: %s", k)
			}
		}
	}
	return nil
}
func semanticPath(s string, env Env, field string) (string, error) {
	if s == "~" || strings.HasPrefix(s, "~/") {
		if env["HOME"] == "" {
			return "", fmt.Errorf("%s requires a nonempty effective HOME for ~ paths", field)
		}
		s = env["HOME"] + s[1:]
	} else if !filepath.IsAbs(s) {
		return "", fmt.Errorf("%s must be an absolute path, ~, or start with ~/", field)
	}
	if !filepath.IsAbs(s) {
		return "", fmt.Errorf("%s must expand to an absolute path", field)
	}
	return s, nil
}

var shellSafe = regexp.MustCompile(`^[A-Za-z0-9_@%+=:,./-]+$`)

func quote(s string) string {
	if shellSafe.MatchString(s) {
		return s
	}
	return "'" + strings.ReplaceAll(s, "'", `'"'"'`) + "'"
}
func compile(p *Profile, env Env) (*Compiled, error) {
	if e := conflicts(p, env); e != nil {
		return nil, e
	}
	values := Env(clone(p.Env))
	values["DEVWHO_PROFILE"] = p.Name
	runtime := []Pair{}
	r, _ := p.Git["config"].(map[string]any)
	for _, k := range p.GitOrder {
		v := r[k]
		a := []any{v}
		if list, ok := v.([]any); ok {
			a = list
		}
		for _, v := range a {
			runtime = append(runtime, Pair{k, v.(string)})
		}
	}
	if n, ok := p.Git["name"]; ok {
		for _, kind := range []string{"user", "author", "committer"} {
			runtime = append(runtime, Pair{kind + ".name", n.(string)}, Pair{kind + ".email", p.Git["email"].(string)})
		}
	}
	for _, pkey := range [][2]string{{"signing_key", "user.signingKey"}, {"signing_format", "gpg.format"}} {
		if v, ok := p.Git[pkey[0]]; ok {
			runtime = append(runtime, Pair{pkey[1], v.(string)})
		}
	}
	if b, ok := p.Git["sign_commits"].(bool); ok {
		runtime = append(runtime, Pair{"commit.gpgSign", strconv.FormatBool(b)})
	}
	pathEnv := Env(clone(env))
	for _, k := range p.Unset {
		delete(pathEnv, k)
	}
	for k, v := range p.Env {
		pathEnv[k] = v
	}
	if len(p.SSH) > 0 {
		id, e := semanticPath(p.SSH["identity_file"].(string), pathEnv, "git_ssh.identity_file")
		if e != nil {
			return nil, e
		}
		stat, e := os.Stat(id)
		if e != nil || !stat.Mode().IsRegular() {
			return nil, fmt.Errorf("git_ssh.identity_file must identify an existing file")
		}
		command := "ssh -i " + quote(id)
		b, ok := p.SSH["identities_only"].(bool)
		if !ok || b {
			command += " -o IdentitiesOnly=yes"
		}
		values["GIT_SSH_COMMAND"] = command
	}
	if len(p.GitHub) > 0 {
		s, e := semanticPath(p.GitHub["config_dir"].(string), pathEnv, "github.config_dir")
		if e != nil {
			return nil, e
		}
		values["GH_CONFIG_DIR"] = s
		host, ok := p.GitHub["hostname"].(string)
		if !ok {
			host = "github.com"
		}
		values["GH_HOST"] = host
	}
	return &Compiled{values, p.Unset, runtime}, nil
}

var digits = regexp.MustCompile(`^[0-9]+$`)

func pairs(env Env) ([]Pair, error) {
	r := []Pair{}
	s, ok := env["GIT_CONFIG_COUNT"]
	if !ok {
		return r, nil
	}
	if len(s) > 6 || !digits.MatchString(s) {
		return nil, fmt.Errorf("Invalid GIT_CONFIG_COUNT")
	}
	n, e := strconv.Atoi(s)
	if e != nil || n > 4096 {
		return nil, fmt.Errorf("Invalid GIT_CONFIG_COUNT")
	}
	for i := 0; i < n; i++ {
		k, ko := env[fmt.Sprintf("GIT_CONFIG_KEY_%d", i)]
		v, vo := env[fmt.Sprintf("GIT_CONFIG_VALUE_%d", i)]
		if !ko || !vo {
			return nil, fmt.Errorf("Missing runtime configuration variable at index %d", i)
		}
		if k == "" || strings.ContainsRune(k, 0) || strings.ContainsRune(v, 0) {
			return nil, fmt.Errorf("Invalid runtime configuration variable at index %d", i)
		}
		r = append(r, Pair{k, v})
	}
	return r, nil
}
func exactKeys(m map[string]any, keys ...string) bool {
	if len(m) != len(keys) {
		return false
	}
	for _, k := range keys {
		if _, ok := m[k]; !ok {
			return false
		}
	}
	return true
}
func readState(raw []byte) (*State, error) {
	if len(raw) == 0 {
		return nil, nil
	}
	if utf8.RuneCount(raw) > 1024*1024 {
		return nil, fmt.Errorf("DevWho shell state exceeds its size limit")
	}
	var v any
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	if e := dec.Decode(&v); e != nil {
		return nil, fmt.Errorf("Invalid DevWho shell state; open a fresh shell")
	}
	if e := dec.Decode(new(any)); e != io.EOF {
		return nil, fmt.Errorf("Invalid DevWho shell state; open a fresh shell")
	}
	if v == nil {
		return nil, nil
	}
	return validateState(v)
}
func validateState(v any) (*State, error) {
	bad := func() (*State, error) { return nil, fmt.Errorf("Invalid DevWho shell state") }
	m, ok := v.(map[string]any)
	if !ok || !exactKeys(m, "version", "profile", "baseline", "managed", "runtime") {
		return bad()
	}
	version, ok := m["version"].(json.Number)
	if !ok || version.String() != "1" {
		return nil, fmt.Errorf("Unsupported DevWho shell state")
	}
	profile, ok := m["profile"].(string)
	if !ok || !profileName.MatchString(profile) {
		return bad()
	}
	b, ok := m["baseline"].(map[string]any)
	if !ok {
		return bad()
	}
	managed, ok := m["managed"].([]any)
	if !ok {
		return bad()
	}
	s := &State{1, profile, map[string]*string{}, []string{}, nil}
	for k, v := range b {
		if e := validateEnv(k, true); e != nil {
			return nil, e
		}
		if runtimeName.MatchString(k) {
			return nil, fmt.Errorf("Invalid DevWho baseline")
		}
		if v != nil {
			x, ok := v.(string)
			if !ok || strings.ContainsRune(x, 0) {
				return nil, fmt.Errorf("Invalid DevWho baseline")
			}
			s.Baseline[k] = &x
		} else {
			s.Baseline[k] = nil
		}
	}
	seen := map[string]bool{}
	for _, v := range managed {
		k, ok := v.(string)
		if !ok {
			return bad()
		}
		if _, ok := s.Baseline[k]; !ok || seen[k] {
			return nil, fmt.Errorf("Invalid DevWho managed variables")
		}
		seen[k] = true
		s.Managed = append(s.Managed, k)
	}
	if !seen["DEVWHO_PROFILE"] {
		return nil, fmt.Errorf("Invalid DevWho managed variables")
	}
	if m["runtime"] != nil {
		r, ok := m["runtime"].(map[string]any)
		if !ok || !exactKeys(r, "baseline", "before", "owned") {
			return nil, fmt.Errorf("Invalid DevWho runtime state")
		}
		rb, ok := r["baseline"].(map[string]any)
		if !ok {
			return nil, fmt.Errorf("Invalid DevWho runtime baseline")
		}
		runtime := &Runtime{Env{}, []Pair{}, []Pair{}}
		for k, v := range rb {
			x, ok := v.(string)
			if !runtimeName.MatchString(k) || !ok || strings.ContainsRune(x, 0) {
				return nil, fmt.Errorf("Invalid DevWho runtime baseline")
			}
			runtime.Baseline[k] = x
		}
		if _, e := pairs(runtime.Baseline); e != nil {
			return nil, e
		}
		for _, field := range []string{"before", "owned"} {
			a, ok := r[field].([]any)
			if !ok || len(a) > 4096 {
				return nil, fmt.Errorf("Invalid DevWho runtime pairs")
			}
			ps := []Pair{}
			for _, v := range a {
				pa, ok := v.([]any)
				if !ok || len(pa) != 2 {
					return nil, fmt.Errorf("Invalid DevWho runtime pairs")
				}
				x, xo := pa[0].(string)
				y, yo := pa[1].(string)
				if !xo || !yo || x == "" || strings.ContainsRune(x, 0) || strings.ContainsRune(y, 0) {
					return nil, fmt.Errorf("Invalid DevWho runtime pairs")
				}
				ps = append(ps, Pair{x, y})
			}
			if field == "before" {
				runtime.Before = ps
			} else {
				runtime.Owned = ps
			}
		}
		s.Runtime = runtime
	}
	return s, nil
}
func runtimeTransition(target Env, old *Runtime, owned []Pair) (*Runtime, error) {
	if old == nil && len(owned) == 0 {
		return nil, nil
	}
	current, e := pairs(target)
	if e != nil {
		return nil, e
	}
	if old == nil {
		b := Env{}
		for k, v := range target {
			if runtimeName.MatchString(k) {
				b[k] = v
			}
		}
		old = &Runtime{b, append([]Pair{}, current...), []Pair{}}
	}
	boundary := len(old.Before)
	end := boundary + len(old.Owned)
	if len(current) < end || !reflect.DeepEqual(current[:boundary], old.Before) || !reflect.DeepEqual(current[boundary:end], old.Owned) {
		return nil, fmt.Errorf("Managed Git runtime configuration was changed; refusing to remove unrelated configuration")
	}
	retained := append(append([]Pair{}, current[:boundary]...), current[end:]...)
	desiredPairs := append(append([]Pair{}, retained...), owned...)
	if len(desiredPairs) > 4096 {
		return nil, fmt.Errorf("Too many Git runtime configuration entries")
	}
	desired := Env(clone(old.Baseline))
	original, e := pairs(old.Baseline)
	if e != nil {
		return nil, e
	}
	if len(owned) > 0 || !reflect.DeepEqual(retained, original) {
		desired["GIT_CONFIG_COUNT"] = strconv.Itoa(len(desiredPairs))
		for i, p := range desiredPairs {
			desired[fmt.Sprintf("GIT_CONFIG_KEY_%d", i)] = p[0]
			desired[fmt.Sprintf("GIT_CONFIG_VALUE_%d", i)] = p[1]
		}
	}
	touched := []string{"GIT_CONFIG_COUNT"}
	n := len(current)
	if len(desiredPairs) > n {
		n = len(desiredPairs)
	}
	for i := 0; i < n; i++ {
		touched = append(touched, fmt.Sprintf("GIT_CONFIG_KEY_%d", i), fmt.Sprintf("GIT_CONFIG_VALUE_%d", i))
	}
	for _, k := range touched {
		if v, ok := desired[k]; ok {
			target[k] = v
		} else {
			delete(target, k)
		}
	}
	return &Runtime{Env(clone(old.Baseline)), retained, append([]Pair{}, owned...)}, nil
}
func transition(cfg *Config, name *string, env Env, old *State) (Patch, *State, error) {
	empty := Patch{Env{}, []string{}}
	var p *Profile
	if name != nil {
		p = cfg.Profiles[*name]
		if p == nil {
			return empty, nil, fmt.Errorf("Unknown profile")
		}
		if e := conflicts(p, env); e != nil {
			return empty, nil, e
		}
	}
	target := Env(clone(env))
	baseline := map[string]*string{}
	var runtime *Runtime
	if old != nil {
		baseline = clone(old.Baseline)
		runtime = old.Runtime
		for _, k := range old.Managed {
			if v := baseline[k]; v == nil {
				delete(target, k)
			} else {
				target[k] = *v
			}
		}
	}
	var compiled *Compiled
	var e error
	owned := []Pair{}
	if p != nil {
		compiled, e = compile(p, target)
		if e != nil {
			return empty, nil, e
		}
		owned = compiled.Runtime
	}
	runtime, e = runtimeTransition(target, runtime, owned)
	if e != nil {
		return empty, nil, e
	}
	var next *State
	if compiled != nil {
		keys := map[string]bool{}
		for k := range compiled.Values {
			keys[k] = true
		}
		for _, k := range compiled.Unset {
			keys[k] = true
		}
		managed := sortedKeys(keys)
		for _, k := range managed {
			if _, ok := baseline[k]; !ok {
				if v, ok := target[k]; ok {
					x := v
					baseline[k] = &x
				} else {
					baseline[k] = nil
				}
			}
		}
		for _, k := range compiled.Unset {
			delete(target, k)
		}
		for k, v := range compiled.Values {
			target[k] = v
		}
		next = &State{1, *name, baseline, managed, runtime}
	}
	for k, v := range target {
		original, ok := env[k]
		if !ok || original != v {
			empty.Set[k] = v
		}
	}
	for _, k := range sortedKeys(env) {
		if _, ok := target[k]; !ok {
			empty.Unset = append(empty.Unset, k)
		}
	}
	return empty, next, nil
}
