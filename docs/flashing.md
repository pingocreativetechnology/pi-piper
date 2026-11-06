# Flashing the stage card

The image is Raspberry Pi OS Lite with a provisioning script. Pi Piper does
not build an operating system from scratch. Two ways lead to the same
installed system: run the script on a card you flashed yourself, or let
pi-gen run that script while it builds a card image.

Nothing here downloads a vendor music application. The card boots to the
Pi Piper launcher.

## What you end up with

- Raspberry Pi OS Lite, 64-bit, no desktop.
- SSH, so the box can be updated without a display.
- PipeWire as the audio engine, with a JACK interface, 48 kHz and a 128-frame
  quantum (about 2.7 ms per period before interface latency).
- A real-time kernel if the archive for that board publishes one, otherwise
  the performance CPU governor, real-time priority for the `audio` group, and
  the same small quantum.
- A read-only root with a tmpfs overlay, using the overlay switch built into
  Raspberry Pi OS (`raspi-config nonint do_overlayfs 0`). Power loss drops
  the RAM overlay and leaves the card as it was.
- The boot partition stays writable so SSH keys and the update flag survive.
- The console shows the independence notice before the launcher attaches to
  the controller.

## Path A — flash Lite, then provision

This is the path to use while the pi-gen image has not been built on a
machine with enough disk.

1. With Raspberry Pi Imager, choose Raspberry Pi OS Lite (64-bit). Set the
   hostname to `pi-piper`. Enable SSH and paste your public key. Set the
   username you want (`performer` matches the systemd unit). Do not use a
   password you would mind leaking; the repo ships no default password.
2. Boot the board on your network. Confirm `ssh performer@pi-piper.local`.
3. Copy this repository to the board, for example with `git clone` into
   `/opt/pi-piper`, or `rsync -a ./ performer@pi-piper.local:/opt/pi-piper/`.
4. On the board:

   ```bash
   sudo PI_PIPER_USER=performer PI_PIPER_ENABLE_OVERLAY=1 \
     bash /opt/pi-piper/image/provision.sh
   sudo reboot
   ```

5. The first boot service enables the overlay and reboots once more. After
   that, `findmnt /` shows an overlay, and `pi-piper doctor` reports the
   service.

Plug the controller into a USB port after the reboot. The launcher is
already waiting. Shift+Stop on the hardware returns to the app list.

## Path B — build a card image with pi-gen

pi-gen is the official image builder. Pi Piper ships a stage, not a fork.

```bash
sudo apt-get install quilt qemu-user-static debootstrap
git clone https://github.com/RPi-Distro/pi-gen.git
cd pi-gen
git checkout 2025-05-13-raspios-bookworm-arm64   # or the current Lite tag
# The stage below is copied from this repo. Adjust the path.
cp -a /path/to/pi-piper/image/pi-gen/stage-pi-piper ./stage-pi-piper
cp /path/to/pi-piper/image/pi-gen/config.example ./config
```

Edit `config` before building:

- `FIRST_USER_NAME` and a `FIRST_USER_PASS` you choose at build time. Do not
  commit the password.
- `PI_PIPER_SSH_PUBKEY` so the image accepts your key.
- `PI_PIPER_SRC` pointing at a tarball or a checkout of this repo that the
  stage can copy. The example stage expects the source at
  `/opt/pi-piper-src` inside the build, which `stage-pi-piper` documents.

Then `sudo ./build.sh`. The zip in `deploy/` is the card image. Flash it
with Raspberry Pi Imager's "use custom" option. The first boot enables the
overlay and reboots, same as path A.

Building the image needs a large disk and root. This development environment
does not produce the zip; the stage and the provisioner are what is tested
here (`bash -n` on the scripts).

## Audio

PipeWire's quantum lives in
`/etc/pipewire/pipewire.conf.d/80-pi-piper.conf`. For a USB audio interface
that crackles, raise the quantum from 128 to 256 before chasing anything
else. The JACK library is `pipewire-jack`, so Pure Data and SuperCollider
can open JACK clients against PipeWire.

`jackd` is installed as a fallback. Do not run it at the same time as
PipeWire.

## Headless updates

The root is read-only after the overlay is on, so an ordinary package
install vanishes at reboot. Updates are a maintenance boot:

```bash
sudo pi-piper-update
```

That writes a flag on the boot partition, turns the overlay off, and
reboots. The next boot is writable. `pi-piper-update --apply` pulls the git
checkout in `/opt/pi-piper` (the remote is whatever you configured; the
script does not invent one), reinstalls the unit files, turns the overlay
back on, and reboots.

If you would rather copy files over SSH yourself:

```bash
sudo raspi-config nonint do_overlayfs 1
sudo reboot
# writable session: rsync, then
sudo raspi-config nonint do_overlayfs 0
sudo reboot
```

`do_overlayfs 0` enables the overlay. `do_overlayfs 1` disables it. Those
are the non-interactive values in Raspberry Pi OS's `raspi-config`.

SSH stays available on both boots. Keys live under the user's home. Home is
on the root filesystem, so keys written after the overlay is enabled are
lost at power-off. Put long-lived keys in place during the writable
provisioning boot. The boot partition is the other durable store; the
update flag uses it for that reason.

## Kernel

`provision.sh` asks apt for a real-time image (`linux-image-rpi-*-rt` or
`linux-image-rt-arm64`) and installs the first match. If the archive has
none, it says so and continues with the low-latency userspace settings.
Check `uname -a` after reboot. Do not mix an RT kernel from an untrusted
archive; the script only uses the board's configured apt sources.

## Unplug test

After the overlay is on, pull power while the launcher is running. On the
next boot the card should come up clean, SSH should answer, and the
launcher should be waiting. If the card wants a filesystem repair, the
overlay did not engage; run `pi-piper doctor` and read the journal for
`pi-piper-firstboot`.
