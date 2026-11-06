# SPDX-License-Identifier: MIT
"""A one-file performance. Run it with:

    pi-piper sim --app examples/hello_app.py
"""

from pi_piper.model import PadEvent, PadPhase
from pi_piper.sdk import App


class Hello(App):
    id = "hello"
    title = "Hello"
    hint = "Strike a pad. It plays one note and lights up."

    def __init__(self) -> None:
        self.last = -1

    def on_event(self, host, event) -> None:
        if isinstance(event, PadEvent) and event.phase is PadPhase.STRIKE:
            self.last = event.index
            note = 60 + event.index
            host.note(0, note, 100, gate=0.2)
            host.osc("/hello/pad", event.index)

    def paint(self, host) -> None:
        host.screen.text(0, 0, "HELLO")
        host.screen.text(0, 8, "YOUR APP")
        if self.last >= 0:
            host.pad(self.last, "mint", 3)
            host.screen.text(0, 16, f"PAD {self.last + 1}")
