import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

type Pad = { index: number; color: number; brightness: number };
type AppInfo = { id: string; title: string; hint: string };
type Snapshot = {
  app: AppInfo;
  apps: AppInfo[];
  tempo: number;
  running: boolean;
  step: number;
  shift: boolean;
  disclaimer: string;
  pads: Pad[];
  buttons: Record<string, number>;
  strip: number[];
  screen: string[];
  midi: string[];
};

const PAD_FILL = [
  "#3c342b",
  "#c44536",
  "#e07a3d",
  "#ef9f55",
  "#e0b15c",
  "#e6c84a",
  "#b6d36a",
  "#3f8f62",
  "#7dcea0",
  "#5ec2c6",
  "#3aa7a0",
  "#3d6fbf",
  "#7a5ea7",
  "#8e6bb5",
  "#6b4c9a",
  "#c45b8a",
  "#d46aaa",
  "#f4efe4",
];

const KEYS: { name: string; label: string }[] = [
  { name: "play", label: "Play" },
  { name: "rec", label: "Rec" },
  { name: "stop", label: "Stop" },
  { name: "restart", label: "Restart" },
  { name: "shift", label: "Shift" },
  { name: "erase", label: "Erase" },
  { name: "swing", label: "Swing" },
  { name: "pattern", label: "Pattern" },
  { name: "notes", label: "Notes" },
  { name: "mute", label: "Mute" },
  { name: "left", label: "Left" },
  { name: "right", label: "Right" },
  { name: "group", label: "Group" },
  { name: "duplicate", label: "Duplicate" },
  { name: "fixed_vel", label: "Fixed" },
  { name: "tempo", label: "Tempo" },
];

const PAD_KEYS = ["1", "2", "3", "4", "q", "w", "e", "r", "a", "s", "d", "f", "z", "x", "c", "v"];

function send(socket: WebSocket | null, body: object) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(body));
  }
}

function Phosphor({ rows }: { rows: string[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || rows.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const width = rows[0]?.length ?? 128;
    const height = rows.length;
    canvas.width = width;
    canvas.height = height;
    const image = ctx.createImageData(width, height);
    for (let y = 0; y < height; y += 1) {
      const row = rows[y] ?? "";
      for (let x = 0; x < width; x += 1) {
        const on = row[x] === "1";
        const offset = (y * width + x) * 4;
        image.data[offset] = on ? 214 : 18;
        image.data[offset + 1] = on ? 227 : 26;
        image.data[offset + 2] = on ? 138 : 16;
        image.data[offset + 3] = 255;
      }
    }
    ctx.putImageData(image, 0, 0);
  }, [rows]);
  return <canvas ref={ref} className="screen-canvas" width={128} height={32} />;
}

