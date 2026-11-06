#!/bin/bash
# Install Pi Piper onto a Raspberry Pi OS Lite system.
# Safe to run more than once. Refuses to run as a non-root user.
# Does not download Native Instruments software or firmware.

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "provision.sh needs root (sudo)." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_NAME="${PI_PIPER_USER:-performer}"
ENABLE_OVERLAY="${PI_PIPER_ENABLE_OVERLAY:-0}"

echo "Pi Piper provision from ${ROOT}"
echo "Pi Piper is not affiliated with or endorsed by Native Instruments."

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  python3 python3-pip python3-venv \
  alsa-utils \
  pipewire pipewire-jack wireplumber \
  jackd2 \
  libasound2 \
  openssh-server \
  git \
  ca-certificates

# Real-time kernel, when this board's archive publishes one.
if RT_PKG="$(apt-cache search --names-only '^linux-image-(rpi-.*-rt|rt-arm64)$' | awk '{print $1}' | head -n 1)"; then
  if [[ -n "${RT_PKG}" ]]; then
    echo "Installing real-time kernel package ${RT_PKG}"
    apt-get install -y "${RT_PKG}" || echo "RT kernel package failed; continuing with low-latency settings."
  else
    echo "No PREEMPT_RT image in the configured apt sources."
    echo "Low-latency settings (governor, rtprio, PipeWire quantum) are still applied."
  fi
fi

if ! id -u "${USER_NAME}" >/dev/null 2>&1; then
  adduser --disabled-password --gecos "Pi Piper performer" "${USER_NAME}"
fi
usermod -a -G audio,plugdev "${USER_NAME}"

install -d -o "${USER_NAME}" -g "${USER_NAME}" /opt/pi-piper
if [[ "${ROOT}" != "/opt/pi-piper" ]]; then
  # Copy the tree. Skip local build debris.
  tar -C "${ROOT}" \
    --exclude node_modules \
    --exclude .git \
    --exclude sim-web/node_modules \
    --exclude __pycache__ \
    -cf - . | tar -C /opt/pi-piper -xf -
  chown -R "${USER_NAME}:${USER_NAME}" /opt/pi-piper
fi

install -d /etc/pi-piper
install -m 0644 "${ROOT}/image/boot/BOOT_NOTICE" /etc/pi-piper/BOOT_NOTICE
# Console notice before login, and again via the banner service.
if [[ -d /etc/issue.d ]]; then
  install -m 0644 "${ROOT}/image/boot/BOOT_NOTICE" /etc/issue.d/pi-piper.issue
fi
# Some images only read /etc/issue.
if ! grep -q "not affiliated with" /etc/issue 2>/dev/null; then
  cat "${ROOT}/image/boot/BOOT_NOTICE" >> /etc/issue
  echo >> /etc/issue
fi

install -m 0644 "${ROOT}/image/udev/80-pi-piper.rules" /etc/udev/rules.d/80-pi-piper.rules
udevadm control --reload || true
udevadm trigger --subsystem-match=hidraw || true
udevadm trigger --subsystem-match=usb || true

install -d /etc/security/limits.d
install -m 0644 "${ROOT}/image/audio/limits.conf" /etc/security/limits.d/pi-piper-audio.conf
install -d /etc/pipewire/pipewire.conf.d
install -m 0644 "${ROOT}/image/audio/80-pi-piper.conf" /etc/pipewire/pipewire.conf.d/80-pi-piper.conf

sed "s/^User=performer/User=${USER_NAME}/" "${ROOT}/image/systemd/pi-piper.service" > /etc/systemd/system/pi-piper.service
install -m 0644 "${ROOT}/image/systemd/pi-piper-banner.service" /etc/systemd/system/pi-piper-banner.service
install -m 0644 "${ROOT}/image/systemd/pi-piper-performance.service" /etc/systemd/system/pi-piper-performance.service
install -m 0644 "${ROOT}/image/systemd/pi-piper-firstboot.service" /etc/systemd/system/pi-piper-firstboot.service
install -m 0755 "${ROOT}/image/scripts/pi-piper-update" /usr/local/sbin/pi-piper-update
install -m 0755 "${ROOT}/image/scripts/pi-piper-firstboot" /usr/local/sbin/pi-piper-firstboot

# Optional threadirqs on the kernel command line. Idempotent.
for CMDLINE in /boot/firmware/cmdline.txt /boot/cmdline.txt; do
  if [[ -f "${CMDLINE}" ]] && ! grep -q 'threadirqs' "${CMDLINE}"; then
    sed -i 's/$/ threadirqs/' "${CMDLINE}"
    echo "Added threadirqs to ${CMDLINE}"
  fi
done

if [[ -n "${PI_PIPER_SSH_PUBKEY:-}" ]]; then
  HOME_DIR="$(getent passwd "${USER_NAME}" | cut -d: -f6)"
  install -d -m 0700 -o "${USER_NAME}" -g "${USER_NAME}" "${HOME_DIR}/.ssh"
  touch "${HOME_DIR}/.ssh/authorized_keys"
  grep -qxF "${PI_PIPER_SSH_PUBKEY}" "${HOME_DIR}/.ssh/authorized_keys" || echo "${PI_PIPER_SSH_PUBKEY}" >> "${HOME_DIR}/.ssh/authorized_keys"
  chown "${USER_NAME}:${USER_NAME}" "${HOME_DIR}/.ssh/authorized_keys"
  chmod 0600 "${HOME_DIR}/.ssh/authorized_keys"
fi

systemctl daemon-reload
systemctl enable ssh || systemctl enable ssh.service || true
systemctl enable pi-piper-banner.service
systemctl enable pi-piper-performance.service
systemctl enable pi-piper.service
if [[ "${ENABLE_OVERLAY}" == "1" ]]; then
  systemctl enable pi-piper-firstboot.service
  echo "Overlay will be enabled on the next boot by pi-piper-firstboot."
else
  echo "Overlay not requested. Set PI_PIPER_ENABLE_OVERLAY=1 on a Raspberry Pi OS card to arm it."
fi

# Make the launcher importable for this user without a venv.
PYTHONPATH="${ROOT}/src" python3 -c 'import pi_piper; print("pi-piper", pi_piper.__version__)'

echo "Provision finished."
echo "Reboot to start the launcher on tty1."
