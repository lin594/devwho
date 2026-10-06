package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

func renderPatch(p Patch, state *State, shell string) string {
	keys := map[string]bool{"__DEVWHO_STATE": true}
	for k := range p.Set {
		keys[k] = true
	}
	for _, k := range p.Unset {
		keys[k] = true
	}
	checks := []string{}
	for _, k := range sortedKeys(keys) {
		checks = append(checks, "__devwho_writable "+quote(k))
	}
	lines := []string{"if " + strings.Join(checks, " && ") + "; then"}
	for _, k := range p.Unset {
		lines = append(lines, "  unset "+k)
	}
	for _, k := range sortedKeys(p.Set) {
		lines = append(lines, "  export "+k+"="+quote(p.Set[k]))
	}
	encoded := ""
	if state != nil {
		data, _ := json.Marshal(state)
		encoded = string(data)
	}
	lines = append(lines, "  __DEVWHO_STATE="+quote(encoded))
	if shell == "bash" {
		lines = append(lines, "  export -n __DEVWHO_STATE")
	} else {
		lines = append(lines, "  typeset -g +x __DEVWHO_STATE")
	}
	lines = append(lines, "else", "  return 1", "fi")
	return strings.Join(lines, "\n") + "\n"
}
func renderInit(shell string, cfg *Config) (string, error) {
	exe, e := os.Executable()
	if e != nil {
		return "", e
	}
	invocation := quote(exe) + " --config " + quote(cfg.Path)
	if cfg.EnvFile {
		invocation = quote(exe) + " --env-file " + quote(cfg.Path) + " --env-profile " + quote(cfg.Shortcut)
	}
	writable := `  local __devwho_decl __devwho_flags
  __devwho_decl=$(declare -p "$1" 2>/dev/null) || return 0
  __devwho_flags=${__devwho_decl#declare -}
  __devwho_flags=${__devwho_flags%% *}
  case "$__devwho_flags" in
    *r*) printf 'devwho: variable %s is readonly; identity unchanged\n' "$1" >&2; return 1 ;;
    *a*|*A*) printf 'devwho: variable %s is an array; identity unchanged\n' "$1" >&2; return 1 ;;
  esac
  case "${__devwho_flags//[x-]/}" in
    '') ;;
    *) printf 'devwho: variable %s has unsupported attributes; identity unchanged\n' "$1" >&2; return 1 ;;
  esac
  return 0`
	if shell == "zsh" {
		writable = `  case "${parameters[$1]-}" in
    *readonly*) printf 'devwho: variable %s is readonly; identity unchanged\n' "$1" >&2; return 1 ;;
    *array*) printf 'devwho: variable %s is an array; identity unchanged\n' "$1" >&2; return 1 ;;
    ''|scalar|scalar-export) return 0 ;;
    *) printf 'devwho: variable %s has unsupported attributes; identity unchanged\n' "$1" >&2; return 1 ;;
  esac
  return 0`
	}
	text := "__devwho_writable() {\n" + writable + "\n}\n__devwho_transition() {\n  local __devwho_patch\n"
	text += "  __devwho_patch=$(printf '%s' \"${__DEVWHO_STATE-}\" | " + invocation + " internal transition --shell " + shell + " \"$@\") || return $?\n  eval \"$__devwho_patch\"\n}\n"
	text += "setdev() {\n  __devwho_transition --activate \"$@\" || return $?\n  " + invocation + " internal notice\n}\nunsetdev() {\n  __devwho_transition --restore || return $?\n  " + invocation + " internal notice\n}\n"
	if cfg.Default != "" {
		text += "if [ -z \"${DEVWHO_PROFILE-}\" ]; then\n  __devwho_bootstrap() {\n    local __devwho_patch\n    __devwho_patch=$(" + invocation + " internal bootstrap --shell " + shell + ") || return $?\n    eval \"$__devwho_patch\"\n  }\n  __devwho_bootstrap\n  unset -f __devwho_bootstrap\nfi\n"
	}
	return text, nil
}
func validShell(s string) error {
	if s != "bash" && s != "zsh" {
		return fmt.Errorf("internal transition requires a shell")
	}
	return nil
}
