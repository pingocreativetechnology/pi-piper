# SPDX-License-Identifier: MIT
"""Read-only checks. Doctor never changes the machine."""

from __future__ import annotations

import os
import shutil
import subprocess


def _line(ok: bool, label: str, detail: str) -> str:
    mark = "ok " if ok else "no "
    return f"[{mark}] {label}: {detail}"


def run() -> int:
    notes = []
    uname = os.uname()
    rt = any(token in uname.release.lower() for token in ("rt", "preempt"))
    notes.append(_line(True, "kernel", uname.release))
    notes.append(_line(rt, "low-latency kernel", "name contains rt or preempt" if rt else "stock kernel; see image/provision.sh"))

    overlay = False
    if os.path.exists("/proc/mounts"):
        with open("/proc/mounts", "r", encoding="utf-8", errors="replace") as handle:
            mounts = handle.read()
        overlay = " overlay " in f" {mounts}" or "overlayroot" in mounts
    notes.append(_line(overlay, "overlay root", "active" if overlay else "not active (expected on a dev machine)"))

    governor = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    if os.path.exists(governor):
        mode = open(governor, encoding="utf-8").read().strip()
        notes.append(_line(mode == "performance", "cpu governor", mode))
    else:
        notes.append(_line(False, "cpu governor", "cpufreq not exposed"))

    for tool in ("pipewire", "jackd", "ssh"):
        found = shutil.which(tool) is not None
        notes.append(_line(found, tool, "on PATH" if found else "not installed"))

    rules = "/etc/udev/rules.d/80-pi-piper.rules"
    notes.append(_line(os.path.exists(rules), "udev rule", rules if os.path.exists(rules) else "not installed"))

    hid = "/sys/class/hidraw"
    count = len(os.listdir(hid)) if os.path.isdir(hid) else 0
    notes.append(_line(True, "hidraw nodes", str(count)))

    try:
        out = subprocess.check_output(["systemctl", "is-active", "pi-piper.service"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        out = "not-installed"
    notes.append(_line(out == "active", "pi-piper.service", out))
    print("\n".join(notes))
    print("Doctor only reports. It does not flash, install, or talk to a controller.")
    return 0
