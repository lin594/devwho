  case "${parameters[$1]-}" in
    *readonly*) printf 'devwho: variable %s is readonly; identity unchanged\n' "$1" >&2; return 1 ;;
    *array*) printf 'devwho: variable %s is an array; identity unchanged\n' "$1" >&2; return 1 ;;
    ''|scalar|scalar-export) return 0 ;;
    *) printf 'devwho: variable %s has unsupported attributes; identity unchanged\n' "$1" >&2; return 1 ;;
  esac
