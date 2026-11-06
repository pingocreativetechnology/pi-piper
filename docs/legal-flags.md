# Compatibility limits

Short note on what Pi Piper supports today, and notices that have to stay
visible. This is not legal advice.

## Current limits

| Topic | Status |
|---|---|
| Mikro MK3 pads, keys, encoder, strip, lamps, mono panel | Supported |
| Full-size MK3 colour panels | Supported |
| Full-size MK3 pads, keys, encoders, lamps | Not implemented yet |
| Full-size MK3 audio and DIN MIDI | Not implemented |
| Firmware updates for either controller | Out of scope — use the vendor's own tools |
| Vendor firmware, software, samples, fonts, manuals | Not shipped and not required |

Do not invent support for an unsupported control surface without testing it
on that hardware. Tick `docs/hardware-test.md` when something is proven.

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

## Before a public release

- Clearance of the word Pi Piper as a project name.
- Raspberry Pi OS redistribution terms, before any image file is published.
- Kenneth's final licence choice (`docs/licence.md`).
