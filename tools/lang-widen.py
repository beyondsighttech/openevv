#!/usr/bin/env python3
"""Widen a language's input statement so its characters can carry a sound.

A character's record in the input statement says what kind of thing the
character is. English's is three bytes -- case, type, letter -- and Italian's
is five, the two extra being `accent' and `phon_form'. That last one is the
phoneme the character stands for on its own, which is letter-to-sound at its
simplest and is the field a new writing system needs above all others: without
it a letter can be declared and still have nothing to say.

A module lifted from English has the narrow shape, and `tools/lang-alphabet.py`
refuses to work on one -- it reads and writes five-byte records and says so
rather than corrupting a three-byte table. This widens the statement in place:
every existing character keeps its code and its first three bytes, and gains
an accent of nought and a phoneme of nought, which is what `undefined' and
`GAP' are. So no character changes meaning and none is lost.

What it changes, all inside one statement:

  length         5 -> 7          two more fields
  at start       3 -> 5          where the variable part begins
  fresh                          a fresh record is two bytes longer
  name           where 3 -> 5    the fields after the new ones move up
  afterslash     where 4 -> 6
  accent         added at 3      with the two values a yes/no field has
  phon_form      added at 4      with the phonemes the language declares

The phonemes it offers are read from the language's own `phone' statement, so
this invents nothing: a character can only be given a sound the language
already has, and `tools/lang-phonemes.py' is what adds one that it has not.

It is idempotent -- a statement already five wide is left alone and said so.

usage: lang-widen.py <tag>...
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATEMENT = "inp"


def path_of(tag):
    return os.path.join(ROOT, "lang", tag, "%s.statements" % tag)


def span(lines, name):
    """Where one statement starts and stops."""
    first = None
    for i, line in enumerate(lines):
        if line == "statement %s" % name:
            first = i
            continue
        if first is not None:
            if line == "end" or line.startswith("statement "):
                return first, i
    raise SystemExit("lang-widen: no %s statement" % name)


def values_of(lines, first, last, field):
    """A field's value names, in order, which is what its numbers mean."""
    out = []
    at = None
    for i in range(first, last):
        if lines[i].startswith("  field "):
            at = lines[i].split()[1]
        elif lines[i].startswith("    value") and at == field:
            text = lines[i][len("    value"):]
            out.append(text[1:] if text.startswith(" ") else text)
    return out


def widen(tag):
    path = path_of(tag)
    lines = open(path).read().split("\n")
    first, last = span(lines, STATEMENT)

    length = None
    for i in range(first, last):
        if lines[i].startswith("  length "):
            length = int(lines[i].split()[1])
            break
    if length is None:
        raise SystemExit("lang-widen: %s's %s has no length" % (tag, STATEMENT))
    if length >= 7:
        print("%s: already %d wide, nothing to do" % (tag, length))
        return True
    if length != 5:
        raise SystemExit("lang-widen: %s's %s is %d wide, which is neither the"
                         " narrow shape nor the wide one" % (tag, STATEMENT,
                                                             length))

    # The records as they are: three bytes each, in one run of `variants'
    # lines. Read them all before anything is written, so a malformed file
    # cannot leave a half-widened statement behind.
    old = bytearray()
    var_at = []
    for i in range(first, last):
        w = lines[i].split()
        if w and w[0] == "variants":
            var_at.append(i)
            old += bytes(int(x, 16) for x in w[1:])
    if not var_at:
        raise SystemExit("lang-widen: %s's %s has no records" % (tag,
                                                                 STATEMENT))
    if len(old) % 3 != 0:
        raise SystemExit("lang-widen: %s has %d bytes of records, which is not"
                         " three each" % (tag, len(old)))
    count = len(old) // 3

    # Every record widened: what it said, then the accent and the phoneme.
    # The accent byte is 1, not nought: the field's values are `yes' then
    # `~yes', so nought would claim every character is accented, and Italian's
    # own ordinary letters carry ~yes. Getting that backwards is audible --
    # it moved all three Hindi hashes the first time -- and costs nothing to
    # get right, since a widened record must mean exactly what the narrow one
    # did. The phoneme stays nought, which reads as GAP: a character that
    # stood for no sound of its own still stands for none.
    accent_no = 1
    new = bytearray()
    for r in range(count):
        new += old[r * 3:r * 3 + 3]
        new += bytes([accent_no, 0])

    # The phonemes this language has, so the new field's values are its own
    # rather than another module's. The phone statement's first field is the
    # list the rules index by.
    pfirst, plast = span(lines, "phone")
    phonemes = values_of(lines, pfirst, plast, "name")
    if not phonemes:
        raise SystemExit("lang-widen: %s declares no phonemes" % tag)

    out = []
    i = first
    while i < last:
        line = lines[i]
        w = line.split()

        if line.startswith("  length "):
            out.append("  length 7")
        elif line.startswith("  at start stride "):
            out.append("  at start stride 5")
        elif line.startswith("  at start varlen "):
            out.append("  at start varlen 5")
        elif line.startswith("  fresh "):
            # Two more bytes, and the one that was last stays last: the
            # narrow shape ends 00 01, and the wide one ends 01 00 00 01.
            out.append("  fresh 00 00 00 01 00 00 01")
        elif w and w[0] == "variants":
            # The whole run replaced at the first of them, the rest dropped.
            if i == var_at[0]:
                for at in range(0, len(new), 32):
                    out.append("  variants %s"
                               % " ".join("%02x" % b
                                          for b in new[at:at + 32]))
        elif line == "  field name":
            out.append(line)
            out.append("    where 5 5 1")
            i += 2                       # its own where line goes
            continue
        elif line == "  field afterslash":
            out.append(line)
            out.append("    where 6 6 1")
            i += 2
            continue
        elif line == "  field letter_type":
            # The last of the narrow fields, so the two new ones go after it,
            # before it in the file being what puts them at bytes 3 and 4.
            out.append(line)
            i += 1
            while i < last and not lines[i].startswith("  field ") \
                    and lines[i] != "    end":
                out.append(lines[i])
                i += 1
            if i < last and lines[i] == "    end":
                out.append(lines[i])
                i += 1
            out.append("  field accent")
            out.append("    where 3 3 1")
            out.append("    what -1 0 0")
            out.append("    format %d")
            out.append("    value yes")
            out.append("    value ~yes")
            out.append("    end")
            out.append("  field phon_form")
            out.append("    where 4 4 1")
            out.append("    what -1 1 0")
            out.append("    format %d")
            for p in phonemes:
                out.append("    value %s" % p)
            out.append("    end")
            continue
        else:
            out.append(line)
        i += 1

    lines[first:last] = out
    open(path, "w").write("\n".join(lines))
    print("%s: %s widened to 7, %d records now five bytes, %d phonemes"
          " offered as sounds" % (tag, STATEMENT, count, len(phonemes)))
    return True


def main(argv):
    if not argv:
        raise SystemExit(__doc__.strip())
    for tag in argv:
        widen(tag)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
