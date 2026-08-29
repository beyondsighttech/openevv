#!/usr/bin/env python3
"""Rebuild lang/hien's two generated rule files out of lang/hien/rules.

`tools/delta-notation.py regenerate' does this for a language whose text was
written out of IBM's objects, and holds the result against what is in the
tree: for enus that is the proof that the text is the source. Hindi has no
objects behind it, so the comparison is not the point -- writing the files is.

It also normalises line endings before comparing, because the tree's enus
files were written on a machine that wrote CRLF and Python writes LF here;
the bytes the compiler sees are the same either way.

usage: hien-regen.py [--write] [tag]     default tag hien, compare only
"""

import os
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_notation(tag):
    """delta-notation.py as a module, pointed at one language's tree."""
    os.environ["EVV_NOTATION_LANG"] = tag
    path = os.path.join(ROOT, "tools", "delta-notation.py")
    src = open(path, encoding="utf-8").read()
    mod = types.ModuleType("delta_notation")
    mod.__dict__["__name__"] = "delta_notation"
    mod.__dict__["__file__"] = path
    exec(compile(src, path, "exec"), mod.__dict__)
    return mod


def build(mod, tag):
    """Every rule of the tree through the emitter, in the emitter's order."""
    e = mod.de.Emitter()
    tree = mod.TREE
    files = sorted(f for f in os.listdir(tree) if f.endswith(".dr"))
    files = ([f for f in files if f != "glob.dr"]
             + [f for f in files if f == "glob.dr"])
    n = 0
    for f in files:
        rules, tables = mod.read_rules(open(os.path.join(tree, f),
                                            encoding="utf-8"))
        for name, d, obj in rules:
            e.rule(name, d, tables, obj)
            e.origin[name] = obj
            n += 1
    return e, n


def main(argv):
    write = "--write" in argv
    argv = [a for a in argv if a != "--write"]
    tag = argv[0] if argv else "hien"

    mod = load_notation(tag)
    e, n = build(mod, tag)
    print("rules read out of lang/%s/rules: %d" % (tag, n))

    stores, names = mod.read_symbols()
    print("stores %d, addresses %d" % (len(stores), len(names)))

    out = os.path.join(ROOT, "lang", tag)
    with tempfile.TemporaryDirectory() as tmp:
        c = os.path.join(tmp, "delta_rules_%s.c" % tag)
        h = os.path.join(tmp, "delta_rules_%s.h" % tag)
        shim = os.path.join(tmp, "delta_rules_shim_%s.c" % tag)
        mod.de.TAG[0] = tag
        mod.de.write_c(e, None, c, h, None, stores, names, tag)
        mod.de.write_shims(e, shim, None)

        made = {}
        for name in (c, h, shim):
            made[os.path.basename(name)] = open(name, "rb").read()

        ok = True
        for base, body in sorted(made.items()):
            have = os.path.join(out, base)
            if os.path.exists(have):
                want = open(have, "rb").read()
                same = (body.replace(b"\r\n", b"\n")
                        == want.replace(b"\r\n", b"\n"))
                print("%-28s %s (%d bytes made, %d in the tree)"
                      % (base, "the same as the tree's" if same
                         else "DIFFERS from the tree's", len(body), len(want)))
                ok = ok and same
            else:
                print("%-28s not in the tree yet" % base)
                ok = False
            if write:
                open(os.path.join(out, base), "wb").write(body)
        if write:
            print("written to lang/%s" % tag)
    return 0 if (ok or write) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
