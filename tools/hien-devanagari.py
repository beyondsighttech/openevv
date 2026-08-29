#!/usr/bin/env python3
"""Point hien's alphabet at Devanagari, and write the code point table to match.

Two files have to agree exactly or nothing works: `lang/hien/hien.codepoints`
says which byte a caller's U+0928 arrives as, and hien's alphabet says what the
character at that byte is and what it sounds like. Maintaining them by hand is
maintaining the same fifty-nine facts twice, so this holds the facts once and
writes both.

The bytes are not chosen: they are taken in order from the slots
`tools/lang-repoint.py show hien` says are takeable, which are the accented
Latin-1 letters the module inherited from English and Hindi will never use. So
which byte a letter gets is an implementation detail and is written down rather
than decided -- what matters is that the two files say the same one.

The phoneme each letter is given is the nearest sound hien already has. For
most of Hindi that is exact: k g t d p b m n s h r l y w and the five vowels
are sounds English has too. Where Hindi has a sound English has not, the letter
is pointed at the nearest one and the table below says what it really wants.
Fourteen of the fifty-nine are in that state -- the aspirates and the
retroflex series -- and they are the next piece of work, through
tools/lang-phonemes.py. A letter pointed at an approximate sound is a letter
that speaks, which is worth having before it is a letter that speaks correctly.

usage: hien-devanagari.py [--dry-run]
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
if not os.path.exists(PY):
    PY = sys.executable

#: Every character, in Unicode order, as
#: (code point, name for the rules, kind, letter type, phoneme, what it wants).
#: The name is a transliteration rather than the character itself so that a
#: rules file stays readable where there is no Devanagari font, and each is
#: prefixed `d' -- `dka', `dmaa' -- because the alphabet already has names of
#: its own and `a' is one of them. A rule naming `dka' can only mean the
#: Devanagari letter, which is the point of a prefix rather than a bare
#: transliteration.
DEVANAGARI = [
    # the independent vowels, written where no consonant opens the syllable
    (0x0905, "da_",     "letter", "vow", "a",  None),
    (0x0906, "daa",     "letter", "vow", "Aa", None),
    (0x0907, "di",      "letter", "vow", "i",  None),
    (0x0908, "dii",     "letter", "vow", "I",  None),
    (0x0909, "du",      "letter", "vow", "u",  None),
    (0x090a, "duu",     "letter", "vow", "U",  None),
    (0x090b, "dri",     "letter", "vow", "r",  "a vocalic r"),
    (0x090f, "de",      "letter", "vow", "e",  None),
    (0x0910, "dai",     "letter", "vow", "E",  None),
    (0x0913, "do",      "letter", "vow", "o",  None),
    (0x0914, "dau",     "letter", "vow", "O",  None),

    # the velars
    (0x0915, "dka",     "letter", "con", "k",  None),
    (0x0916, "dkha",    "letter", "con", "k",  "an aspirated k"),
    (0x0917, "dga",     "letter", "con", "g",  None),
    (0x0918, "dgha",    "letter", "con", "g",  "a breathy g"),
    (0x0919, "dnga",    "letter", "con", "G",  None),

    # the palatals
    (0x091a, "dca",     "letter", "con", "C",  None),
    (0x091b, "dcha",    "letter", "con", "C",  "an aspirated ch"),
    (0x091c, "dja",     "letter", "con", "J",  None),
    (0x091d, "djha",    "letter", "con", "J",  "a breathy j"),
    (0x091e, "dnya",    "letter", "con", "n",  "a palatal n"),

    # the retroflex, articulated with the tongue curled back: the series
    # English has nothing of at all
    (0x091f, "dTa",     "letter", "con", "t",  "a retroflex t"),
    (0x0920, "dTha",    "letter", "con", "t",  "an aspirated retroflex t"),
    (0x0921, "dDa",     "letter", "con", "d",  "a retroflex d"),
    (0x0922, "dDha",    "letter", "con", "d",  "a breathy retroflex d"),
    (0x0923, "dNa",     "letter", "con", "n",  "a retroflex n"),

    # the dentals, which are further forward than English's t and d
    (0x0924, "dta",     "letter", "con", "t",  None),
    (0x0925, "dtha",    "letter", "con", "t",  "an aspirated t"),
    (0x0926, "dda",     "letter", "con", "d",  None),
    (0x0927, "ddha",    "letter", "con", "d",  "a breathy d"),
    (0x0928, "dna",     "letter", "con", "n",  None),

    # the labials
    (0x092a, "dpa",     "letter", "con", "p",  None),
    (0x092b, "dpha",    "letter", "con", "f",  None),
    (0x092c, "dba",     "letter", "con", "b",  None),
    (0x092d, "dbha",    "letter", "con", "b",  "a breathy b"),
    (0x092e, "dma",     "letter", "con", "m",  None),

    # the semivowels, the sibilants and h
    (0x092f, "dya",     "letter", "glid", "y", None),
    (0x0930, "dra",     "letter", "con", "r",  None),
    (0x0932, "dla",     "letter", "con", "l",  None),
    (0x0935, "dva",     "letter", "glid", "v", None),
    (0x0936, "dsha",    "letter", "con", "S",  None),
    (0x0937, "dSha",    "letter", "con", "S",  "a retroflex sh"),
    (0x0938, "dsa",     "letter", "con", "s",  None),
    (0x0939, "dha",     "letter", "con", "h",  None),

    # the vowel signs. Each follows a consonant and replaces the a that
    # consonant carries on its own, which is the rule the letter-to-sound
    # work turns on.
    (0x093e, "dmaa",    "letter", "vow", "Aa", None),
    (0x093f, "dmi",     "letter", "vow", "i",  None),
    (0x0940, "dmii",    "letter", "vow", "I",  None),
    (0x0941, "dmu",     "letter", "vow", "u",  None),
    (0x0942, "dmuu",    "letter", "vow", "U",  None),
    (0x0943, "dmri",    "letter", "vow", "r",  "a vocalic r"),
    (0x0947, "dme",     "letter", "vow", "e",  None),
    (0x0948, "dmai",    "letter", "vow", "E",  None),
    (0x094b, "dmo",     "letter", "vow", "o",  None),
    (0x094c, "dmau",    "letter", "vow", "O",  None),

    # the signs
    (0x0902, "danu",    "letter", "con", "n",  "a nasal on the vowel before"),
    (0x0901, "dcandra", "letter", "con", "n",  "a nasal on the vowel before"),
    (0x0903, "dvisarga", "letter", "con", "h", None),
    # the virama kills the a a consonant carries, which makes a cluster. It is
    # punctuation rather than a letter because it stands for no sound at all.
    (0x094d, "dvirama", "punct",  "undefined", "GAP", None),

    # and the full stop
    (0x0964, "ddanda",  "punct",  "undefined", "GAP", None),
]


def run(args):
    out = subprocess.run([PY] + args, cwd=ROOT, capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    if out.returncode:
        sys.stderr.write(out.stdout + out.stderr)
        raise SystemExit("hien-devanagari: %s failed" % " ".join(args[1:4]))
    return out.stdout


def takeable_bytes():
    """The slots lang-repoint says may be taken, in byte order."""
    text = run(["tools/lang-repoint.py", "show", "hien"])
    out = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        for i in range(0, len(parts) - 1, 2):
            try:
                out.append(int(parts[i], 16))
            except ValueError:
                pass
    return sorted(set(out))


def main(argv):
    dry = "--dry-run" in argv

    free = takeable_bytes()
    if len(free) < len(DEVANAGARI):
        raise SystemExit("hien-devanagari: %d characters wanted and %d slots"
                         " takeable" % (len(DEVANAGARI), len(free)))
    print("%d characters to place, %d slots takeable" % (len(DEVANAGARI),
                                                         len(free)))

    plan = list(zip(DEVANAGARI, free))

    # The code point table first, so that a failure part way through leaves the
    # two files disagreeing in the direction that is obvious -- a character
    # that arrives as a byte whose slot is still an accented letter speaks
    # wrongly and loudly, where the other way round is silent.
    lines = [
        "# Which Devanagari character arrives as which byte of hien's"
        " alphabet.",
        "#",
        "# The machine reads one byte at a time. A caller writes code points --",
        "# U+0928 for na -- and the engine turns each into a byte before any",
        "# rule sees it, through one Windows Western list, keeping the low byte",
        "# of anything else. Devanagari is nowhere in that list, so U+0928",
        "# arrived as 0x28, an open bracket, and a Hindi word came out as a row",
        "# of punctuation. That is the whole of why Hindi spoke gibberish.",
        "#",
        "# Written by tools/hien-devanagari.py, which also points the alphabet",
        "# at these bytes: the two have to agree exactly, so one file holds the",
        "# facts and writes both.",
        "",
    ]
    for (spec, byte) in plan:
        cp, name, _kind, _lt, ph, wants = spec
        note = "  # %s says %s" % (name, ph)
        if wants:
            note += ", wants %s" % wants
        lines.append("%04x %02x%s" % (cp, byte, note))
    lines.append("")

    if dry:
        print("\n".join(lines[13:]))
        return 0

    path = os.path.join(ROOT, "lang", "hien", "hien.codepoints")
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    print("wrote lang/hien/hien.codepoints")

    approximate = 0
    for (spec, byte) in plan:
        cp, name, kind, lt, ph, wants = spec
        run(["tools/lang-repoint.py", "take", "hien", "%02x" % byte, name,
             "case=lower", "type=%s" % kind, "letter=%s" % lt,
             "accent=~yes", "phoneme=%s" % ph])
        if wants:
            approximate += 1
    print("pointed %d characters, %d of them at an approximate sound"
          % (len(plan), approximate))
    print("run tools/lang-codepoints.py hien next, then delta-link.py write"
          " hien")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
