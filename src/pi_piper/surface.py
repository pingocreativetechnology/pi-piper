# SPDX-License-Identifier: MIT
"""The lamps and pictures an app is currently asking the hardware to show."""

from __future__ import annotations

from .model import PadColor, color_id
from .protocol import PAD_COUNT, STRIP_LED_COUNT
from .screen import MonoScreen


class Surface:
    def __init__(self) -> None:
        self.pads: list[tuple[int, int]] = [(0, 0)] * PAD_COUNT
        self.buttons: dict[int, int] = {}
        self.strip: list[int] = [0] * STRIP_LED_COUNT
        self.screen = MonoScreen()

    def reset_lights(self) -> None:
        self.pads = [(0, 0)] * PAD_COUNT
        self.buttons = {}
        self.strip = [0] * STRIP_LED_COUNT
        self.screen.clear()

    def set_pad(self, index: int, color: str | int | PadColor, brightness: int) -> None:
        if not 0 <= index < PAD_COUNT:
            return
        level = max(0, min(3, int(brightness)))
        self.pads[index] = (color_id(color), level)

    def set_button(self, button: int, level: int) -> None:
        self.buttons[int(button)] = max(0, min(3, int(level)))

    def set_strip(self, values: list[int]) -> None:
        self.strip = [max(0, min(3, int(v))) for v in values[:STRIP_LED_COUNT]]
        if len(self.strip) < STRIP_LED_COUNT:
            self.strip.extend([0] * (STRIP_LED_COUNT - len(self.strip)))

    def fill_strip(self, fraction: float) -> None:
        fraction = max(0.0, min(1.0, fraction))
        lit = int(round(fraction * STRIP_LED_COUNT))
        self.strip = [2 if i < lit else 0 for i in range(STRIP_LED_COUNT)]
