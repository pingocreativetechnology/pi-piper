# SPDX-License-Identifier: MIT
"""A small OSC 1.0 client and a parallel plain-text UDP feed.

Pure Data's stock objects read the text feed. SuperCollider reads the OSC
feed. Neither bridge needs a third-party Python package.
"""

from __future__ import annotations

import socket
import struct
from typing import Iterable


def _pad(blob: bytes) -> bytes:
    blob += b"\x00"
    while len(blob) % 4:
        blob += b"\x00"
    return blob


def encode_message(address: str, args: Iterable[object]) -> bytes:
    if not address.startswith("/"):
        raise ValueError("OSC address must start with /")
    tags = [","]
    body = b""
    for arg in args:
        if isinstance(arg, bool):
            raise TypeError("pass 0 or 1, not a boolean")
        if isinstance(arg, int) and not isinstance(arg, bool):
            tags.append("i")
            body += struct.pack(">i", int(arg))
        elif isinstance(arg, float):
            tags.append("f")
            body += struct.pack(">f", float(arg))
        elif isinstance(arg, str):
            tags.append("s")
            body += _pad(arg.encode("utf-8"))
        else:
            raise TypeError(f"unsupported OSC value {arg!r}")
    return _pad(address.encode("utf-8")) + _pad("".join(tags).encode("ascii")) + body


class OscHub:
    def __init__(
        self,
        host: str = "127.0.0.1",
        osc_port: int = 9000,
        text_port: int = 9002,
        enabled: bool = True,
    ) -> None:
        self.host = host
        self.osc_port = osc_port
        self.text_port = text_port
        self.enabled = enabled
        self.sent: list[tuple[str, tuple]] = []
        self._sock: socket.socket | None = None
        if enabled:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, address: str, *args: object) -> None:
        self.sent.append((address, tuple(args)))
        if len(self.sent) > 200:
            del self.sent[:100]
        if not self.enabled or self._sock is None:
            return
        try:
            self._sock.sendto(encode_message(address, args), (self.host, self.osc_port))
        except OSError:
            pass
        text = address + " " + " ".join(str(a) for a in args)
        try:
            self._sock.sendto(text.encode("utf-8"), (self.host, self.text_port))
        except OSError:
            pass

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None
