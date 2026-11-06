// Pi Piper OSC input. This file is not affiliated with Native Instruments.
// Boot the server, then evaluate this block. Notes arrive as /pipiper/note.

(
OSCdef(\pipiperNote, { |msg|
	var channel = msg[1];
	var note = msg[2];
	var velocity = msg[3];
	if (velocity > 0) {
		{
			var env = EnvGen.kr(Env.perc(0.005, 0.2), doneAction: 2);
			var tone = SinOsc.ar((note + 1).midicps) * env * (velocity / 127) * 0.2;
			Out.ar(0, [tone, tone]);
		}.play;
	};
	("pi-piper note" + channel + note + velocity).postln;
}, '/pipiper/note');

OSCdef(\pipiperPad, { |msg| msg.postln }, '/pipiper/pad');
OSCdef(\pipiperStep, { |msg| ("step" + msg[1]).postln }, '/pipiper/step');
"Pi Piper OSC defs are listening.".postln;
)
