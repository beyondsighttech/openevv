#!/usr/bin/env python3
"""Hindi's letters, spliced into the chain generate_diaphones actually walks.

The chain is the run of arms inside L15 in `et_phone.dr': each one sets the scan
from the left-hand end, asks whether what is there is a particular character,
and either lays phonemes down or falls into the next arm. It is the only path by
which a letter is ever spoken, and this writes Devanagari's arms into it.

They go at the HEAD OF L15's BODY, not in front of the label. The letter loop is
re-entered through `backtrack_function', which dispatches on a tag with a
switch, and entry nine of that switch is L15 -- so anything spliced above the
label runs once and is stepped over on every pass after the first. That was the
first version of this tool, and it reached one letter of six.

An arm needs no backtrack tag, which matters because the rule's 76 tags are all
taken and the dispatch is bounded at 75. A tag is what lets a matched arm be
undone and the next tried, and these have nothing to undo: the tests are
mutually exclusive, so the first match is the only match.

WHAT DEVANAGARI NEEDS THAT LATIN DOES NOT

A consonant carries the vowel a with no sign saying so -- क is `ka', not `k'.
Three things take that vowel away, and the arms are ordered so that the longer
test is asked first:

  क् a virama, the vowel-killer: the consonant is bare, and the virama itself
     says nothing. Tested as two characters, and the pair says one sound.
  का a vowel sign: the consonant is bare and the sign's own vowel follows.
     Also two characters, and the pair says the consonant then that vowel.
  क  neither: the inherent a is said.

Which is why a consonant has two strings in rules/constants -- `hi_k' and
`hi_ka' -- and why the two-character arms come first. test_string_s walks the
scan one character per byte of the string it is given, so a two-byte string is
`this character then that one', and the insert that follows covers both. That
is not a trick of ours: English's own `th' arm is the same shape, two
characters tested and one phoneme laid down.

WHAT IS STILL MISSING

Word-final schwa deletion: राम is `raam', not `raama'. Hindi drops the inherent
a at the end of a word, and testing for the end of a word without consuming it
needs a lookahead this has no primitive for yet. Every arm here consumes what it
matches.

DO NOT EDIT et_phone.dr's chain by hand. Run this; it splices, and it refuses to
splice twice.

usage: hien-arms.py [--dry-run]
"""

import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHONE = os.path.join(ROOT, "lang", "hien", "rules", "et_phone.dr")
CONSTANTS = os.path.join(ROOT, "lang", "hien", "rules", "constants")

# The same lists tools/hien-thunks.py works from, imported rather than copied so
# that a letter cannot be in one and not the other.
THUNKS = os.path.join(ROOT, "tools", "hien-thunks.py")

# Where the chain begins, and where a matched arm goes. Both are read out of the
# file rather than assumed, so a change to either is a loud failure.
CHAIN_HEAD = "label L15 was $X10$99757"
MATCHED = "L56"

HEAD = """\
# ---------------------------------------------------------------------------
# Devanagari's arms in the chain, written by tools/hien-arms.py. Everything
# from here to %(english)s is Hindi's; do not edit it by hand.
#
# These sit at the head of L15's body rather than in front of the label,
# because the letter loop is re-entered through the backtrack switch and that
# switch names L15: anything above the label runs once and is stepped over on
# every pass after the first.
#
# Each arm is the shape of an English arm with the backtrack tag left out: set
# the scan from the left-hand end, ask whether what is there is this character
# or this pair of them, and if it is, put the phonemes between the two ends and
# go to the matched join. An arm that does not match falls into the next, and
# the last falls into %(english)s, which is English's own body -- so English is
# untouched either way.
#
# The order is the whole of the Devanagari in here. A consonant carries the
# vowel a unless something takes it away, so the pairs that take it away are
# asked first: consonant-then-virama says the bare consonant, consonant-then-
# vowel-sign says the bare consonant and that sign's vowel, and a consonant
# that matched neither says its inherent a. test_string_s walks one character
# per byte of the string, which is what makes a two-character test possible;
# English's own `th' arm is the same shape.
"""

ARM = """\
label %(label)s was hi_arm_%(name)s
  push reg r6
  call ZZlpta_load_vvg__setscan_0106r__1 arity 1 depth 1
  cmp testl reg r0 reg r0
  popreg r1
  branch jne to %(fall)s
  push reg r6
  call ZZtest_string_s_1_%(chars)d_%(char)s arity 1 depth 1
  cmp testl reg r0 reg r0
  popreg r1
  branch jne to %(next)s
  push reg r6
  call ZZ_lprp_load_vvg_0106_0107__insert_2pt_s_2_%(n)d_%(sound)s arity 1 depth 1
  cmp testl reg r0 reg r0
  popreg r1
  branch je to %(matched)s
"""


