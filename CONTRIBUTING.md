# Contributing

Pi Piper is an independent project. It is not affiliated with Native
Instruments. Contributions have to keep it that way.

## Licence and sign-off

The working licence is MIT. Kenneth makes the final call (`docs/licence.md`).
Do not add GPL-3.0 code, including MusicPI, Zynthian, or GPL controller
drivers. If a change cannot be written without that code, stop and say so
in the pull request instead of pasting it.

By submitting a patch you agree to the Developer Certificate of Origin:

```
Developer Certificate of Origin
Version 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source licence
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    licence and I have the right under that licence to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source licence (unless I am
    permitted to submit under a different licence), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source licence(s) involved.
```

Add `Signed-off-by: Your Name <you@example.com>` as the last line of the
commit message. `git commit -s` does this.

## Reverse engineering

- Black box only: your own USB captures, the device's own descriptors, and
  permissive open drivers.
- Run REA only through `tools/rea-blackbox`. Do not point Ghidra, Hopper,
  IDA, or REA at Native Instruments software, drivers, firmware, or updaters.
- Do not commit firmware, samples, presets, fonts, logos, product photos,
  manual text, or raw captures that contain panel bitmaps.
- Write protocol changes in your own words in `docs/protocol.md` and name
  the source of each new fact (capture file and date, or the permissive
  driver and file). Append the REA summary to `provenance/REA-LOG.md`.
- If you meet encryption, an authentication handshake, or signed firmware,
  stop that part of the work and add a row to `docs/legal-flags.md`.

## Code

- Python 3.11+. `PYTHONPATH=src python3 -m pytest` should pass.
- New performance ideas belong in an `App` subclass. The three built-in
  apps are the reference for lamps, the clock, and MIDI.
- The bench UI must keep the independence notice on screen.
- Do not add a dependency on a Native Instruments library, header, or SDK.

## Hardware changes

A change to report parsing or lamp encoding needs a tick on
`docs/hardware-test.md` from someone with the controller, or it stays behind
a note that it is untested on hardware. Simulator tests are required either
way.
