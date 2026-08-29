#!/usr/bin/env python3
"""Give a language's alphabet slots to another writing system.

`tools/lang-alphabet.py add' puts a character at a byte value nothing claims
yet, which is right when a language wants a few letters more than the module it
came from. Devanagari wants fifty-nine and hien had twenty-two byte values
free, so adding is not enough: the slots have to come from somewhere.

They come from the accented Latin-1 letters. hien's alphabet is its own table,
copied from English's when the module was made, and a hundred and eight of its
entries are things like a-grave and o-tilde and the fraction signs. Hindi is
written in Devanagari and will never see one of them. Taking those slots
changes nothing English says, because English reads its own alphabet out of
`lang/enus' and this file is not that.

What it does NOT do is move a slot something already means in this language:
the plain ASCII letters, the digits and the punctuation stay exactly where they
are, because Hindi text carries English words, numerals and full stops and
those have to keep working. Only the accented range is taken, and the tool
refuses a target outside it.

    lang-repoint.py show <tag>              which slots are takeable
    lang-repoint.py take <tag> <byte> <name> <field>=<value>...

`take' renames one slot and rewrites its record. The byte is in hex and has to
be one `show' listed. The name is what the rules will call it, which for a
Devanagari letter is its transliteration -- `ka', `kha' -- rather than the
character itself, so that a rules file stays readable in a terminal that has no
Devanagari font.

    lang-repoint.py take hien e0 ka case=lower type=letter letter=con \\
                              accent='~yes' phoneme=k

usage: as above
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATEMENT = "inp"
RECORD = ("case", "type", "letter", "accent", "phoneme")
FIELD = {"case": "letcase", "type": "character_type", "letter": "letter_type",
         "accent": "accent", "phoneme": "phon_form"}

#: A slot is takeable when its name is one character above 0x7f -- the accented
#: and symbol range of Latin-1. Everything a Hindi text still needs in ASCII is
#: below that and is refused.
def takeable(name):
    return len(name) == 1 and 0x7f < ord(name) < 0x100


def path_of(tag):
    return os.path.join(ROOT, "lang", tag, "%s.statements" % tag)


def read(tag):
    lines = open(path_of(tag), encoding="utf-8").read().split("\n")
    first = last = None
    names, values, var_at = [], {}, []
    variants = bytearray()
    field = None
    for i, line in enumerate(lines):
        if line == "statement %s" % STATEMENT:
            first = i
            continue
        if first is not None and last is None:
            if line == "end" or line.startswith("statement "):
                last = i
                continue
            w = line.split()
            if line.startswith("  field "):
                field = w[1]
                values.setdefault(field, [])
            elif line.startswith("    value") and field:
                text = line[len("    value"):]
                text = text[1:] if text.startswith(" ") else text
                text = text.replace("\\s", " ").replace("\\\\", "\\")
                values[field].append(text)
                if field == "name":
                    names.append((i, text))
            elif w and w[0] == "variants":
                var_at.append(i)
                variants += bytes(int(x, 16) for x in w[1:])
    if first is None:
        raise SystemExit("lang-repoint: %s has no %s statement"
                         % (tag, STATEMENT))
    return lines, first, last, names, values, bytes(variants), var_at


def number(values, field, text):
    table = values.get(FIELD[field], [])
    if text in table:
        return table.index(text)
    raise SystemExit("lang-repoint: %s has no %s called %r; it has %s"
                     % (FIELD[field], field, text,
                        ", ".join(table[:12]) + ("..." if len(table) > 12
                                                 else "")))


def show(tag):
    _l, _f, _t, names, _v, _var, _at = read(tag)
    free = [(code, n) for code, (_i, n) in enumerate(names) if takeable(n)]
    print("%s: %d slots takeable out of %d" % (tag, len(free), len(names)))
    for at in range(0, len(free), 10):
        row = free[at:at + 10]
        print("  " + "  ".join("%02x %s" % (ord(n), n) for _c, n in row))
    return True


def take(tag, byte, newname, args):
    lines, first, last, names, values, variants, var_at = read(tag)

    want = {}
    for a in args:
        if "=" not in a:
            raise SystemExit("lang-repoint: %r is not field=value" % a)
        k, v = a.split("=", 1)
        if k not in RECORD:
            raise SystemExit("lang-repoint: a record has no %r; it has %s"
                             % (k, ", ".join(RECORD)))
        want[k] = v
    for k in RECORD:
        if k not in want:
            raise SystemExit("lang-repoint: say what its %s is" % k)

    ch = bytes([int(byte, 16)]).decode("latin-1")
    where = None
    for code, (line_at, n) in enumerate(names):
        if n == ch:
            where = (code, line_at)
            break
    if where is None:
        raise SystemExit("lang-repoint: %s's alphabet has no character at %s"
                         % (tag, byte))
    code, line_at = where
    if not takeable(ch):
        raise SystemExit("lang-repoint: %s at %s is not in the accented range,"
                         " and Hindi text still needs it" % (ch, byte))
    if any(n == newname for _i, n in names):
        raise SystemExit("lang-repoint: %s already has a character called %r"
                         % (tag, newname))

    if len(variants) % 5:
        raise SystemExit("lang-repoint: %s's records are %d bytes, not five"
                         " each -- run tools/lang-widen.py first"
                         % (tag, len(variants)))

    record = bytes(number(values, k, want[k]) for k in RECORD)

    was = variants[code * 5:code * 5 + 5]
    new = bytearray(variants)
    new[code * 5:code * 5 + 5] = record

    lines[line_at] = "    value %s" % newname

    body = []
    for at in range(0, len(new), 32):
        body.append("  variants %s"
                    % " ".join("%02x" % b for b in new[at:at + 32]))
    lines[var_at[0]:var_at[-1] + 1] = body

    open(path_of(tag), "w", encoding="utf-8").write("\n".join(lines))

    # And a note of which byte this slot is reached by, because renaming it
    # throws that away. A slot's name is normally the character itself, so its
    # byte can be read out of the spelling; a name like `dka' cannot be spelt
    # in Latin-1 at all, and then nothing in the statements file says what byte
    # the slot answers to. tools/lang-codepoints.py needs to know, or it cannot
    # tell a mapping onto a real slot from one onto a byte the alphabet never
    # names -- and that check is the one thing standing between a letter that
    # speaks and a letter that arrives as something else.
    note = os.path.join(ROOT, "lang", tag, "%s.repointed" % tag)
    seen = {}
    if os.path.exists(note):
        for line in open(note, encoding="utf-8"):
            line = line.split("#")[0].strip()
            if line:
                w = line.split()
                seen[int(w[0], 16)] = w[1]
    seen[int(byte, 16)] = newname
    with open(note, "w", encoding="utf-8") as f:
        f.write("# Which byte each repointed slot of %s's alphabet is reached"
                " by.\n"
                "# Written by tools/lang-repoint.py. A slot renamed away from"
                " the character\n"
                "# it held no longer says its own byte, and"
                " tools/lang-codepoints.py reads\n"
                "# this to know a real slot from a byte nothing names.\n\n"
                % tag)
        for b in sorted(seen):
            f.write("%02x %s\n" % (b, seen[b]))

    print("%s: code %d was %r, is %r now -- %s"
          % (tag, code, ch, newname,
             ", ".join("%s %s" % (k, want[k]) for k in RECORD)))
    print("  its record was %s and is %s"
          % (" ".join("%02x" % b for b in was),
             " ".join("%02x" % b for b in record)))
    return True


def main(argv):
    if len(argv) >= 2 and argv[0] == "show":
        return 0 if show(argv[1]) else 1
    if len(argv) >= 4 and argv[0] == "take":
        return 0 if take(argv[1], argv[2], argv[3], argv[4:]) else 1
    raise SystemExit(__doc__.strip())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