def lists():
    """The letters, as tools/hien-thunks.py has them."""
    spec = importlib.util.spec_from_file_location("hien_thunks", THUNKS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def constant_length(name, text):
    for raw in text.splitlines():
        line = raw.split("#")[0].strip()
        w = line.split()
        if len(w) >= 3 and w[0] == "bytes" and w[1] == name:
            return len(w) - 2
    return None


def highest_label(text, start, end):
    body = text[start:end]
    got = [int(n) for n in re.findall(r"^label L(\d+) ", body, re.MULTILINE)]
    if not got:
        raise ValueError("no labels between %d and %d" % (start, end))
    return max(got)


def plan(mod, consts):
    """Every arm, in the order they are tried.

    Each is (name, how many characters it tests, the character constant, the
    sound it says). A pair is named for both of its characters, which is also
    the name of the constant holding the two codes.
    """
    out = []

    # A consonant whose vowel is killed outright. Two characters in, one sound
    # out, and the virama is consumed with it.
    for name, bare, _with_a in mod.CONSONANTS:
        out.append(("%s_virama" % name, 2,
                    "hi_%s_virama_char" % name, bare))

    # A consonant carrying a vowel sign: the consonant bare, then the sign's
    # own vowel, as one string over two characters.
    for name, bare, _with_a in mod.CONSONANTS:
        for sign, vowel in mod.MATRAS:
            out.append(("%s_%s" % (name, sign), 2,
                        "hi_%s_%s_char" % (name, sign),
                        "%s_%s" % (bare, vowel[len("hi_"):])))

    # A consonant with neither: the inherent a is said.
    for name, _bare, with_a in mod.CONSONANTS:
        out.append((name, 1, "hi_%s_char" % name, with_a))

    # A vowel written in full.
    for name, sound in mod.VOWELS:
        out.append((name, 1, "hi_%s_char" % name, sound))

    # A vowel sign that followed something other than a consonant. Rare in
    # well-formed text, and it says its vowel rather than nothing.
    for name, sound in mod.MATRAS:
        out.append((name, 1, "hi_%s_char" % name, sound))

    # The marks that say something of their own.
    for name, sound in mod.SIGNS:
        out.append((name, 1, "hi_%s_char" % name, sound))

    # And a virama that reached here on its own, which says nothing: whatever
    # it was killing the vowel of has already been dealt with.
    out.append(("dvirama", 1, "hi_dvirama_char", "hi_nothing"))

    return out


def main(argv):
    text = open(PHONE, encoding="utf-8", newline="").read()
    consts = open(CONSTANTS, encoding="utf-8").read()
    mod = lists()

    if "hi_arm_" in text:
        print("hien-arms: et_phone.dr already has the Devanagari arms")
        return 0

    at = text.find(CHAIN_HEAD)
    if at < 0:
        print("hien-arms: %s is not in et_phone.dr; the chain has moved and"
              " this tool has to be looked at before it is trusted"
              % CHAIN_HEAD, file=sys.stderr)
        return 1

    begin = text.rfind("\nrule ", 0, at) + 1
    stop = re.search(r"\r?\nend\r?\n", text[at:])
    if not stop:
        print("hien-arms: no end to the rule after the chain head",
              file=sys.stderr)
        return 1
    top = highest_label(text, begin, at + stop.start())

    arms = plan(mod, consts)
    labels = ["L%d" % (top + 1 + i) for i in range(len(arms))]
    english = "L%d" % (top + 1 + len(arms))

    out = [HEAD % {"english": english}]
    for i, (name, chars, char, sound) in enumerate(arms):
        # hi_nothing is the empty string: the insert that takes a character out
        # rather than speaking it, so there is nothing in rules/constants to
        # count. Everything else is a real string and has to be there.
        if sound == "hi_nothing":
            n = 0
        else:
            n = constant_length(sound, consts)
            if n is None:
                print("hien-arms: %s is not in rules/constants" % sound,
                      file=sys.stderr)
                return 1
        if constant_length(char, consts) is None:
            print("hien-arms: %s is not in rules/constants" % char,
                  file=sys.stderr)
            return 1
        after = labels[i + 1] if i + 1 < len(labels) else english
        out.append(ARM % {"label": labels[i], "name": name, "chars": chars,
                          "char": char, "sound": sound, "n": n,
                          "next": after, "fall": english,
                          "matched": MATCHED})
    out.append("label %s was hi_arms_done\n" % english)

    block = "".join(out)
    if "\r\n" in text:
        block = block.replace("\n", "\r\n")

    if "--dry-run" in argv:
        print(block[:2000])
        print("... %d arms, %d bytes, labels %s..%s, English's body %s"
              % (len(arms), len(block), labels[0], labels[-1], english))
        return 0

    # After the label rather than before it: the label is what the backtrack
    # switch names, so Hindi's arms have to be the first thing inside it.
    cut = text.index("\n", at) + 1
    open(PHONE, "w", encoding="utf-8", newline="").write(
        text[:cut] + block + text[cut:])
    print("hien-arms: %d arms spliced into et_phone.dr at the head of %s"
          " (labels %s..%s); English's body is %s"
          % (len(arms), CHAIN_HEAD.split()[1], labels[0], labels[-1],
             english))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
