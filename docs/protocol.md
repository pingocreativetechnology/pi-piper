# Controller protocol notes

These notes are Pi Piper's own description of the USB traffic a host has to
exchange with two pad controllers in order to perform. They are functional
facts: report ids, byte offsets, and lamp values. They are not a copy of any
other project's source, and they are not a dump of a capture.

No Native Instruments application, driver, firmware image, or updater was
loaded into REA, Ghidra, Hopper, IDA, or any other decompiler. See
[rea.md](rea.md) for the allow list that enforces that.

Where a fact came from is marked inline.

- **MIT driver** means the public userspace driver at
  `r00tman/maschine-mikro-mk3-driver` (MIT). Pi Piper read that source and
  reimplemented the layout. The code in `src/pi_piper/protocol.py` is not a
  transcription of it.
- **MIT display** means `openAVproductions/ni-display` (MIT OR Apache-2.0),
  which frames the two colour panels on the larger 2017 controller.
- **Not captured here** means this environment had no controller attached and
  no USB capture of our own. Those fields are implemented only when an
  MIT-licensed reference already publishes them. They still need the hardware
  checklist before a show.

A second public write-up of the small controller exists in a GPL-3.0 fork.
Pi Piper did not copy that text or that code, and REA is not pointed at that
tree, because the tree also contains a rendered screen bitmap and a
controller-editor template. A few field widths below are marked **capture
notes** when the MIT driver only reads part of a field that the capture
write-up describes in full. Treat those as provisional until you confirm
them on your own hardware with your own capture.

## Identity

| Controller | USB id | What Pi Piper drives | Source |
|---|---|---|---|
| Mikro MK3 (2017, one small mono panel) | vendor `0x17CC`, product `0x1700` | pads, keys, encoder, touch strip, lamps, mono panel | MIT driver |
| Full-size MK3 (2017, two colour panels) | vendor `0x17CC`, product `0x1600` | colour panels only | MIT display |

Both ids are the ids the open drivers open. Pi Piper does not claim any other
product id. Older models, the Jam, and the Studio are named in the driver
registry as unsupported until someone publishes a black-box layout under a
permissive licence or a capture we can describe ourselves.

The Mikro MK3 is not a USB MIDI class device. A host that only opens a MIDI
interface will see silence. Pi Piper reads HID reports and publishes its own
virtual MIDI port.

## What we deliberately do not touch

- The Mikro MK3's second interface is described, outside the MIT driver, as a
  firmware-update interface. Pi Piper never claims it. Firmware update channels
  can be signed. If a unit requires a signature, a challenge, or an encrypted
  body, stop. Do not search for a bypass.
- Feature reports other than the input report the host can read back are not
  sent. The MIT driver brings the lamps and the panel up with ordinary output
  reports and no handshake. That is the behaviour Pi Piper relies on.
- The full-size unit's audio interface and its DIN MIDI ports are not
  implemented. Their framing was not in the MIT display crate.
- Pad, key, encoder, and lamp reports for the full-size unit are a gap. The
  MIT display crate does not describe them. Pi Piper will not fill the gap from
  GPL driver source or from proprietary software. `Mk3.poll()` returns no
  events and says so once.

No encryption and no authentication handshake appears in the MIT Mikro MK3
driver or in the MIT display crate's panel writes. That is an observation
about those sources, not a promise about every firmware revision. The hardware
checklist says to stop if a unit behaves otherwise.

## Mikro MK3 input, report `0x01`

Sent when keys, the encoder, or the strip change. The report id is the first
byte. The MIT driver reads this report from hidraw and treats byte 0 as the id.

| Payload offset (after the id) | Contents | Source |
|---|---|---|
| 0..5 | 48 key bits, little-endian. Bit n lives in byte `n // 8`, mask `1 << (n % 8)`. | MIT driver walks six bytes, eight bits each |
| 6 | Encoder position in the low nibble, range 0..15, wrapping. The MIT driver reads the whole byte. Pi Piper keeps the low nibble, which matches that byte while the high nibble stays 0. | MIT driver, byte index 7 of the raw report |
| 7..8 | Strip timestamp, unsigned 16-bit little-endian milliseconds, wrapping at 65536. | capture notes; the MIT driver does not read it |
| 9..10 | First finger, unsigned 16-bit little-endian. 0 means up. Touched positions fit in the low byte. | MIT driver reads the low byte at raw index 10. The 16-bit width and the 1..200 range are capture notes |
| 11..12 | Second finger, same units. 0 means one finger. | capture notes |

