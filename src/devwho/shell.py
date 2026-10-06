"""Render literal environment values for real Bash and Zsh sessions."""

import json
import shlex
import sys
import zipfile
from pathlib import Path

from .engine import EnvironmentPatch


def render_patch(patch: EnvironmentPatch, state: dict | None, shell: str) -> str:
    keys = sorted(set(patch.set) | set(patch.unset) | {"__DEVWHO_STATE"})
    checks = " && ".join("__devwho_writable " + shlex.quote(key) for key in keys)
    lines = ["if " + checks + "; then"]
    lines.extend("  unset " + key for key in sorted(patch.unset))
    lines.extend(
        "  export " + key + "=" + shlex.quote(value) for key, value in sorted(patch.set.items())
    )
    encoded = "" if state is None else json.dumps(state, ensure_ascii=True, separators=(",", ":"))
    lines.append("  __DEVWHO_STATE=" + shlex.quote(encoded))
    lines.append(
        "  " + ("export -n __DEVWHO_STATE" if shell == "bash" else "typeset -g +x __DEVWHO_STATE")
    )
    lines.extend(["else", "  return 1", "fi"])
    return "\n".join(lines) + "\n"


def render_init(shell: str, config_path: Path, has_default: bool) -> str:
    # Pin the interpreter and package entry point; changing PATH cannot redirect
    # the shell's transition engine to a different executable.
    archive = Path(sys.argv[0]).resolve()
    launcher = (
        archive
        if archive.is_file() and zipfile.is_zipfile(archive)
        else Path(__file__).with_name("__main__.py").resolve()
    )
    invocation = shlex.join(
        [
            sys.executable,
            str(launcher),
            "--config",
            str(config_path),
        ]
    )
    if shell == "bash":
        writable = r"""  local __devwho_decl __devwho_flags
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
  return 0"""
    else:
        writable = r"""  case "${parameters[$1]-}" in
    *readonly*) printf 'devwho: variable %s is readonly; identity unchanged\n' "$1" >&2; return 1 ;;
    *array*) printf 'devwho: variable %s is an array; identity unchanged\n' "$1" >&2; return 1 ;;
    ''|scalar|scalar-export) return 0 ;;
    *) printf 'devwho: variable %s has unsupported attributes; identity unchanged\n' "$1" >&2; return 1 ;;
  esac
  return 0"""
    text = "__devwho_writable() {\n" + writable + "\n}\n"
    text += "__devwho_transition() {\n"
    text += "  local __devwho_patch\n"
    text += (
        "  __devwho_patch=$(printf '%s' \"${__DEVWHO_STATE-}\" | "
        + invocation
        + " internal transition --shell "
        + shell
        + ' "$@") || return $?\n'
    )
    text += '  eval "$__devwho_patch"\n}\n'
    text += 'setdev() {\n  __devwho_transition --activate "$@" || return $?\n'
    text += "  " + invocation + " internal notice\n}\n"
    text += "unsetdev() {\n  __devwho_transition --restore || return $?\n"
    text += "  " + invocation + " internal notice\n}\n"
    if has_default:
        text += 'if [ -z "${DEVWHO_PROFILE-}" ]; then\n'
        text += "  __devwho_bootstrap() {\n    local __devwho_patch\n"
        text += "    __devwho_patch=$(" + invocation + " internal bootstrap --shell " + shell
        text += ') || return $?\n    eval "$__devwho_patch"\n  }\n'
        text += "  __devwho_bootstrap\n  unset -f __devwho_bootstrap\nfi\n"
    return text
