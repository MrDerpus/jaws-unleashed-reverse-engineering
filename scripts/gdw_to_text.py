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

"""Rewrite a binary .GDW level in the GDED *text* format, using a read trace from the game.

Jaws.exe's GDFile can read levels in a text format ("GDED TEXT FORMAT, VERSION ..."), the format the
Game World Builder editor could save; nothing in the game writes it (docs/exe_analysis.md, "GDED text
format"). Every value in a text level must be written in the syntax of the reader that loads it (int,
real, string, vector, ...), and a binary GDW does not say which reader reads which bytes. The mod's
GDFile trace (mod/src/gdtrace.h) records, for each raw read, which reader made it, so this script can
replay a real load of the same file and write each value the way that reader expects.

Text syntax (taken from the readers' text branches, Jaws.exe 0x6BC240-0x6C08A0):
  Chunk: TAGN {            chunk start (ReadChunkID)      }   chunk end
  INT: -5                  ReadInt (atoi)                 SHORT: 3        ReadShort
  REAL: 1.5                ReadReal (atof)                SET: ACD        ReadSet (bit n = 'A'+n, '-' = 0)
  CLASSID: 36-2-1          ReadClassID (bits 0-11, 12-23, 24-31)
  ResID: GTEX              ReadResID (4 characters, 0000 = 0)
  STRING: "text"           ReadString ('-' = none)
  VECTOR: x, y, z          COLOR: r, g, b, a              MATRIX: 12 values
  BUFFER: 0a ff ...        ReadMemBuffer (one hex token per byte)
Vectors of ints/reals/shorts/texture coordinates are read one value per line in text mode.

Not supported in text by the game: the 24-byte names in FDIR are read raw, so they are written as raw
bytes. The embedded loading-screen sub-archives (bytes after ENDF) are appended unchanged and the FDIR
offsets (and FSIZ) are patched to their new positions.

Usage:
  python3 gdw_to_text.py LEVEL.GDW jaws_gdfile_trace.bin OUT.GDW
"""
import struct
import sys
from collections import Counter

# Jaws.exe GDFile readers: [start, end) -> kind
READERS = [
    (0x6BBAC0, 0x6BC240, 'header'), (0x6BC240, 0x6BC4A0, 'short'), (0x6BC4A0, 0x6BC570, 'shortvect'),
    (0x6BC570, 0x6BC7D0, 'int'), (0x6BC7D0, 0x6BC8A0, 'intvect'), (0x6BC8A0, 0x6BCCB0, 'classid'),
    (0x6BCCB0, 0x6BCF80, 'resid'), (0x6BCFA0, 0x6BD200, 'real'), (0x6BD200, 0x6BD2D0, 'realvect'),
    (0x6BD2D0, 0x6BD820, 'color'), (0x6BD840, 0x6BDE30, 'vertcolor'), (0x6BDE30, 0x6BDF40, 'texpos'),
    (0x6BDF40, 0x6BE060, 'vertpos'), (0x6BE060, 0x6BE180, 'normvect'), (0x6BE180, 0x6BE260, 'vectors'),
    (0x6BE260, 0x6BE6A0, 'vector'), (0x6BE6A0, 0x6BE7A0, 'matrices'), (0x6BE7A0, 0x6BF3C0, 'matrix'),
    (0x6BF3C0, 0x6BF720, 'string'), (0x6BF720, 0x6BFA50, 'stringbuf'), (0x6BFA50, 0x6BFCD0, 'set'),
    (0x6BFCE0, 0x6BFEF0, 'buffer'), (0x6BFF10, 0x6C00A0, 'header'), (0x6C0310, 0x6C08A0, 'chunk'),
    (0x6C08A0, 0x6C0930, 'skip'), (0x6C3D90, 0x6C3F20, 'fdir_raw'),
]
RET_CHUNK_DECIDE = 0x6C0375     # Tell in ReadChunkID whose result decides "end of chunk"
RET_CHUNK_TAG, RET_CHUNK_SIZE = 0x6C03D1, 0x6C03E7
RET_SKIP_SEEK = 0x6C08C2        # skip-unknown-chunk seeks to the chunk end

NUMW = 12                       # fixed width of patched numbers (FDIR offsets, FSIZ)


def kind_of(ret):
    for a, b, k in READERS:
        if a <= ret < b:
            return k
    return None


NONFINITE = [0]


def real(f):
    # NaN/Inf cannot be written as text (atof). In stock levels they only occur as uninitialised
    # padding, e.g. the weights of unused bone slots (index -1) in WGHT; they are written as 0.
    if f != f or f in (float('inf'), float('-inf')):
        NONFINITE[0] += 1
        return '0'
    return '%.9g' % f


def load_trace(path):
    data = open(path, 'rb').read()
    return [struct.unpack_from('<6I', data, i) for i in range(0, len(data) - 23, 24)]


