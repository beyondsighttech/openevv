#!/usr/bin/env python3
"""The thunks a Devanagari arm in generate_diaphones needs, per letter.

English's letter arms in `et_phone.obj' are handed nothing. They read the text
through the machine's two ends -- the globals at 844 and 852 -- rather than
through arguments, so both halves of an arm are wrappers over those: one asking
whether the character at the scan is a particular one, one putting a string of
phonemes between the ends. `lang/hien/rules/hien_lts.up' is Italian-shaped and
takes pointers, which is why none of it can be reached from that chain.

Two shapes, then, and one of each per letter:

    ZZtest_string_s_1_1_hi_<letter>_char
    ZZ_lprp_load_vvg_0106_0107__insert_2pt_s_2_<n>_<sound>

The character each one tests is a code of hien's own alphabet -- NOT the byte
the character arrives as. The engine turns an incoming byte into a code before
any rule sees it, and a record at the scan holds the code. Getting that wrong
is silent: every arm simply misses.

And one insert with no string at all, which is how a character that says
nothing -- the vowel-killer -- is taken out rather than spoken.

usage: hien-thunks.py [--dry-run]
"""

import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOB = os.path.join(ROOT, "lang", "hien", "rules", "glob.dr")
CONSTANTS = os.path.join(ROOT, "lang", "hien", "rules", "constants")
REPOINTED = os.path.join(ROOT, "lang", "hien", "hien.repointed")

#: Every consonant, with the two things it can say: the bare sound, which is
#: what a vowel-killer or a vowel sign or the end of a word leaves, and the
#: sound carrying the inherent a, which is the ordinary case. Devanagari is an
#: abugida and that is the whole of why there are two.
CONSONANTS = [
    ("dka", "hi_k", "hi_ka"), ("dkha", "hi_kh", "hi_kha"),
    ("dga", "hi_g", "hi_ga"), ("dgha", "hi_gh", "hi_gha"),
    ("dnga", "hi_ng", "hi_nga"), ("dca", "hi_c", "hi_ca"),
    ("dcha", "hi_ch", "hi_cha"), ("dja", "hi_j", "hi_ja"),
    ("djha", "hi_jh", "hi_jha"), ("dnya", "hi_ny", "hi_nya"),
    ("dTa", "hi_tt", "hi_tta"), ("dTha", "hi_tth", "hi_ttha"),
    ("dDa", "hi_dd", "hi_dda"), ("dDha", "hi_ddh", "hi_ddha"),
    ("dNa", "hi_nn", "hi_nna"), ("dta", "hi_t", "hi_ta"),
    ("dtha", "hi_th", "hi_tha"), ("dda", "hi_d", "hi_da"),
    ("ddha", "hi_dh", "hi_dha"), ("dna", "hi_n", "hi_na"),
    ("dpa", "hi_p", "hi_pa"), ("dpha", "hi_ph", "hi_pha"),
    ("dba", "hi_b", "hi_ba"), ("dbha", "hi_bh", "hi_bha"),
    ("dma", "hi_m", "hi_ma"), ("dya", "hi_y", "hi_ya"),
    ("dra", "hi_r", "hi_ra"), ("dla", "hi_l", "hi_la"),
    ("dva", "hi_v", "hi_va"), ("dsha", "hi_sh", "hi_sha"),
    ("dSha", "hi_ssh", "hi_ssha"), ("dsa", "hi_s", "hi_sa"),
    ("dha", "hi_h", "hi_ha"),
]

#: The vowels written in full, where no consonant opens the syllable. One
#: sound each and nothing after them changes it.
VOWELS = [
    ("da_", "hi_a"), ("daa", "hi_aa"), ("di", "hi_i"), ("dii", "hi_ii"),
    ("du", "hi_u"), ("duu", "hi_uu"), ("dri", "hi_ri"), ("de", "hi_e"),
    ("dai", "hi_ai"), ("do", "hi_o"), ("dau", "hi_au"),
]

#: The same vowels as signs, written after a consonant. A sign says exactly
#: what its full letter says -- का is k and then aa -- so the sound is shared
#: and only the character differs. Which is why a consonant does not need a
#: string per sign: it lays down its bare self and the sign speaks for itself
#: on the next pass of the loop.
MATRAS = [
    ("dmaa", "hi_aa"), ("dmi", "hi_i"), ("dmii", "hi_ii"),
    ("dmu", "hi_u"), ("dmuu", "hi_uu"), ("dmri", "hi_ri"),
    ("dme", "hi_e"), ("dmai", "hi_ai"), ("dmo", "hi_o"),
    ("dmau", "hi_au"),
]

