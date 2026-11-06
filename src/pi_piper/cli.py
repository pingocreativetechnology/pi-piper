# SPDX-License-Identifier: MIT
"""Command line. ``pi-piper sim`` is the bench. ``pi-piper run`` is the stage."""

from __future__ import annotations

import argparse
import sys
import time

from . import DISCLAIMER, __version__
from .drivers import SimDevice, open_first_controller
from .engine import Engine, load_app_file
from .midi import MidiHub
from .osc import OscHub


def _engine(device, args) -> Engine:
    apps = None
    if getattr(args, "app", None):
        from .apps import Launcher

        extra = []
        for path in args.app:
            extra.extend(load_app_file(path))
        apps = [Launcher(), *extra]
        # Keep the three examples available alongside a user app unless asked not to.
        if not args.only:
            from .apps import builtin_apps

            user_ids = {app.id for app in extra}
            apps = [Launcher()] + [app for app in builtin_apps() if app.id != "launcher" and app.id not in user_ids]
            apps.extend(extra)
    midi_backend = "loopback" if args.midi == "loopback" else "auto"
    return Engine(
        device,
        apps=apps,
        midi=MidiHub(backend=midi_backend),
        osc=OscHub(host=args.osc_host, osc_port=args.osc_port, text_port=args.text_port, enabled=not args.no_osc),
    )


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--app", action="append", default=[], help="Python file with an App subclass")
    parser.add_argument("--only", action="store_true", help="with --app, hide the built-in performances")
    parser.add_argument("--midi", choices=("auto", "loopback"), default="auto")
    parser.add_argument("--osc-host", default="127.0.0.1")
    parser.add_argument("--osc-port", type=int, default=9000)
    parser.add_argument("--text-port", type=int, default=9002)
    parser.add_argument("--no-osc", action="store_true")


def cmd_sim(args: argparse.Namespace) -> int:
    print(DISCLAIMER)
    print(f"Pi Piper bench on http://{args.host}:{args.port}  (WebSocket /ws)")
    engine = _engine(SimDevice(), args)
    engine.tick(0.0)
    from .server import BenchServer
    import asyncio

    server = BenchServer(engine, args.host, args.port)
    try:
        asyncio.run(server.serve_forever())
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        engine.midi.close()
        engine.osc.close()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    print(DISCLAIMER)
    print("Compatible with Native Instruments Maschine Mikro MK3 and MK3 controllers.")
    print("Shift + Stop returns to the launcher. Pulling power is safe once the overlay root is enabled.")
    while True:
        device = open_first_controller()
        if device is None:
            print("Waiting for a controller. `pi-piper sim` runs the same apps with no hardware.")
            try:
                time.sleep(args.poll)
            except KeyboardInterrupt:
                return 0
            continue
        print(f"Opened {device.model}.")
        engine = _engine(device, args)
        try:
            previous = time.monotonic()
            while True:
                now = time.monotonic()
                engine.tick(now - previous)
                previous = now
                time.sleep(0.002)
        except KeyboardInterrupt:
            device.close()
            engine.stop_transport()
            engine.midi.close()
            return 0
        except Exception as exc:  # hardware unplug, USB reset
            print(f"device closed: {exc}")
            try:
                device.close()
            except Exception:
                pass
            time.sleep(1)


def cmd_doctor(args: argparse.Namespace) -> int:
    from . import doctor

    return doctor.run()


def cmd_tui(args: argparse.Namespace) -> int:
    from .tui import run_tui

    print(DISCLAIMER)
    engine = _engine(SimDevice(), args)
    run_tui(engine)
    engine.midi.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pi-piper", description="Pi Piper performance framework")
    parser.add_argument("--version", action="version", version=f"pi-piper {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sim = sub.add_parser("sim", help="run the apps against the virtual controller")
    sim.add_argument("--host", default="127.0.0.1")
    sim.add_argument("--port", type=int, default=44731)
    _add_common(sim)
    sim.set_defaults(func=cmd_sim)

    run = sub.add_parser("run", help="run on a plugged-in controller")
    run.add_argument("--poll", type=float, default=2.0, help="seconds between hardware probes")
    _add_common(run)
    run.set_defaults(func=cmd_run)

    tui = sub.add_parser("tui", help="terminal controller, no browser")
    _add_common(tui)
    tui.set_defaults(func=cmd_tui)

    doctor = sub.add_parser("doctor", help="check the stage image and USB access")
    doctor.set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
