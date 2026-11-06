# Source offer for the system image

Pi Piper's own code is in this repository under the MIT licence (see
`docs/licence.md`; Kenneth makes the final licence call).

A card or image produced with `image/provision.sh` or pi-gen also contains
Raspberry Pi OS Lite and the packages that script installs. Those programs
keep their own licences. For every GPL-covered package on a given card
(including the kernel), corresponding source is the source package in the
Debian or Raspberry Pi OS archive that the card's apt sources point at, for
the exact version `dpkg -l` reports.

To collect that source on a writable boot of the card:

```bash
mkdir -p /var/tmp/pi-piper-source
cd /var/tmp/pi-piper-source
dpkg -l | awk '/^ii/ {print $2 "=" $3}' > installed.txt
# Download source for the GPL packages you ship. apt-get source reads the
# versions in the configured deb-src lines. Enable deb-src first.
sudo sed -i 's/^# *deb-src/deb-src/' /etc/apt/sources.list /etc/apt/sources.list.d/*.list || true
sudo apt-get update
while read -r pkg; do
  name="${pkg%%=*}"
  apt-cache show "$name" | awk '/^License: GPL/ {found=1} END {exit !found}' \
    && apt-get source "$pkg" || true
done < installed.txt
```

Written offer: for three years after the image is handed to someone, the
person who published that image will provide this corresponding source to
any third party, on request, for the cost of physically performing the
distribution. Publish the request address next to the image. This file is
the procedure; it is not itself a filled-in postal offer.

Raspberry Pi OS boot firmware is under Raspberry Pi Ltd's own terms. Check
those terms before you redistribute an image. Pi Piper does not strip or
replace that firmware.

Pi Piper does not add Native Instruments firmware to the image.
