#!/bin/bash
# DevWho compatibility core: Bash orchestration, jq data transformations,
# independently vendored Perl TOML parser. No Python runtime dependency.
set -o pipefail
# Bounded diagnostic process execution using Bash and the standard command -p sleep utility.
__devwho_timeout() {
 local __devwho_seconds=$1 __devwho_pid __devwho_guard __devwho_rc
 shift
 "$@" &
 __devwho_pid=$!
 (
   __devwho_sleeper=''
   trap '[ -z "$__devwho_sleeper" ] || kill "$__devwho_sleeper" 2>/dev/null; exit 0' TERM
   command -p sleep "$__devwho_seconds" & __devwho_sleeper=$!
   wait "$__devwho_sleeper"
   kill -TERM "$__devwho_pid" 2>/dev/null
   command -p sleep 1 & __devwho_sleeper=$!
   wait "$__devwho_sleeper"
   kill -KILL "$__devwho_pid" 2>/dev/null
 ) >/dev/null 2>&1 &
 __devwho_guard=$!
 wait "$__devwho_pid" 2>/dev/null; __devwho_rc=$?
 kill "$__devwho_guard" 2>/dev/null
 wait "$__devwho_guard" 2>/dev/null
 return "$__devwho_rc"
}
__devwho_die() { printf 'devwho: %s\n' "$*" >&2; exit 1; }
__devwho_usage_error() { printf 'devwho: %s\n' "$*" >&2; exit 2; }
__devwho_capture_fd=''; __devwho_launcher=''
if [ "${1-}" = --capture-fd ]; then
 [ $# -ge 4 ] && [ "$3" = --launcher ] || __devwho_die 'invalid environment transport'
 [[ $2 =~ ^[0-9]+$ ]] || __devwho_die 'invalid environment descriptor'
 __devwho_capture_fd=$2; __devwho_launcher=$4; shift 4
fi
if [ "${1-}" = --tools ]; then
 [ $# -ge 3 ] || __devwho_die 'invalid internal tool binding'
 __devwho_jq=$2; __devwho_perl=$3; shift 3
else
 __devwho_jq=$(command -v jq || command -p -v jq) || __devwho_die 'jq 1.6 or newer is required'
 __devwho_perl=$(command -v perl || command -p -v perl) || __devwho_die 'Perl 5.18 or newer is required'
fi
__devwho_perl_run() { PERL5OPT= PERL5LIB= PERLLIB= PERL_UNICODE=0 PERLIO= "$__devwho_perl" "$@"; }
__devwho_jq=$(__devwho_perl_run -MCwd=abs_path -e 'print abs_path($ARGV[0]), "."' "$__devwho_jq"); __devwho_jq=${__devwho_jq%.}
__devwho_perl=$(__devwho_perl_run -MCwd=abs_path -e 'print abs_path($ARGV[0]), "."' "$__devwho_perl"); __devwho_perl=${__devwho_perl%.}
__devwho_self=$(__devwho_perl_run -MCwd=abs_path -e 'print abs_path($ARGV[0])' "$0") || exit 1
__devwho_dir=${__devwho_self%/*}
__devwho_self=${__devwho_launcher:-$__devwho_dir/devwho}
__devwho_home=${HOME:-$(__devwho_perl_run -e 'print((getpwuid($<))[7])')}
__devwho_config=${DEVWHO_CONFIG:-${XDG_CONFIG_HOME:-${__devwho_home}/.config}/devwho/config.toml}
__devwho_env_file=''; __devwho_env_profile=''; __devwho_explicit_config=false; __devwho_explicit_env_file=false; __devwho_explicit_env_profile=false
while [ $# -gt 0 ]; do
 case $1 in
 --config) [ $# -ge 2 ] || __devwho_die '--config needs a path'; __devwho_config=$2; __devwho_explicit_config=true; shift 2;;
 --env-file) [ $# -ge 2 ] || __devwho_die '--env-file needs a path'; __devwho_env_file=$2; __devwho_explicit_env_file=true; shift 2;;
 --env-profile) [ $# -ge 2 ] || __devwho_die '--env-profile needs a name'; __devwho_env_profile=$2; __devwho_explicit_env_profile=true; shift 2;;
 *) break;; esac
done
if [ "$__devwho_explicit_env_file" = true ]; then
 [ "$__devwho_explicit_config" != true ] || __devwho_die '--env-file and --config are mutually exclusive'
 __devwho_config=$__devwho_env_file
elif [ "$__devwho_explicit_env_profile" = true ]; then __devwho_die '--env-profile requires --env-file'; fi
if [ "$__devwho_explicit_env_profile" = true ] && [ -z "$__devwho_env_profile" ]; then __devwho_die '--env-profile requires a nonempty name'; fi
case ${1-} in --help|-h) printf '%s\n' 'Usage: devwho [--config PATH] COMMAND' 'Optional dotenv frontend: --env-file PATH [--env-profile NAME]' 'Commands: list, show PROFILE, current [--verbose], doctor [PROFILE] [--offline],' '  exec PROFILE -- COMMAND..., config path|init, init bash|zsh'; exit 0;; --version) printf '%s\n' 'devwho 0.1.0 (Bash compatibility core v1)'; exit 0;; esac
[ $# -gt 0 ] || __devwho_usage_error 'a command is required; use --help'
__devwho_command=$1; shift
if [ "${1-}" = --help ] || [ "${1-}" = -h ]; then
 printf 'Usage: devwho %s [arguments]\n' "$__devwho_command"; exit 0
fi
case $__devwho_config in '~') __devwho_config=$__devwho_home;; '~/'*) __devwho_config=$__devwho_home/${__devwho_config:2};; '~'*) __devwho_config=$(__devwho_perl_run -e 'my $p=shift; if($p =~ /^~([^\/]+)(.*)$/s){my $h=(getpwnam($1))[7]; $p=$h.$2 if defined $h} print $p' "$__devwho_config");; esac
if [ "$__devwho_command" = config ] && [ "${1-}" != export-env ]; then
 [ $# = 1 ] || __devwho_usage_error 'config requires path or init'
 case $1 in
 path) printf '%s\n' "$__devwho_config";;
 init) [ "$__devwho_explicit_env_file" != true ] || __devwho_die 'config init does not create dotenv files'; (umask 077; command -p mkdir -p "$(command -p dirname -- "$__devwho_config")" && set -C && command -p cat > "$__devwho_config" <<'TOML'
version = 1

[profiles.personal.git]
name = "Jane Doe"
email = "jane@example.com"

[profiles.work.git]
name = "Jane Doe"
email = "jane@company.example"
TOML
 ) 2>/dev/null || __devwho_die 'cannot create configuration exclusively'; printf 'Created %s; edit its example identities before use.\n' "$__devwho_config";;
 *) __devwho_usage_error 'config requires path or init';; esac; exit 0
fi
if [ "$__devwho_command" = current ]; then
 printf '%s\n' "${DEVWHO_PROFILE:-none}"
 if [ "${1-}" = --verbose ]; then
  printf 'Configuration: %s\nGitHub config directory: %s\nGitHub hostname: %s\n' "$__devwho_config" "${GH_CONFIG_DIR-default}" "${GH_HOST-github.com}"
  for __devwho_kind in AUTHOR COMMITTER; do
   __devwho_ident=$(__devwho_timeout 10 git var "GIT_${__devwho_kind}_IDENT" 2>/dev/null) || __devwho_ident=''
   __devwho_ident=$(printf '%s' "$__devwho_ident" | "$__devwho_jq" -Rrs '(try capture("^(?<identity>[^\\r\\n]*<[^\\r\\n]*>) [0-9]+ [+-][0-9]+$").identity catch null) // "unavailable"')
   case $__devwho_kind in AUTHOR) __devwho_label=author;; COMMITTER) __devwho_label=committer;; esac
   printf 'Git %s: %s\n' "$__devwho_label" "$__devwho_ident"
  done
  printf '%s\n' 'Use devwho doctor to verify actual tool identity.'
 elif [ $# -gt 0 ]; then __devwho_usage_error 'unknown current option'; fi
 exit 0
fi
__devwho_config=$(__devwho_perl_run -MCwd=abs_path -MFile::Spec -e 'print((abs_path($ARGV[0]) // File::Spec->rel2abs($ARGV[0])), ".")' "$__devwho_config"); __devwho_config=${__devwho_config%.}
umask 077
__devwho_tmp=$(command -p mktemp -d "/tmp/devwho-bash.XXXXXXXX") || exit 1
trap 'command -p rm -rf -- "$__devwho_tmp"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
__devwho_run_jq() { "$__devwho_jq" -L "$__devwho_dir" "$@" 2>"$__devwho_tmp/error" || { printf 'devwho: ' >&2; __devwho_perl_run -ne 'if (/Conflicting environment variable: (GH_TOKEN|GITHUB_TOKEN|GIT_AUTHOR_NAME|GIT_AUTHOR_EMAIL|GIT_COMMITTER_NAME|GIT_COMMITTER_EMAIL)$/) { print STDERR "Conflicting environment variable: $1\n"; $seen=1 } END { print STDERR "Invalid configuration, state, or environment\n" unless $seen }' "$__devwho_tmp/error"; return 1; }; }
if [ "$__devwho_explicit_env_file" = true ]; then
 __devwho_perl_run "$__devwho_dir/dotenv-json.pl" "$__devwho_config" "$__devwho_env_profile" > "$__devwho_tmp/raw.json" || exit 1
else
 __devwho_perl_run "$__devwho_dir/toml-json.pl" "$__devwho_config" > "$__devwho_tmp/raw.json" || exit 1
fi
__devwho_run_jq 'include "core"; config' "$__devwho_tmp/raw.json" > "$__devwho_tmp/config.json" || exit 1
if [ -n "$__devwho_capture_fd" ]; then
 command -p cat <&"$__devwho_capture_fd" > "$__devwho_tmp/env.json" || exit 1
 # Descriptor is validated numeric above; this eval contains no profile values.
 eval "exec $__devwho_capture_fd<&-"
else
 "$__devwho_jq" -n env > "$__devwho_tmp/env.json" || exit 1
fi
__devwho_get() { "$__devwho_jq" -r "$@" "$__devwho_tmp/config.json"; }
__devwho_profile_exists() { __devwho_get --arg name "$1" '.profiles|has($name)' | "$__devwho_jq" -e . >/dev/null || __devwho_die 'Unknown profile; run devwho list'; }
__devwho_transition() {
 __devwho_run_jq -n --slurpfile cfg "$__devwho_tmp/config.json" --slurpfile environ "$__devwho_tmp/env.json" --slurpfile old "$__devwho_tmp/state.json" --arg name "$1" 'include "core"; transition($cfg[0];(if $name=="" then null else $name end);$environ[0];$old[0])' > "$__devwho_tmp/patch.json" || return 1
 __devwho_check_key "$__devwho_tmp/patch.json"
}
__devwho_check_key() {
 if "$__devwho_jq" -e '.ssh_file != null' "$1" >/dev/null; then
  __devwho_key=$("$__devwho_jq" -r '.ssh_file+"."' "$1"); __devwho_key=${__devwho_key%.}
  [ -f "$__devwho_key" ] || { printf '%s\n' 'devwho: git_ssh.identity_file must identify an existing file' >&2; return 1; }
 fi
}
__devwho_notice() {
 [ "$(__devwho_get '.settings.handoff_warning // false')" = true ] || return 0
 if ! command -v git >/dev/null; then printf '%s\n' 'devwho: handoff check unavailable; check git status before taking over.' >&2; return 0; fi
 __devwho_dirty=$(__devwho_timeout 2 git status --porcelain --untracked-files=normal 2>/dev/null) || return 0
 [ -z "$__devwho_dirty" ] || printf '%s\n' 'devwho: this repository has uncommitted changes; confirm the handoff before editing or committing. Switching identity does not assign those changes.' >&2
 return 0
}
case $__devwho_command in
 config)
 [ $# = 2 ] && [ "$1" = export-env ] || __devwho_die 'config export-env needs PROFILE'
 __devwho_profile_exists "$2"
 __devwho_run_jq -r --arg name "$2" 'include "core"; .profiles[$name] | check((.git|del(.config)|length)==0 and (.git.config|length)==0 and (.git_ssh|length)==0 and (.github|length)==0 and (.unset_env|length)==0;"Cannot export semantic settings or unsets to dotenv") | "DEVWHO_PROFILE="+($name|tojson), (.env|to_entries[]|.key+"="+(.value|tojson))' "$__devwho_tmp/config.json";;
 list) [ $# = 0 ] || __devwho_usage_error 'unexpected argument'; __devwho_get '.profiles|keys[]';;
 show)
 [ $# = 1 ] || __devwho_usage_error 'show needs a profile'; __devwho_profile_exists "$1"
 __devwho_get --arg name "$1" '.profiles[$name] | "Profile: "+$name, (if .git|has("name") then "Git: "+.git.name+" <"+.git.email+">" else empty end), (if (.git_ssh|length)>0 then "Git SSH key: "+.git_ssh.identity_file else empty end), (if (.github|length)>0 then "GitHub expected user: "+.github.expected_user,"GitHub config: "+.github.config_dir else empty end), "Custom environment keys: "+(.env|keys|join(", ")), "Unset keys: "+(.unset_env|join(", "))';;
 exec)
 [ $# -ge 2 ] || __devwho_die 'exec needs PROFILE -- COMMAND'; __devwho_name=$1; shift; [ "${1-}" != -- ] || shift; [ $# -gt 0 ] || __devwho_die 'exec needs a command after --'; __devwho_profile_exists "$__devwho_name"
 printf null > "$__devwho_tmp/state.json"; __devwho_transition "$__devwho_name" || exit 1
 "$__devwho_jq" '.target' "$__devwho_tmp/patch.json" > "$__devwho_tmp/child.json" || exit 1
 trap - EXIT INT TERM
 PERL5OPT= PERL5LIB= PERLLIB= PERL_UNICODE=0 PERLIO= exec "$__devwho_perl" "$__devwho_dir/child-exec.pl" "$__devwho_tmp/child.json" "$__devwho_tmp" "$@";;
 internal)
 [ $# -gt 0 ] || __devwho_usage_error 'internal needs action'; __devwho_action=$1; shift
 if [ "$__devwho_action" = notice ]; then __devwho_notice; exit $?; fi
 __devwho_shell=''; __devwho_name=''; __devwho_restore=false
 while [ $# -gt 0 ]; do case $1 in
 --shell) [ $# -ge 2 ] || __devwho_usage_error 'missing shell'; __devwho_shell=$2; shift 2;;
 --restore) __devwho_restore=true; shift;;
 --activate) shift; if [ $# -gt 0 ] && [[ $1 != --* ]]; then __devwho_name=$1; shift; fi;;
 *) __devwho_usage_error 'unknown internal argument';; esac; done
 case $__devwho_shell in bash|zsh);; *) __devwho_die 'internal transition requires bash or zsh';; esac
 case $__devwho_action in
 bootstrap) __devwho_name=$(__devwho_get '.settings.default_profile // ""'); [ -n "$__devwho_name" ] || exit 0; printf null > "$__devwho_tmp/state.json";;
 transition) command -p head -c 1048577 > "$__devwho_tmp/state.json"; [ "$(command -p wc -c < "$__devwho_tmp/state.json")" -le 1048576 ] || __devwho_die 'DevWho shell state exceeds its size limit'; [ -s "$__devwho_tmp/state.json" ] || printf null > "$__devwho_tmp/state.json"
 __devwho_perl_run "$__devwho_dir/state-json.pl" "$__devwho_tmp/state.json" > "$__devwho_tmp/parsed-state.json" || exit 1
 command -p mv "$__devwho_tmp/parsed-state.json" "$__devwho_tmp/state.json"
 if [ "$__devwho_restore" != true ]; then [ -n "$__devwho_name" ] || __devwho_name=$(__devwho_get '.settings.shortcut_profile // ""'); [ -n "$__devwho_name" ] || __devwho_die 'setdev needs PROFILE or settings.shortcut_profile'; fi;;
 *) __devwho_die 'unknown internal action';; esac
 [ -z "$__devwho_name" ] || __devwho_profile_exists "$__devwho_name"
 __devwho_transition "$__devwho_name" || exit 1
 if [ "$__devwho_action" = bootstrap ]; then "$__devwho_jq" '.state=null' "$__devwho_tmp/patch.json" > "$__devwho_tmp/bootstrap.json"; command -p mv "$__devwho_tmp/bootstrap.json" "$__devwho_tmp/patch.json"; fi
 __devwho_run_jq -r --arg shell "$__devwho_shell" 'include "core"; render($shell)' "$__devwho_tmp/patch.json";;
 init)
 [ $# = 1 ] || __devwho_usage_error 'init needs bash or zsh'; __devwho_shell=$1
 case $__devwho_shell in bash|zsh);; *) __devwho_usage_error 'unsupported shell';; esac
 __devwho_default=$(__devwho_get '.settings.default_profile // ""')
 if [ -n "$__devwho_default" ] && [ -z "${DEVWHO_PROFILE-}" ]; then printf null > "$__devwho_tmp/state.json"; __devwho_transition "$__devwho_default" || exit 1; fi
 __devwho_source_flag=--config
 __devwho_source_profile=''
 if [ "$__devwho_explicit_env_file" = true ]; then __devwho_source_flag=--env-file; __devwho_source_profile=$(__devwho_get '.settings.shortcut_profile'); fi
 __devwho_invocation=$("$__devwho_jq" -nr --arg exe "$__devwho_self" --arg jq "$__devwho_jq" --arg perl "$__devwho_perl" --arg cfg "$__devwho_config" --arg flag "$__devwho_source_flag" --arg profile "$__devwho_source_profile" '[$perl,$exe,"--tools",$jq,$perl,$flag,$cfg]+(if $profile!="" then ["--env-profile",$profile] else [] end)|@sh')
 printf '__devwho_writable() {\n'; command -p cat "$__devwho_dir/writable.$__devwho_shell"; printf '}\n'
 command -p cat <<INIT
__devwho_transition() {
  local __devwho_patch
  __devwho_patch=\$(printf '%s' "\${__DEVWHO_STATE-}" | $__devwho_invocation internal transition --shell $__devwho_shell "\$@") || return \$?
  eval "\$__devwho_patch"
}
setdev() {
  __devwho_transition --activate "\$@" || return \$?
  $__devwho_invocation internal notice
}
unsetdev() {
  __devwho_transition --restore || return \$?
  $__devwho_invocation internal notice
}
INIT
 if [ -n "$__devwho_default" ]; then command -p cat <<INIT
if [ -z "\${DEVWHO_PROFILE-}" ]; then
  __devwho_bootstrap() {
    local __devwho_patch
    __devwho_patch=\$($__devwho_invocation internal bootstrap --shell $__devwho_shell) || return \$?
    eval "\$__devwho_patch"
  }
  __devwho_bootstrap
  unset -f __devwho_bootstrap
fi
INIT
 fi;;
 doctor) source "$__devwho_dir/doctor.bash"; __devwho_doctor "$@";;
 *) __devwho_usage_error 'unknown command';;
esac
