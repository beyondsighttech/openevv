#!/usr/bin/env bash
#
# Write test/hien.sha256 from what the binary says today.
#
# Deliberately separate from hien-hash.sh: recording is not checking, and a
# check that quietly re-records what it found would never fail. Run this only
# when a change to lang/hien is intended and the audio has been listened to.
#
# Each case is spoken twice and the two runs must agree before its hash is
# kept -- a case that does not reproduce is either outrunning probe.c's
# 3000-nap cap (see hien-timing.sh) or genuinely nondeterministic, and either
# way its hash is worth nothing.
#
# usage: hien-bless.sh [binary]     default build/probe-enus-hien.exe

set -u
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
bin=${1:-$here/../build/probe-enus-hien.exe}
want=$here/hien.sha256

[ -x "$bin" ] || { echo "bless: no binary at $bin" >&2; exit 2; }

tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT
case $(uname -s 2>/dev/null) in
MINGW*|MSYS*|CYGWIN*) out=$(cygpath -m "$tmp") ; PE= ;;
*)                    out=$tmp ; PE=wine ;;
esac

say() {
    local case=$1 nth=$2 file=$here/cases/$1-hien.txt read_from
    case $(uname -s 2>/dev/null) in
    MINGW*|MSYS*|CYGWIN*) read_from=$(cygpath -m "$file") ;;
    *)                    read_from=$file ;;
    esac
    EVV_LANGUAGE=0x90000 $PE "$bin" "@$read_from" "$out/$case$nth.wav" \
        >/dev/null 2>&1
    [ -s "$tmp/$case$nth.wav" ] || return 1
    sha256sum < "$tmp/$case$nth.wav" | cut -d' ' -f1
}

bad=0
new=$tmp/hien.sha256
: > "$new"

for case in plain matra utf8; do
    [ -f "$here/cases/$case-hien.txt" ] || {
        echo "bless: no cases/$case-hien.txt" >&2; bad=1; continue; }

    one=$(say "$case" 1) || { echo "bless: $case produced nothing" >&2
                              bad=1; continue; }
    two=$(say "$case" 2) || { echo "bless: $case produced nothing" >&2
                              bad=1; continue; }

    if [ "$one" != "$two" ]; then
        echo "bless: $case does not reproduce, not recording it" >&2
        echo "  $one" >&2
        echo "  $two" >&2
        echo "  run test/hien-timing.sh: a case past probe.c's cap comes out" >&2
        echo "  a different length every time." >&2
        bad=1
        continue
    fi

    printf '%s  %s\n' "$one" "$case" >> "$new"
    echo "bless: $case $one ($(stat -c%s "$tmp/${case}1.wav") bytes)"
done

[ "$bad" = 0 ] || { echo "bless: nothing written" >&2; exit 1; }

cp "$new" "$want"
echo "bless: written to test/hien.sha256"
exit 0