#: The two marks that say something of their own.
SIGNS = [("danu", "hi_anu"), ("dvisarga", "hi_visg")]

#: The vowel-killer, which says nothing: it is why the consonant before it was
#: bare, and once that is done there is nothing left of it to speak.
SILENT = ["dvirama"]

#: Thunks the hand-written rules in `hien_lts.up' call by name and that nothing
#: else wants. Those rules are Italian-shaped and unreachable from the arm
#: chain, but they are in the tree and the link needs every name they use.
#: `hi_matra_chars' is asked as a one-character test against a ten-code
#: constant, so it really answers "is this the first vowel sign", which is why
#: the arms do not use it: they test each consonant-and-sign pair outright.
REFERENCED = [("hi_matra_chars", 1)]


def pairs():
    """Every two-character string an arm tests, and what the pair says.

    A consonant carries the vowel a unless something takes it away, and both
    things that take it away are the character after it. There is no primitive
    here for looking at the next character without consuming it, so the pair is
    tested as one string of two: test_string_s walks the scan one character per
    byte of what it is given, and the insert that follows covers the whole
    range. English's own `th' arm is the same shape.

    So: thirty-three consonants each with the vowel-killer, and each with each
    of the ten vowel signs. The sound of a pair is the consonant bare followed
    by whatever the second character says -- nothing, for the killer.
    """
    out = []
    for name, bare, _with_a in CONSONANTS:
        out.append(("%s_virama" % name, [name, "dvirama"], bare, None))
        for sign, vowel in MATRAS:
            out.append(("%s_%s" % (name, sign), [name, sign], bare, vowel))
    return out


TEST = """
rule ZZtest_string_s_1_%(chars)d_%(char)s from glob.obj
shape frame 0 argbase 8 params 1
label L0 was _ZZtest_string_s_1_%(chars)d_%(char)s
  push sym %(char)s
  push imm %(chars)d
  push imm 1
  push param 0
  call test_string_s arity 4 depth 4
  popn 4
  return reg r0
end
"""

SAY = """
rule ZZ_lprp_load_vvg_0106_0107__insert_2pt_s_2_%(n)d_%(sound)s from glob.obj
shape frame 0 argbase 8 params 1
label L0 was _ZZ_lprp_load_vvg_0106_0107__insert_2pt_s_2_%(n)d_%(sound)s
  load movl state 0 into r6
  load movl state 852 into r0
  push state 852
  load movl state 844 into r0
  push state 844
  push state 0
  call lpta_rpta_loadp arity 3 depth 3
  push imm 0
  push sym %(sound)s
  push imm %(n)d
  push imm 2
  push state 0
  call insert_2pt_s arity 5 depth 8
  popn 8
  return reg r0
end
"""

#: The same shape with nothing to put in. insert_2pt_s opens the range between
#: the two ends and then lays a string of n codes into it, so n of nought opens
#: the range and lays nothing -- which is a deletion written as an insert. The
#: string is still named because the shape wants a symbol; nothing reads it.
NOTHING = """
rule ZZ_lprp_load_vvg_0106_0107__insert_2pt_s_2_0_hi_nothing from glob.obj
shape frame 0 argbase 8 params 1
label L0 was _ZZ_lprp_load_vvg_0106_0107__insert_2pt_s_2_0_hi_nothing
  load movl state 0 into r6
  load movl state 852 into r0
  push state 852
  load movl state 844 into r0
  push state 844
  push state 0
  call lpta_rpta_loadp arity 3 depth 3
  push imm 0
  push sym hi_k
  push imm 0
  push imm 2
  push state 0
  call insert_2pt_s arity 5 depth 8
  popn 8
  return reg r0
end
"""

HEAD = """
# ---------------------------------------------------------------------------
# What a Devanagari character is, and what it says, in the shape English's own
# letter arms are in. Written by tools/hien-thunks.py.
#
# An arm in generate_diaphones is handed nothing: it reads the character
# through the machine's two ends, the globals at 844 and 852, so the test and
# the insert are thunks over those rather than rules taking pointers. That is
# the whole difference from lang/hien/rules/hien_lts.up, which is
# Italian-shaped and cannot be reached from that chain.
#
# The character each test names is a code of hien's own alphabet, and the sound
# each insert names is a string in rules/constants. Both are read out of the
# tree rather than typed here, so the three files cannot disagree.
"""


