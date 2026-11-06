# System image

Raspberry Pi OS Lite, provisioned. Read `docs/flashing.md` before building.

- `provision.sh` — run on a fresh Lite card, as root.
- `scripts/pi-piper-firstboot` — enables the official overlay root and reboots.
- `scripts/pi-piper-update` — SSH update through a writable maintenance boot.
- `systemd/` — launcher, console notice, performance governor, first boot.
- `udev/80-pi-piper.rules` — hidraw access for product ids `1700` and `1600`.
- `audio/` — PipeWire quantum and real-time limits.
- `boot/BOOT_NOTICE` — the independence notice printed on tty1.
- `pi-gen/` — a stage to drop into the official pi-gen builder.
- `SOURCE-OFFER.md` — how GPL package source is provided for an image.

`bash -n` is the check this repository runs. Producing the zip needs pi-gen
on a machine with root and a lot of disk, which is not this one.
