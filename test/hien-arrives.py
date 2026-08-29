#!/usr/bin/env python3
"""Does a Devanagari letter arrive as one character now, or as three bytes?

This is the measurement the whole codepoints exercise is for, and it is worth
having as a script rather than as a remark in a commit message.

Before: the engine turned each code point into a byte through one Windows
Western list, and Devanagari is nowhere in it, so U+0928 kept its low byte and
arrived as 0x28 -- an open bracket. A six-letter word was eighteen bytes and
came out as eighteen pieces of junk, which is why it took nine seconds to say.

After: hien's own table is asked first, so U+0928 arrives as the byte hien's
alphabet calls `dna'. Six letters, six characters.

What that looks like from outside is length. Nothing here reads the engine's
mind: it speaks the same word before and after and compares how long the audio
is. A word being spoken as six letters rather than eighteen junk characters is
roughly a third of the samples, and the ratio is the evidence.

usage: hien-arrives.py [binary]     default build/probe-enus-hien.exe
"""

import hashlib
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Short on purpose: cli/probe.c gives up pumping the engine's queue after
#: three thousand naps of ten milliseconds, and a word spoken letter by letter
#: can outrun that. See test/hien-timing.sh.
WORDS = [
    ("\u0928\u092e\u0938\u094d\u0924\u0947", "namaste", 6),
    ("\u0930\u093e\u092e", "raam", 3),
    ("\u0915\u092e\u0932", "kamal", 3),
]


def say(binary, text, language, tmp, tag):
    """Speak one word, and answer how many samples came back."""
    txt = os.path.join(tmp, tag + ".txt")
    wav = os.path.join(tmp, tag + ".wav")
    with open(txt, "wb") as f:
        f.write(text.encode("utf-8"))
    subprocess.run([binary, "@" + txt, wav],
                   env=dict(os.environ, EVV_LANGUAGE=language),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(wav):
        return None, None
    body = open(wav, "rb").read()
    return (len(body) - 44) // 2, hashlib.sha256(body).hexdigest()[:16]


def main(argv):
    binary = argv[0] if argv else os.path.join(ROOT, "build",
                                               "probe-enus-hien.exe")
    if not os.path.exists(binary):
        raise SystemExit("hien-arrives: no binary at %s" % binary)

    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        print("%-10s %-9s %8s %8s   %-6s %s"
              % ("word", "letters", "Hindi", "English", "ratio", "hash"))
        said = {}
        for i, (word, roman, letters) in enumerate(WORDS):
            hi, hh = say(binary, word, "0x90000", tmp, "hi%d" % i)
            en, _e = say(binary, word, "0x10000", tmp, "en%d" % i)
            if hi is None or en is None:
                print("%-10s produced nothing" % roman)
                bad = 1
                continue

            ratio = (float(hi) / en) if en else 0.0
            print("%-10s %-9d %8d %8d   %-6.2f %s"
                  % (roman, letters, hi, en, ratio, hh))
            said[roman] = (hi, hh)

            # English has no table of its own, so it still spells the bytes out
            # and is the `before' picture in the same run. Hindi reading the
            # word as letters has to be markedly shorter; equal lengths mean
            # the table is not being consulted at all.
            if hi >= en:
                print("           Hindi is not shorter than English, so the"
                      " code point table is not in force")
                bad = 1

        # And the part that matters more than the lengths. Arriving as one
        # character is worth nothing if every character then says the same
        # thing: three different words have to come out as three different
        # sounds. They did not the first time this ran -- all three gave
        # 18,557 samples under one hash, because the letters arrive and no rule
        # knows what any of them sounds like, so each fell to the same default.
        # Shorter audio is not better audio when the reason it is shorter is
        # that it is silence.
        hashes = set(h for _n, h in said.values())
        if len(said) > 1 and len(hashes) == 1:
            print()
            print("           every word came out as the same samples, so the"
                  " letters arrive and")
            print("           say nothing of their own: what is missing is the"
                  " rule that turns")
            print("           a Devanagari letter into a sound.")
            bad = 1

    print()
    print("hien-arrives: %s" % ("something is wrong" if bad
                                else "Devanagari arrives as characters and"
                                     " each says its own sound"))
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
