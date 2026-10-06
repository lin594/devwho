#!/bin/bash
# Install this complete source tree; jq and Perl remain explicit prerequisites.
set -eu
prefix=${1:-"${HOME}/.local"}
command -v jq >/dev/null || { printf '%s\n' 'jq 1.6+ required' >&2; exit 1; }
command -v perl >/dev/null || { printf '%s\n' 'Perl 5.18+ required' >&2; exit 1; }
source_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
mkdir -p "$prefix"
prefix=$(CDPATH= cd -- "$prefix" && pwd -P)
if [ -e "$prefix/bin/devwho" ] || [ -L "$prefix/bin/devwho" ]; then
 printf '%s\n' 'devwho already exists in the selected prefix' >&2; exit 1
fi
mkdir -p "$prefix/lib/devwho-bash" "$prefix/bin"
cp "$source_dir"/{devwho,devwho.bash,child-exec.pl,core.jq,doctor.bash,toml-json.pl,state-json.pl,dotenv-json.pl,writable.bash,writable.zsh,THIRD_PARTY.md} "$prefix/lib/devwho-bash/"
cp -R "$source_dir/vendor" "$prefix/lib/devwho-bash/"
chmod +x "$prefix/lib/devwho-bash/devwho"
# ln without -f refuses to overwrite another selected implementation.
ln -s "$prefix/lib/devwho-bash/devwho" "$prefix/bin/devwho"
printf 'Installed %s\n' "$prefix/bin/devwho"
