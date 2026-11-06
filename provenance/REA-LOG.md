# REA session log

Recorded 5 November 2026 in the build environment. REA was `rea-agents` 6.8.0,
invoked only through `tools/rea-blackbox`. Ghidra, Hopper, IDA, JADX and Kuna
were not started. No Native Instruments software, driver, firmware, or
updater was present or opened.

## Policy checks (wrapper exited before REA)

| Invocation | Result |
|---|---|
| `decompile /tmp/rea-work/sample-report.bin` | blocked, exit 2. Decompile is disabled. |
| `inspect-artifact --provider=ghidra` on the MIT driver README | blocked, exit 2. Decompiler providers are disabled. |
| `inspect-artifact /opt/native-instruments/Maschine 2.exe` | blocked, exit 2. The path matches the vendor denylist. The file was not created. |
| `inspect-artifact` on `midi_mode.bin` in the GPL fork | blocked, exit 2. Rendered screen bitmaps are denied. |

## Allowed calls

`rea --help` ran and reported `rea@6.8.0`.

`rea inspect-artifact /tmp/rea-work/sample-report.bin --json` was allowed.
The file is 64 bytes written by this project: report id `0x02`, one pad group
(index 12, strike nibble `0x10`, value `0x40`), then zeros. It is not a
capture from vendor software and contains no panel bitmap.

REA's reply:

```
code: target_unavailable
category: unsupported_target
message: Cannot open artifact: unsupported binary format.
```

That is the correct stop. A raw HID report is not a container REA knows, and
the wrapper does not offer a decompiler as a fallback. The byte layout in
`docs/protocol.md` comes from reading the MIT-licensed driver, not from this
inspection.

There was no physical controller and no USB capture in this environment, so
REA was not shown a device descriptor or a pcap. A later capture goes through
the same wrapper and gets a new section in this file. If that capture shows
encryption, a challenge, or a signature, work on that report stops.
