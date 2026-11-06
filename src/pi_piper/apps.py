# SPDX-License-Identifier: MIT
"""Built-in performances: launcher, step sequencer, clip launcher, MIDI mode.

Patterns in the clip launcher were written for this project. They are not
factory kits, presets, or transcriptions of a commercial library.
"""

from __future__ import annotations

from . import DISCLAIMER_LINES
from .midi import control_change, poly_pressure
from .model import (
    Button,
    ButtonEvent,
    EncoderEvent,
    PadEvent,
    PadPhase,
    StripEvent,
    scale_12bit,
)
from .screen import note_name
from .sdk import App, Host

DRUM_CHANNEL = 9
DRUM_NOTES = (36, 38, 42, 39)
DRUM_NAMES = ("KICK", "SNARE", "HAT", "CLAP")
DRUM_COLORS = ("orange", "red", "cyan", "yellow")

# Pi Piper's own controller map. It is not the map used by any vendor editor.
BUTTON_CC = {
    Button.wordmark: 20,
    Button.star: 21,
    Button.browse: 22,
    Button.volume: 23,
    Button.swing: 24,
    Button.tempo: 25,
    Button.plugin: 26,
    Button.sampling: 27,
    Button.pitch: 28,
    Button.mod: 29,
    Button.perform: 30,
    Button.notes: 31,
    Button.group: 32,
    Button.auto: 33,
    Button.lock: 34,
    Button.note_repeat: 35,
    Button.restart: 36,
    Button.erase: 37,
    Button.tap: 38,
    Button.follow: 39,
    Button.play: 40,
    Button.rec: 41,
    Button.stop: 42,
    Button.fixed_vel: 43,
    Button.pad_mode: 44,
    Button.keyboard: 45,
    Button.chords: 46,
    Button.step: 47,
    Button.scene: 48,
    Button.pattern: 49,
    Button.events: 50,
    Button.variation: 51,
    Button.duplicate: 52,
    Button.select: 53,
    Button.solo: 54,
    Button.mute: 55,
    Button.encoder_press: 56,
    Button.encoder_touch: 57,
}

# scene, track -> list of (step, velocity). Notes come from the track.
_CLIP_HITS: dict[tuple[int, int], tuple[tuple[int, int], ...]] = {
    (0, 0): ((0, 110), (4, 100), (8, 110), (12, 100)),
    (0, 1): ((4, 108), (12, 96)),
    (0, 2): ((2, 70), (6, 64), (10, 70), (14, 60)),
    (0, 3): ((4, 90),),
    (1, 0): ((0, 116), (3, 80), (6, 104), (10, 112)),
    (1, 1): ((4, 110), (11, 88)),
    (1, 2): ((0, 50), (2, 72), (4, 50), (6, 72), (8, 50), (10, 72), (12, 50), (14, 72)),
    (1, 3): ((4, 100), (12, 84)),
    (2, 0): ((0, 100), (7, 90), (8, 108)),
    (2, 1): ((4, 100), (7, 70), (12, 110)),
    (2, 2): ((1, 40), (2, 66), (5, 40), (6, 66), (9, 40), (10, 66), (13, 40), (14, 66)),
    (2, 3): ((6, 96), (14, 80)),
    (3, 0): ((0, 90), (10, 100)),
    (3, 1): ((2, 70), (6, 104), (11, 90), (14, 80)),
    (3, 2): ((0, 60), (4, 55), (8, 60), (12, 55)),
    (3, 3): ((0, 40), (4, 100), (8, 40), (13, 90)),
}
SCENE_NAMES = ("FLOOR", "PUSH", "SKIP", "BREAK")


def _down(event: object, button: Button) -> bool:
    return isinstance(event, ButtonEvent) and event.button is button and event.down


def _pad_strike(event: object) -> PadEvent | None:
    if isinstance(event, PadEvent) and event.phase is PadPhase.STRIKE:
        return event
    return None


