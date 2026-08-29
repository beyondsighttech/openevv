#!/usr/bin/env python3
"""The Windows build, driven through zig cc rather than mingw-make.

The Makefile's `win' target wants a mingw cross toolchain, which a machine
without nix or mingw does not have. This drives the same recipe through
`zig cc' instead: the same sources, the same flags, one static exe. It exists
so that a Windows machine can build and test without anything installed --
Python and this venv's zig are the whole of it.

usage: build-zig.py [--rules bytecode|c] [--langs enus,hien] evv|probe|dll

The objects go where the Makefile puts them -- build/objwin-<rules>/<tags> --
so the two drivers never hand each other a stale object.
"""

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
BUILD = os.path.join(ROOT, "build")

# CC may name a whole other compiler, the way CC32 and CCWIN do in the
# Makefile: "zig" drives zig cc, anything else is split as a command.
_cc = os.environ.get("EVV_CC")
if _cc is None:
    # The machine's mingw gcc when it is there -- zig cc miscompiles one
    # object (delta_consts_enus.o under some layouts) and is the fallback.
    _mingw = os.path.join(ROOT, ".toolchain", "mingw64", "bin", "gcc.exe")
    _cc = _mingw if os.path.exists(_mingw) else "zig"
if _cc == "zig":
    ZIG = [sys.executable, "-m", "ziglang", "cc"]
else:
    ZIG = _cc.split()

# The Makefile's WARN, minus -Werror=int-conversion and the pointer-types
# error, which zig's clang spells differently; the narrowed-pointer class of
# mistake is what -Werror=int-conversion guards, and zig cc answers
# -Wint-conversion too, so both are kept.
WARN = ["-w", "-Wno-implicit-function-declaration",
        "-Werror=int-conversion", "-Werror=incompatible-pointer-types"]


