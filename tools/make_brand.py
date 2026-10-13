"""Sinh brand image cho integration (icon.png 256, icon@2x.png 512, logo.png 512).

Máy này KHÔNG có PIL/Pillow nên PNG được ghi trực tiếp bằng stdlib (zlib + struct).
Thiết kế: nền gradient xanh nước bo góc + giọt nước trắng.

Dùng: python tools/make_brand.py
"""

from __future__ import annotations

import pathlib
import struct
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = (
    pathlib.Path(__file__).resolve().parent.parent
    / "custom_components"
    / "karofi_ha"
    / "brand"
)
TOP = (0, 105, 160)  # #0069A0
BOTTOM = (0, 188, 212)  # #00BCD4
# Giọt nước = đường tròn đáy + tam giác nhọn phía trên (2 cạnh tiếp tuyến đường tròn)
DROP_C, DROP_R, DROP_TIP = (0.5, 0.60), 0.24, (0.5, 0.13)


def inside_drop(x: float, y: float) -> bool:
    (cx, cy), r, (tx, ty) = DROP_C, DROP_R, DROP_TIP
    if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
        return True
    d = cy - ty  # khoảng cách đỉnh → tâm
    # điểm tiếp tuyến: y_t = cy - r²/d; nửa bề rộng tại đó = r·sqrt(1 - (r/d)²)
    yt = cy - r * r / d
    half = r * (1 - (r / d) ** 2) ** 0.5
    if not ty <= y <= yt:
        return False
    return abs(x - tx) <= half * (y - ty) / (yt - ty)


def render(size: int) -> bytes:
    radius = size * 0.22
    px = bytearray()
    for y in range(size):
        px.append(0)  # filter type 0 mỗi scanline
        t = y / (size - 1)
        bg = tuple(round(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
        for x in range(size):
            cx, cy = min(x, size - 1 - x), min(y, size - 1 - y)
            if cx < radius and cy < radius:
                dx, dy = radius - cx, radius - cy
                if dx * dx + dy * dy > radius * radius:
                    px.extend((0, 0, 0, 0))
                    continue
            px.extend(
                (255, 255, 255, 255) if inside_drop(x / size, y / size) else (*bg, 255)
            )
    return bytes(px)


def write_png(path: pathlib.Path, size: int) -> None:
    raw = render(size)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    print(f"  {path.name:14} {size}x{size}  {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Sinh brand image vào {OUT}:")
    write_png(OUT / "icon.png", 256)
    write_png(OUT / "icon@2x.png", 512)
    write_png(OUT / "logo.png", 512)
    print("Lưu ý: HA chỉ hiển thị brand mới SAU KHI RESTART.")