export default function App() {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [link, setLink] = useState<"connecting" | "live" | "closed">("connecting");
  const socketRef = useRef<WebSocket | null>(null);
  const held = useRef<Set<number>>(new Set());

  const transmit = useCallback((body: object) => send(socketRef.current, body), []);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);
    socketRef.current = socket;
    socket.onopen = () => setLink("live");
    socket.onclose = () => setLink("closed");
    socket.onerror = () => setLink("closed");
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data as string) as { type?: string } & Snapshot;
      if (payload.app) setSnap(payload);
    };
    return () => socket.close();
  }, []);

  useEffect(() => {
    const down = (event: KeyboardEvent) => {
      if (event.repeat) return;
      const pad = PAD_KEYS.indexOf(event.key.toLowerCase());
      if (pad >= 0) {
        held.current.add(pad);
        transmit({ type: "pad", index: pad, phase: "strike", value: 2800 });
      } else if (event.key === "ArrowRight") transmit({ type: "encoder", delta: 1 });
      else if (event.key === "ArrowLeft") transmit({ type: "encoder", delta: -1 });
      else if (event.key === "Enter") transmit({ type: "button", name: "encoder_press", down: true });
      else if (event.key === " ") {
        event.preventDefault();
        transmit({ type: "button", name: "play", down: true });
      } else if (event.key === "Shift") transmit({ type: "button", name: "shift", down: true });
    };
    const up = (event: KeyboardEvent) => {
      const pad = PAD_KEYS.indexOf(event.key.toLowerCase());
      if (pad >= 0 && held.current.has(pad)) {
        held.current.delete(pad);
        transmit({ type: "pad", index: pad, phase: "release", value: 0 });
      } else if (event.key === "Enter") transmit({ type: "button", name: "encoder_press", down: false });
      else if (event.key === " ") transmit({ type: "button", name: "play", down: false });
      else if (event.key === "Shift") transmit({ type: "button", name: "shift", down: false });
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  }, [transmit]);

  const strike = (index: number, value = 3000) => {
    transmit({ type: "pad", index, phase: "strike", value });
  };
  const release = (index: number) => {
    transmit({ type: "pad", index, phase: "release", value: 0 });
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-4 py-6 md:px-8">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-[#3a3126] pb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--brass)]">Stage framework</p>
          <h1 className="font-['Fraunces',Georgia,serif] text-4xl font-semibold tracking-tight md:text-5xl">
            Pi Piper bench
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={link === "live" ? "default" : "secondary"}>{link === "live" ? "Live" : link}</Badge>
          <Badge variant="outline">{snap ? snap.app.title : "…"}</Badge>
          {snap?.running ? <Badge>Running</Badge> : <Badge variant="secondary">Stopped</Badge>}
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,280px)_minmax(0,1fr)_minmax(220px,280px)]">
        <section className="flex flex-col gap-4 rounded-2xl bg-[var(--panel)] p-4 shadow-[inset_0_0_0_1px_rgba(224,177,92,0.18)]">
          <Phosphor rows={snap?.screen ?? []} />
          <p className="min-h-10 text-sm text-[#d9cbb6]">{snap?.app.hint ?? "Waiting for the launcher."}</p>
          <div>
            <div className="mb-2 flex items-baseline justify-between text-xs uppercase tracking-wider text-[#b5a48c]">
              <span>Strip</span>
              <span>touch</span>
            </div>
            <Strip values={snap?.strip ?? []} onPick={(primary) => transmit({ type: "strip", primary, secondary: 0 })} />
          </div>
          <div>
            <div className="mb-2 text-xs uppercase tracking-wider text-[#b5a48c]">Tempo {Math.round(snap?.tempo ?? 120)}</div>
            <Slider
              min={40}
              max={240}
              step={1}
              value={[Math.round(snap?.tempo ?? 120)]}
              onValueChange={([bpm]) => transmit({ type: "tempo", bpm })}
            />
          </div>
          <div className="max-h-36 overflow-auto rounded-md bg-black/30 p-2 font-mono text-[11px] leading-5 text-[#d6e38a]">
            {(snap?.midi ?? []).slice(-8).map((line, index) => (
              <div key={`${line}-${index}`}>{line}</div>
            ))}
            {(snap?.midi ?? []).length === 0 && <div className="text-[#8d866f]">MIDI will print here.</div>}
          </div>
        </section>

        <section className="rounded-2xl bg-[var(--panel)] p-4 shadow-[inset_0_0_0_1px_rgba(224,177,92,0.18)]">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="font-['Fraunces',Georgia,serif] text-2xl">Pads</h2>
            <span className="text-xs text-[#b5a48c]">top-left is report 0</span>
          </div>
          <div className="grid grid-cols-4 gap-2 sm:gap-3">
            {(snap?.pads ?? Array.from({ length: 16 }, (_, index) => ({ index, color: 0, brightness: 0 }))).map((pad) => {
              const fill = PAD_FILL[pad.color] ?? PAD_FILL[0];
              const glow = pad.brightness === 0 ? 0.35 : 0.45 + pad.brightness * 0.18;
              return (
                <button
                  key={pad.index}
                  type="button"
                  aria-label={`Pad ${pad.index + 1}`}
                  onPointerDown={(event) => {
                    event.currentTarget.setPointerCapture(event.pointerId);
                    strike(pad.index);
                  }}
                  onPointerUp={() => release(pad.index)}
                  onPointerCancel={() => release(pad.index)}
                  className="aspect-square rounded-xl border border-black/40 text-left text-xs font-medium text-white/80 shadow-inner"
                  style={{
                    background: `linear-gradient(160deg, rgba(255,255,255,0.16), transparent 42%), ${fill}`,
                    opacity: glow,
                  }}
                >
                  <span className="block p-2">{pad.index + 1}</span>
                </button>
              );
            })}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {(snap?.apps ?? []).map((app) => (
              <Button
                key={app.id}
                size="sm"
                variant={snap?.app.id === app.id ? "default" : "secondary"}
                onClick={() => transmit({ type: "switch", id: app.id })}
              >
                {app.title}
              </Button>
            ))}
            <Button size="sm" variant="outline" onClick={() => transmit({ type: "switch", id: "launcher" })}>
              Launcher
            </Button>
          </div>
        </section>

        <section className="flex flex-col gap-4 rounded-2xl bg-[var(--panel)] p-4 shadow-[inset_0_0_0_1px_rgba(224,177,92,0.18)]">
          <h2 className="font-['Fraunces',Georgia,serif] text-2xl">Keys</h2>
          <Encoder
            onDelta={(delta) => transmit({ type: "encoder", delta })}
            onPress={(down) => transmit({ type: "button", name: "encoder_press", down })}
            lit={Boolean(snap?.buttons.encoder_press)}
          />
          <div className="grid grid-cols-2 gap-2">
            {KEYS.map((key) => {
              const level = snap?.buttons[key.name] ?? 0;
              return (
                <Button
                  key={key.name}
                  size="sm"
                  variant={level > 0 ? "default" : "secondary"}
                  onPointerDown={() => transmit({ type: "button", name: key.name, down: true })}
                  onPointerUp={() => transmit({ type: "button", name: key.name, down: false })}
                  onPointerLeave={() => transmit({ type: "button", name: key.name, down: false })}
                >
                  {key.label}
                </Button>
              );
            })}
          </div>
        </section>
      </div>

      <footer className="mt-auto rounded-xl border border-[#6a5a42] bg-black/25 px-4 py-3 text-sm leading-relaxed text-[#e7dcc8]">
        <p>
          {snap?.disclaimer ??
            "Pi Piper is not affiliated with, endorsed by, or sponsored by Native Instruments."}{" "}
          Raspberry Pi is a trademark of Raspberry Pi Ltd. This bench is a development surface, not a picture of any product.
        </p>
        <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[#e0b15c]">
          <a className="underline" href="https://pipiper.pingocreativetechnology.com">Pi Piper</a>
          <a className="underline" href="https://github.com/pingocreativetechnology/pi-piper">GitHub</a>
          <a className="underline" href="https://pingocreativetechnology.com">Made by PCT</a>
          <a className="underline" href="https://buymeacoffee.com/pingoism">Buy Me a Coffee</a>
        </p>
      </footer>
    </div>
  );
}

