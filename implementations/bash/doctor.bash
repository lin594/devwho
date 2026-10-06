# Sourced only from this implementation's fixed installation directory.
__devwho_report() {
 printf '%s: %s%s\n' "$1" "$2" "${3:+ — $3}"
 case $2 in FAIL) __devwho_failed=true;; UNVERIFIED) __devwho_unverified=true;; esac
}
__devwho_doctor() {
 local __devwho_name='' __devwho_offline=false __devwho_failed=false __devwho_unverified=false
 local __devwho_expected __devwho_actual __devwho_status __devwho_key __devwho_value __devwho_kind __devwho_rc
 while [ $# -gt 0 ]; do case $1 in --offline) __devwho_offline=true;; --*) __devwho_die 'unknown doctor option';; *) [ -z "$__devwho_name" ] || __devwho_die 'unexpected doctor argument'; __devwho_name=$1;; esac; shift; done
 __devwho_name=${__devwho_name:-${DEVWHO_PROFILE-}}
 if [ -z "$__devwho_name" ]; then printf '%s\n' 'FAIL: no active profile; use setdev PROFILE or name a profile to diagnose'; return 1; fi
 __devwho_profile_exists "$__devwho_name"
 printf 'Profile: %s\n' "$__devwho_name"
 __devwho_status=FAIL; [ "${DEVWHO_PROFILE-}" != "$__devwho_name" ] || __devwho_status=OK
 __devwho_report Context "$__devwho_status" 'metadata is not proof of authentication'
 if ! __devwho_run_jq -n --slurpfile cfg "$__devwho_tmp/config.json" --slurpfile environ "$__devwho_tmp/env.json" --arg name "$__devwho_name" 'include "core"; compile($cfg[0].profiles[$name];$name;$environ[0])' > "$__devwho_tmp/desired.json" || ! __devwho_check_key "$__devwho_tmp/desired.json"; then
  __devwho_report 'Configuration/environment' FAIL 'invalid profile/environment'; return 1
 fi
 if __devwho_get -e --arg name "$__devwho_name" '.profiles[$name].git|has("name")' >/dev/null; then
  __devwho_expected=$(__devwho_get --arg name "$__devwho_name" '.profiles[$name].git|.name+" <"+.email+">"')
  for __devwho_kind in AUTHOR COMMITTER; do
   case $__devwho_kind in AUTHOR) __devwho_label=author;; COMMITTER) __devwho_label=committer;; esac
   if __devwho_actual=$(__devwho_timeout 10 git var "GIT_${__devwho_kind}_IDENT" 2>/dev/null); then
    if [[ $__devwho_actual = "$__devwho_expected "* ]]; then __devwho_report "Git $__devwho_label" OK "$__devwho_expected"
    else
     __devwho_actual=$(printf "%s" "$__devwho_actual" | "$__devwho_jq" -Rrs '(try capture("^(?<identity>[^\\r\\n]*<[^\\r\\n]*>) [0-9]+ [+-][0-9]+$").identity catch null) // "unrecognized identity output"')
     __devwho_report "Git $__devwho_label" FAIL "expected $__devwho_expected; actual $__devwho_actual"
    fi
   else __devwho_report "Git $__devwho_label" UNVERIFIED 'Git unavailable or cannot resolve identity'; fi
  done
 fi
 if "$__devwho_jq" -e '.runtime|length>0' "$__devwho_tmp/desired.json" >/dev/null; then
  __devwho_status=OK
  if ! command -v git >/dev/null; then __devwho_status=UNVERIFIED
  else
   while IFS= read -r -d '' __devwho_key; do
    __devwho_timeout 10 git config --null --get-all "$__devwho_key" > "$__devwho_tmp/git-values" 2>/dev/null; __devwho_rc=$?
    if [ "$__devwho_rc" != 0 ] || ! "$__devwho_jq" -e -Rs --slurpfile desired "$__devwho_tmp/desired.json" --arg key "$__devwho_key" 'split("\u0000")|if .[-1]=="" then .[:-1] else . end | . as $actual | [$desired[0].runtime[]|select(.[0]==$key)|.[1]] as $wanted | $actual[-($wanted|length):]==$wanted' "$__devwho_tmp/git-values" >/dev/null; then __devwho_status=FAIL; fi
   done < <("$__devwho_jq" -j '[.runtime[][0]]|unique[]|.,"\u0000"' "$__devwho_tmp/desired.json")
  fi
  __devwho_report 'Git runtime configuration' "$__devwho_status" 'values hidden'
 fi
 if "$__devwho_jq" -e '.ssh_file!=null' "$__devwho_tmp/desired.json" >/dev/null; then
  __devwho_status=FAIL
  "$__devwho_jq" -ne --slurpfile environ "$__devwho_tmp/env.json" --slurpfile d "$__devwho_tmp/desired.json" '$environ[0].GIT_SSH_COMMAND==$d[0].values.GIT_SSH_COMMAND' >/dev/null && __devwho_status=OK
  __devwho_report 'Git SSH command' "$__devwho_status" 'local command/key check only; remote authentication is unverified'
 fi
 while IFS= read -r __devwho_key; do
  __devwho_status=FAIL
  "$__devwho_jq" -ne --slurpfile environ "$__devwho_tmp/env.json" --slurpfile d "$__devwho_tmp/desired.json" --arg key "$__devwho_key" '$environ[0][$key]==$d[0].values[$key]' >/dev/null && __devwho_status=OK
  __devwho_report "Environment $__devwho_key" "$__devwho_status" 'value hidden'
 done < <(__devwho_get --arg name "$__devwho_name" '.profiles[$name].env|keys[]')
 while IFS= read -r __devwho_key; do
  __devwho_status=FAIL
  "$__devwho_jq" -ne --slurpfile environ "$__devwho_tmp/env.json" --arg key "$__devwho_key" '$environ[0]|has($key)|not' >/dev/null && __devwho_status=OK
  __devwho_report "Unset $__devwho_key" "$__devwho_status"
 done < <("$__devwho_jq" -r '.unset[]' "$__devwho_tmp/desired.json")
 if __devwho_get -e --arg name "$__devwho_name" '.profiles[$name].github|length>0' >/dev/null; then
  for __devwho_key in GH_CONFIG_DIR GH_HOST; do
   __devwho_status=FAIL
   "$__devwho_jq" -ne --slurpfile environ "$__devwho_tmp/env.json" --slurpfile d "$__devwho_tmp/desired.json" --arg key "$__devwho_key" '$environ[0][$key]==$d[0].values[$key]' >/dev/null && __devwho_status=OK
   case $__devwho_key in GH_CONFIG_DIR) __devwho_label='config directory';; GH_HOST) __devwho_label=hostname;; esac
   __devwho_report "GitHub $__devwho_label" "$__devwho_status"
  done
  __devwho_expected=$(__devwho_get --arg name "$__devwho_name" '.profiles[$name].github.expected_user')
  if [ "$__devwho_offline" = true ]; then __devwho_report 'GitHub identity' UNVERIFIED "offline mode; expected $__devwho_expected"
  elif ! command -v gh >/dev/null; then __devwho_report 'GitHub identity' UNVERIFIED "install GitHub CLI; expected $__devwho_expected"
  else
   __devwho_host=$(__devwho_get --arg name "$__devwho_name" '.profiles[$name].github.hostname // "github.com"')
   if __devwho_actual=$(__devwho_timeout 15 gh api --hostname "$__devwho_host" user --jq .login 2>/dev/null) && [[ $__devwho_actual =~ ^[A-Za-z0-9_.-]{1,100}$ ]]; then
    __devwho_status=FAIL; [ "$__devwho_actual" != "$__devwho_expected" ] || __devwho_status=OK
    __devwho_report 'GitHub identity' "$__devwho_status" "expected $__devwho_expected; actual $__devwho_actual"
   else __devwho_report 'GitHub identity' UNVERIFIED "API/login unavailable; expected $__devwho_expected"; fi
  fi
 fi
 [ "$__devwho_failed" != true ] || return 1
 [ "$__devwho_unverified" != true ] || return 2
 return 0
}
