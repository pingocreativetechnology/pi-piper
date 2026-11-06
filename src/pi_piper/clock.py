# SPDX-License-Identifier: MIT
"""Straight MIDI clock plus a swung 16th-note grid.

MIDI clock stays even, at 24 pulses per quarter note. Swing only changes when
the next 16th-note step is due. A swing of 0.5 is straight. 0.66 is a triplet
feel: the first 16th of each pair takes that fraction of the eighth note.
"""

from __future__ import annotations


class MusicalClock:
    def __init__(self, bpm: float = 120.0) -> None:
        self.bpm = float(bpm)
        self.swing = 0.5
        self.running = False
        self.step = 0
        self._step_elapsed = 0.0
        self._clock_elapsed = 0.0
        self.time = 0.0

    def set_bpm(self, bpm: float) -> None:
        self.bpm = max(40.0, min(240.0, float(bpm)))

    def eighth_seconds(self) -> float:
        return 30.0 / self.bpm

    def step_seconds(self, index: int) -> float:
        pair = self.eighth_seconds()
        portion = self.swing if index % 2 == 0 else (1.0 - self.swing)
        return pair * portion

    def clock_seconds(self) -> float:
        return (60.0 / self.bpm) / 24.0

    def reset(self) -> None:
        self.step = 0
        self._step_elapsed = 0.0
        self._clock_elapsed = 0.0

    def advance(self, dt: float) -> tuple[int, list[int]]:
        """Return ``(midi_clocks, steps_reached)``.

        ``steps_reached`` lists each 16th-note index the grid landed on during
        this slice, in order. The clock does not fire step 0 by itself; the
        app fires the downbeat when the performer presses Play.
        """

        self.time += dt
        if not self.running or dt < 0:
            return 0, []
        clocks = 0
        self._clock_elapsed += dt
        interval = self.clock_seconds()
        while self._clock_elapsed >= interval:
            self._clock_elapsed -= interval
            clocks += 1
            if clocks > 64:
                self._clock_elapsed = 0.0
                break
        reached: list[int] = []
        self._step_elapsed += dt
        guard = 0
        while self._step_elapsed >= self.step_seconds(self.step):
            self._step_elapsed -= self.step_seconds(self.step)
            self.step = (self.step + 1) % 16
            reached.append(self.step)
            guard += 1
            if guard > 32:
                self._step_elapsed = 0.0
                break
        return clocks, reached
