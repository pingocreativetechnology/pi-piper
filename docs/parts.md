# Parts

A list of what a stage box is made of. No retailer, no price, and nothing
in this project was purchased. Check current boards and supplies yourself.
Rough prices in the November 2026 research note are already stale.

## The box

- A recent Raspberry Pi board with USB host ports. A Pi 5 has the headroom
  for SuperCollider and a small quantum. A Pi 4 is enough for the sequencer,
  the clip launcher, and MIDI.
- The official power supply for that board. A shared stage power strip is a
  common cause of USB dropouts; give the board its own supply.
- A microSD card, A2, 32 GB or larger.
- An active cooler on a Pi 5. The performance governor will otherwise thermal
  throttle.
- A case that still lets you reach the SD card.

## The controller

- Native Instruments Maschine Mikro MK3. This is the model Pi Piper's control
  driver is written for. It is bus-powered. One small mono panel.
- Or a Native Instruments Maschine MK3 if you need the two colour panels and
  the DIN sockets. Pi Piper drives the panels and does not yet parse that
  model's pads or keys (see `docs/legal-flags.md`). It also wants its own
  power supply for full lamp brightness; on USB power the lamps stay dim.
  Pi Piper does not change that.

Pi Piper is not affiliated with Native Instruments. The names above identify
the hardware.

## Around it

- A powered USB hub if the controller and an audio interface share the board's
  ports. Unpowered hubs brown out.
- A class-compliant USB audio interface. The image does not ship a vendor
  driver for any interface.
- A class-compliant USB MIDI interface, or a USB-to-DIN lead, when the
  destination is a hardware synth. The virtual `Pi Piper` port is inside the
  box; an interface carries it out.
- An Ethernet lead or a known-good USB Wi-Fi path for SSH. Do the first
  update on a bench, not on a dark stage.

## Not required

- A Teensy, a display, a desktop environment, or any Native Instruments
  application. The controller stays on the factory firmware it already has.
  Update that firmware, if you ever do, with the vendor's own tool on a
  machine you choose. Pi Piper does not ship or install firmware.
