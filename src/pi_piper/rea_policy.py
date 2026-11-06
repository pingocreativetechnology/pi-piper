# SPDX-License-Identifier: MIT
"""Gate in front of REA.

REA may inspect open-source driver trees and captures we made ourselves.
It may not be pointed at Native Instruments software, firmware, updaters,
decompiler projects, or files that carry rendered product graphics.
"""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

DENY_FRAGMENTS = (
    "native-instruments",
    "native_instruments",
    "native instruments",
    "inmusic",
    "nihia",
    "komplete",
    "kontakt",
    "traktor",
    "maschine 2",
    "maschine2",
    "midi_mode.bin",
    "bitwig.ncmm3",
    ".dll",
    ".exe",
    ".dfu",
    ".syx",
    "firmware",
    "updater",
    ".gpr",
    ".idb",
    ".i64",
)

DENY_OPTIONS = (
    "--provider=ghidra",
    "--provider=hopper",
    "--provider=ida",
    "--provider=kuna",
    "--provider=jadx",
)

DENY_COMMANDS = ("decompile", "disassemble", "extract-artifact")

# Roots REA is allowed to read. Jimpo's tree is excluded on purpose: it is
# GPL-3.0 and it contains a rendered screen bitmap plus a controller-editor
# template. The MIT trees are source, which REA may inventory.
ALLOW_ROOTS = (
    Path("/tmp/reference/mikro-mk3"),
    Path("/tmp/reference/ni-display"),
    Path("/tmp/rea-work"),
)


class PolicyError(PermissionError):
    pass


def _normalise(text: str) -> str:
    return text.replace("\\", "/").lower()


def assess(argv: list[str]) -> None:
    """Raise PolicyError when this REA invocation is outside the black-box rules."""

    if not argv:
        raise PolicyError("REA needs a command")
    lowered = [_normalise(arg) for arg in argv]
    command = lowered[0]
    if command in DENY_COMMANDS:
        raise PolicyError(f"REA command {argv[0]!r} is disabled. Decompilers stay off.")
    for arg in lowered:
        for option in DENY_OPTIONS:
            if arg == option or arg.startswith(option):
                raise PolicyError(
                    "Ghidra, Hopper, IDA, JADX and Kuna are disabled. "
                    "Pi Piper does not decompile Native Instruments software or firmware."
                )
        for fragment in DENY_FRAGMENTS:
            if fragment in arg:
                raise PolicyError(
                    f"refusing {arg!r}: it matches a blocked Native Instruments "
                    "or firmware path. Black-box inputs only."
                )
    paths = [arg for arg in argv[1:] if arg.startswith("/") or arg.startswith(".")]
    # Also catch a target that is not a flag.
    for arg in argv[1:]:
        if arg.startswith("-"):
            continue
        if arg in ("json",):
            continue
        candidate = Path(arg)
        if candidate.exists() or arg.startswith("/") or "/" in arg:
            paths.append(arg)
    if command in ("--help", "-h", "help", "--version", "version", "providers", "doctor"):
        if command == "doctor" and any(part.startswith("--provider") for part in lowered):
            raise PolicyError("doctor may not select a decompiler provider")
        return
    if not paths:
        raise PolicyError("REA needs an explicit file inside an allow-listed directory")
    for raw in paths:
        if raw.startswith("-"):
            continue
        path = Path(raw).expanduser().resolve()
        if not _allowed(path):
            raise PolicyError(
                f"{path} is outside the allow list ({', '.join(str(p) for p in ALLOW_ROOTS)}). "
                "Add a capture only after confirming it contains no product graphics."
            )


def _allowed(path: Path) -> bool:
    for root in ALLOW_ROOTS:
        try:
            path.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        assess(args)
    except PolicyError as exc:
        print(f"pi-piper rea: blocked: {exc}", file=sys.stderr)
        return 2
    rea = os.environ.get("REA_BIN", "rea")
    print("pi-piper rea: allowed:", " ".join(shlex.quote(part) for part in args), file=sys.stderr, flush=True)
    os.execvp(rea, [rea, *args])
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
