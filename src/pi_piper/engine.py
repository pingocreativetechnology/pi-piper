# SPDX-License-Identifier: MIT
"""Runs one app at a time and owns the clock, MIDI port, and OSC feed."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from .apps import builtin_apps
from .clock import MusicalClock
from .midi import MidiHub, note_off
from .model import Button, ButtonEvent, EncoderEvent, PadEvent, PadPhase, StripEvent
from .osc import OscHub
from .sdk import App, Host
from .surface import Surface


class Engine:
    def __init__(
        self,
        device,
        apps: list[App] | None = None,
        midi: MidiHub | None = None,
        osc: OscHub | None = None,
        bpm: float = 120.0,
    ) -> None:
        self.device = device
        self.apps = apps if apps is not None else builtin_apps()
        self.midi = midi if midi is not None else MidiHub(backend="loopback")
        self.osc = osc if osc is not None else OscHub(enabled=False)
        self.clock = MusicalClock(bpm)
        self.surface = Surface()
        self.host = Host(self)
        self.shift = False
        self.gates: list[tuple[float, list[int]]] = []
        self._index = {app.id: app for app in self.apps}
        self.current = self.apps[0]
        self.current.on_enter(self.host)

    @property
    def performance_apps(self) -> list[App]:
        return [app for app in self.apps if app.id != "launcher"]

    def switch(self, app_id: str) -> None:
        nxt = self._index.get(app_id)
        if nxt is None or nxt is self.current:
            return
        self.stop_transport()
        self.current.on_exit(self.host)
        self.current = nxt
        self.osc.send("/pipiper/app", nxt.id)
        self.current.on_enter(self.host)

    def start_transport(self) -> None:
        if self.clock.running:
            return
        self.clock.reset()
        self.clock.running = True
        self.midi.send([0xFA])
        self.osc.send("/pipiper/transport", "start")

    def stop_transport(self) -> None:
        was = self.clock.running
        self.clock.running = False
        self.clock.reset()
        if was:
            self.midi.send([0xFC])
            self.osc.send("/pipiper/transport", "stop")
        self._silence()

    def _silence(self) -> None:
        pending = self.gates
        self.gates = []
        for _when, message in pending:
            self.midi.send(message)

    def tick(self, dt: float) -> None:
        self._flush_gates()
        clocks, steps = self.clock.advance(max(0.0, dt))
        for _ in range(clocks):
            self.midi.send([0xF8])
        for event in self.device.poll():
            self._dispatch(event)
        for message in self.midi.poll():
            self.current.on_midi(self.host, message)
        for step in steps:
            self.current.on_step(self.host, step)
        self.current.on_tick(self.host, dt)
        self._present()

    def _flush_gates(self) -> None:
        now = self.clock.time
        keep: list[tuple[float, list[int]]] = []
        for when, message in self.gates:
            if when <= now:
                self.midi.send(message)
            else:
                keep.append((when, message))
        self.gates = keep

    def _dispatch(self, event: object) -> None:
        if isinstance(event, ButtonEvent) and event.button is Button.shift:
            self.shift = event.down
        if (
            self.shift
            and isinstance(event, ButtonEvent)
            and event.button is Button.stop
            and event.down
            and self.current.id != "launcher"
        ):
            launcher = self._index.get("launcher")
            if launcher is not None:
                self.switch("launcher")
                return
        self._tap(event)
        self.current.on_event(self.host, event)

    def _tap(self, event: object) -> None:
        if isinstance(event, PadEvent):
            self.osc.send("/pipiper/pad", event.index, int(event.phase), int(event.value))
        elif isinstance(event, ButtonEvent):
            self.osc.send("/pipiper/button", event.button.name, 1 if event.down else 0)
        elif isinstance(event, EncoderEvent):
            self.osc.send("/pipiper/encoder", event.delta)
        elif isinstance(event, StripEvent):
            self.osc.send("/pipiper/strip", event.primary, event.secondary)

    def _present(self) -> None:
        self.surface.reset_lights()
        self.current.paint(self.host)
        if self.shift:
            self.surface.set_button(int(Button.shift), 3)
        self.device.push(self.surface)

    def snapshot(self) -> dict:
        return {
            "app": {"id": self.current.id, "title": self.current.title, "hint": self.current.hint},
            "apps": [{"id": app.id, "title": app.title, "hint": app.hint} for app in self.performance_apps],
            "tempo": self.clock.bpm,
            "running": self.clock.running,
            "step": self.clock.step,
            "swing": self.clock.swing,
            "shift": self.shift,
            "disclaimer": (
                "Pi Piper is compatible with Maschine hardware. It is not affiliated with, "
                "endorsed by, or sponsored by Native Instruments / inMusic Brands, Inc., "
                "and it is not made by them. Maschine and Native Instruments are trademarks "
                "of their respective owners, used only to identify compatible hardware."
            ),
            "pads": [
                {"index": i, "color": color, "brightness": level}
                for i, (color, level) in enumerate(self.surface.pads)
            ],
            "buttons": {
                Button(bit).name: level for bit, level in sorted(self.surface.buttons.items())
            },
            "strip": list(self.surface.strip),
            "screen": self.surface.screen.rows(),
            "midi": [" ".join(f"{byte:02X}" for byte in msg) for msg in self.midi.recent()],
        }


def load_app_file(path: str | Path) -> list[App]:
    """Load extra App subclasses from a Python file a performer wrote."""

    file = Path(path)
    spec = importlib.util.spec_from_file_location(f"pi_piper_user_{file.stem}", file)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import {file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    found: list[App] = []
    for value in vars(module).values():
        if isinstance(value, type) and issubclass(value, App) and value is not App:
            found.append(value())
    if not found:
        raise ImportError(f"{file} does not define an App subclass")
    return found


# Re-exported so user apps can `from pi_piper.sdk import App` only,
# while tests can silence a note without importing midi helpers twice.
__all__ = ["Engine", "load_app_file", "note_off", "PadPhase"]
