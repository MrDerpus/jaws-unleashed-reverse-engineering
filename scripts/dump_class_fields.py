# SPDX-License-Identifier: GPL-3.0-or-later
#
# Jaws Unleashed reverse engineering tools
# Copyright (C) 2026 MrDerpus and contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Scan Jaws.exe for reflection field-registration stubs and dump a class->fields table.

Stub shape (per field):
  mov eax,[typedesc_ptr]      A1 xx xx xx xx
  push a                      6A ib | 68 id
  push b                      6A ib | 68 id
  push eax                    50
  push classdesc              68 id
  push name                   68 id
  push 0                      6A 00
  mov ecx, fielddesc          B9 id
  call register               E8 rel32
Class name getters: B8 <name> C3 ... A1 <..> C3 ... B8 <classdesc> C3  (16-byte aligned stubs)
"""
import struct, re, json, sys
from collections import defaultdict
EXE = 'game_binary/Jaws.exe'
data = open(EXE, 'rb').read()
# sections: (va, size, fileoff)
SECS = [(0x401000, 0x3cd000, 0x1000), (0x7ce000, 0x77000, 0x3ce000), (0x845000, 0x627000, 0x445000)]
def va2off(va):
    for v, s, o in SECS:
        if v <= va < v + s: return va - v + o
    return None
def off2va(off):
    for v, s, o in SECS:
        if o <= off < o + s: return off - o + v
def cstr(va):
    o = va2off(va)
    if o is None: return None
    e = data.find(b'\0', o, o + 128)
    try: s = data[o:e].decode('ascii')
    except UnicodeDecodeError: return None
    return s if s and s.isprintable() else None

pat = re.compile(rb'\xA1(.{4})(?:\x6A(.)|\x68(.{4}))(?:\x6A(.)|\x68(.{4}))\x50\x68(.{4})\x68(.{4})\x6A\x00\xB9(.{4})\xE8(.{4})', re.S)
u = lambda b: struct.unpack('<I', b)[0]
s8 = lambda b: struct.unpack('<b', b)[0]
text = (0x1000, 0x1000 + 0x3cd000)
fields = defaultdict(list)
regfuncs = defaultdict(int)
for m in pat.finditer(data, *text):
    a = s8(m.group(2)) if m.group(2) is not None else u(m.group(3))
    b = s8(m.group(4)) if m.group(4) is not None else u(m.group(5))
    cls, name = u(m.group(6)), u(m.group(7))
    callsite = off2va(m.end())
    target = (callsite + struct.unpack('<i', m.group(9))[0]) & 0xffffffff
    regfuncs[target] += 1
    n = cstr(name)
    if n: fields[cls].append({'name': n, 'a': a, 'b': b, 'typedesc_ptr': u(m.group(1)), 'reg': target})

# class name getters: mov eax,name; ret; (pad) mov eax,[x]; ret; (pad) mov eax,classdesc; ret
clsnames = {}
for m in re.finditer(rb'\xB8(.{4})\xC3\x90*\xA1.{4}\xC3\x90*\xB8(.{4})\xC3', data[text[0]:text[1]], re.S):
    n = cstr(u(m.group(1)))
    if n: clsnames.setdefault(u(m.group(2)), n)

out = {}
for cls, fl in fields.items():
    out[f'{clsnames.get(cls, "?")}@{cls:#x}'] = fl
json.dump(out, open(sys.argv[1], 'w'), indent=1)
print('registration funcs:', {hex(k): v for k, v in regfuncs.items()})
print('classes:', len(out), 'fields:', sum(len(v) for v in out.values()), 'named classes:', sum(1 for c in fields if c in clsnames))
