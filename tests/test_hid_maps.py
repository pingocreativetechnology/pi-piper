# SPDX-License-Identifier: MIT

from pi_piper.model import Button, PadPhase
from pi_piper.hid_maps import (
    MK3_HEIGHT,
    MK3_WIDTH,
    ControlState,
    encode_leds,
    mk3_transfers,
    parse_report,
    screen_pixel,
    set_screen_pixel,
    blank_screen,
)
from pi_piper.screen import MonoScreen


def _status(*down_bits: int) -> bytearray:
    report = bytearray(14)
    report[0] = 0x01
    for bit in down_bits:
        report[1 + bit // 8] |= 1 << (bit % 8)
    return report


def test_play_button_is_an_edge():
    state = ControlState()
    first = parse_report(bytes(_status(int(Button.play))), state)
    assert any(getattr(ev, "button", None) is Button.play and ev.down for ev in first)
    second = parse_report(bytes(_status(int(Button.play))), state)
    assert second == []
    released = parse_report(bytes(_status()), state)
    assert any(getattr(ev, "button", None) is Button.play and not ev.down for ev in released)


def test_encoder_wraps_the_short_way():
    state = ControlState()
    report = bytearray(14)
    report[0] = 0x01
    report[7] = 1
    assert parse_report(bytes(report), state) == [] or all(
        type(ev).__name__ != "EncoderEvent" for ev in parse_report(bytes(report), ControlState())
    )
    state = ControlState()
    parse_report(bytes(report), state)
    report[7] = 2
    step = parse_report(bytes(report), state)
    assert step[0].delta == 1
    report[7] = 15
    back = parse_report(bytes(report), state)
    assert back[0].delta == -3


def test_strip_and_second_finger():
    state = ControlState()
    report = bytearray(14)
    report[0] = 0x01
    report[10] = 100
    report[12] = 20
    events = parse_report(bytes(report), state)
    strip = [ev for ev in events if type(ev).__name__ == "StripEvent"]
    assert strip[0].primary == 100
    assert strip[0].secondary == 20
    assert parse_report(bytes(report), state) == [] or all(
        type(ev).__name__ != "StripEvent" for ev in parse_report(bytes(report), state)
    )


def test_pad_strike_and_terminator():
    report = bytearray(64)
    report[0] = 0x02
    report[1] = 12
    report[2] = 0x10
    report[3] = 0x80
    report[4] = 0
    events = parse_report(bytes(report))
    assert len(events) == 1
    assert events[0].index == 12
    assert events[0].phase is PadPhase.STRIKE
    assert events[0].value == 0x80


def test_led_and_screen_layout():
    leds = encode_leds({int(Button.play): 3}, [(1, 2)] + [(0, 0)] * 15, [3] + [0] * 24)
    assert leds[0] == 0x80
    assert leds[1 + int(Button.play)] == 0x7F
    assert leds[1 + 39] == (1 << 2) | 2
    assert leds[1 + 55] == 0x7F
    assert leds[1 + 39 + 15] == 0

    buffer = blank_screen()
    set_screen_pixel(buffer, 10, 3, True)
    assert screen_pixel(buffer, 10, 3)
    assert not screen_pixel(buffer, 10, 4)
    screen = MonoScreen()
    screen.text(0, 0, "PI PIPER")
    assert screen.get(0, 0) or screen.get(1, 0) or any(screen.get(x, 1) for x in range(20))
    upper, lower = screen.reports()
    assert upper[0] == 0xE0 and lower[0] == 0xE0
    assert upper[3] == 0x00 and lower[3] == 0x02
    assert upper[5] == 0x80 and len(upper) == 265


def test_mk3_frame_is_four_writes_without_inventing_controls():
    frame = bytes(MK3_WIDTH * MK3_HEIGHT * 3)
    parts = mk3_transfers(1, frame)
    assert len(parts) == 4
    assert parts[0][2] == 1
    assert parts[1] == bytes([0x00, 0x00, 0xFF, 0x00])
    assert len(parts[2]) == MK3_WIDTH * MK3_HEIGHT * 2
    assert parts[3][0] == 0x03
