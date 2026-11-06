# SPDX-License-Identifier: MIT
"""Shared names for controls, colours, and input events.

Button numbers match the bit positions used by the Mikro MK3 status report.
Colour numbers match the pad palette indices used by that controller's LED
report. Both are recorded in docs/protocol.md with their sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Button(IntEnum):
    """Physical keys. ``wordmark`` is the upper-left key printed with the
    product name; Pi Piper does not use that name as an API identifier."""

    wordmark = 0
    star = 1
    browse = 2
    volume = 3
    swing = 4
    tempo = 5
    plugin = 6
    sampling = 7
    left = 8
    right = 9
    pitch = 10
    mod = 11
    perform = 12
    notes = 13
    group = 14
    auto = 15
    lock = 16
    note_repeat = 17
    restart = 18
    erase = 19
    tap = 20
    follow = 21
    play = 22
    rec = 23
    stop = 24
    shift = 25
    fixed_vel = 26
    pad_mode = 27
    keyboard = 28
    chords = 29
    step = 30
    scene = 31
    pattern = 32
    events = 33
    variation = 34
    duplicate = 35
    select = 36
    solo = 37
    mute = 38
    encoder_press = 39
    encoder_touch = 40


# Keys that have no lamp of their own.
UNLIT_BUTTONS = frozenset({Button.encoder_press, Button.encoder_touch})


class PadPhase(IntEnum):
    """Pad report event codes, already shifted down from the high nibble."""

    TOUCH = 0
    STRIKE = 1
    UNTOUCH = 2
    RELEASE = 3
    PRESSURE = 4


class PadColor(IntEnum):
    OFF = 0
    RED = 1
    ORANGE = 2
    LIGHT_ORANGE = 3
    WARM_YELLOW = 4
    YELLOW = 5
    LIME = 6
    GREEN = 7
    MINT = 8
    CYAN = 9
    TURQUOISE = 10
    BLUE = 11
    PLUM = 12
    VIOLET = 13
    PURPLE = 14
    MAGENTA = 15
    FUCHSIA = 16
    WHITE = 17


COLOR_NAMES = {color.name.lower(): color for color in PadColor}
COLOR_NAMES["light_orange"] = PadColor.LIGHT_ORANGE
COLOR_NAMES["warm_yellow"] = PadColor.WARM_YELLOW


def color_id(name: str | int | PadColor) -> int:
    if isinstance(name, PadColor):
        return int(name)
    if isinstance(name, int):
        return name
    key = name.strip().lower().replace(" ", "_").replace("-", "_")
    try:
        return int(COLOR_NAMES[key])
    except KeyError as exc:
        known = ", ".join(sorted(COLOR_NAMES))
        raise ValueError(f"unknown pad colour {name!r}; expected one of {known}") from exc


@dataclass(frozen=True)
class ButtonEvent:
    button: Button
    down: bool


@dataclass(frozen=True)
class PadEvent:
    index: int
    phase: PadPhase
    value: int


@dataclass(frozen=True)
class EncoderEvent:
    delta: int
    position: int


@dataclass(frozen=True)
class StripEvent:
    primary: int
    secondary: int
    timestamp_ms: int


InputEvent = ButtonEvent | PadEvent | EncoderEvent | StripEvent


def scale_12bit(value: int) -> int:
    """Map a 0..4095 pad reading onto a MIDI 0..127 value.

    A non-zero reading never collapses to zero, so a very soft strike still
    produces a velocity of 1.
    """

    value = max(0, min(4095, int(value)))
    scaled = (value * 127 + 2047) // 4095
    if value > 0 and scaled == 0:
        return 1
    return scaled
