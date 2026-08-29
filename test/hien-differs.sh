#!/usr/bin/env bash
#
# One language of a two-language build against the other, on the same text.
#
# The point is not that the two agree -- they must not, once Hindi has rules
# of its own -- but that the language asked for is the language that ran.
# test/langs.py says the same thing through the library; this says it through
# the console driver, which is the one that needs no Wine and no ctypes.
#
# usage: hien-differs.sh [binary]      default build/probe-enus-hien.exe

set -u
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
bin=${1:-$here/../build/probe-enus-hien.exe}
text=${EVV_TEXT:-"नमस्ते दुनिया"}

[ -x "$bin" ] || { echo "differs: no binary at $bin" >&2; exit 2; }

# A native Windows exe cannot open an MSYS /tmp path, so the names it is
# given are translated the way test/hash.sh translates its own.
tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT
case $(uname -s 2>/dev/null) in
MINGW*|MSYS*|CYGWIN*) out=$(cygpath -m "$tmp") ; PE= ;;
*)                    out=$tmp ; PE=wine ;;
esac

say() {
    EVV_LANGUAGE=$1 $PE "$bin" "$text" "$out/$2" >/dev/null 2>&1
    if [ ! -s "$tmp/$2" ]; then
        echo "differs: language $1 produced nothing" >&2
        exit 1
    fi
    sha256sum < "$tmp/$2" | cut -d' ' -f1
}

en=$(say 0x10000 en.wav)
hi=$(say 0x90000 hi.wav)

echo "  0x10000 (US English) $en"
echo "  0x90000 (Hindi)      $hi"

if [ "$en" = "$hi" ]; then
    echo "differs: both languages spoke the same samples" >&2
    echo "Either lang/hien still holds English's rules unchanged, or the" >&2
    echo "language asked for is not the one in force -- which is the fault" >&2
    echo "worth finding, and the one test/langs.py looks for too." >&2
    exit 1
fi

echo "differs: the two languages speak differently, as they must"
exit 0
