# What REA was used for

REA (`morluto/rea`, MIT) is a local analysis tool. Pi Piper uses it only as a
black-box inspector, and only through `tools/rea-blackbox`, which refuses the
invocation before REA starts.

## Hard rules encoded in `src/pi_piper/rea_policy.py`

The wrapper exits with status 2, and does not exec REA, when the arguments:

- name Ghidra, Hopper, IDA, JADX, or Kuna as a provider
- ask REA to decompile, disassemble, or extract an artifact
- mention Native Instruments software, NIHIA, Komplete, Kontakt, Traktor,
  an updater, a firmware image, a DFU file, a SysEx dump, a Windows driver
  binary, a Ghidra project, or an IDA database
- point at `midi_mode.bin` or a controller-editor template (`Bitwig.ncmm3`),
  both of which live in a GPL fork and are treated as vendor screen content
  and a vendor template
- point outside three directories:
  - `/tmp/reference/mikro-mk3` (the MIT driver, source only)
  - `/tmp/reference/ni-display` (the MIT OR Apache-2.0 panel crate)
  - `/tmp/rea-work` (files this project creates for the tool, never a
    capture that contains screen bitmaps)

The GPL fork is not an allow root. Proprietary software is not an allow root.
There is no flag that relaxes this. Adding one is a licence decision, not a
convenience.

## What was actually run in this environment

There was no controller on the bench, and there was no USB capture taken
from a host running vendor software. Raw captures of that software are not
collected and would not be committed: they contain the pictures the software
draws.

REA was installed from the public `rea-agents` package and invoked only
through the wrapper. The session log is `provenance/REA-LOG.md`, written
when the tool ran. If that file says the package could not be executed, the
policy module was still unit-tested (`tests/test_server.py`) and the
protocol notes do not depend on a decompiler.

REA was not used to design the apps, the image, or the bench. Those are
ordinary source. The tool's own guidance is to skip it for source you can
already read. It is in the loop so that any later capture or descriptor dump
has exactly one door, and that door is locked against vendor binaries.

## Adding a capture later

1. Take it on a machine that is speaking to hardware you own.
2. If the other end of the cable is vendor software, do not commit the
   pcap. Describe the report layout in your own words in `docs/protocol.md`,
   with the capture's filename and date in the provenance log, and delete
   the pcap from the tree.
3. A capture that is only HID input reports you generated with Pi Piper
   itself may live under `/tmp/rea-work` while you inspect it. Do not move
   it into git if it contains panel bitmaps.
4. Run `tools/rea-blackbox inspect-artifact <file>` or the pcap inspector if
   REA provides one for that file type. Paste the summary into
   `provenance/REA-LOG.md`.
5. If the capture shows a challenge, a signature, or ciphertext, stop work
   on that report and write the stop in `docs/legal-flags.md`. Do not
   "try one more flag".
