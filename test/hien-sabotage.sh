#!/usr/bin/env bash
#
# Break one Hindi rule on purpose and prove the tests notice.
#
# CLAUDE.md asks for this before any claim that a language is done: a test
# that passes proves nothing until it has been seen to fail. lang/hien has no
# oracle behind it, so hien-hash.sh is only as good as its willingness to
# fail, and this is what says it is willing.
#
# What it breaks: one of the duration numbers in lang/hien/rules/es_val.dr,
# the segment lengths Hindi sets differently from English. It is the smallest
# change with a reach anything can hear -- one immediate of one store -- so a
# harness that catches it catches anything coarser. Everything is put back
# whether the run succeeds or not.
#
# Not the intonation number in hien_lts.dr, which was the first choice and is
# the wrong one: offset 4134 is written by e_vars and read by nothing in the
# tree -- grep it -- so a run with a different value there is byte for byte
# the run before it, and a harness pointed at it reports a pass no matter how
# broken the language is. 4130 next door does have a reader
# (insert_dict_root, lang/*/rules/et_morph.dr). A sabotage target has to be
# a number something downstream reads.
#
# It also holds English still: the same binary carries enus, and a change to
# Hindi's rules that moved English would be the worst kind of bug this
# project can have. test/hash.sh is what says English has not moved.
#
# usage: hien-sabotage.sh

set -u
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=$(cd "$here/.." && pwd)
cd "$root" || exit 2

dr=lang/hien/rules/es_val.dr
py=./.venv/Scripts/python
[ -x "$py" ] || py=python3
cc=$root/.toolchain/mingw64/bin/gcc.exe

[ -f "$dr" ] || { echo "sabotage: no $dr" >&2; exit 2; }
[ -x "$cc" ] || { echo "sabotage: no compiler at $cc" >&2; exit 2; }

# Everything the regenerator writes, kept aside so the tree comes back
# exactly as it was -- the generated files are large and are not worth
# trusting a second regeneration to reproduce.
save=$(mktemp -d) || exit 1
keep="$dr lang/hien/delta_rules_hien.c lang/hien/delta_rules_hien.h \
lang/hien/delta_rules_shim_hien.c"
for f in $keep; do
    mkdir -p "$save/$(dirname "$f")"
    cp "$f" "$save/$f"
done

restore() {
    for f in $keep; do cp "$save/$f" "$f"; done
}

trap 'restore; rm -rf "$save"' EXIT

build() {
    # Both fronts: probe is what takes EVV_LANGUAGE and so is what can be
    # told to speak Hindi, and evv is what test/hash.sh's canonical English
    # hash belongs to. They are not interchangeable -- probe walks a few more
    # API entries before it speaks (et_insertIndex among them) and its
    # samples differ from evv's for that reason alone, on a tree with no
    # Hindi in it at all. Holding probe against test/samples.sha256 reports
    # English as broken every time.
    EVV_CC="$(cygpath -w "$root")/.toolchain/mingw64/bin/gcc.exe" \
        "$py" tools/build-zig.py --rules bytecode --langs enus,hien probe \
        > "$save/build.log" 2>&1 || return 1
    EVV_CC="$(cygpath -w "$root")/.toolchain/mingw64/bin/gcc.exe" \
        "$py" tools/build-zig.py --rules bytecode --langs enus,hien evv \
        >> "$save/build.log" 2>&1
}

regen() {
    "$py" tools/hien-regen.py --write hien > "$save/regen.log" 2>&1
}

echo "sabotage: turning a duration in $dr from 1800 into 1200"
if ! grep -q 'store movw imm 1800 statefld 3086' "$dr"; then
    echo "sabotage: that line is not in $dr any more -- this script names one" >&2
    echo "  operation by its text, so a rewritten rule wants it renamed too." >&2
    exit 2
fi
sed -i 's/store movw imm 1800 statefld 3086/store movw imm 1200 statefld 3086/' \
    "$dr"

regen || { echo "sabotage: the regenerator refused the broken rule" >&2
           echo "  which is itself a kind of pass, but not the one asked for;" >&2
           echo "  see $save/regen.log" >&2; exit 1; }
build || { echo "sabotage: the broken tree would not build, see build.log" >&2
           exit 1; }

echo "sabotage: with Hindi broken --"
if bash test/hien-hash.sh > "$save/broken.log" 2>&1; then
    echo "sabotage: hien-hash.sh PASSED a deliberately broken rule" >&2
    sed 's/^/  /' "$save/broken.log" >&2
    echo "  The check is not reaching the rules. Until that is understood," >&2
    echo "  a passing hien-hash.sh says nothing about lang/hien." >&2
    exit 1
fi
sed 's/^/  /' "$save/broken.log"
echo "sabotage: hien-hash.sh failed, as it must"

if ! bash test/hash.sh build/evv-enus-hien.exe > "$save/en.log" 2>&1; then
    echo "sabotage: English moved when Hindi was broken" >&2
    sed 's/^/  /' "$save/en.log" >&2
    echo "  Hindi's rules are reaching English's, which is a fault in the" >&2
    echo "  module boundary and not in the rule this script edited." >&2
    exit 1
fi
echo "sabotage: English did not move"

restore
echo "sabotage: putting the rule back and building again"
regen || { echo "sabotage: the restored tree would not regenerate" >&2; exit 1; }
build || { echo "sabotage: the restored tree would not build" >&2; exit 1; }

if ! bash test/hien-hash.sh; then
    echo "sabotage: hien-hash.sh still fails with the rule restored" >&2
    echo "  The tree is back but the hashes are not, so something outside" >&2
    echo "  $dr moved too." >&2
    exit 1
fi
echo "sabotage: restored, and the hashes are what they were"
exit 0
