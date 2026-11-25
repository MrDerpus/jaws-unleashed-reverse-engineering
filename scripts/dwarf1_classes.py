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

"""Dump class/struct layouts from the DWARF v1 `.debug` section of an ELF
(written for Ecco: Defender's unstripped Dreamcast `ecco.elf`, 2000-06-02).

Usage:
  python3 dwarf1_classes.py ecco.elf                 # every class, one block each
  python3 dwarf1_classes.py ecco.elf GDBrick NAWhirl2000   # only these
  python3 dwarf1_classes.py ecco.elf --list          # name + size of every class

Output per class: size, base classes (with offset), then members as
`+0xOFF  type  name`.  Standard tools (readelf, objdump, Ghidra) don't read DWARF v1.
"""
import struct
import sys

# ---- ELF ----------------------------------------------------------------------

def elf_section(data, want):
    e_shoff, = struct.unpack_from('<I', data, 0x20)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from('<HHH', data, 0x2E)
    def sh(i):
        return struct.unpack_from('<IIIIIIIIII', data, e_shoff + i * e_shentsize)
    stroff = sh(e_shstrndx)[4]
    for i in range(e_shnum):
        s = sh(i)
        name = data[stroff + s[0]:data.index(b'\0', stroff + s[0])].decode()
        if name == want:
            return data[s[4]:s[4] + s[5]]
    raise SystemExit('no section ' + want)

# ---- DWARF v1 -----------------------------------------------------------------

TAG = {0x01: 'array', 0x02: 'class', 0x04: 'enum', 0x0d: 'member', 0x0f: 'pointer',
       0x10: 'reference', 0x11: 'cu', 0x13: 'struct', 0x15: 'subroutine_type',
       0x16: 'typedef', 0x17: 'union', 0x1c: 'inheritance', 0x1f: 'ptr_to_member'}
AT_SIBLING, AT_LOCATION, AT_NAME = 0x0012, 0x0023, 0x0038
AT_FUND, AT_MOD_FUND, AT_UDT, AT_MOD_UDT = 0x0055, 0x0063, 0x0072, 0x0083
AT_BYTE_SIZE, AT_SUBSCR, AT_BIT_OFFSET, AT_BIT_SIZE = 0x00b6, 0x00a8, 0x000c, 0x000d
FUND = {0x1: 'char', 0x2: 'schar', 0x3: 'uchar', 0x4: 'short', 0x5: 'short', 0x6: 'ushort',
        0x7: 'int', 0x8: 'int', 0x9: 'uint', 0xa: 'long', 0xb: 'long', 0xc: 'ulong',
        0xd: 'void*', 0xe: 'float', 0xf: 'double', 0x10: 'long double', 0x14: 'void',
        0x15: 'bool', 0x8008: 'longlong', 0x8208: 'ulonglong'}
MOD = {1: '*', 2: '&', 3: 'const ', 4: 'volatile '}


def parse(dbg):
    """Return {offset: die}; die = dict(tag, attrs, children(list of offsets))."""
    dies, i, n = {}, 0, len(dbg)
    order = []
    while i + 4 <= n:
        length, = struct.unpack_from('<I', dbg, i)
        if length < 8:                      # null entry / padding
            order.append((i, None))
            i += max(length, 4)
            continue
        end = i + length
        tag, = struct.unpack_from('<H', dbg, i + 4)
        j, attrs = i + 6, {}
        while j < end:
            at, = struct.unpack_from('<H', dbg, j); j += 2
            form = at & 0xF
            if form in (1, 2, 6):
                v, = struct.unpack_from('<I', dbg, j); j += 4
            elif form == 5:
                v, = struct.unpack_from('<H', dbg, j); j += 2
            elif form == 7:
                v, = struct.unpack_from('<Q', dbg, j); j += 8
            elif form == 3:
                ln, = struct.unpack_from('<H', dbg, j); v = dbg[j + 2:j + 2 + ln]; j += 2 + ln
            elif form == 4:
                ln, = struct.unpack_from('<I', dbg, j); v = dbg[j + 4:j + 4 + ln]; j += 4 + ln
            elif form == 8:
                k = dbg.index(b'\0', j); v = dbg[j:k].decode('latin-1'); j = k + 1
            else:
                break
            attrs[at] = v
        dies[i] = {'tag': tag, 'a': attrs, 'kids': []}
        order.append((i, dies[i]))
        i = end
    # children: a DIE with a sibling attribute owns the DIEs up to that sibling
    stack = []
    for off, d in order:
        while stack and off >= stack[-1][1]:
            stack.pop()
        if d is None:
            continue
        if stack:
            stack[-1][0]['kids'].append(off)
        sib = d['a'].get(AT_SIBLING)
        if sib and sib > off and d['tag'] in (0x02, 0x13, 0x17, 0x11, 0x04):
            stack.append((d, sib))
    return dies


