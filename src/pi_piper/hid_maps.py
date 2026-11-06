# SPDX-License-Identifier: MIT
"""Controller report packing and unpacking for Pi Piper.

Pure helpers: bytes to events, surface to bytes. No USB I/O here.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import (
    UNLIT_BUTTONS,
    Button,
    ButtonEvent,
    EncoderEvent,
    PadEvent,
    PadPhase,
    StripEvent,
)

MIKRO_MK3_VID = 0x17CC
MIKRO_MK3_PID = 0x1700
MK3_VID = 0x17CC
MK3_PID = 0x1600

# Lamp bytes for the four brightness steps the Mikro MK3 buttons accept.
# 0 is dark. 0x7C, 0x7E and 0x7F are the dim, medium and full steps named by
# the MIT-licensed reference driver.
BUTTON_LEVEL_BYTE = {0: 0x00, 1: 0x7C, 2: 0x7E, 3: 0x7F}

LED_REPORT_ID = 0x80
LED_PAYLOAD_LEN = 80
PAD_LED_OFFSET = 39
STRIP_LED_OFFSET = 55
STRIP_LED_COUNT = 25
PAD_COUNT = 16

SCREEN_W = 128
SCREEN_H = 32
SCREEN_REPORT_ID = 0xE0

# MK3 colour panels. Size and bulk framing follow the MIT-or-Apache
# ni-display reference. Channel order of the pixel words is not confirmed
# on hardware yet; see docs/legal-flags.md.
MK3_WIDTH = 480
MK3_HEIGHT = 272
MK3_DISPLAY_INTERFACE = 5
MK3_BULK_ENDPOINT_OUT = 0x04
_MK3_HEADER = bytes(
    [0x84, 0x00, 0x00, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0xE0, 0x01, 0x10]
)
_MK3_COMMAND = bytes([0x00, 0x00, 0xFF, 0x00])
_MK3_FOOTER = bytes([0x03, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00])


@dataclass
class ControlState:
    """Previous status-report values, so edges and encoder steps can be found."""

    buttons: int = 0
    encoder: int | None = None
    primary: int | None = None
    secondary: int | None = None
    seen_status: bool = False


def parse_report(data: bytes, state: ControlState | None = None) -> list:
    """Parse one incoming report, report-id byte first.

    ``state`` is updated in place when the report is a status report. Pad
    reports do not use it. Unknown report ids yield an empty list: Pi Piper
    does not guess at feature reports.
    """

    if not data:
        return []
    report_id = data[0]
    if report_id == 0x01:
        if state is None:
            state = ControlState()
        return _parse_status(data, state)
    if report_id == 0x02:
        return _parse_pads(data)
    return []


def _parse_status(data: bytes, state: ControlState) -> list:
    events: list = []
    window = data[1:7]
    bits = 0
    for index, byte in enumerate(window):
        bits |= int(byte) << (8 * index)

    if state.seen_status:
        changed = bits ^ state.buttons
        bit = 0
        while changed:
            if changed & 1:
                try:
                    button = Button(bit)
                except ValueError:
                    button = None
                if button is not None:
                    events.append(ButtonEvent(button, down=bool(bits & (1 << bit))))
            changed >>= 1
            bit += 1
    else:
        # The first report establishes a baseline. Held keys are reported so
        # a just-opened device does not swallow a finger already on Play.
        for bit in range(41):
            if bits & (1 << bit):
                events.append(ButtonEvent(Button(bit), down=True))
    state.buttons = bits
    state.seen_status = True

    if len(data) > 7:
        position = data[7] & 0x0F
        if state.encoder is not None:
            delta = (position - state.encoder) & 0x0F
            if delta > 8:
                delta -= 16
            if delta != 0:
                events.append(EncoderEvent(delta=delta, position=position))
        state.encoder = position

    if len(data) >= 14:
        timestamp = data[8] | (data[9] << 8)
        primary = data[10] | (data[11] << 8)
        secondary = data[12] | (data[13] << 8)
        if primary != state.primary or secondary != state.secondary:
            events.append(
                StripEvent(primary=primary, secondary=secondary, timestamp_ms=timestamp)
            )
        state.primary = primary
        state.secondary = secondary
    elif len(data) >= 11:
        primary = data[10]
        if primary != state.primary:
            events.append(StripEvent(primary=primary, secondary=0, timestamp_ms=0))
        state.primary = primary
    return events


def _parse_pads(data: bytes) -> list:
    events: list = []
    index = 1
    while index + 2 < len(data):
        pad = data[index]
        raw = data[index + 1]
        value = ((raw & 0x0F) << 8) | data[index + 2]
        phase_bits = raw & 0xF0
        if pad == 0 and phase_bits == 0 and value == 0:
            break
        if pad < PAD_COUNT:
            try:
                phase = PadPhase(phase_bits >> 4)
            except ValueError:
                phase = None
            if phase is not None:
                events.append(PadEvent(index=pad, phase=phase, value=value))
        index += 3
    return events


def encode_leds(
    buttons: dict[int, int],
    pads: list[tuple[int, int]],
    strip: list[int],
) -> bytes:
    """Build one 0x80 lamp report, including the report id."""

    payload = bytearray(LED_PAYLOAD_LEN)
    for bit, level in buttons.items():
        if bit in UNLIT_BUTTONS or not 0 <= bit < PAD_LED_OFFSET:
            continue
        payload[bit] = BUTTON_LEVEL_BYTE.get(int(level), 0)
    for pad_index, (color, level) in enumerate(pads[:PAD_COUNT]):
        level = int(level)
        color = int(color)
        if level <= 0 or color <= 0:
            payload[PAD_LED_OFFSET + pad_index] = 0
        else:
            payload[PAD_LED_OFFSET + pad_index] = ((color & 0x1F) << 2) | (level & 0x03)
    for led_index, level in enumerate(strip[:STRIP_LED_COUNT]):
        payload[STRIP_LED_OFFSET + led_index] = BUTTON_LEVEL_BYTE.get(int(level), 0)
    return bytes([LED_REPORT_ID]) + bytes(payload)


def blank_screen() -> bytearray:
    return bytearray([0xFF]) * (SCREEN_W * 4)


def set_screen_pixel(buffer: bytearray, x: int, y: int, lit: bool) -> None:
    """Set one pixel. A lit pixel stores a 0 bit, which is how the panel draws."""

    if not 0 <= x < SCREEN_W or not 0 <= y < SCREEN_H:
        return
    chunk = y // 8
    bit = y % 8
    offset = chunk * SCREEN_W + x
    mask = 1 << bit
    if lit:
        buffer[offset] &= ~mask & 0xFF
    else:
        buffer[offset] |= mask


def screen_pixel(buffer: bytes | bytearray, x: int, y: int) -> bool:
    chunk = y // 8
    bit = y % 8
    offset = chunk * SCREEN_W + x
    return (buffer[offset] & (1 << bit)) == 0


def screen_reports(buffer: bytes) -> tuple[bytes, bytes]:
    """Two 0xE0 writes that cover the full 128×32 panel.

    Each header is the report id plus four little-endian fields: x, y, width,
    height. ``y`` and ``height`` count bands of eight pixel rows. The upper
    write sends y=0, the lower write sends y=2, and both send height=2 and
    width=128, followed by 256 payload bytes.
    """

    if len(buffer) != SCREEN_W * 4:
        raise ValueError(f"screen buffer must be {SCREEN_W * 4} bytes, got {len(buffer)}")
    upper = bytes([SCREEN_REPORT_ID, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x02, 0x00]) + buffer[:256]
    lower = bytes([SCREEN_REPORT_ID, 0x00, 0x00, 0x02, 0x00, 0x80, 0x00, 0x02, 0x00]) + buffer[256:]
    return upper, lower


def mk3_transfers(display_index: int, rgb888: bytes) -> list[bytes]:
    """Four bulk writes that push one MK3 panel.

    ``rgb888`` is tightly packed R,G,B, one byte each, row-major, 480×272.
    Pixels are sent as 16-bit RGB565, high byte first. This channel order is
    a Pi Piper choice pending the hardware swatch in the test checklist; the
    reference crate's own colour shuffle is marked unfinished upstream.
    """

    expected = MK3_WIDTH * MK3_HEIGHT * 3
    if len(rgb888) != expected:
        raise ValueError(f"MK3 frame must be {expected} bytes, got {len(rgb888)}")
    if display_index not in (0, 1):
        raise ValueError("display index must be 0 or 1")
    header = bytearray(_MK3_HEADER)
    header[2] = display_index
    frame = bytearray(MK3_WIDTH * MK3_HEIGHT * 2)
    out = 0
    for offset in range(0, expected, 3):
        red = rgb888[offset] >> 3
        green = rgb888[offset + 1] >> 2
        blue = rgb888[offset + 2] >> 3
        word = (red << 11) | (green << 5) | blue
        frame[out] = (word >> 8) & 0xFF
        frame[out + 1] = word & 0xFF
        out += 2
    return [bytes(header), _MK3_COMMAND, bytes(frame), _MK3_FOOTER]

