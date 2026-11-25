"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { Recorder, speak } from "@/components/Recorder";
import { Button, ErrorNote, Spinner, inputClass } from "@/components/ui";
import { api, type Session } from "@/lib/api";

export function InterviewRoom({ session }: { session: Session }) {
  const qc = useQueryClient();
  const current = session.turns[session.turns.length - 1]!;
  const processing = session.status === "processing";
  const baseAsked = new Set(session.turns.map((t) => t.question_id)).size;
  const [typing, setTyping] = useState(false);
  const [voiceOn, setVoiceOn] = useState(true);
  const [text, setText] = useState("");
  const spoken = useRef<number | null>(null);

  useEffect(() => {
    if (voiceOn && !processing && current.status === "asked" && spoken.current !== current.id) {
      spoken.current = current.id;
      speak(current.question_text);
    }
  }, [current.id, current.status, current.question_text, voiceOn, processing]);

  const update = (s: Session) => qc.setQueryData(["session", String(session.id)], s);
  const sendText = useMutation({
    mutationFn: (t: string) => api<Session>(`/sessions/${session.id}/answer`, { method: "POST", json: { text: t } }),
    onSuccess: (s) => {
      setText("");
      update(s);
    },
  });
  const sendAudio = useMutation({
    mutationFn: (blob: Blob) => {
      const fd = new FormData();
      fd.append("audio", blob, `answer.${blob.type.split("/")[1] ?? "webm"}`);
      return api<Session>(`/sessions/${session.id}/answer-audio`, { method: "POST", body: fd });
    },
    onSuccess: update,
  });
  const finish = useMutation({
    mutationFn: () => api<Session>(`/sessions/${session.id}/finish`, { method: "POST" }),
    onSuccess: update,
  });

  const busy = processing || sendText.isPending || sendAudio.isPending;
  const previous = session.turns.slice(0, -1).filter((t) => t.answer_text);

  return (
    <div className="grid max-w-3xl gap-10">
      <div className="flex flex-wrap items-center justify-between gap-4 text-sm text-muted">
        <p>
          Question {Math.min(baseAsked, session.planned_questions)} of {session.planned_questions}, {session.pack_name.toLowerCase()}
        </p>
        <div className="flex items-center gap-5">
          <label className="inline-flex cursor-pointer items-center gap-2">
            <input type="checkbox" checked={voiceOn} onChange={(e) => setVoiceOn(e.target.checked)} className="accent-interviewer" />
            Read questions aloud
          </label>
          <Button
            variant="quiet"
            className="px-0 py-0 text-sm text-muted"
            disabled={finish.isPending || busy}
            onClick={() => confirm("End the interview now and score the answers so far?") && finish.mutate()}
          >
            End interview
          </Button>
        </div>
      </div>

      <section aria-live="polite">
        <p className="text-sm font-medium text-interviewer">{current.is_follow_up ? "Interviewer, following up" : "Interviewer"}</p>
        <h1 className="mt-2 max-w-[30ch] font-voice text-question font-normal text-pretty sm:text-4xl sm:leading-tight">{current.question_text}</h1>
        {voiceOn && (
          <button onClick={() => speak(current.question_text)} className="mt-3 text-sm text-muted underline-offset-4 hover:underline">
            Repeat the question
          </button>
        )}
      </section>

      <section aria-label="Respond" className="rounded-xl border border-line bg-sheet p-6">
        {processing || sendAudio.isPending ? (
          <p className="text-muted">
            <Spinner label="Listening back to your answer…" />
          </p>
        ) : typing ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (text.trim()) sendText.mutate(text.trim());
            }}
            className="grid gap-3"
          >
            <label htmlFor="answer" className="text-sm font-medium text-candidate">
              Your answer
            </label>
            <textarea id="answer" rows={6} maxLength={5000} value={text} onChange={(e) => setText(e.target.value)}
              className={`${inputClass} font-voice text-lg leading-relaxed`} autoFocus />
            <div className="flex items-center gap-4">
              <Button type="submit" busy={sendText.isPending} disabled={!text.trim()}>
                Submit answer
              </Button>
              <Button type="button" variant="quiet" onClick={() => setTyping(false)}>
                Answer out loud instead
              </Button>
              <span className="ml-auto text-sm text-muted tabular-nums">{text.trim().split(/\s+/).filter(Boolean).length} words</span>
            </div>
          </form>
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-4">
            <Recorder onRecorded={(b) => sendAudio.mutate(b)} disabled={busy} />
            <Button variant="quiet" onClick={() => setTyping(true)}>
              Type instead
            </Button>
          </div>
        )}
        <div className="mt-4">
          <ErrorNote error={sendText.error ?? sendAudio.error ?? finish.error} />
        </div>
      </section>

      {previous.length > 0 && (
        <details className="text-[15px]">
          <summary className="cursor-pointer text-muted">Earlier in this interview ({previous.length})</summary>
          <ol className="mt-4 grid gap-5 border-l border-line pl-5">
            {previous.map((t) => (
              <li key={t.id}>
                <p className="font-voice text-interviewer">{t.question_text}</p>
                <p className="mt-1 font-voice text-muted">{t.answer_text}</p>
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}
