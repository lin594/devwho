#!/bin/bash
# Runtime acceptance in a filesystem with no Python, compilers or source cores.
set -euo pipefail
core=$1
fixtures=${2:-/checks/fixtures}
for program in python python3 go rustc cargo; do
    if command -v "$program" >/dev/null; then
        printf 'Unexpected runtime dependency present: %s\n' "$program" >&2
        exit 1
    fi
done
if find /usr /opt /artifacts -type f \( -name 'python[0-9]*' -o -name libpython\* \) -print -quit | /bin/grep -q .; then
    printf 'Python files present in runtime filesystem\n' >&2
    exit 1
fi
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
export HOME="$work/home" XDG_CONFIG_HOME="$work/home/.config"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 LC_ALL=C.UTF-8
mkdir -p "$HOME"
cd "$work"
"$core" --version
"$core" --config "$work/init.toml" config init
test "$(stat -c %a "$work/init.toml")" = 600
if "$core" --config "$work/init.toml" config init >/dev/null 2>&1; then exit 1; fi

# Consume the same language-neutral TOML vectors without a Python test driver.
count=$(jq length "$fixtures/configurations.json")
for ((i=0; i<count; i++)); do
    jq -j --argjson i "$i" '.[$i].toml' "$fixtures/configurations.json" > config.toml
    name=$(jq -r --argjson i "$i" '.[$i].name' "$fixtures/configurations.json")
    if jq -e --argjson i "$i" '.[$i].valid' "$fixtures/configurations.json" >/dev/null; then
        "$core" --config "$work/config.toml" exec a -- /usr/bin/env -0 > actual.nul
        jq -Rs 'split("\u0000")|map(select(length>0)|capture("^(?<key>[^=]+)=(?<value>[\\s\\S]*)$"))|from_entries' < actual.nul > actual.json
        jq -e --argjson i "$i" --slurpfile actual actual.json '
          .[$i] | (.env // {} | to_entries | all(. as $p | $actual[0][$p.key] == $p.value))
          and ((.runtime // []) | to_entries | all(. as $p |
            $actual[0]["GIT_CONFIG_KEY_"+($p.key|tostring)] == $p.value[0]
            and $actual[0]["GIT_CONFIG_VALUE_"+($p.key|tostring)] == $p.value[1]))
        ' "$fixtures/configurations.json" >/dev/null
    else
        if "$core" --config "$work/config.toml" list > out 2> err; then
            printf 'Accepted invalid vector: %s\n' "$name" >&2; exit 1
        fi
        test ! -s out
    fi
done
test ! -e marker && test ! -e other

for kind in valid invalid; do
    count=$(jq --arg kind "$kind" '.[$kind]|length' "$fixtures/dotenv.json")
    for ((i=0; i<count; i++)); do
        jq -j --arg kind "$kind" --argjson i "$i" '.[$kind][$i].text' "$fixtures/dotenv.json" > profile.env
        if [ "$kind" = valid ]; then
            "$core" --env-file "$work/profile.env" exec demo -- /usr/bin/env -0 > actual.nul
            jq -Rs 'split("\u0000")|map(select(length>0)|capture("^(?<key>[^=]+)=(?<value>[\\s\\S]*)$"))|from_entries' < actual.nul > actual.json
            jq -e --argjson i "$i" --slurpfile actual actual.json '.valid[$i].env|to_entries|all(. as $p|$actual[0][$p.key]==$p.value)' "$fixtures/dotenv.json" >/dev/null
        elif "$core" --env-file "$work/profile.env" list >/dev/null 2>&1; then
            printf 'Accepted invalid dotenv vector %s\n' "$i" >&2; exit 1
        fi
    done
done
test ! -e sentinel

cat > session.toml <<'EOF'
version=1
[settings]
shortcut_profile="work"
[profiles.work.git]
name="Work User"
email="work@example.test"
[profiles.work.env]
APP_ACCOUNT="work"
[profiles.personal.git]
name="Personal User"
email="personal@example.test"
[profiles.personal.env]
APP_ACCOUNT="personal"
EOF
for shell in /bin/bash /bin/zsh; do
    "$core" --config "$work/session.toml" init "${shell##*/}" > init.sh
    CORE="$core" "$shell" -c '
      set -e
      export APP_ACCOUNT=before HTTPS_PROXY=http://proxy.example:8080
      . ./init.sh
      setdev
      test "$DEVWHO_PROFILE:$APP_ACCOUNT" = work:work
      test "$(git config user.email)" = work@example.test
      "$CORE" --config "$PWD/session.toml" doctor --offline >/dev/null
      setdev personal
      test "$(git config user.email)" = personal@example.test
      unsetdev
      test "$APP_ACCOUNT" = before
      test -z "${DEVWHO_PROFILE+x}"
      test "$HTTPS_PROXY" = http://proxy.example:8080
    '
done

# Real Git replay: the original author survives while the selected committer changes.
git init -q -b main replay
cd replay
git -c user.name=Base -c user.email=base@example.test commit -q --allow-empty -m base
git branch topic
printf main > main.txt
git add main.txt
git -c user.name=Main -c user.email=main@example.test commit -q -m main
git checkout -q topic
printf original > topic.txt
git add topic.txt
git -c user.name=Original -c user.email=original@example.test commit -q -m topic
"$core" --config "$work/session.toml" exec work -- git rebase main
test "$(git log -1 --format=%ae)" = original@example.test
test "$(git log -1 --format=%ce)" = work@example.test
git checkout -q main
"$core" --config "$work/session.toml" exec personal -- git cherry-pick topic
test "$(git log -1 --format=%ae)" = original@example.test
test "$(git log -1 --format=%ce)" = personal@example.test
cd "$work"
if "$core" --config session.toml exec work -- /bin/sh -c 'exit 17'; then exit 1; else test "$?" = 17; fi
if [ -x /artifacts/devwho-setup ]; then
    setup=/artifacts/devwho-setup
    printf '%s\n' '{"version":1,"profiles":{"work":{"env":{"APP_ACCOUNT":"private-value"}}}}' |
        "$setup" --config "$work/edited.toml" replace --if-revision missing > saved.json
    "$setup" --config "$work/edited.toml" read > redacted.json
    if /bin/grep -q private-value redacted.json; then exit 1; fi
    "$setup" --config "$work/edited.toml" read --show-values > full.json
    jq -e '.configuration.profiles.work.env.APP_ACCOUNT == "private-value"' full.json >/dev/null
    rev=$(jq -r .revision full.json)
    jq '.configuration.profiles.work.env.APP_ACCOUNT="revised" | .configuration' full.json |
        "$setup" --config "$work/edited.toml" replace --if-revision "$rev" > saved.json
    test "$(stat -c %a "$work/edited.toml")" = 600
    test "$(find "$work/.devwho-backups" -type f | wc -l)" = 1
    "$core" --config "$work/edited.toml" exec work -- /bin/sh -c 'test "$APP_ACCOUNT" = revised'
    printf 'Python-free configuration frontend passed\n'
fi
printf 'Python-free runtime acceptance passed: %s\n' "$core"