Pi Piper emits a key event only when a bit changes, plus the keys that are
already down on the first report (so a finger resting on Play is not lost).
Encoder motion is the shortest signed step around a 16-position ring. The
first sample sets the origin and does not emit a step.

Key bits, using Pi Piper's names. Bit 0 is the upper-left key that the hardware
prints with the product wordmark; the API calls it `wordmark`.

| Bit | Name | Bit | Name | Bit | Name |
|---|---|---|---|---|---|
| 0 | wordmark | 14 | group | 28 | keyboard |
| 1 | star | 15 | auto | 29 | chords |
| 2 | browse | 16 | lock | 30 | step |
| 3 | volume | 17 | note_repeat | 31 | scene |
| 4 | swing | 18 | restart | 32 | pattern |
| 5 | tempo | 19 | erase | 33 | events |
| 6 | plugin | 20 | tap | 34 | variation |
| 7 | sampling | 21 | follow | 35 | duplicate |
| 8 | left | 22 | play | 36 | select |
| 9 | right | 23 | rec | 37 | solo |
| 10 | pitch | 24 | stop | 38 | mute |
| 11 | mod | 25 | shift | 39 | encoder_press |
| 12 | perform | 26 | fixed_vel | 40 | encoder_touch |
| 13 | notes | 27 | pad_mode | | |

The names for bits 1..40 are the words printed on the keys. The MIT driver
uses the same numbering.

## Mikro MK3 pads, report `0x02`

A list of three-byte groups, starting at raw byte 1. A group of `0, 0, 0`
ends the list. The MIT driver applies that rule after the first group;
capture notes say a real group is never all zeros. Pi Piper stops at the first
all-zero group, including a leading one, so an empty report cannot invent a
hit on pad 0.

Each group is `index, (event << 4) | value[11:8], value[7:0]`. The value is
12 bits, 0..4095. Index 0 is the top-left pad and the index increases across
each row, then down. The hardware's own pad numbers run the other way, from
the bottom-left. Pi Piper's apps use the report index, so the top-left pad is
step 1 in the sequencer.

| High nibble | Phase | Typical value |
|---|---|---|
| `0x00` | touch, no strike yet | pressure |
| `0x10` | strike (the hit crossed the trigger) | strike strength |
| `0x20` | end of a touch that never struck | 0 |
| `0x30` | release after a strike | 0 |
| `0x40` | pressure changed | current pressure |

Source: the MIT driver's pad-event constants, which use these high nibbles.

Pi Piper's MIDI mode maps strength with `round(value * 127 / 4095)`, and a
non-zero reading never becomes velocity 0. Pressure repeats become polyphonic
aftertouch. Touches that never strike do not send notes; their pressure still
arrives as the pressure phase.

The note under a pad, with `root` at the bottom-left pad, is:

```
root + (3 - index / 4) * 4 + (index % 4)
```

Bottom-left is `root`, top-left is `root + 12`. That placement matches the
geometric reading of the report index. It is Pi Piper's map.

## Mikro MK3 lamps, report `0x80`

Eighty payload bytes after the id. Pi Piper sends the report only when the
picture changed. The MIT driver writes the same 80-byte image.

| Payload offset | What |
|---|---|
| 0..38 | Key lamps, same index as the key bit. Encoder press and encoder touch have no lamp. |
| 39..54 | Pad lamps, `39 + report index`. |
| 55..79 | Twenty-five strip lamps, left to right. |

Key and strip bytes use four levels. Source: the MIT driver's brightness
constants, and its README stating that the keys have four levels.

| Level | Byte |
|---|---|
| 0 off | `0x00` |
| 1 dim | `0x7C` |
| 2 medium | `0x7E` |
| 3 full | `0x7F` |

