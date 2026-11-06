#!/bin/bash -e
# pi-gen runs this inside the image chroot, after packages from 00-packages.
# Copy the Pi Piper source in from the build host before invoking pi-gen:
#   sudo mkdir -p "${ROOTFS_DIR}/opt/pi-piper"
# is not available here. Instead, place a tarball at /opt/pi-piper-src.tgz
# on the build host and export PI_PIPER_TARBALL to that path. This script
# copies from "${PI_PIPER_TARBALL:-/opt/pi-piper-src.tgz}" if the file was
# bound into the chroot at the same path.

if [ -f /opt/pi-piper-src.tgz ]; then
  mkdir -p /opt/pi-piper
  tar -C /opt/pi-piper -xzf /opt/pi-piper-src.tgz
else
  echo "No /opt/pi-piper-src.tgz inside the chroot."
  echo "Bind or copy a tarball of this repository there before build.sh."
  exit 1
fi

# Overlay is armed, not enabled, inside the chroot. raspi-config needs the
# running kernel, so pi-piper-firstboot does it on the real first boot.
PI_PIPER_USER=performer PI_PIPER_ENABLE_OVERLAY=1 bash /opt/pi-piper/image/provision.sh

# provision.sh ran apt-get update again; that is fine.
# Drop a marker the host can see in the image log.
echo "pi-piper stage installed" > /etc/pi-piper/IMAGE
