# Hardware test checklist

Run this with the controller you will take on stage. The simulator does not
count as a pass. Tick the lines in the commit message or the show notes when
they pass. Stop at the first red line that mentions encryption or a
signature; that is a legal stop, not a bug to route around.

## Before power

- [ ] The card was flashed from Raspberry Pi OS Lite or from a pi-gen image
      built with `image/pi-gen`, then provisioned with `image/provision.sh`.
- [ ] `pi-piper doctor` shows the udev rule and `pi-piper.service`.
- [ ] The console banner contains the sentence that Pi Piper is not affiliated
      with, endorsed by, or sponsored by Native Instruments.
- [ ] SSH from another machine works with a key, and no default password is
      in the image.

## Mikro MK3

- [ ] `lsusb` shows `17cc:1700`.
- [ ] A hidraw node appears and is in group `audio`
      (`ls -l /dev/hidraw*`).
- [ ] `pi-piper run` opens the device without root.
- [ ] The panel shows the four-line independence notice, then the launcher.
- [ ] Striking each of the 16 pads lights a launcher or sequencer cell, and
      the top-left pad is report index 0.
- [ ] A soft hit and a hard hit produce different MIDI velocities on the
      `Pi Piper` port (`aseqdump -p Pi Piper` or a DAW).
- [ ] After a strike, leaning on the pad changes polyphonic aftertouch in
      MIDI mode and does not retrigger the note.
- [ ] Every key in `docs/protocol.md` changes a bit. Encoder press and
      encoder touch are distinct.
- [ ] The encoder steps up and down, including across the 15→0 wrap, one
      step at a time when turned slowly.
- [ ] One finger on the strip moves controller 11 in MIDI mode. A second
      finger is reported on `/pipiper/strip` and does not jump the first.
- [ ] Key lamps show off, dim, medium, and full (`0x00`, `0x7C`, `0x7E`,
      `0x7F`) on Play while you change apps.
- [ ] Pad colours: red, green, blue, and white are distinguishable. If a
      colour is clearly the wrong hue, stop and fix the palette byte, do
      not load vendor software to compare screenshots.
- [ ] The strip lamps fill left to right with the clock.
- [ ] The panel updates while the sequencer is running and survives a minute
      of continuous drawing.
- [ ] Shift+Stop returns to the launcher from every built-in app.
- [ ] Unplugging the controller and plugging it back is recovered by
      `pi-piper run` without a reboot.

## Full-size MK3

- [ ] `lsusb` shows `17cc:1600` and the unit has its own power supply.
- [ ] Pi Piper opens interface 5 and both panels show the centred mono picture.
- [ ] The red/green/blue swatch (draw one solid colour at a time from a
      scratch app) matches the colour you asked for. If the channels are
      swapped, the only change allowed is the packing in `mk3_transfers`.
- [ ] Confirm there is still no challenge or encrypted blob on the bulk
      endpoint. If there is, stop and write it into `docs/legal-flags.md`.
- [ ] Pads and keys are expected to do nothing. That is the documented gap,
      not a failure of the panel test.

## Audio and survival

- [ ] A class-compliant interface plays a SuperCollider or Pure Data tone
      through PipeWire at 48 kHz / 128 without dropouts for ten minutes.
      If it crackles, retry at 256 before changing anything else.
- [ ] MIDI clock from the sequencer reaches a hardware synth through the USB
      MIDI interface and holds tempo against a stopwatch for two minutes.
- [ ] With the overlay enabled, pull the power supply mid-bar. The next boot
      reaches SSH and the launcher without `fsck` repairs.
- [ ] `sudo pi-piper-update` on a dirty tree reboots writable, applies, and
      returns to the overlay. Confirm with `findmnt /` after the second boot.

## Record the run

Write the board model, the kernel (`uname -a`), the controller model, and
the firmware version the unit already had. Do not extract that version by
dumping firmware; read it from the device's own about screen if it has one,
or leave it blank.
