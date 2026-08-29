#!/usr/bin/env python3
"""Emit build/consts_check.c: hashes each uint8_t table in a language's
delta_consts file at its declared length, so two compilers' objects can be
compared byte-for-byte over exactly the bytes the engine reads."""
import re
import sys

src_path = sys.argv[1] if len(sys.argv) > 1 else "lang/enus/delta_consts_enus.c"
out_path = sys.argv[2] if len(sys.argv) > 2 else "build/consts_check.c"

src = open(src_path).read()
decls = re.findall(r"^uint8_t (\w+)\[(\d+)\]", src, re.M)

lines = ["#include <stdio.h>", "#include <stdint.h>"]
for name, n in decls:
    lines.append("extern uint8_t %s[%s];" % (name, n))
lines.append(
    "static unsigned long long h(const uint8_t *p, int n)"
    "{unsigned long long x=1469598103934665603ULL;"
    "for(int i=0;i<n;i++){x^=p[i];x*=1099511628211ULL;}return x;}")
lines.append("int main(void){")
for name, n in decls:
    # putchar(10) instead of "\n" keeps this generator free of escapes
    lines.append('printf("%s %%llX", h(%s,%s)); putchar(10);'
                 % (name, name, n))
lines.append("return 0;}")
open(out_path, "w").write("\n".join(lines) + "\n")
print(len(decls), "tables ->", out_path)
