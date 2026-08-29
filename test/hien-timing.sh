#!/usr/bin/env bash
#
# How long one Hindi utterance takes, and whether its length is stable.
#
# cli/probe.c pumps the engine's queue for at most 3000 naps of 10 ms and
# then writes whatever it has, so a sentence that outruns that cap comes out
# short -- and comes out a *different* length on a slower run, which reads
# as nondeterminism when it is really a timeout. This says which it is: the
# samples of a short utterance must not move between runs.
#
# usage: hien-timing.sh [binary]     default build/probe-enus-hien.exe

set -u
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
bin=${1:-$here/../build/probe-enus-hien.exe}

[ -x "$bin" ] || { echo "timing: no binary at $bin" >&2; exit 2; }

tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT
case $(uname -s 2>/dev/null) in
MINGW*|MSYS*|CYGWIN*) out=$(cygpath -m "$tmp") ; PE= ;;
*)                    out=$tmp ; PE=wine ;;
esac

printf 'नमस्ते।\n'            > "$tmp/one.txt"
printf 'नमस्ते। कमल, नगर।\n'  > "$tmp/two.txt"

for n in one two; do
    case $(uname -s 2>/dev/null) in
    MINGW*|MSYS*|CYGWIN*) f=$(cygpath -m "$tmp/$n.txt") ;;
    *)                    f=$tmp/$n.txt ;;
    esac
    for i in 1 2; do
        s=$(date +%s)
        EVV_LANGUAGE=0x90000 $PE "$bin" "@$f" "$out/$n$i.wav" \
            > "$tmp/$n$i.log" 2>&1
        e=$(date +%s)
        printf '%-4s run%d  %8s bytes  %3ss  %s\n' \
            "$n" "$i" \
            "$(stat -c%s "$tmp/$n$i.wav" 2>/dev/null)" \
            "$((e - s))" \
            "$(sha256sum < "$tmp/$n$i.wav" 2>/dev/null | cut -c1-16)"
    done
done
