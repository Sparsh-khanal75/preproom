"use client";

import clsx from "clsx";
import { useEffect, useRef, useState } from "react";

const TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];

function pickType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return TYPES.find((t) => MediaRecorder.isTypeSupported(t));
}

type State = "idle" | "asking" | "recording" | "denied" | "unsupported";

/** Record an answer with a live voice-level ring. Audio never leaves the user's machine except to your own API. */
export function Recorder({
  onRecorded,
  disabled,
  maxSeconds = 180,
}: {
  onRecorded: (blob: Blob) => void;
  disabled?: boolean;
  maxSeconds?: number;
}) {
  const [state, setState] = useState<State>("idle");
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState(0);
  const rec = useRef<MediaRecorder | null>(null);
  const stopAll = useRef<() => void>(() => {});

  useEffect(() => {
    if (typeof window !== "undefined" && (!navigator.mediaDevices || !pickType())) setState("unsupported");
    return () => stopAll.current();
  }, []);

  async function start() {
    setState("asking");
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    } catch {
      setState("denied");
      return;
    }
    const type = pickType();
    const chunks: Blob[] = [];
    const mr = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
    mr.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    mr.onstop = () => {
      const base = (mr.mimeType || type || "audio/webm").split(";")[0] ?? "audio/webm";
      onRecorded(new Blob(chunks, { type: base }));
    };

    const ctx = new AudioContext();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 512;
    ctx.createMediaStreamSource(stream).connect(analyser);
    const buf = new Uint8Array(analyser.fftSize);
    let raf = 0;
    const tick = () => {
      analyser.getByteTimeDomainData(buf);
      let sum = 0;
      for (const v of buf) sum += ((v - 128) / 128) ** 2;
      setLevel(Math.min(1, Math.sqrt(sum / buf.length) * 4));
      raf = requestAnimationFrame(tick);
    };
    tick();
    const started = Date.now();
    const timer = setInterval(() => {
      const s = Math.floor((Date.now() - started) / 1000);
      setSeconds(s);
      if (s >= maxSeconds) stop();
    }, 250);

    stopAll.current = () => {
      cancelAnimationFrame(raf);
      clearInterval(timer);
      stream.getTracks().forEach((t) => t.stop());
      void ctx.close();
    };
    rec.current = mr;
    mr.start();
    setSeconds(0);
    setState("recording");
  }

  function stop() {
    if (rec.current?.state === "recording") rec.current.stop();
    stopAll.current();
    setLevel(0);
    setState("idle");
  }

  if (state === "unsupported")
    return <p className="text-sm text-muted">This browser can&apos;t record audio. Type your answer instead.</p>;

  const recording = state === "recording";
  const mm = String(Math.floor(seconds / 60)).padStart(1, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  return (
    <div className="flex items-center gap-5">
      <div className="relative grid size-20 place-items-center">
        <span
          aria-hidden
          className="absolute inset-0 rounded-full bg-candidate/15 transition-transform duration-75"
          style={{ transform: `scale(${recording ? 0.75 + level * 0.6 : 0.75})` }}
        />
        <button
          type="button"
          onClick={recording ? stop : start}
          disabled={disabled || state === "asking"}
          aria-pressed={recording}
          aria-label={recording ? "Stop recording and submit" : "Start recording your answer"}
          className={clsx(
            "relative grid size-14 place-items-center rounded-full text-white transition-colors disabled:opacity-50",
            recording ? "bg-candidate" : "bg-ink hover:bg-candidate",
          )}
        >
          {recording ? <span className="size-4 rounded-[3px] bg-white" /> : <MicIcon />}
        </button>
      </div>
      <div className="text-sm">
        {recording ? (
          <>
            <p className="font-medium text-candidate">
              Recording {mm}:{ss}
            </p>
            <p className="text-muted">Press stop when you finish your answer.</p>
          </>
        ) : state === "denied" ? (
          <p className="text-danger" role="alert">
            Microphone access was blocked. Allow it in the browser&apos;s address bar, or type your answer.
          </p>
        ) : (
          <p className="text-muted">Press to answer out loud. Up to {Math.round(maxSeconds / 60)} minutes.</p>
        )}
      </div>
    </div>
  );
}

function MicIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" strokeLinecap="round" />
    </svg>
  );
}

/** Read the question aloud with the browser's built-in (free) voice, preferring a British English voice. */
export function speak(text: string) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const voices = window.speechSynthesis.getVoices();
  u.voice = voices.find((v) => v.lang === "en-GB") ?? voices.find((v) => v.lang.startsWith("en")) ?? null;
  u.rate = 0.95;
  window.speechSynthesis.speak(u);
}
