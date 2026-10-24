#!/usr/bin/env python3
"""Convert the BMPs OncoPattern exports into PNGs for previewing."""
import struct, zlib, sys, os

def convert(src, dst):
    d = open(src, 'rb').read()
    w = struct.unpack('<i', d[18:22])[0]
    h = struct.unpack('<i', d[22:26])[0]
    off = struct.unpack('<I', d[10:14])[0]
    stride = (w * 3 + 3) // 4 * 4
    rows = []
    for y in range(h - 1, -1, -1):
        r = d[off + y * stride: off + y * stride + w * 3]
        rows.append(b'\x00' + bytes(b for i in range(0, w * 3, 3) for b in (r[i+2], r[i+1], r[i])))
    raw = b''.join(rows)
    def chunk(t, data):
        c = t + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c))
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 6))
           + chunk(b'IEND', b''))
    open(dst, 'wb').write(png)
    return w, h

if __name__ == '__main__':
    for f in sys.argv[1:]:
        out = os.path.splitext(f)[0] + '.png'
        print(f, '->', out, convert(f, out))
