#!/usr/bin/env python3
"""Bisect which object, compiled by zig cc rather than mingw gcc, changes
the engine's samples.

Both compilers build the whole tree into their own object directories; this
then links the driver out of gcc's objects everywhere except a chosen subset,
taken from zig's, and speaks the hash sentence. The smallest subset whose
audio moves names the source file where the two compilers disagree.

usage: bisect-cc.py [start end]     indices into the sorted object list;
                                    default bisects the whole set.
"""

import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
GCC = os.path.join(BUILD, "objwin-bytecode-gcc", "enus")
ZIG = os.path.join(BUILD, "objwin-bytecode-zig", "enus")
CC = r"C:\Users\aakash\AppData\Local\Temp\mingw64\bin\gcc.exe"

# What the samples must be: the tree's own canonical hash, which the all-gcc
# build answers on this machine.
WANT = "f4de90c69c89aa1bfdc4e22dfc35d1ae6e9b39cf0e2db875ec6d5c2e9c05e987"
TEXT = "The quick brown fox jumps over the lazy dog."


def speak(subset):
    objs = []
    for name in sorted(os.listdir(GCC)):
        if not name.endswith(".o"):
            continue
        src = ZIG if name in subset and name not in EXCLUDE else GCC
        objs.append(os.path.join(src, name))
    exe = os.path.join(BUILD, "bisect.exe")
    cmd = [CC, "-O2", "-std=gnu99",
           "-I" + os.path.join(ROOT, "src"),
           "-I" + os.path.join(ROOT, "lang", "enus"),
           "-w", "-DEVV_ARENA=1",
           os.path.join(ROOT, "cli", "evv.c")] + objs + \
        ["-o", exe]
    subprocess.run(cmd, check=True, cwd=ROOT)
    wav = os.path.join(BUILD, "bisect.wav")
    r = subprocess.run([exe, "-o", wav, TEXT], capture_output=True)
    if r.returncode != 0 or not os.path.exists(wav):
        return "CRASH"
    h = hashlib.sha256(open(wav, "rb").read()).hexdigest()
    return h


# Files whose object must stay gcc's whatever happens: they reach the C
# library through spellings the two compilers' headers disagree about
# (stat64i32 is msvcrt's name; zig emits it, mingw wants _stat64i32).
EXCLUDE = {"eci_usrdct.o"}


def main():
    names = [n for n in sorted(os.listdir(GCC))
             if n.endswith(".o") and n not in EXCLUDE]
    lo, hi = 0, len(names)
    if len(sys.argv) > 2:
        lo, hi = int(sys.argv[1]), int(sys.argv[2])

    # Everything from zig: expected bad. Everything from gcc: expected good.
    allzig = set(names)
    assert speak(EXCLUDE) == WANT, "the all-gcc build does not answer canonically"
    assert speak(allzig | EXCLUDE) != WANT, "the all-zig build answers canonically"

    bad = allzig
    good = set()
    while len(bad - good) > 1:
        mid = set(sorted(bad - good)[:max(1, len(bad - good) // 2)])
        trial = good | mid | EXCLUDE
        r = speak(trial)
        print("%6d of %6d -> %s" % (len(trial), len(names),
                                    "good" if r == WANT else r),
              file=sys.stderr)
        if r == WANT:
            good = trial          # these zig objects are innocent
        else:
            bad = trial           # the fault is in here
    culprit = bad - good
    for n in sorted(culprit):
        print("culprit:", n)


if __name__ == "__main__":
    main()
