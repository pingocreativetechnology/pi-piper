# SPDX-License-Identifier: MIT

import asyncio
import json

import websockets

from pi_piper.drivers import SimDevice, find_hidraw
from pi_piper.engine import Engine
from pi_piper.midi import MidiHub
from pi_piper.osc import OscHub
from pi_piper.server import BenchServer


def test_hidraw_scan(tmp_path):
    device = tmp_path / "hidraw3" / "device"
    device.mkdir(parents=True)
    (device / "uevent").write_text("HID_ID=0003:000017CC:00001700\n", encoding="utf-8")
    assert find_hidraw(0x17CC, 0x1700, sysfs_root=str(tmp_path)) == "/dev/hidraw3"
    assert find_hidraw(0x17CC, 0x1600, sysfs_root=str(tmp_path)) is None



def test_websocket_switches_app():
    async def scenario():
        eng = Engine(SimDevice(), midi=MidiHub("loopback"), osc=OscHub(enabled=False))
        server = BenchServer(eng, "127.0.0.1", 0)
        await server.start()
        clock = asyncio.create_task(server._clock())
        try:
            async with websockets.connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
                raw = await asyncio.wait_for(ws.recv(), 1)
                hello = json.loads(raw)
                assert hello["app"]["id"] == "launcher"
                assert "not affiliated" in hello["disclaimer"].lower()
                await ws.send(json.dumps({"type": "pad", "index": 0, "phase": "strike", "value": 2000}))
                await ws.send(json.dumps({"type": "pad", "index": 0, "phase": "release", "value": 0}))
                seen = ""
                for _ in range(6):
                    payload = json.loads(await asyncio.wait_for(ws.recv(), 1))
                    seen = payload["app"]["id"]
                    if seen == "sequencer":
                        break
                assert seen == "sequencer"
        finally:
            clock.cancel()
            if server._server is not None:
                server._server.close()

    asyncio.run(scenario())
