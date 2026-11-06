# SPDX-License-Identifier: MIT
"""Monochrome 128×32 surface used by every built-in app.

MK3 colour panels are larger. Apps draw here, and the MK3 driver scales this
buffer onto the colour panels so the same apps run on either controller.
"""

from __future__ import annotations

from .font import FONT, GLYPH_H, GLYPH_W
from .protocol import SCREEN_H, SCREEN_W, blank_screen, screen_pixel, screen_reports, set_screen_pixel


class MonoScreen:
    width = SCREEN_W
    height = SCREEN_H

    def __init__(self) -> None:
        self.buffer = blank_screen()

    def clear(self) -> None:
        self.buffer = blank_screen()

    def pixel(self, x: int, y: int, lit: bool = True) -> None:
        set_screen_pixel(self.buffer, x, y, lit)

    def get(self, x: int, y: int) -> bool:
        if not 0 <= x < SCREEN_W or not 0 <= y < SCREEN_H:
            return False
        return screen_pixel(self.buffer, x, y)

    def text(self, x: int, y: int, message: str) -> None:
        cursor = x
        for char in message.upper():
            glyph = FONT.get(char, FONT[" "])
            for row, bits in enumerate(glyph):
                for col in range(GLYPH_W):
                    if bits & (1 << (GLYPH_W - 1 - col)):
                        self.pixel(cursor + col, y + row, True)
            cursor += GLYPH_W + 1
            if cursor >= SCREEN_W:
                break

    def rows(self) -> list[str]:
        lines: list[str] = []
        for y in range(SCREEN_H):
            lines.append("".join("1" if self.get(x, y) else "0" for x in range(SCREEN_W)))
        return lines

    def reports(self) -> tuple[bytes, bytes]:
        return screen_reports(bytes(self.buffer))


def note_name(note: int) -> str:
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    note = int(note)
    octave = note // 12 - 1
    return f"{names[note % 12]}{octave}"