def lang_list_c(langs):
    """build/delta_langs_<tags>.c, byte for byte what the Makefile writes."""
    lines = [
        "/* Written by the Makefile: which languages this program has",
        "   in it, and the first of them, which is the one a caller",
        "   gets when it asks for no language in particular. */",
        "",
        '#include "delta_lang.h"',
        "",
    ]
    for t in langs:
        lines.append("extern delta_language delta_lang_%s;" % t)
        lines.append("void delta_lang_bind_%s(void);" % t)
    lines.append("")
    lines.append("const delta_language *const delta_languages[] = {")
    for t in langs:
        lines.append("    &delta_lang_%s," % t)
    lines.append("    0,")
    lines.append("};")
    lines.append("")
    lines.append("void delta_lang_bind_all(void)")
    lines.append("{")
    for t in langs:
        lines.append("    delta_lang_bind_%s();" % t)
    lines.append("}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", choices=["bytecode", "c"], default="bytecode")
    ap.add_argument("--langs", default="enus")
    ap.add_argument("target", choices=["evv", "probe", "dll"])
    args = ap.parse_args()

    tags = [t.strip() for t in args.langs.split(",") if t.strip()]
    lang_dirs = ["lang/" + t for t in tags]

    # Sources: the Makefile's SOURCESWIN -- the POSIX platform layer out,
    # every language module in, the stub table of rules-written-as-C in.
    srcs = []
    for name in sorted(os.listdir(SRC)):
        if name.endswith(".c") and name != "port_posix.c":
            srcs.append(os.path.join(SRC, name))
    # The Makefile filters both rule tables out of every module and puts one
    # back -- the stub when the rules run as bytecode, the generated C when
    # they run as C.
    for d in lang_dirs:
        for name in sorted(os.listdir(d)):
            if not name.endswith(".c"):
                continue
            if name.startswith("delta_rules_none_"):
                want = args.rules == "bytecode"
            elif name.startswith("delta_rules_c_"):
                want = args.rules == "c"
            else:
                want = True
            if want:
                srcs.append(os.path.join(d, name))

    _cctag = (os.path.splitext(os.path.basename(ZIG[-1]))[0]
              if _cc != "zig" else "zig")
    objdir = os.path.join(BUILD, "objwin-%s-%s" % (args.rules, _cctag),
                          "-".join(tags))
    os.makedirs(objdir, exist_ok=True)

    langlist = os.path.join(BUILD, "delta_langs_%s.c" % "_".join(tags))
    with open(langlist, "w", newline="\n") as f:
        f.write(lang_list_c(tags))
    srcs.append(langlist)

    incs = ["-I" + SRC] + ["-I" + os.path.join(ROOT, d) for d in lang_dirs]
    cflags = (["-O2", "-std=gnu99", "-g"] + incs + WARN +
              ["-DEVV_ARENA=1"])
    # An escape hatch for chasing a codegen question: what a difference
    # between two optimisers is worth saying out loud.
    extra = os.environ.get("ZIG_CFLAGS")
    if extra:
        cflags += extra.split()
    if args.rules == "c":
        cflags += ["-DEVV_NO_BYTECODE", "-ffunction-sections",
                   "-fdata-sections", "-Wl,--gc-sections"]

    objs = []
    for s in srcs:
        obj = os.path.join(
            objdir, os.path.splitext(os.path.basename(s))[0] + ".o")
        objs.append(obj)
        newer = (not os.path.exists(obj) or
                 os.path.getmtime(s) > os.path.getmtime(obj))
        if newer or "--force" in sys.argv:
            cmd = ZIG + cflags + ["-c", s, "-o", obj]
            print(" ".join(cmd), file=sys.stderr)
            subprocess.run(cmd, check=True, cwd=ROOT)

    if args.target == "dll":
        # The engine under the names IBM published, the Makefile's eci.dll
        # target: win/eci_api.c is fifty-two wrappers and an entry point over
        # the same objects. eci.ini goes beside it because add-ons look for
        # one; nothing here reads it.
        #
        # The name does not take the tags the way the exes do -- a caller
        # loads "eci.dll" by that name and nothing else -- so a build with
        # more languages in it overwrites the one before. test/langs.py is
        # what wants this, and it wants the many-language one.
        out = os.path.join(BUILD, "eci.dll")
        res = os.path.join(objdir, "eci.res")
        windres = os.path.join(ROOT, ".toolchain", "mingw64", "bin",
                               "windres.exe")
        if os.path.exists(windres) and (
                not os.path.exists(res) or
                os.path.getmtime(os.path.join(ROOT, "win", "eci.rc"))
                > os.path.getmtime(res)):
            cmd = [windres, "-I", os.path.join(ROOT, "win"),
                   os.path.join(ROOT, "win", "eci.rc"), "-O", "coff",
                   "-o", res]
            print(" ".join(cmd), file=sys.stderr)
            subprocess.run(cmd, check=True, cwd=ROOT)
        cmd = ZIG + cflags + ["-shared", os.path.join(ROOT, "win",
                                                      "eci_api.c")]
        if os.path.exists(res):
            cmd.append(res)
        # A caller loads this by name out of whatever directory it likes, so
        # it must not want anything beside it: the exes get -static and this
        # gets it too, for libgcc and libwinpthread both. Without it ctypes
        # reports the library itself as not found, which is the loader naming
        # a missing import and not saying which.
        cmd += objs + ["-static", "-o", out]
        print(" ".join(cmd), file=sys.stderr)
        subprocess.run(cmd, check=True, cwd=ROOT)
        ini_src = os.path.join(ROOT, "win", "eci.ini")
        if os.path.exists(ini_src):
            with open(ini_src, "rb") as f:
                body = f.read()
            with open(os.path.join(BUILD, "eci.ini"), "wb") as f:
                f.write(body)
        print("built %s" % out)
        return

    front = os.path.join(ROOT, "cli", "evv.c" if args.target == "evv"
                         else "probe.c")
    out = os.path.join(BUILD, "%s%s.exe"
                       % (args.target, "" if tags == ["enus"]
                          else "-" + "-".join(tags)))
    cmd = ZIG + cflags + [front] + objs + \
        (["-static"] if _cc == "zig" else []) + ["-o", out]
    print(" ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, check=True, cwd=ROOT)
    print("built %s" % out)


if __name__ == "__main__":
    main()
