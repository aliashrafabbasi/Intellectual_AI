#!/usr/bin/env python3
"""
Remove baked-in checkerboard backgrounds from the logo PNG and write true RGBA transparency.

Usage (from repo root):
  python scripts/make_transparent_logo.py [input.png] [output.png]

Defaults: reads assets/logo_raw.png, writes frontend/public/logo.png
"""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


def background_like(r: int, g: int, b: int) -> bool:
    """Checkerboard neutrals — excludes bright white text and saturated logo colors."""
    mx = max(r, g, b)
    mn = min(r, g, b)
    lum = (r + g + b) / 3.0
    sat = (mx - mn) / max(mx, 1)

    if lum >= 135:
        return False
    if sat >= 0.14:
        return False
    if sat < 0.14 and 38 <= lum <= 122:
        return True
    return False


def crop_generator_footer(rgba: np.ndarray, min_row_content: int = 40) -> np.ndarray:
    """
    Crop away the bottom strip that holds generator badges (e.g. Gemini spark icon)
    and empty checker margin below the wordmark. Rows kept match real logo ink/text.
    """
    r = rgba[:, :, 0].astype(np.int16)
    g = rgba[:, :, 1].astype(np.int16)
    b = rgba[:, :, 2].astype(np.int16)
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    lum = (r + g + b) / 3.0
    sat = (mx - mn) / np.maximum(mx, 1)
    # Same rule as background_like: checker cells are "background"
    is_checker = (sat < 0.14) & (lum >= 38) & (lum <= 122)
    content_px = ~is_checker
    counts = content_px.sum(axis=1)
    idx = np.flatnonzero(counts >= min_row_content)
    if idx.size == 0:
        return rgba
    end = int(idx[-1]) + 1
    return rgba[:end, :, :]


def flood_transparent(rgba: np.ndarray) -> np.ndarray:
    h, w = rgba.shape[:2]
    rgb = rgba[:, :, :3].astype(np.int16)
    reachable = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    def push(y: int, x: int) -> None:
        if y < 0 or y >= h or x < 0 or x >= w or reachable[y, x]:
            return
        r, g, b = rgb[y, x]
        if not background_like(int(r), int(g), int(b)):
            return
        reachable[y, x] = True
        q.append((y, x))

    for x in range(w):
        push(0, x)
        push(h - 1, x)
    for y in range(h):
        push(y, 0)
        push(y, w - 1)

    while q:
        y, x = q.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            push(y + dy, x + dx)

    out = rgba.copy()
    out[:, :, 3] = np.where(reachable, 0, out[:, :, 3])
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_in = root / "assets" / "logo_raw.png"
    default_out = root / "frontend" / "public" / "logo.png"
    args = sys.argv[1:]
    src = Path(args[0]) if len(args) >= 1 else default_in
    dst = Path(args[1]) if len(args) >= 2 else default_out

    if not src.is_file():
        print(f"Input not found: {src}", file=sys.stderr)
        return 1

    img = Image.open(src).convert("RGBA")
    arr = np.array(img)
    arr = crop_generator_footer(arr)
    out = flood_transparent(arr)

    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out, "RGBA").save(dst, format="PNG", optimize=True)
    print(f"Wrote transparent PNG: {dst} ({out.shape[1]}×{out.shape[0]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