class Launcher(App):
    id = "launcher"
    title = "Launcher"
    hint = "Turn the encoder, then press it. Or strike a pad."

    def __init__(self) -> None:
        self.index = 0

    def on_enter(self, host: Host) -> None:
        self.index = 0

    def on_event(self, host: Host, event: object) -> None:
        choices = host.apps
        if not choices:
            return
        if isinstance(event, EncoderEvent):
            self.index = (self.index + event.delta) % len(choices)
        if _down(event, Button.encoder_press) or _down(event, Button.play):
            host.switch(choices[self.index].id)
            return
        strike = _pad_strike(event)
        if strike is not None and strike.index < len(choices):
            host.switch(choices[strike.index].id)

    def paint(self, host: Host) -> None:
        choices = host.apps
        for line, text in enumerate(DISCLAIMER_LINES):
            host.screen.text(0, line * 8, text if line else "PI PIPER")
        if choices:
            chosen = choices[self.index % len(choices)]
            host.screen.text(0, 24, ">" + chosen.title.upper())
        for index, app in enumerate(choices[:16]):
            host.pad(index, "white" if index == self.index else "blue", 3 if index == self.index else 1)
        host.light(Button.play, 1)


class StepSequencer(App):
    id = "sequencer"
    title = "Steps"
    hint = "Pads toggle steps. Play starts the bar. Encoder changes tempo."

    def __init__(self) -> None:
        self.bank = 0
        self.track = 0
        # banks × tracks × 16 velocities (0 = rest)
        self.patterns = [[[0] * 16 for _ in range(4)] for _ in range(4)]
        self.audition = False

    def on_exit(self, host: Host) -> None:
        host.engine.stop_transport()

    def on_event(self, host: Host, event: object) -> None:
        if isinstance(event, EncoderEvent) and not host.shift:
            host.set_tempo(host.tempo + event.delta)
        elif isinstance(event, EncoderEvent) and host.shift:
            self.track = (self.track + event.delta) % 4
        elif _down(event, Button.left):
            self.track = (self.track - 1) % 4
        elif _down(event, Button.right):
            self.track = (self.track + 1) % 4
        elif _down(event, Button.pattern) or _down(event, Button.group):
            self.bank = (self.bank + 1) % 4
        elif _down(event, Button.swing):
            host.engine.clock.swing = {0.5: 0.58, 0.58: 0.66, 0.66: 0.5}.get(
                round(host.engine.clock.swing, 2), 0.5
            )
        elif _down(event, Button.erase):
            self.patterns[self.bank][self.track] = [0] * 16
        elif _down(event, Button.duplicate):
            nxt = (self.bank + 1) % 4
            self.patterns[nxt][self.track] = list(self.patterns[self.bank][self.track])
        elif _down(event, Button.notes):
            self.audition = not self.audition
        elif _down(event, Button.play):
            if host.engine.clock.running:
                host.engine.stop_transport()
            else:
                host.engine.start_transport()
                self.on_step(host, 0)
        elif _down(event, Button.stop):
            host.engine.stop_transport()
        elif _down(event, Button.restart):
            host.engine.clock.step = 0
            host.engine.clock._step_elapsed = 0.0
        strike = _pad_strike(event)
        if strike is None:
            return
        if self.audition:
            track = strike.index % 4
            host.note(DRUM_CHANNEL, DRUM_NOTES[track], scale_12bit(strike.value), gate=0.06)
            if host.engine.clock.running and event_is_record(host):
                self.patterns[self.bank][track][host.engine.clock.step] = scale_12bit(strike.value)
            return
        row = self.patterns[self.bank][self.track]
        row[strike.index] = 0 if row[strike.index] else max(40, scale_12bit(strike.value))

    def on_step(self, host: Host, step: int) -> None:
        gate = min(0.12, host.engine.clock.step_seconds(step) * 0.8)
        for track in range(4):
            velocity = self.patterns[self.bank][track][step]
            if velocity:
                host.note(DRUM_CHANNEL, DRUM_NOTES[track], velocity, gate=gate)
        host.osc("/pipiper/step", step)

    def paint(self, host: Host) -> None:
        clock = host.engine.clock
        host.screen.text(0, 0, f"STEPS {int(clock.bpm)}")
        host.screen.text(0, 8, f"{DRUM_NAMES[self.track]} SW{int(clock.swing * 100)}")
        state = "PLAY" if clock.running else "STOP"
        host.screen.text(0, 16, f"{state} BANK{self.bank + 1}")
        host.screen.text(0, 24, "LIVE" if self.audition else "EDIT")
        row = self.patterns[self.bank][self.track]
        color = DRUM_COLORS[self.track]
        for index in range(16):
            playhead = clock.running and clock.step == index
            if playhead and row[index]:
                host.pad(index, "white", 3)
            elif playhead:
                host.pad(index, color, 1)
            elif row[index]:
                host.pad(index, color, 3 if index % 4 == 0 else 2)
        host.light(Button.play, 3 if clock.running else 1)
        host.light(Button.rec, 3 if self.audition else 0)
        host.light(Button.swing, 2 if clock.swing > 0.5 else 0)
        host.strip(clock.step / 15 if clock.running else 0)