def sessions(events):
    """Split into loads: a header read at position 0 starts a new load on that file object."""
    starts, seen_other = [], {}
    for i, (kind, f, ret, pos, a, b) in enumerate(events):
        is_hdr = kind & 0xFF == 0 and kind_of(ret) == 'header'
        if is_hdr and pos == 0 and seen_other.get(f, True):
            starts.append((i, f))
            seen_other[f] = False
        elif not is_hdr:
            seen_other[f] = True
    res = []
    for j, (i, f) in enumerate(starts):
        end = next((i2 for i2, f2 in starts[j + 1:] if f2 == f), len(events))
        res.append((f, i, end))
    return res


def top_chunks(gdw):
    pos, out = 0x2C, {}
    while pos + 8 <= len(gdw):
        tag, size = gdw[pos:pos + 4], struct.unpack_from('<I', gdw, pos + 4)[0]
        out.setdefault(tag, (pos, size))
        if tag == b'ENDF':
            out[b'_end'] = (pos + 8 + size, 0)
            break
        pos = (pos + 8 + size + 3) & ~3
    return out


class Writer:
    def __init__(self):
        self.parts = []
        self.depth = 0
        self.size = 0
        self.patches = []       # (offset in output, value function)

    def raw(self, b):
        self.parts.append(b)
        self.size += len(b)

    def line(self, s):
        self.raw(('  ' * self.depth + s + '\n').encode('latin-1'))

    def patched(self, label, fn):
        pre = ('  ' * self.depth + label + ': ').encode()
        self.raw(pre)
        self.patches.append((self.size, fn))
        self.raw(b'0' * NUMW + b'\n')