def alphabet():
    """hien's alphabet as its slot names, in code order."""
    spec = importlib.util.spec_from_file_location(
        "lang_alphabet", os.path.join(ROOT, "tools", "lang-alphabet.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.read("hien")[3]


def alphabet_codes():
    """Each Devanagari character's name and the alphabet code it is.

    Not the byte it arrives as. The engine turns an incoming byte into a code
    of the input statement's alphabet before any rule sees it, and what a
    record at the scan holds -- what test_string_s compares against -- is that
    code. English's own arms show it: the string `b' tests against is 0b, which
    is b's eleventh slot, not ASCII 0x62.

    Devanagari's slots are still named after the Latin-1 character each one
    took over, because a slot's name is what an arriving byte is matched
    against and a name like `dka' answers to no byte at all -- see
    tools/lang-repoint.py. So the code is found by going through
    `lang/hien/hien.repointed', which is the one file that says which byte, and
    therefore which slot, each letter took.
    """
    names = alphabet()

    slot = {}
    for i, name in enumerate(names):
        if len(name) == 1:
            b = name.encode("latin-1", errors="replace")
            if len(b) == 1:
                slot[b[0]] = i

    out = {}
    for raw in open(REPOINTED, encoding="utf-8"):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        w = line.split()
        byte = int(w[0], 16)
        if byte in slot:
            out[w[1]] = slot[byte]

    # And the ones that were always there, found by the character itself.
    if " " in names:
        out["space"] = names.index(" ")
    return out


def constant_names():
    """Which strings rules/constants already declares."""
    got = set()
    for raw in open(CONSTANTS, encoding="utf-8"):
        line = raw.split("#")[0].strip()
        w = line.split()
        if len(w) >= 2 and w[0] == "bytes":
            got.add(w[1])
    return got


def constant_length(name):
    """How many phoneme codes a sound is, which insert_2pt_s has to be told."""
    got = constant_bytes(name)
    return None if got is None else len(got.split())


def constant_bytes(name):
    """The codes a constant holds, as the text says them."""
    for raw in open(CONSTANTS, encoding="utf-8"):
        line = raw.split("#")[0].strip()
        w = line.split()
        if len(w) >= 3 and w[0] == "bytes" and w[1] == name:
            return " ".join(w[2:])
    return None


def main(argv):
    have = open(GLOB, encoding="utf-8").read()
    codes = alphabet_codes()
    sounds = constant_names()

    # ---- what has to exist -------------------------------------------------
    # Every single character an arm tests for.
    singles = [n for n, _b, _a in CONSONANTS]
    singles += [n for n, _s in VOWELS + MATRAS + SIGNS]
    singles += SILENT + ["space"]

    missing = [c for c in singles if c not in codes]
    if missing:
        print("hien-thunks: not a slot of hien's alphabet: %s"
              % ", ".join(missing), file=sys.stderr)
        return 1

    # Every string an arm says. The single sounds are in rules/constants
    # already; a pair's sound is the consonant bare followed by the sign's
    # vowel, and those are made here because there are three hundred of them
    # and no person should type that.
    made_sounds = {}
    for _name, members, bare, vowel in pairs():
        if vowel is None:
            continue
        sound = "%s_%s" % (bare, vowel[len("hi_"):])
        if sound not in sounds and sound not in made_sounds:
            a, b = constant_bytes(bare), constant_bytes(vowel)
            if a is None or b is None:
                print("hien-thunks: %s or %s is not in rules/constants"
                      % (bare, vowel), file=sys.stderr)
                return 1
            made_sounds[sound] = "%s %s" % (a, b)

    # And every character constant: one code for a single, two for a pair.
    want = {}
    for name in singles:
        want["hi_%s_char" % name] = "%02x" % codes[name]
    for _name, members, _bare, _vowel in pairs():
        want["hi_%s_char" % _name] = " ".join("%02x" % codes[m]
                                              for m in members)
    # The name the hand-written letter rules ask the vowel-killer by.
    want["hi_virama_char"] = "%02x" % codes["dvirama"]
    # And the one they ask the whole set of vowel signs by: ten codes, so a
    # consonant can ask whether what follows is any of them in one call. The
    # test is one character wide even so -- test_string_s walks a string of ten
    # against ten characters, which is not what this wants, so the rule that
    # names it is a set test rather than a string test and the length below is
    # deliberate.
    want["hi_matra_chars"] = " ".join("%02x" % codes[n] for n, _s in MATRAS)

    # ---- rules/constants ---------------------------------------------------
    text = open(CONSTANTS, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in text else "\n"
    added = []
    fixed = 0
    for char in sorted(want):
        pat = re.compile(r"^(bytes %s\s+)([0-9a-f][0-9a-f ]*?)(\s*(?:#.*)?)$"
                         % re.escape(char), re.MULTILINE)
        m = pat.search(text)
        if m is None:
            added.append((char, want[char]))
        elif m.group(2).strip() != want[char]:
            text = text[:m.start(2)] + want[char] + text[m.end(2):]
            fixed += 1

    if made_sounds:
        block = [
            "",
            "# ---- a consonant and the vowel sign after it, as one string"
            " ----------",
            "# A consonant loses its inherent a to a vowel sign and says the"
            " sign's vowel",
            "# instead, and the pair is matched as one string of two"
            " characters, so what",
            "# it says is one string too. Every consonant against every sign,"
            " which is",
            "# three hundred and thirty lines nobody should type: written by"
            " tools/hien-thunks.py",
            "# out of the single sounds above, so a change to one of those"
            " reaches these.",
        ]
        for name in sorted(made_sounds):
            block.append("bytes %-14s %s" % (name, made_sounds[name]))
        text = text.rstrip("\r\n") + nl + nl.join(block) + nl

    if added:
        block = [
            "",
            "# ---- the characters the arms in generate_diaphones test against"
            " ------",
            "# Codes of hien's own alphabet -- what a record at the scan holds"
            " -- rather",
            "# than the bytes the characters arrive as. Two codes where the arm"
            " matches a",
            "# pair. Written by tools/hien-thunks.py out of the alphabet"
            " itself, so these",
            "# and it cannot disagree.",
        ]
        for char, code in added:
            block.append("bytes %-22s %s" % (char, code))
        text = text.rstrip("\r\n") + nl + nl.join(block) + nl

    if "--dry-run" not in argv and (added or fixed or made_sounds):
        open(CONSTANTS, "w", encoding="utf-8", newline="").write(text)
        if made_sounds:
            print("hien-thunks: %d pair sounds added to %s"
                  % (len(made_sounds), os.path.relpath(CONSTANTS, ROOT)))
        if added:
            print("hien-thunks: %d character constants added to %s"
                  % (len(added), os.path.relpath(CONSTANTS, ROOT)))
        if fixed:
            print("hien-thunks: %d character constants corrected in %s"
                  % (fixed, os.path.relpath(CONSTANTS, ROOT)))
        sounds = constant_names()

    # ---- the thunks --------------------------------------------------------
    body = []
    for char in sorted(want):
        n = len(want[char].split())
        # The pair that hien_lts.up names is asked one character wide whatever
        # the constant holds, so its width is stated rather than counted.
        for name, width in REFERENCED:
            if char == name:
                n = width
        if ("ZZtest_string_s_1_%d_%s\n" % (n, char)) not in have:
            body.append(TEST % {"char": char, "chars": n})

    says = [b for _n, b, _a in CONSONANTS] + [a for _n, _b, a in CONSONANTS]
    says += [s for _n, s in VOWELS + SIGNS]
    says += sorted(made_sounds)
    seen = set()
    for sound in says:
        if sound in seen:
            continue
        seen.add(sound)
        if sound in made_sounds:
            n = len(made_sounds[sound].split())
        else:
            n = constant_length(sound)
        if n is None:
            print("hien-thunks: %s is not in rules/constants" % sound,
                  file=sys.stderr)
            return 1
        entry = ("ZZ_lprp_load_vvg_0106_0107__insert_2pt_s_2_%d_%s"
                 % (n, sound))
        if (entry + " ") not in have:
            body.append(SAY % {"sound": sound, "n": n})

    if "insert_2pt_s_2_0_hi_nothing " not in have:
        body.append(NOTHING)

    if not body:
        print("hien-thunks: glob.dr already has every thunk")
        return 0

    made = len(body)
    out = "".join(body)
    if HEAD.strip().splitlines()[1] not in have:
        out = HEAD + out
    if "--dry-run" in argv:
        print(out[:1500])
        print("... %d thunks, %d bytes" % (made, len(out)))
        return 0

    with open(GLOB, "a", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print("hien-thunks: %d thunks appended to %s"
          % (made, os.path.relpath(GLOB, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