def loc_offset(block):
    """Member location: OP_CONST n, OP_ADD (cfront/Hitachi style)."""
    i, val = 0, None
    while i < len(block):
        op = block[i]; i += 1
        if op in (1, 2, 3, 4):            # REG/BASEREG/ADDR/CONST take a 4-byte operand
            v, = struct.unpack_from('<I', block, i); i += 4
            if op == 4:
                val = v
        # 5 DEREF2, 6 DEREF4, 7 ADD: no operand
    return val


class Types:
    def __init__(self, dies):
        self.d = dies

    def name(self, a, depth=0):
        if AT_FUND in a:
            return FUND.get(a[AT_FUND], 'fund%x' % a[AT_FUND])
        if AT_UDT in a:
            return self.ref(a[AT_UDT], depth)
        if AT_MOD_FUND in a or AT_MOD_UDT in a:
            b = a.get(AT_MOD_FUND) or a.get(AT_MOD_UDT)
            mods, rest = b[:-2] if AT_MOD_FUND in a else b[:-4], None
            if AT_MOD_FUND in a:
                ft, = struct.unpack_from('<H', b, len(b) - 2)
                base = FUND.get(ft, 'fund%x' % ft)
            else:
                r, = struct.unpack_from('<I', b, len(b) - 4)
                base = self.ref(r, depth)
            pre = ''.join(MOD.get(m, '?') for m in mods if MOD.get(m, '').endswith(' '))
            post = ''.join(MOD.get(m, '?') for m in reversed(mods) if MOD.get(m) in ('*', '&'))
            return pre + base + post
        return '?'

    def ref(self, off, depth=0):
        d = self.d.get(off)
        if not d:
            return '?@%x' % off
        a = d['a']
        if AT_NAME in a:
            return a[AT_NAME]
        if depth > 4:
            return '...'
        if d['tag'] == 0x01:              # array
            return self.array(a, depth) or 'array'
        if d['tag'] == 0x15:
            return 'func'
        if d['tag'] == 0x0f:
            return self.name(a, depth + 1) + '*'
        return '<anon %s>' % TAG.get(d['tag'], hex(d['tag']))

    def array(self, a, depth):
        b = a.get(AT_SUBSCR)
        if not b:
            return None
        # subscript data: FMT_FT_C_C (0) = fund type(2), lo(4), hi(4); FMT_ET (8) = element type attr
        i, dims, elem = 0, [], '?'
        while i < len(b):
            fmt = b[i]; i += 1
            if fmt == 0:
                lo, hi = struct.unpack_from('<Ii', b, i + 2); i += 10; dims.append(hi - lo + 1)
            elif fmt == 8:
                at, = struct.unpack_from('<H', b, i); i += 2
                form = at & 0xF
                if form == 5:
                    v, = struct.unpack_from('<H', b, i); i += 2
                elif form in (2, 6):
                    v, = struct.unpack_from('<I', b, i); i += 4
                elif form == 3:
                    ln, = struct.unpack_from('<H', b, i); v = b[i + 2:i + 2 + ln]; i += 2 + ln
                else:
                    break
                elem = self.name({at: v}, depth + 1)
            else:
                break
        return elem + ''.join('[%d]' % x for x in dims)


def classes(dies):
    """Pick one complete definition per class name (the largest with members)."""
    best = {}
    for off, d in dies.items():
        if d['tag'] not in (0x02, 0x13, 0x17) or AT_NAME not in d['a']:
            continue
        nm, kids = d['a'][AT_NAME], d['kids']
        if not kids:
            continue
        cur = best.get(nm)
        if cur is None or len(kids) > len(dies[cur]['kids']):
            best[nm] = off
    return best


def render(dies, T, off):
    d = dies[off]; a = d['a']
    out = ['%s %s  size 0x%X' % (TAG[d['tag']], a[AT_NAME], a.get(AT_BYTE_SIZE, 0))]
    for k in d['kids']:
        m = dies[k]; ma = m['a']
        o = loc_offset(ma[AT_LOCATION]) if AT_LOCATION in ma else None
        os_ = '+0x%03X' % o if o is not None else '     ?'
        if m['tag'] == 0x1c:
            out.append('  %s  : %s' % (os_, T.name(ma)))
        elif m['tag'] == 0x0d:
            bits = ''
            if AT_BIT_SIZE in ma:
                bits = ' :%d' % ma[AT_BIT_SIZE]
            out.append('  %s  %-28s %s%s' % (os_, T.name(ma), ma.get(AT_NAME, '?'), bits))
    return '\n'.join(out)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    data = open(sys.argv[1], 'rb').read()
    dies = parse(elf_section(data, '.debug'))
    T = Types(dies)
    best = classes(dies)
    args = sys.argv[2:]
    if args == ['--list']:
        for nm in sorted(best, key=str.lower):
            print('0x%05X  %s' % (dies[best[nm]]['a'].get(AT_BYTE_SIZE, 0), nm))
        return
    names = args or sorted(best, key=str.lower)
    for nm in names:
        if nm not in best:
            print('-- %s: not found\n' % nm)
            continue
        print(render(dies, T, best[nm]) + '\n')


if __name__ == '__main__':
    main()