A pad byte is `(colour << 2) | (brightness & 3)`, or `0` when the pad is
dark. Colour numbers, from the MIT driver's palette:

0 off, 1 red, 2 orange, 3 light orange, 4 warm yellow, 5 yellow, 6 lime,
7 green, 8 mint, 9 cyan, 10 turquoise, 11 blue, 12 plum, 13 violet,
14 purple, 15 magenta, 16 fuchsia, 17 white.

Brightness for a pad is the low two bits, 0..3, not the key-lamp bytes.
Pi Piper keeps those two encodings separate on purpose. The bench draws its
own approximation of the colour names; it is not a photograph of the hardware.

## Mikro MK3 panel, report `0xE0`

The panel is 128 by 32, one bit per pixel. A 0 bit is lit. A blank panel is
`0xFF` in every byte. Source: the MIT driver's screen buffer, which starts
filled with `0xFF` and clears a bit to draw.

The buffer is 512 bytes. Pixel `(x, y)` lives at byte `(y // 8) * 128 + x`,
bit `y % 8`, with bit 0 at the top of that eight-pixel band.

The picture is pushed as two output reports. Each begins with the id and four
little-endian unsigned fields: x, y, width, height. `y` and `height` count
bands of eight rows. Both writes use x = 0, width = 128, height = 2. The
first uses y = 0 and the first 256 bytes. The second uses y = 2 and the last
256 bytes. Source: the two 9-byte headers in the MIT driver.

Pi Piper's on-screen type is the 5×7 font in `src/pi_piper/font.py`, drawn for
this project.

## Full-size MK3 colour panels

Source: the MIT display crate. Two panels, each 480×272. The host claims
interface 5 and writes bulk endpoint `0x04`. One frame is four writes:

1. A 16-byte header. Byte 2 selects the panel, 0 or 1. The other bytes are
   the constant sequence published by that crate, beginning `84 00` and
   ending `01 e0 01 10`.
2. Four command bytes `00 00 ff 00`. `0xFF00` is half the pixel count
   (`480 * 272 / 2`).
3. The pixels, 480 × 272 × 2 bytes.
4. An 8-byte footer beginning `03 00 00 00 40 00 00 00`.

Pi Piper stores each pixel as RGB565, high byte first: five bits of red, six
of green, five of blue, taken from an 8-bit RGB frame. The MIT crate's own
colour shuffle is marked unfinished in its source, and this environment never
saw a panel. The red/green/blue swatch in the hardware checklist is the test
that confirms or corrects the channel order. Until that swatch passes, treat
MK3 colour as provisional.

The crate comments that a panel goes black if no frame arrives for about two
seconds. Pi Piper has not confirmed the timeout.

Apps draw the 128×32 mono surface. The MK3 backend scales that picture by
three and centres it on both panels, in a brass-green the bench also uses.
That scaling is Pi Piper's, not a vendor layout.

## MIDI and OSC that Pi Piper adds

These are Pi Piper's ports, not a reconstruction of a vendor MIDI mode.

- Virtual port name: `Pi Piper` (output) and `Pi Piper in` (input), via
  `python-rtmidi` when the system can open a virtual ALSA port.
- Drums in the step and clip apps go out on MIDI channel 10, notes 36, 38,
  42 and 39 (kick, snare, closed hat, clap).
- MIDI mode plays the pad grid from a movable root, sends key controllers
  from the map in `src/pi_piper/apps.py` (controllers 20 and up), puts the
  encoder on controller 3 as a relative step around 64, and puts the strip
  on controller 11.
- Transport uses the real-time messages start (`FA`), clock (`F8` at 24 per
  quarter, unsung), and stop (`FC`).
- OSC goes to UDP port 9000. The same text, space-separated, goes to UDP
  port 9002 so Pure Data can read it with `netreceive` and no external
  library. Addresses are listed in `bridges/README.md`.

## Report descriptor

This environment never read the device's HID report descriptor. Pi Piper does
not invent one. The parser keys off the report id in the first byte, which is
how the MIT driver demultiplexes hidraw reads.
