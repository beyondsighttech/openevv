#!/usr/bin/env bash
#
# Hindi's own fixed-utterance check: speak each case through the Hindi module
# and hold the samples against what they were.
#
# This is test/hash.sh's job for a language whose oracle does not exist. IBM
# never shipped an Indic module, so there is nothing to compare against and
# test/suite.sh cannot say whether lang/hien is *right*; what this says is
# that it is unchanged, which is what catches a careless edit to the rules.
# When a change to lang/hien is deliberate, listen to the result, then put
# the new hashes in test/hien.sha256.
#
# It goes through build/probe-<tags>.exe rather than evv, because probe is
# what takes EVV_LANGUAGE and so is what can be told to speak Hindi out of a
# binary that also has English in it. A build with both is the point: it is
# what says nothing has quietly stayed global.
#
# usage: hien-hash.sh [binary]     default build/probe-enus-hien.exe
#
# Hindi alone in a binary gives the same samples: build/probe-hien.exe and
# build/probe-enus-hien.exe both hash to what hien.sha256 records, which is
# the same thing test/langs.py says through the library and is worth knowing
# before reading a difference as Hindi's own.

set -u
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
bin=${1:-$here/../build/probe-enus-hien.exe}
want=$here/hien.sha256

[ -x "$bin" ] || { echo "hien-hash: no binary at $bin" >&2; exit 2; }
[ -f "$want" ] || { echo "hien-hash: no $want" >&2; exit 2; }

tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT

# A native Windows exe cannot open an MSYS /tmp path; the same translation
# test/hash.sh makes.
case $(uname -s 2>/dev/null) in
MINGW*|MSYS*|CYGWIN*) out=$(cygpath -m "$tmp") ; PE= ;;
*)                    out=$tmp ; PE=wine ;;
esac

bad=0
# The cases are deliberately short. cli/probe.c pumps the engine's queue for
# at most 3000 naps of 10 ms and then writes whatever it has, so a sentence
# long enough to outrun that cap comes out truncated at a length that follows
# the machine's mood -- which reads as a bug in the rules when it is really a
# timeout. test/hien-timing.sh is what proves a case is inside the cap.
for case in plain matra utf8; do
    file=$here/cases/$case-hien.txt
    [ -f "$file" ] || { echo "hien-hash: no $file" >&2; bad=1; continue; }

    # The text file is read by the binary, not by the shell, so its name
    # wants the same translation the output does.
    case $(uname -s 2>/dev/null) in
    MINGW*|MSYS*|CYGWIN*) read_from=$(cygpath -m "$file") ;;
    *)                    read_from=$file ;;
    esac

    EVV_LANGUAGE=0x90000 $PE "$bin" "@$read_from" "$out/$case.wav" \
        >/dev/null 2>&1
    if [ ! -s "$tmp/$case.wav" ]; then
        echo "hien-hash: $case produced nothing" >&2
        bad=1
        continue
    fi

    have=$(sha256sum < "$tmp/$case.wav" | cut -d' ' -f1)
    expect=$(awk -v c="$case" '$2 == c { print $1 }' "$want")

    if [ -z "$expect" ]; then
        echo "hien-hash: $case has no hash in hien.sha256" >&2
        echo "  it is now $have" >&2
        bad=1
    elif [ "$have" = "$expect" ]; then
        echo "hien-hash: $case is what it has always been"
    else
        echo "hien-hash: $case has moved" >&2
        echo "  wanted $expect" >&2
        echo "  got    $have" >&2
        bad=1
    fi
done

[ "$bad" = 0 ] || exit 1
exit 0
