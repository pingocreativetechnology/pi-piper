# Licence decision

**Working choice: MIT.** The final call belongs to Kenneth. Nothing in this
repository locks that choice in beyond the `LICENSE` file, which can be
replaced before any public release.

## Why this tree is MIT

Pi Piper's Python, the bench UI, the image scripts, and these docs were
written for this project. They do not copy or link:

- MusicPI (`music-pi/music-pi`), GPL-3.0
- Zynthian, GPL-3.0
- the Linux `snd-usb-caiaq` driver, GPL-2.0
- the GPL-3.0 Mikro MK3 forks, including the one that carries a protocol
  essay, a rendered "MIDI mode" bitmap, and a controller-editor template

Those GPL programs were not vendored, not built into the wheel, and not
paraphrased into `src/`. REA is configured so it will not open the GPL fork.
See `NOTICE` and `docs/rea.md`.

MIT-licensed code was used as a reference for facts (report ids, offsets,
panel framing), which are recorded in `docs/protocol.md`. The reference
projects are not shipped. Their copyright notices would be required only if
we distributed their code. We do not.

## When the choice would have to change

If a later change pastes or statically links GPL-3.0 code (MusicPI, Zynthian,
a GPL driver, Tracktion Engine under its GPL option, JUCE under the AGPL
option), the combined work has to be offered under GPL-3.0 or a
GPL-3.0-compatible licence, and MIT on that combined work would be wrong.
Stop and relicense deliberately. Do not "just MIT the file".

Apache-2.0 was the other permissive option. MIT was chosen because the
reference drivers Pi Piper learned from are MIT (or MIT OR Apache-2.0), and
MIT keeps the obligations to a copyright notice. Apache-2.0's patent grant
is worth having if Kenneth prefers it; switching before release is a
one-file change plus the SPDX lines.

## The operating-system image is not the framework licence

An image built from Raspberry Pi OS Lite aggregates thousands of packages
under their own licences. That is aggregation, not a relicense of Pi Piper.
GPL components in the image (the kernel, coreutils, and so on) keep their
licence. `image/SOURCE-OFFER.md` is the written offer for corresponding
source of the GPL packages the provisioner installs, plus a pointer at the
Raspberry Pi OS image the card was flashed from.

Raspberry Pi OS also includes proprietary boot firmware under its own terms.
Pi Piper does not redistribute that firmware by itself. A pi-gen image is a
derivative of Raspberry Pi OS, so anyone who publishes an image needs to
comply with Raspberry Pi OS redistribution terms as well as the GPL. Those
terms were not re-audited for this commit. Do that before handing anyone a
card or a URL.

## What Kenneth should decide before a public release

1. MIT, Apache-2.0, or GPL-3.0-or-later.
2. Whether a published image is in scope at all.
3. Trademark clearance of the name "Pi Piper" in the countries where it will
   be used. This tree only checked that the name does not contain
   "Maschine", "NI", or "Raspberry Pi".
