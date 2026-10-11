"""Resize the provided indexed PNG app icon with only the Python standard library.

The preview supplied to ARVEXQ is indexed PNG; preserve its brand colors and
produce dimensionally correct iOS/PWA assets without introducing a deployment
dependency (Pillow is intentionally not needed in the static build).
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def resize_indexed_png(path: Path, size: int) -> bytes:
    data = Path(path).read_bytes()
    if not data.startswith(SIGNATURE):
        raise ValueError("Expected PNG source")
    at, compressed, palette, width, height, depth = 8, bytearray(), b"", 0, 0, 0
    while at + 12 <= len(data):
        length = struct.unpack(">I", data[at:at + 4])[0]
        kind = data[at + 4:at + 8]
        raw = data[at + 8:at + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", raw)
            if color_type != 3 or depth not in (1, 2, 4, 8) or interlace:
                raise ValueError("Indexed, noninterlaced PNG required")
        elif kind == b"PLTE":
            palette = raw
        elif kind == b"IDAT":
            compressed.extend(raw)
        elif kind == b"IEND":
            break
        at += length + 12
    if not width or not height or not palette or not 16 <= size <= 1024:
        raise ValueError("Invalid dimensions or palette")
    pixel_data = zlib.decompress(bytes(compressed))
    row_len = (width * depth + 7) // 8
    prev = bytearray(row_len)
    pixels = []
    pos = 0
    for _ in range(height):
        mode = pixel_data[pos]
        pos += 1
        encoded = pixel_data[pos:pos + row_len]
        pos += row_len
        row = bytearray(row_len)
        for i, value in enumerate(encoded):
            left = row[i - 1] if i else 0
            up = prev[i]
            upper_left = prev[i - 1] if i else 0
            if mode == 0:
                delta = 0
            elif mode == 1:
                delta = left
            elif mode == 2:
                delta = up
            elif mode == 3:
                delta = (left + up) // 2
            elif mode == 4:
                predictor = left + up - upper_left
                distances = (abs(predictor - left), abs(predictor - up), abs(predictor - upper_left))
                delta = (left, up, upper_left)[distances.index(min(distances))]
            else:
                raise ValueError("Unsupported PNG row filter")
            row[i] = (value + delta) & 255
        for x in range(width):
            shift = 8 - depth - (x * depth) % 8
            index = (row[(x * depth) // 8] >> shift) & ((1 << depth) - 1)
            j = index * 3
            if j + 3 > len(palette):
                raise ValueError("Palette index out of range")
            pixels.append(tuple(palette[j:j + 3]))
        prev = row

    # Bilinear interpolation of source colors; no external imaging package.
    result = bytearray()
    for y in range(size):
        fy = max(0.0, min(height - 1.0, (y + .5) * height / size - .5))
        y0, y1 = int(fy), min(height - 1, int(fy) + 1)
        wy = fy - y0
        row = bytearray([0])
        for x in range(size):
            fx = max(0.0, min(width - 1.0, (x + .5) * width / size - .5))
            x0, x1 = int(fx), min(width - 1, int(fx) + 1)
            wx = fx - x0
            a, b = pixels[y0 * width + x0], pixels[y0 * width + x1]
            c, d = pixels[y1 * width + x0], pixels[y1 * width + x1]
            row.extend(max(0, min(255, round((a[i] * (1 - wx) + b[i] * wx) * (1 - wy)
                + (c[i] * (1 - wx) + d[i] * wx) * wy))) for i in range(3))
        result.extend(row)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return SIGNATURE + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(result, 6)) + _chunk(b"IEND", b"")