function Strip({ values, onPick }: { values: number[]; onPick: (position: number) => void }) {
  return (
    <button
      type="button"
      aria-label="Touch strip"
      className="flex h-8 w-full overflow-hidden rounded-full bg-[#12100d]"
      onPointerDown={(event) => {
        const rect = event.currentTarget.getBoundingClientRect();
        const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
        onPick(ratio === 0 ? 0 : 1 + Math.round(ratio * 199));
      }}
    >
      {(values.length ? values : Array.from({ length: 25 }, () => 0)).map((level, index) => (
        <span
          key={index}
          className="h-full flex-1"
          style={{ background: level > 0 ? `rgba(224,177,92,${0.35 + level * 0.2})` : "transparent" }}
        />
      ))}
    </button>
  );
}

function Encoder({
  onDelta,
  onPress,
  lit,
}: {
  onDelta: (delta: number) => void;
  onPress: (down: boolean) => void;
  lit: boolean;
}) {
  const last = useRef<number | null>(null);
  return (
    <button
      type="button"
      aria-label="Encoder"
      className="mx-auto grid h-24 w-24 place-items-center rounded-full border-4 text-xs uppercase tracking-widest"
      style={{
        borderColor: lit ? "#f4efe4" : "var(--brass)",
        background: "radial-gradient(circle at 40% 35%, #f0d7a2, #8a6428 62%, #2a2114)",
        color: "#241b10",
      }}
      onPointerDown={(event) => {
        event.currentTarget.setPointerCapture(event.pointerId);
        last.current = event.clientY;
        onPress(true);
      }}
      onPointerMove={(event) => {
        if (last.current === null) return;
        const delta = last.current - event.clientY;
        if (Math.abs(delta) >= 12) {
          onDelta(delta > 0 ? 1 : -1);
          last.current = event.clientY;
        }
      }}
      onPointerUp={() => {
        last.current = null;
        onPress(false);
      }}
    >
      Turn
    </button>
  );
}
