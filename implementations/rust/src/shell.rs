use crate::engine::{Patch, State};
use std::path::Path;
pub fn quote(s: &str) -> String {
    if s.is_empty() {
        return "''".into();
    }
    if s.bytes()
        .all(|b| b.is_ascii_alphanumeric() || b"_@%+=:,./-".contains(&b))
    {
        return s.into();
    }
    format!("'{}'", s.replace('\'', "'\\''"))
}
pub fn patch(p: &Patch, s: Option<&State>, shell: &str) -> String {
    let mut keys: Vec<String> = p
        .set
        .keys()
        .cloned()
        .chain(p.unset.iter().cloned())
        .chain(std::iter::once("__DEVWHO_STATE".into()))
        .collect();
    keys.sort();
    keys.dedup();
    let checks = keys
        .iter()
        .map(|k| format!("__devwho_writable {}", quote(k)))
        .collect::<Vec<_>>()
        .join(" && ");
    let mut out = format!("if {checks}; then\n");
    for k in &p.unset {
        out.push_str(&format!("  unset {k}\n"))
    }
    for (k, v) in &p.set {
        out.push_str(&format!("  export {k}={}\n", quote(v)))
    }
    let state = s
        .map(|v| serde_json::to_string(v).unwrap())
        .unwrap_or_default();
    out.push_str(&format!("  __DEVWHO_STATE={}\n", quote(&state)));
    out.push_str(if shell == "bash" {
        "  export -n __DEVWHO_STATE\n"
    } else {
        "  typeset -g +x __DEVWHO_STATE\n"
    });
    out.push_str("else\n  return 1\nfi\n");
    out
}
pub fn init(shell: &str, path: &Path, has_default: bool, env_profile: Option<&str>) -> String {
    let exe = std::env::current_exe().unwrap_or_default();
    let invoke = if let Some(profile) = env_profile {
        format!(
            "{} --env-file {} --env-profile {}",
            quote(&exe.display().to_string()),
            quote(&path.display().to_string()),
            quote(profile)
        )
    } else {
        format!(
            "{} --config {}",
            quote(&exe.display().to_string()),
            quote(&path.display().to_string())
        )
    };
    let writable = if shell == "bash" {
        r#"  local __devwho_decl __devwho_flags
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
  return 0"#
    } else {
        r#"  case "${parameters[$1]-}" in
    *readonly*) printf 'devwho: variable %s is readonly; identity unchanged\n' "$1" >&2; return 1 ;;
    *array*) printf 'devwho: variable %s is an array; identity unchanged\n' "$1" >&2; return 1 ;;
    ''|scalar|scalar-export) return 0 ;;
    *) printf 'devwho: variable %s has unsupported attributes; identity unchanged\n' "$1" >&2; return 1 ;;
  esac
  return 0"#
    };
    let mut text=format!("__devwho_writable() {{\n{writable}\n}}\n__devwho_transition() {{\n  local __devwho_patch\n  __devwho_patch=$(printf '%s' \"${{__DEVWHO_STATE-}}\" | {invoke} internal transition --shell {shell} \"$@\") || return $?\n  eval \"$__devwho_patch\"\n}}\nsetdev() {{\n  __devwho_transition --activate \"$@\" || return $?\n  {invoke} internal notice\n}}\nunsetdev() {{\n  __devwho_transition --restore || return $?\n  {invoke} internal notice\n}}\n");
    if has_default {
        text.push_str(&format!("if [ -z \"${{DEVWHO_PROFILE-}}\" ]; then\n  __devwho_bootstrap() {{\n    local __devwho_patch\n    __devwho_patch=$({invoke} internal bootstrap --shell {shell}) || return $?\n    eval \"$__devwho_patch\"\n  }}\n  __devwho_bootstrap\n  unset -f __devwho_bootstrap\nfi\n"));
    }
    text
}
