# SPDX-License-Identifier: MIT

from pi_piper.apps import ClipLauncher, MidiController, StepSequencer
from pi_piper.drivers import SimDevice
from pi_piper.engine import Engine, load_app_file
from pi_piper.midi import MidiHub
from pi_piper.model import Button, ButtonEvent, PadEvent, PadPhase
from pi_piper.osc import OscHub, encode_message


def engine() -> Engine:
    return Engine(SimDevice(), midi=MidiHub("loopback"), osc=OscHub(enabled=False))


def tap(eng: Engine, index: int, value: int = 3000) -> None:
    eng.device.inject(PadEvent(index, PadPhase.STRIKE, value))
    eng.device.inject(PadEvent(index, PadPhase.RELEASE, 0))
    eng.tick(0)


def key(eng: Engine, button: Button) -> None:
    eng.device.inject(ButtonEvent(button, True))
    eng.device.inject(ButtonEvent(button, False))
    eng.tick(0)


def test_launcher_opens_sequencer_and_shift_stop_returns():
    eng = engine()
    eng.tick(0)
    assert eng.current.id == "launcher"
    assert any(eng.surface.screen.get(x, 0) for x in range(40))
    tap(eng, 0)
    assert isinstance(eng.current, StepSequencer)
    tap(eng, 0)
    assert eng.current.patterns[0][0][0] > 0
    key(eng, Button.play)
    notes = [msg for msg in eng.midi.recent() if msg[0] == 0x99]
    assert notes and notes[-1][1] == 36
    eng.device.inject(ButtonEvent(Button.shift, True))
    eng.device.inject(ButtonEvent(Button.stop, True))
    eng.tick(0)
    assert eng.current.id == "launcher"
    assert not eng.clock.running


def test_sequencer_clock_reaches_the_next_step():
    eng = engine()
    tap(eng, 0)
    key(eng, Button.play)
    assert eng.clock.step == 0
    eng.tick(0.2)
    assert eng.clock.step == 1
    clocks = [msg for msg in eng.midi.recent() if msg == [0xF8]]
    assert clocks


def test_clips_wait_for_the_next_bar():
    eng = engine()
    tap(eng, 1)
    assert isinstance(eng.current, ClipLauncher)
    tap(eng, 0)
    assert eng.current.playing[0] == 0
    eng.tick(0.05)
    eng.device.inject(PadEvent(4, PadPhase.STRIKE, 2000))
    eng.device.inject(PadEvent(4, PadPhase.RELEASE, 0))
    eng.tick(0)
    assert eng.current.playing[0] == 0
    assert eng.current.queued[0] == 1
    eng.clock.step = 15
    eng.clock._step_elapsed = eng.clock.step_seconds(15) - 0.001
    eng.tick(0.01)
    assert eng.clock.step == 0
    assert eng.current.playing[0] == 1
    assert eng.current.queued[0] is None


def test_midi_mode_notes_channel_and_incoming_light():
    eng = engine()
    tap(eng, 2)
    assert isinstance(eng.current, MidiController)
    eng.device.inject(PadEvent(12, PadPhase.STRIKE, 4095))
    eng.tick(0)
    note = [msg for msg in eng.midi.recent() if msg[0] == 0x90][-1]
    assert note[1] == 48 and note[2] == 127
    eng.device.inject(EncoderEvent_delta(eng, 1))
    eng.tick(0)
    assert eng.current.channel == 1
    eng.midi.inject([0x90, 50, 100])
    eng.tick(0)
    # root 48, pad index 2 is root+2 = 50, which is HID index 14 (bottom row, third pad)
    pad = eng.surface.pads[14]
    assert pad[1] == 3


def EncoderEvent_delta(eng, delta):
    from pi_piper.model import EncoderEvent

    return EncoderEvent(delta, 0)


def test_user_app_and_osc_packet():
    found = load_app_file("examples/hello_app.py")
    assert found[0].id == "hello"
    packet = encode_message("/pipiper/pad", [3, 1, 100])
    assert packet.startswith(b"/pipiper/pad\x00")
    assert b",iii" in packet


def test_disclaimer_constant_is_explicit():
    from pi_piper import DISCLAIMER

    assert "not affiliated" in DISCLAIMER.lower()
    assert "Native Instruments" in DISCLAIMER
    assert "Raspberry Pi is a trademark" in DISCLAIMER
