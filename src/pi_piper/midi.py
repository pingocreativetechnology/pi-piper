# SPDX-License-Identifier: MIT
"""Virtual MIDI port.

``python-rtmidi`` opens an ALSA or CoreMIDI port named Pi Piper when it is
installed and the platform allows virtual ports. Otherwise messages stay in
an in-process loopback, which is what the simulator and the tests use.
"""

from __future__ import annotations

from collections import deque


def note_on(channel: int, note: int, velocity: int) -> list[int]:
    return [0x90 | (channel & 0x0F), note & 0x7F, max(0, min(127, velocity))]


def note_off(channel: int, note: int) -> list[int]:
    return [0x80 | (channel & 0x0F), note & 0x7F, 0]


def control_change(channel: int, controller: int, value: int) -> list[int]:
    return [0xB0 | (channel & 0x0F), controller & 0x7F, max(0, min(127, value))]


def poly_pressure(channel: int, note: int, value: int) -> list[int]:
    return [0xA0 | (channel & 0x0F), note & 0x7F, max(0, min(127, value))]


class MidiHub:
    def __init__(self, backend: str = "auto", port_name: str = "Pi Piper") -> None:
        self.port_name = port_name
        self.backend = "loopback"
        self.outgoing: deque[list[int]] = deque(maxlen=64)
        self.incoming: deque[list[int]] = deque(maxlen=64)
        self._rt_out = None
        self._rt_in = None
        if backend in ("auto", "rtmidi"):
            self._open_rtmidi()
            if backend == "rtmidi" and self._rt_out is None:
                self.backend = "loopback"

    def _open_rtmidi(self) -> None:
        try:
            import rtmidi
        except ImportError:
            return
        try:
            port = rtmidi.MidiOut()
            port.open_virtual_port(self.port_name)
            self._rt_out = port
            self.backend = "rtmidi"
        except Exception:
            self._rt_out = None
            return
        try:
            inlet = rtmidi.MidiIn()
            inlet.open_virtual_port(f"{self.port_name} in")
            inlet.ignore_types(False, False, False)
            self._rt_in = inlet
        except Exception:
            self._rt_in = None

    def send(self, message: list[int]) -> None:
        data = [int(b) & 0xFF for b in message]
        self.outgoing.append(data)
        if self._rt_out is not None:
            try:
                self._rt_out.send_message(data)
            except Exception:
                pass

    def inject(self, message: list[int]) -> None:
        """Queue a message as if an external synth or sequencer had sent it."""

        self.incoming.append([int(b) & 0xFF for b in message])

    def poll(self) -> list[list[int]]:
        found: list[list[int]] = []
        while self.incoming:
            found.append(self.incoming.popleft())
        if self._rt_in is not None:
            try:
                while True:
                    packet = self._rt_in.get_message()
                    if not packet:
                        break
                    payload, _delta = packet
                    found.append(list(payload))
            except Exception:
                pass
        return found

    def recent(self) -> list[list[int]]:
        return list(self.outgoing)

    def close(self) -> None:
        for port in (self._rt_in, self._rt_out):
            if port is None:
                continue
            try:
                port.close_port()
            except Exception:
                pass
        self._rt_in = None
        self._rt_out = None
