# Pure Data and SuperCollider

Pi Piper does not host those programs. It publishes a virtual MIDI port and
two UDP feeds, which is enough for either one to be a performance app.

| Feed | Port | Who reads it |
|---|---|---|
| OSC 1.0 | UDP 9000 | SuperCollider `OSCdef`, or a Pure Data OSC library if you have one |
| Plain text | UDP 9002 | Pure Data `netreceive -u 9002`, no extra library |
| MIDI | virtual port `Pi Piper` | both, through ALSA or JACK |

Text lines look like `/pipiper/pad 3 1 2400`. OSC packets use the same
address and integer arguments. The address prefix is `/pipiper`.

| Address | Arguments |
|---|---|
| `/pipiper/pad` | index, phase (0 touch, 1 strike, 2 untouch, 3 release, 4 pressure), raw value |
| `/pipiper/button` | name, 1 or 0 |
| `/pipiper/encoder` | signed steps |
| `/pipiper/strip` | primary, secondary (0..200, 0 is up) |
| `/pipiper/note` | channel, note, velocity (0 is note off) |
| `/pipiper/step` | 16th-note index 0..15 |
| `/pipiper/tempo` | bpm |
| `/pipiper/transport` | `start` or `stop` |
| `/pipiper/app` | app id |
| `/pipiper/scene` | four scene numbers, or -1 |

Open the patch `puredata/pi-piper-listen.pd` or boot SuperCollider and
evaluate `supercollider/PiPiper.scd`. Route MIDI onward with `aconnect` or
JACK. The image installs both Pure Data's usual neighbours (PipeWire and
JACK) but not Pure Data itself; install `puredata` or SuperCollider from
the archive on a writable boot if you want them on the card.
