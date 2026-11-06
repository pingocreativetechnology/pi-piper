# SPDX-License-Identifier: MIT
"""Device backends.

``SimDevice`` is the hardware stand-in. ``MikroMk3`` speaks HID reports.
``Mk3`` can push the two colour panels and deliberately does not invent a
pad or button parser: that report layout was not available from a
black-box capture or from an MIT-licensed driver.
"""

from __future__ import annotations

import os
import select
from dataclasses import dataclass, field

from .model import InputEvent
from .protocol import (
    MK3_BULK_ENDPOINT_OUT,
    MK3_DISPLAY_INTERFACE,
    MK3_HEIGHT,
    MK3_PID,
    MK3_VID,
    MK3_WIDTH,
    MIKRO_MK3_PID,
    MIKRO_MK3_VID,
    ControlState,
    encode_leds,
    mk3_transfers,
    parse_report,
)
from .surface import Surface

# Linux HIDIOC request for GET_REPORT on an input report. This is the kernel
# UAPI macro, not a vendor command.
_HIDIOCGINPUT = lambda length: (3 << 30) | (length << 16) | (ord("H") << 8) | 0x0A  # noqa: E731


class DeviceError(RuntimeError):
    pass


class CapabilityGap(RuntimeError):
    """Raised when a model has no captured, licence-clean control layout."""


@dataclass
class HardwareView:
    led_report: bytes
    screen_reports: tuple[bytes, bytes]
    mono_rows: list[str]


def view_from(surface: Surface) -> HardwareView:
    upper, lower = surface.screen.reports()
    return HardwareView(
        led_report=encode_leds(surface.buttons, surface.pads, surface.strip),
        screen_reports=(upper, lower),
        mono_rows=surface.screen.rows(),
    )


class SimDevice:
    """Queue of events injected by the browser, the terminal, or a test."""

    def __init__(self) -> None:
        self._queue: list[InputEvent] = []
        self.view: HardwareView | None = None
        self.model = "sim"

    def inject(self, event: InputEvent) -> None:
        self._queue.append(event)

    def poll(self) -> list[InputEvent]:
        queued, self._queue = self._queue, []
        return queued

    def push(self, surface: Surface) -> None:
        self.view = view_from(surface)

    def close(self) -> None:
        return None


class _HidRaw:
    def __init__(self, fd: int) -> None:
        self.fd = fd

    def read(self, size: int = 64) -> bytes:
        ready, _, _ = select.select([self.fd], [], [], 0)
        if not ready:
            return b""
        try:
            return os.read(self.fd, size)
        except BlockingIOError:
            return b""

    def write(self, payload: bytes) -> None:
        os.write(self.fd, payload)

    def get_input(self, report_id: int, length: int) -> bytes:
        import fcntl

        buf = bytearray(length)
        buf[0] = report_id
        fcntl.ioctl(self.fd, _HIDIOCGINPUT(length), buf, True)
        return bytes(buf)

    def close(self) -> None:
        os.close(self.fd)


