# Architecture

```
controller or bench
        │  HID reports / WebSocket JSON
        ▼
   device driver  ── SimDevice, MikroMk3, Mk3
        │  InputEvent
        ▼
     Engine  ── clock, shift+stop, OSC tap, note gates
        │
        ▼
   one App   ── Launcher, Steps, Clips, MIDI, or yours
        │  Surface (pads, keys, strip, 128×32)
        ▼
   driver.push  ── lamps and panel, or the bench picture
        │
        ├── virtual MIDI port "Pi Piper"
        └── OSC :9000 and text UDP :9002
```

The engine is single-threaded. `tick(dt)` polls the device, advances the
clock, delivers events, paints, and pushes. The bench server calls it from
one asyncio task and from the WebSocket reader; `tick` itself does not
await, so a call runs to the end.

Apps never see a file descriptor. They use `Host` (`src/pi_piper/sdk.py`):
`pad`, `light`, `strip`, `screen`, `midi`, `note`, `osc`, `set_tempo`,
`switch`. `paint` redraws the whole surface. The engine clears the lamps
first.

`MikroMk3` finds `/dev/hidrawN` by the USB id in sysfs and reads reports
itself, so a show does not need the `hidapi` package. `Mk3` uses pyusb for
the panel bulk endpoint and refuses to pretend it understands the keys.

The image is a stock Lite userspace plus `image/provision.sh`. The launcher
is `pi-piper run` under systemd, on tty1, so the notice and the waiting line
are the boot screen.
