# SPDX-License-Identifier: MIT
"""One-port HTTP and WebSocket server for the bench simulator.

The browser loads the built UI (or the fallback page) and speaks JSON on
``/ws``. No extra web framework is required, so the same file runs on a
development machine and on the appliance.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import mimetypes
from pathlib import Path

from .engine import Engine
from .model import Button, ButtonEvent, EncoderEvent, PadEvent, PadPhase, StripEvent

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_ROOT = Path(__file__).resolve().parent
_DIST_CANDIDATES = (
    _ROOT.parents[1] / "sim-web" / "dist",
    Path("/opt/pi-piper/sim-web/dist"),
)


def static_dir() -> Path | None:
    for path in _DIST_CANDIDATES:
        if (path / "index.html").is_file():
            return path
    fallback = _ROOT / "web"
    if (fallback / "index.html").is_file():
        return fallback
    return None


def _accept_key(key: str) -> str:
    digest = hashlib.sha1((key.strip() + _WS_GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


class BenchServer:
    def __init__(self, engine: Engine, host: str = "127.0.0.1", port: int = 44731) -> None:
        self.engine = engine
        self.host = host
        self.port = port
        self.clients: set[asyncio.StreamWriter] = set()
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, self.host, self.port)
        sockets = self._server.sockets or []
        if sockets:
            self.port = sockets[0].getsockname()[1]

    async def serve_forever(self) -> None:
        await self.start()
        tick = asyncio.create_task(self._clock())
        try:
            assert self._server is not None
            async with self._server:
                await self._server.serve_forever()
        finally:
            tick.cancel()

    async def _clock(self) -> None:
        loop = asyncio.get_running_loop()
        previous = loop.time()
        while True:
            await asyncio.sleep(0.02)
            now = loop.time()
            self.engine.tick(now - previous)
            previous = now
            await self._broadcast()

    async def _broadcast(self) -> None:
        if not self.clients:
            return
        payload = json.dumps({"type": "state", **self.engine.snapshot()}).encode("utf-8")
        frame = _encode_frame(payload)
        dead: list[asyncio.StreamWriter] = []
        for writer in list(self.clients):
            try:
                writer.write(frame)
                await writer.drain()
            except (ConnectionError, OSError):
                dead.append(writer)
        for writer in dead:
            self.clients.discard(writer)

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            header = await reader.readuntil(b"\r\n\r\n")
        except asyncio.IncompleteReadError:
            writer.close()
            return
        text = header.decode("latin1")
        first = text.split("\r\n", 1)[0]
        parts = first.split(" ")
        if len(parts) < 2:
            writer.close()
            return
        method, path = parts[0], parts[1].split("?", 1)[0]
        if path == "/ws" and "websocket" in text.lower():
            await self._websocket(text, reader, writer)
            return
        if method != "GET":
            await self._http(writer, 405, b"method not allowed", "text/plain")
            return
        await self._route_http(path, writer)

    async def _route_http(self, path: str, writer: asyncio.StreamWriter) -> None:
        if path == "/api/health":
            body = json.dumps({"ok": True, "app": self.engine.current.id}).encode()
            await self._http(writer, 200, body, "application/json")
            return
        if path == "/api/state":
            body = json.dumps(self.engine.snapshot()).encode()
            await self._http(writer, 200, body, "application/json")
            return
        folder = static_dir()
        if folder is None:
            await self._http(writer, 200, _BARE_PAGE, "text/html; charset=utf-8")
            return
        relative = "index.html" if path in ("/", "") else path.lstrip("/")
        file = (folder / relative).resolve()
        if not str(file).startswith(str(folder.resolve())) or not file.is_file():
            file = folder / "index.html"
        mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        await self._http(writer, 200, file.read_bytes(), mime)

    async def _http(self, writer: asyncio.StreamWriter, status: int, body: bytes, mime: str) -> None:
        reason = {200: "OK", 404: "Not Found", 405: "Method Not Allowed"}.get(status, "OK")
        head = (
            f"HTTP/1.1 {status} {reason}\r\n"
            f"Content-Type: {mime}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Cache-Control: no-store\r\n"
            "Connection: close\r\n\r\n"
        )
        writer.write(head.encode("ascii") + body)
        await writer.drain()
        writer.close()

    async def _websocket(self, header: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        key = ""
        for line in header.split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
        if not key:
            writer.close()
            return
        accept = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {_accept_key(key)}\r\n\r\n"
        )
        writer.write(accept.encode("ascii"))
        await writer.drain()
        self.clients.add(writer)
        await self._broadcast()
        try:
            while True:
                payload = await _read_frame(reader)
                if payload is None:
                    break
                self._apply_client(payload)
                self.engine.tick(0.0)
                await self._broadcast()
        finally:
            self.clients.discard(writer)
            try:
                writer.close()
            except OSError:
                pass

    def _apply_client(self, payload: bytes) -> None:
        try:
            message = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        kind = message.get("type")
        if kind == "pad":
            try:
                phase = PadPhase[str(message.get("phase", "STRIKE")).upper()]
            except KeyError:
                return
            self.engine.device.inject(
                PadEvent(int(message.get("index", 0)), phase, int(message.get("value", 0)))
            )
        elif kind == "button":
            name = str(message.get("name", "")).upper()
            try:
                button = Button[name.lower()]
            except KeyError:
                return
            self.engine.device.inject(ButtonEvent(button, down=bool(message.get("down", True))))
        elif kind == "encoder":
            self.engine.device.inject(EncoderEvent(delta=int(message.get("delta", 0)), position=0))
        elif kind == "strip":
            self.engine.device.inject(
                StripEvent(
                    primary=int(message.get("primary", 0)),
                    secondary=int(message.get("secondary", 0)),
                    timestamp_ms=0,
                )
            )
        elif kind == "midi":
            data = message.get("data", [])
            if isinstance(data, list):
                self.engine.midi.inject([int(b) for b in data])
        elif kind == "tempo":
            self.engine.clock.set_bpm(float(message.get("bpm", self.engine.clock.bpm)))
        elif kind == "switch":
            self.engine.switch(str(message.get("id", "")))


def _encode_frame(payload: bytes) -> bytes:
    length = len(payload)
    if length < 126:
        head = bytes([0x81, length])
    elif length < 65536:
        head = bytes([0x81, 126]) + length.to_bytes(2, "big")
    else:
        head = bytes([0x81, 127]) + length.to_bytes(8, "big")
    return head + payload


async def _read_exact(reader: asyncio.StreamReader, count: int) -> bytes | None:
    try:
        return await reader.readexactly(count)
    except asyncio.IncompleteReadError:
        return None


async def _read_frame(reader: asyncio.StreamReader) -> bytes | None:
    head = await _read_exact(reader, 2)
    if head is None:
        return None
    opcode = head[0] & 0x0F
    masked = head[1] & 0x80
    length = head[1] & 0x7F
    if length == 126:
        extra = await _read_exact(reader, 2)
        if extra is None:
            return None
        length = int.from_bytes(extra, "big")
    elif length == 127:
        extra = await _read_exact(reader, 8)
        if extra is None:
            return None
        length = int.from_bytes(extra, "big")
    if length > 1_000_000:
        return None
    mask = b""
    if masked:
        mask = await _read_exact(reader, 4) or b""
        if len(mask) != 4:
            return None
    data = await _read_exact(reader, length) if length else b""
    if data is None:
        return None
    if masked:
        data = bytes(byte ^ mask[i % 4] for i, byte in enumerate(data))
    if opcode == 0x8:
        return None
    if opcode != 0x1:
        return b""
    return data


_BARE_PAGE = b"""<!doctype html><meta charset=utf-8><title>Pi Piper bench</title>
<body style="font-family:Georgia,serif;background:#211c16;color:#f4efe4;padding:2rem">
<h1>Pi Piper bench</h1>
<p>The simulator UI has not been built yet. From the repo run <code>npm install && npm run build</code> inside <code>sim-web</code>, then reload.</p>
<p>Pi Piper is not affiliated with or endorsed by Native Instruments.</p>
</body>"""