def event_is_record(host: Host) -> bool:
    return True


class ClipLauncher(App):
    id = "clips"
    title = "Clips"
    hint = "Each pad is a clip. Playback changes on the next bar."

    def __init__(self) -> None:
        self.playing: list[int | None] = [None, None, None, None]
        self.queued: list[int | None] = [None, None, None, None]
        self.muted = [False, False, False, False]

    def on_exit(self, host: Host) -> None:
        host.engine.stop_transport()

    def on_event(self, host: Host, event: object) -> None:
        if isinstance(event, EncoderEvent):
            host.set_tempo(host.tempo + event.delta)
        elif _down(event, Button.play):
            if not host.engine.clock.running:
                host.engine.start_transport()
                self._apply_queue(host, fire=True)
            else:
                self._apply_queue(host, fire=False)
        elif _down(event, Button.stop) or _down(event, Button.erase):
            self.queued = [None, None, None, None]
            self.playing = [None, None, None, None]
            host.engine.stop_transport()
        elif _down(event, Button.mute):
            self._mute_next = True
        strike = _pad_strike(event)
        if strike is None:
            return
        scene, track = divmod(strike.index, 4)
        if host.shift or getattr(self, "_mute_next", False):
            self.muted[track] = not self.muted[track]
            self._mute_next = False
            return
        if self.playing[track] == scene and self.queued[track] is None:
            self.queued[track] = -1  # stop this track on the next bar
        else:
            self.queued[track] = scene
        if not host.engine.clock.running:
            host.engine.start_transport()
            self._apply_queue(host, fire=True)

    def on_step(self, host: Host, step: int) -> None:
        if step == 0:
            self._apply_queue(host, fire=False)
        gate = min(0.1, host.engine.clock.step_seconds(step) * 0.75)
        for track, scene in enumerate(self.playing):
            if scene is None or self.muted[track]:
                continue
            for hit_step, velocity in _CLIP_HITS.get((scene, track), ()):
                if hit_step == step:
                    host.note(DRUM_CHANNEL, DRUM_NOTES[track], velocity, gate=gate)
        host.osc("/pipiper/step", step)

    def _apply_queue(self, host: Host, fire: bool) -> None:
        changed = False
        for track, scene in enumerate(self.queued):
            if scene is None:
                continue
            changed = True
            self.playing[track] = None if scene < 0 else scene
        self.queued = [None, None, None, None]
        if fire and host.engine.clock.step == 0:
            self.on_step(host, 0)
        if changed:
            host.osc("/pipiper/scene", *(s if s is not None else -1 for s in self.playing))

    def paint(self, host: Host) -> None:
        clock = host.engine.clock
        active = next((s for s in self.playing if s is not None), None)
        host.screen.text(0, 0, f"CLIPS {int(clock.bpm)}")
        host.screen.text(0, 8, SCENE_NAMES[active] if active is not None else "EMPTY")
        host.screen.text(0, 16, "PLAY" if clock.running else "STOP")
        host.screen.text(0, 24, f"BAR {clock.step // 4 + 1}")
        for scene in range(4):
            for track in range(4):
                index = scene * 4 + track
                color = DRUM_COLORS[track]
                if self.muted[track]:
                    host.pad(index, color, 0)
                    continue
                if self.playing[track] == scene:
                    host.pad(index, color, 3)
                elif self.queued[track] == scene:
                    host.pad(index, "white", 2)
                else:
                    host.pad(index, color, 1)
        host.light(Button.play, 3 if clock.running else 1)
        host.strip(clock.step / 15 if clock.running else 0)


