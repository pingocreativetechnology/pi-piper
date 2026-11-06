# SPDX-License-Identifier: MIT
"""A plain terminal picture of the 16 pads. Useful over SSH, with no browser."""

from __future__ import annotations

import curses

from .engine import Engine
from .model import Button, ButtonEvent, EncoderEvent, PadColor, PadEvent, PadPhase

# Keyboard: top row of pads is 1 2 3 4, matching the hardware's top row
# (HID indices 0..3). The bottom letter row is z x c v.
_PAD_KEYS = {
    ord("1"): 0, ord("2"): 1, ord("3"): 2, ord("4"): 3,
    ord("q"): 4, ord("w"): 5, ord("e"): 6, ord("r"): 7,
    ord("a"): 8, ord("s"): 9, ord("d"): 10, ord("f"): 11,
    ord("z"): 12, ord("x"): 13, ord("c"): 14, ord("v"): 15,
}
_BUTTON_KEYS = {
    ord(" "): Button.play,
    ord("p"): Button.play,
    ord("."): Button.stop,
    ord("m"): Button.mute,
    ord("["): Button.left,
    ord("]"): Button.right,
    ord("\n"): Button.encoder_press,
    ord("\t"): Button.shift,
}


def run_tui(engine: Engine) -> None:
    curses.wrapper(lambda stdscr: _loop(stdscr, engine))


def _loop(stdscr, engine: Engine) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(20)
    engine.tick(0.0)
    while True:
        key = stdscr.getch()
        if key in (ord("Q"), 27):
            return
        if key == curses.KEY_RIGHT:
            engine.device.inject(EncoderEvent(1, 0))
        elif key == curses.KEY_LEFT:
            engine.device.inject(EncoderEvent(-1, 0))
        elif key in _PAD_KEYS:
            index = _PAD_KEYS[key]
            engine.device.inject(PadEvent(index, PadPhase.STRIKE, 2800))
            engine.device.inject(PadEvent(index, PadPhase.RELEASE, 0))
        elif key in _BUTTON_KEYS:
            button = _BUTTON_KEYS[key]
            engine.device.inject(ButtonEvent(button, True))
            engine.device.inject(ButtonEvent(button, False))
        engine.tick(0.02)
        _draw(stdscr, engine)


def _draw(stdscr, engine: Engine) -> None:
    stdscr.erase()
    snap = engine.snapshot()
    stdscr.addstr(0, 0, "PI PIPER  " + snap["app"]["title"] + f"   {int(snap['tempo'])} bpm")
    stdscr.addstr(1, 0, "not affiliated with or endorsed by Native Instruments")
    stdscr.addstr(2, 0, snap["app"]["hint"][:78])
    names = {color.value: color.name for color in PadColor}
    for index, pad in enumerate(snap["pads"]):
        row, col = divmod(index, 4)
        label = names.get(pad["color"], "?")[:4]
        cell = f"{index:02d}{label[:3]:<3}{pad['brightness']}"
        stdscr.addstr(4 + row, col * 12, cell)
    y = 9
    for line in snap["screen"][0:32:8]:
        chars = []
        for x in range(0, 128, 2):
            chars.append("#" if line[x] == "1" else " ")
        try:
            stdscr.addstr(y, 0, "".join(chars)[:78])
        except curses.error:
            pass
        y += 1
    stdscr.addstr(14, 0, "pads 1234/qwer/asdf/zxcv  arrows=encoder  enter=press  space=play  q=quit")
    stdscr.refresh()
