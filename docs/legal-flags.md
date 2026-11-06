# Legal flags and technical stops

This is an engineering log, not legal advice. The 5 November 2026 research
note is the background. A lawyer should read the name, the README notice,
the licence, and the provenance log before any public release.

## Stops already taken

| Topic | What Pi Piper did |
|---|---|
| Vendor software, firmware, updaters | Never downloaded, never opened, never passed to REA or a decompiler. The wrapper refuses those paths. |
| Rendered panel bitmaps and editor templates | The GPL fork that contains `midi_mode.bin` and a controller-editor template is not an REA allow root and is not vendored. |
| GPL application code | Not copied. MusicPI and Zynthian are not dependencies. The framework stays MIT only while that remains true. Kenneth chooses the licence. See `docs/licence.md`. |
| Full-size MK3 pads, keys, encoders, lamps | Not implemented. The permissive reference we have describes the panels, not the control reports. We did not open a GPL driver to fill the gap. |
| Firmware update interface on the Mikro MK3 | Not claimed and not written. Signed or encrypted update traffic is out of scope. |
| Full-size MK3 audio and DIN MIDI | Not implemented. No permissive framing notes. |
| Report descriptor | Not invented. We never read one from a device. |
| Colour channel order on the MK3 panels | Provisional RGB565, high byte first. The permissive crate's colour shuffle is marked unfinished upstream. Confirm with the swatch in the hardware checklist before trusting hue. |
| Authentication or encryption | None is described by the MIT Mikro MK3 driver or the MIT panel crate. If a unit asks for a challenge, a signature check, or an encrypted body, stop that model and record it here. Do not implement a workaround. |

## Notices that have to stay visible

- `README.md` carries the full "not affiliated with, endorsed by, or
  sponsored by Native Instruments" notice, and the Raspberry Pi trademark
  line.
- The image prints the same notice on the console at boot
  (`image/boot/BOOT_NOTICE`).
- The launcher draws a short form on the controller panel.
- The bench keeps a one-line form on screen the whole time it is open.

Wording elsewhere should stay nominative: "compatible with Native Instruments
Maschine Mikro MK3 and MK3". The project name does not contain "Maschine",
"NI", or "Raspberry Pi".

## Things a lawyer still needs to see

- Clearance of the word Pi Piper as a project name.
- Raspberry Pi OS redistribution terms, before any image file is published.
- Whether the MK3 panel header constants, which are a 16-byte functional
  sequence restated from an MIT-licensed crate, need any further notice
  beyond the citation in `docs/protocol.md` and `NOTICE`.
- A human pass over `provenance/REA-LOG.md` after any session that inspected
  a capture.