class MidiController(App):
    id = "midi"
    title = "MIDI"
    hint = "Pads play notes. Encoder changes channel. Left and right change octave."

    def __init__(self) -> None:
        self.channel = 0
        self.root = 48
        self.fixed = False
        self.held: dict[int, int] = {}
        self.external: set[int] = set()
        self.last = "READY"

    def on_exit(self, host: Host) -> None:
        self._release_all(host)

    def on_event(self, host: Host, event: object) -> None:
        if isinstance(event, EncoderEvent):
            if host.shift:
                self.root = max(0, min(96, self.root + event.delta))
            else:
                self.channel = (self.channel + event.delta) % 16
            host.midi(control_change(self.channel, 3, 64 + max(-63, min(63, event.delta))))
        elif _down(event, Button.left):
            self.root = max(0, self.root - 12)
        elif _down(event, Button.right):
            self.root = min(96, self.root + 12)
        elif _down(event, Button.fixed_vel):
            self.fixed = not self.fixed
        elif isinstance(event, StripEvent):
            if event.primary <= 0:
                value = 0
            else:
                value = max(0, min(127, round((event.primary - 1) * 127 / 199)))
            host.midi(control_change(self.channel, 11, value))
            host.strip(value / 127)
        elif isinstance(event, ButtonEvent) and event.button in BUTTON_CC:
            if event.button in (Button.shift, Button.left, Button.right):
                return
            host.midi(
                control_change(self.channel, BUTTON_CC[event.button], 127 if event.down else 0)
            )
        elif isinstance(event, PadEvent):
            self._pad(host, event)

    def on_midi(self, host: Host, message: list[int]) -> None:
        if len(message) < 3:
            return
        kind = message[0] & 0xF0
        note = message[1]
        if kind == 0x90 and message[2] > 0:
            self.external.add(note)
        elif kind in (0x80, 0x90):
            self.external.discard(note)

    def _pad(self, host: Host, event: PadEvent) -> None:
        note = self.root + (3 - event.index // 4) * 4 + (event.index % 4)
        if event.phase is PadPhase.STRIKE:
            velocity = 100 if self.fixed else scale_12bit(event.value)
            self.held[event.index] = note
            host.midi([0x90 | self.channel, note & 0x7F, velocity])
            host.osc("/pipiper/note", self.channel, note & 0x7F, velocity)
            self.last = f"{note_name(note)} {velocity}"
        elif event.phase is PadPhase.PRESSURE and event.index in self.held:
            host.midi(poly_pressure(self.channel, self.held[event.index], scale_12bit(event.value)))
        elif event.phase in (PadPhase.RELEASE, PadPhase.UNTOUCH):
            played = self.held.pop(event.index, None)
            if played is not None:
                host.midi([0x80 | self.channel, played & 0x7F, 0])
                host.osc("/pipiper/note", self.channel, played & 0x7F, 0)

    def _release_all(self, host: Host) -> None:
        for note in list(self.held.values()):
            host.midi([0x80 | self.channel, note & 0x7F, 0])
        self.held.clear()

    def paint(self, host: Host) -> None:
        host.screen.text(0, 0, f"MIDI CH{self.channel + 1}")
        host.screen.text(0, 8, f"ROOT {note_name(self.root)}")
        host.screen.text(0, 16, self.last[:21])
        host.screen.text(0, 24, "VEL FIX" if self.fixed else "VEL DYN")
        for index in range(16):
            note = self.root + (3 - index // 4) * 4 + (index % 4)
            if index in self.held:
                host.pad(index, "white", 3)
            elif note in self.external:
                host.pad(index, "green", 3)
            else:
                host.pad(index, "blue" if note % 12 in (0, 5) else "plum", 1)
        host.light(Button.fixed_vel, 3 if self.fixed else 0)


def builtin_apps() -> list[App]:
    return [Launcher(), StepSequencer(), ClipLauncher(), MidiController()]