def convert(gdw, events, out_path):
    tops = top_chunks(gdw)
    end_of_level = tops[b'_end'][0]
    tail = gdw[end_of_level:]
    fdir_fields = set()
    fsiz_field = None
    if b'FDIR' in tops:
        p, size = tops[b'FDIR']
        count = struct.unpack_from('<I', gdw, p + 12)[0]
        fdir_fields = {p + 16 + 32 * i for i in range(count)}
    if b'FSIZ' in tops:
        fsiz_field = tops[b'FSIZ'][0] + 8

    w = Writer()
    stack = []                  # chunk end offsets (binary)
    pending_chunk = None        # 'tag' / 'size' expected next
    tag = None
    string_len = {}             # kind -> pending data length
    acc_kind, acc = None, b''   # vector/matrix read in several 4-byte parts
    stats = Counter()
    header_done = False
    tail_start = []             # filled after writing; used by patches

    def u32(b, o=0):
        return struct.unpack_from('<I', b, o)[0]

    for kind, f, ret, pos, a, b in events:
        op = kind & 0xFF
        k = kind_of(ret)
        if op == 2:                                   # Tell
            if ret == RET_CHUNK_DECIDE:
                if stack and pos >= stack[-1] - 3:
                    stack.pop()
                    w.depth -= 1
                    w.line('}')
                    stats['chunk_end'] += 1
                else:
                    pending_chunk = 'tag'
            continue
        if op == 1:                                   # Seek
            if ret == RET_SKIP_SEEK:
                stack.pop()
                w.depth -= 1
                w.line('}')
                stats['chunk_skipped'] += 1
            continue
        n = a
        data = gdw[pos:pos + n]
        if len(data) != n:
            raise SystemExit('trace read past end of file at %#x (wrong GDW for this trace?)' % pos)
        stats[k or 'unknown'] += 1
        if k == 'header':
            if not header_done:
                pre = gdw[:0x2C].rstrip(b'\0')
                if not pre.startswith(b'GDED BINARY FORMAT'):
                    raise SystemExit('not a binary GDED file')
                w.raw(pre.replace(b'BINARY', b'TEXT', 1))
                header_done = True
            continue
        if k == 'chunk':
            if ret == RET_CHUNK_TAG and pending_chunk == 'tag':
                tag = data
                if not all(0x21 <= c < 0x7F for c in tag):
                    raise SystemExit('chunk tag %r at %#x cannot be written as text' % (tag, pos))
                pending_chunk = 'size'
            elif ret == RET_CHUNK_SIZE and pending_chunk == 'size':
                stack.append(pos + 4 + u32(data))
                w.line('Chunk: %s {' % tag.decode())
                w.depth += 1
                pending_chunk = None
                if tag == b'ENDF':
                    break           # the loader stops here
            else:
                raise SystemExit('unexpected chunk read at %#x (ret %#x)' % (pos, ret))
            continue
        if k in ('vector', 'matrix'):
            need = 12 if k == 'vector' else 48
            if acc_kind != k:
                acc_kind, acc = k, b''
            acc += data
            if len(acc) < need:
                continue
            vals = struct.unpack('<%df' % (need // 4), acc)
            w.line('%s: %s' % (k.upper(), ', '.join(real(v) for v in vals)))
            acc_kind, acc = None, b''
            continue
        if acc_kind:
            raise SystemExit('incomplete %s before %#x' % (acc_kind, pos))
        if k in ('string', 'stringbuf'):
            L = string_len.get(k)
            if L is not None and n == L:
                s = data.split(b'\0', 1)[0]
                if b'"' in s or len(s) > 990 or s[:1].isspace():
                    raise SystemExit('string %r at %#x cannot be written as text' % (s[:40], pos))
                w.line('STRING: "%s"' % s.decode('latin-1'))
                del string_len[k]
            else:
                if n != 4:
                    raise SystemExit('unexpected string read of %d bytes at %#x' % (n, pos))
                L = struct.unpack('<i', data)[0]
                if L < 1:
                    w.line('STRING: -')
                    string_len.pop(k, None)
                else:
                    string_len[k] = L
            continue
        if k == 'int':
            v = struct.unpack('<i', data)[0]
            if pos in fdir_fields:
                old = v
                w.patched('INT', lambda old=old: old - end_of_level + tail_start[0])
            elif pos == fsiz_field:
                w.patched('INT', lambda: tail_start[0] + len(tail))
            else:
                w.line('INT: %d' % v)
        elif k == 'short':
            w.line('SHORT: %d' % struct.unpack('<h', data)[0])
        elif k == 'real':
            w.line('REAL: ' + real(struct.unpack('<f', data)[0]))
        elif k == 'classid':
            v = u32(data)
            w.line('CLASSID: %d-%d-%d' % (v & 0xFFF, (v >> 12) & 0xFFF, v >> 24))
        elif k == 'resid':
            if data == b'\0\0\0\0':
                w.line('ResID: 0000')
            elif all(0x21 <= c < 0x7F for c in data):
                w.line('ResID: ' + data.decode())
            else:
                raise SystemExit('resource ID %r at %#x cannot be written as text' % (data, pos))
        elif k == 'set':
            v = u32(data)
            w.line('SET: ' + (''.join(chr(0x41 + i) for i in range(32) if v >> i & 1) or '-'))
        elif k == 'intvect':
            for (v,) in struct.iter_unpack('<i', data):
                w.line('INT: %d' % v)
        elif k == 'shortvect':
            for (v,) in struct.iter_unpack('<h', data):
                w.line('SHORT: %d' % v)
        elif k in ('realvect', 'texpos'):
            for (v,) in struct.iter_unpack('<f', data):
                w.line('REAL: ' + real(v))
        elif k in ('vertpos', 'normvect', 'vectors'):
            for v in struct.iter_unpack('<3f', data):
                w.line('VECTOR: ' + ', '.join(real(x) for x in v))
        elif k == 'matrices':
            for v in struct.iter_unpack('<12f', data):
                w.line('MATRIX: ' + ', '.join(real(x) for x in v))
        elif k in ('color', 'vertcolor'):
            for v in struct.iter_unpack('<4f', data):
                w.line('COLOR: ' + ', '.join(real(x) for x in v))
        elif k == 'buffer':
            w.line('BUFFER:')
            ind = '  ' * (w.depth + 1)
            for i in range(0, len(data), 48):
                w.raw((ind + data[i:i + 48].hex(' ') + '\n').encode())
        elif k == 'fdir_raw':
            # read raw by the FDIR loader: bytes go straight after the previous value's newline
            w.raw(data)
            w.raw(b'\n')
        else:
            raise SystemExit('read of %d bytes at %#x by unknown code (return address %#x)' % (n, pos, ret))

    if len(stack) > 1:
        print('warning: %d chunks still open at the end of the trace' % (len(stack) - 1))
    while stack:
        stack.pop()
        w.depth -= 1
        w.line('}')
    tail_start.append(w.size)
    body = bytearray(b''.join(w.parts))
    for off, fn in w.patches:
        v = fn()
        s = ('%0*d' % (NUMW, v)).encode()
        if len(s) != NUMW:
            raise SystemExit('patched value too large')
        body[off:off + NUMW] = s
    with open(out_path, 'wb') as fo:
        fo.write(body)
        fo.write(tail)
    return stats, len(body), len(tail)


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    gdw = open(sys.argv[1], 'rb').read()
    events = load_trace(sys.argv[2])
    chosen = None
    endf = top_chunks(gdw)[b'ENDF'][0]
    for f, s, e in sessions(events):
        ev = [x for x in events[s:e] if x[1] == f]
        tags = [x[3] for x in ev if x[0] & 0xFF == 0 and x[2] == RET_CHUNK_TAG]
        # the right load reads this file's ENDF at its offset, and every chunk tag it reads is text
        if endf in tags and all(p + 4 <= len(gdw) and all(0x21 <= c < 0x7F for c in gdw[p:p + 4]) for p in tags):
            chosen = ev
            print('using load at trace record %d (%d events)' % (s, len(ev)))
            break
    if chosen is None:
        raise SystemExit('no load of this file found in the trace')
    stats, nb, nt = convert(gdw, chosen, sys.argv[3])
    print('wrote %s: %d bytes text + %d bytes appended sub-archives' % (sys.argv[3], nb, nt))
    if NONFINITE[0]:
        print('  %d NaN/Inf floats written as 0' % NONFINITE[0])
    for k, v in sorted(stats.items()):
        print('  %-14s %d' % (k, v))


if __name__ == '__main__':
    main()
