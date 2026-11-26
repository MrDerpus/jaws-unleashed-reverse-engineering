#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 MrDerpus and contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If
# not, see <https://www.gnu.org/licenses/>.
"""Clean Ghidra SH-4 decompiler output: Ghidra forks every float operation on the FPU mode flags
(FPSCR.PR / FPSCR.SZ). With SetFpscrZero.java applied they show up as locals set to '\\0'
(or as in_FPSCR_PR / in_FPSCR_SZ). This keeps only the branch taken when the flag is 0.
Usage: python3 sh4_fpmode_filter.py IN.c [OUT.c]   (default: overwrite IN.c)"""
import re, sys

def block_end(lines, i):
    """i = line with an opening '{' at its end; return the index of its matching '}' line."""
    depth = 0
    for j in range(i, len(lines)):
        depth += lines[j].count('{') - lines[j].count('}')
        if depth == 0:
            return j
    return len(lines) - 1

def dedent(body):
    return [l[2:] if l.startswith('  ') else l for l in body]

def clean(lines):
    flags = {'in_FPSCR_PR', 'in_FPSCR_SZ'}
    for l in lines:
        m = re.match(r"\s*(\w+) = '\\0';\s*$", l)
        if m and re.match(r'cVar\d+$', m.group(1)):
            flags.add(m.group(1))
    pat = re.compile(r'^(\s*)if \((%s) (==|!=) \'\\0\'\) \{$' % '|'.join(map(re.escape, flags)))
    out, i = [], 0
    while i < len(lines):
        m = pat.match(lines[i])
        if not m:
            if not re.match(r"\s*(%s) = '\\0';\s*$" % '|'.join(map(re.escape, flags)), lines[i]):
                out.append(lines[i])
            i += 1
            continue
        e1 = block_end(lines, i)
        then = lines[i + 1:e1]
        els = []
        nxt = e1 + 1
        if lines[e1].strip() == '}' and nxt < len(lines) and lines[nxt].strip() == 'else {':
            e2 = block_end(lines, nxt)
            els = lines[nxt + 1:e2]
            nxt = e2 + 1
        elif lines[e1].strip() == '} else {':
            e2 = block_end(lines, e1)  # same-line else
            then = lines[i + 1:e1]
            els = lines[e1 + 1:e2]
            nxt = e2 + 1
        keep = then if m.group(3) == '==' else els
        out.extend(clean(dedent(keep)) if keep else [])
        i = nxt
    return out

src = sys.argv[1]
lines = open(src).read().split('\n')
open(sys.argv[2] if len(sys.argv) > 2 else src, 'w').write('\n'.join(clean(lines)))
