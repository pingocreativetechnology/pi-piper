# SPDX-License-Identifier: MIT
"""The small surface a performance app is written against."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .model import Button, PadColor
from .screen import MonoScreen

if TYPE_CHECKING:
    from .engine import Engine


class App:
    """Subclass this. Register an instance with the engine.

    ``paint`` is called after every event and tick. Draw the whole picture
    each time; the engine clears the lamps first.
    """

    id = "app"
    title = "App"
    hint = ""

    def on_enter(self, host: "Host") -> None:
        return None

    def on_exit(self, host: "Host") -> None:
        return None

    def on_event(self, host: "Host", event: object) -> None:
        return None

    def on_tick(self, host: "Host", dt: float) -> None:
        return None

    def on_step(self, host: "Host", step: int) -> None:
        return None

    def on_midi(self, host: "Host", message: list[int]) -> None:
        return None

    def paint(self, host: "Host") -> None:
        return None


class Host:
    """Capabilities an app is allowed to use. There is no USB handle here."""

    def __init__(self, engine: "Engine") -> None:
        self.engine = engine

    @property
    def screen(self) -> MonoScreen:
        return self.engine.surface.screen

    @property
    def tempo(self) -> float:
        return self.engine.clock.bpm

    def set_tempo(self, bpm: float) -> None:
        self.engine.clock.set_bpm(bpm)
        self.engine.osc.send("/pipiper/tempo", float(self.engine.clock.bpm))

    def pad(self, index: int, color: str | int | PadColor, brightness: int = 2) -> None:
        self.engine.surface.set_pad(index, color, brightness)

    def light(self, button: Button | int, level: int) -> None:
        self.engine.surface.set_button(int(button), level)

    def strip(self, fraction: float) -> None:
        self.engine.surface.fill_strip(fraction)

    def midi(self, message: list[int]) -> None:
        self.engine.midi.send(message)
        status = message[0] if message else 0
        kind = status & 0xF0
        if kind in (0x90, 0x80) and len(message) >= 3:
            velocity = 0 if kind == 0x80 or message[2] == 0 else message[2]
            channel = status & 0x0F
            self.engine.osc.send("/pipiper/note", channel, message[1], velocity)

    def note(self, channel: int, note: int, velocity: int, gate: float = 0.08) -> None:
        from .midi import note_off, note_on

        self.midi(note_on(channel, note, velocity))
        if velocity > 0 and gate > 0:
            when = self.engine.clock.time + gate
            self.engine.gates.append((when, note_off(channel, note)))

    def osc(self, address: str, *args: object) -> None:
        self.engine.osc.send(address, *args)

    def switch(self, app_id: str) -> None:
        self.engine.switch(app_id)

    @property
    def shift(self) -> bool:
        return self.engine.shift

    @property
    def apps(self) -> list[App]:
        return self.engine.performance_apps
