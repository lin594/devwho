  local __devwho_decl __devwho_flags
  __devwho_decl=$(declare -p "$1" 2>/dev/null) || return 0
  __devwho_flags=${__devwho_decl#declare -}
  __devwho_flags=${__devwho_flags%% *}
  case "$__devwho_flags" in
    *r*) printf 'devwho: variable %s is readonly; identity unchanged\n' "$1" >&2; return 1 ;;
    *a*|*A*) printf 'devwho: variable %s is an array; identity unchanged\n' "$1" >&2; return 1 ;;
  esac
  case "${__devwho_flags//[x-]/}" in
    '') return 0;;
    *) printf 'devwho: variable %s has unsupported attributes; identity unchanged\n' "$1" >&2; return 1;;
  esac