def find_hidraw(vid: int, pid: int, sysfs_root: str = "/sys/class/hidraw") -> str | None:
    """Return ``/dev/hidrawN`` for a USB HID device, or None."""

    needle = f"{vid:08X}:{pid:08X}".lower()
    if not os.path.isdir(sysfs_root):
        return None
    for name in sorted(os.listdir(sysfs_root)):
        uevent = os.path.join(sysfs_root, name, "device", "uevent")
        try:
            with open(uevent, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read().lower()
        except OSError:
            continue
        if needle in text and "hid_id=" in text:
            return f"/dev/{name}"
    return None


class MikroMk3:
    model = "mikro-mk3"

    def __init__(self, io=None, path: str | None = None) -> None:
        self.io = io
        self.path = path
        self.state = ControlState()
        self._last_leds: bytes | None = None
        self._last_screen: tuple[bytes, bytes] | None = None

    def open(self) -> "MikroMk3":
        if self.io is not None:
            return self
        path = self.path or find_hidraw(MIKRO_MK3_VID, MIKRO_MK3_PID)
        if path is None:
            raise DeviceError(
                "No Mikro MK3 hidraw node (17cc:1700). Plug the controller in, "
                "or run `pi-piper sim` to work without hardware."
            )
        fd = os.open(path, os.O_RDWR | os.O_NONBLOCK | os.O_CLOEXEC)
        self.io = _HidRaw(fd)
        self.path = path
        try:
            initial = self.io.get_input(0x01, 14)
            parse_report(initial, self.state)
        except OSError:
            # The device still streams changes. Missing the baseline is fine.
            pass
        return self

    def poll(self) -> list[InputEvent]:
        if self.io is None:
            raise DeviceError("driver is not open")
        events: list[InputEvent] = []
        for _ in range(32):
            data = self.io.read(64)
            if not data:
                break
            events.extend(parse_report(data, self.state))
        return events

    def push(self, surface: Surface) -> None:
        if self.io is None:
            return
        view = view_from(surface)
        if view.led_report != self._last_leds:
            self.io.write(view.led_report)
            self._last_leds = view.led_report
        if view.screen_reports != self._last_screen:
            self.io.write(view.screen_reports[0])
            self.io.write(view.screen_reports[1])
            self._last_screen = view.screen_reports

    def close(self) -> None:
        if self.io is not None:
            self.io.close()
            self.io = None


@dataclass
class Mk3:
    """Colour-display backend for the full-size MK3.

    Pad, button, encoder and lamp reports are a known gap. Pi Piper will not
    fill that gap by reading proprietary software, firmware, or GPL driver
    source. ``inputs_available`` stays false until a black-box capture is
    written up in our own words.
    """

    model: str = "mk3"
    inputs_available: bool = False
    _handle: object = None
    _last_mono: tuple[str, ...] | None = None
    notes: list[str] = field(default_factory=list)

    def open(self) -> "Mk3":
        try:
            import usb.core
            import usb.util
        except ImportError as exc:
            raise DeviceError("pyusb is not installed; pip install 'pi-piper[usb]'") from exc
        device = usb.core.find(idVendor=MK3_VID, idProduct=MK3_PID)
        if device is None:
            raise DeviceError(
                "No MK3 found (17cc:1600). The Mikro MK3 is the model with a "
                "finished control driver. MK3 colour panels need this device."
            )
        try:
            if device.is_kernel_driver_active(MK3_DISPLAY_INTERFACE):
                device.detach_kernel_driver(MK3_DISPLAY_INTERFACE)
        except (NotImplementedError, usb.core.USBError):
            pass
        device.set_configuration()
        usb.util.claim_interface(device, MK3_DISPLAY_INTERFACE)
        self._handle = device
        self.notes.append(
            "MK3 controls are not parsed. Only the two colour panels are driven. "
            "No authentication handshake was required by the display writes "
            "described in the MIT-licensed display crate. If a unit demands a "
            "challenge, signature, or encrypted frame, stop and do not work around it."
        )
        return self

    def poll(self) -> list[InputEvent]:
        return []

    def push(self, surface: Surface) -> None:
        rows = tuple(surface.screen.rows())
        if rows == self._last_mono or self._handle is None:
            return
        frame = _mono_centered_rgb(rows)
        for display in (0, 1):
            for chunk in mk3_transfers(display, frame):
                self._handle.write(MK3_BULK_ENDPOINT_OUT, chunk, timeout=1000)
        self._last_mono = rows

    def close(self) -> None:
        if self._handle is not None:
            try:
                import usb.util

                usb.util.dispose_resources(self._handle)
            except Exception:
                pass
            self._handle = None


def _mono_centered_rgb(rows: tuple[str, ...] | list[str]) -> bytes:
    """Place the 128×32 picture, scaled by three, in the middle of a 480×272 frame."""

    scale = 3
    src_w, src_h = 128, 32
    origin_x = (MK3_WIDTH - src_w * scale) // 2
    origin_y = (MK3_HEIGHT - src_h * scale) // 2
    pixels = bytearray(MK3_WIDTH * MK3_HEIGHT * 3)
    for y, row in enumerate(rows):
        for x, bit in enumerate(row):
            if bit != "1":
                continue
            for dy in range(scale):
                py = origin_y + y * scale + dy
                if not 0 <= py < MK3_HEIGHT:
                    continue
                for dx in range(scale):
                    px = origin_x + x * scale + dx
                    if not 0 <= px < MK3_WIDTH:
                        continue
                    offset = (py * MK3_WIDTH + px) * 3
                    pixels[offset : offset + 3] = b"\xd6\xe3\x8a"
    return bytes(pixels)


def open_first_controller():
    """Open a plugged-in controller, preferring the Mikro MK3."""

    mikro = find_hidraw(MIKRO_MK3_VID, MIKRO_MK3_PID)
    if mikro:
        return MikroMk3(path=mikro).open()
    try:
        return Mk3().open()
    except DeviceError:
        return None
