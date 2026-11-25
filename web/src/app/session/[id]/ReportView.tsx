"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { Legend, MarkedText } from "@/components/MarkedText";
import { SubscoreBars } from "@/components/Scores";
import { Button, ButtonLink, ErrorNote, inputClass, scoreTone } from "@/components/ui";
import { LABELS, api, type Comment, type Report, type Scores, type Session, type Turn } from "@/lib/api";
import { useMe } from "@/lib/hooks";

export function ReportView({ session }: { session: Session }) {
  const me = useMe();
  const r = (session.report ?? {}) as Report;
  const own = me.data?.id === session.user_id;
  const contradictions = (r.flags ?? [])
    .filter((f) => f.type === "contradiction")
    .filter((f, i, all) => all.findIndex((g) => g.said === f.said && g.profile === f.profile) === i);

  return (
    <article className="grid gap-14">
      <header className="grid gap-8 md:grid-cols-[auto_1fr] md:items-end">
        <div>
          <p className="text-sm text-muted">
            {session.pack_name}, {new Date(session.started_at).toLocaleDateString(undefined, { dateStyle: "medium" })}
          </p>
          <p className={`font-voice text-8xl leading-none tabular-nums ${scoreTone(r.overall, 100)}`}>{r.overall ?? "—"}</p>
          <p className="mt-2 text-lg font-medium">{r.band}</p>
        </div>
        <div className="md:pl-10">
          <SubscoreBars subscores={r.subscores ?? {}} />
        </div>
      </header>

      <section className="grid gap-10 md:grid-cols-2">
        <div>
          <h2 className="text-lg font-semibold">Fix first</h2>
          {r.fixes?.length ? (
            <ol className="mt-4 grid gap-4">
              {r.fixes.map((f, i) => (
                <li key={f.area} className="grid grid-cols-[1.5rem_1fr] gap-2">
                  <span className="text-muted tabular-nums">{i + 1}.</span>
                  <div>
                    <p className="font-medium">
                      {f.area} <span className="font-normal text-muted">({f.score}/10)</span>
                    </p>
                    <p className="text-muted">{f.tip}</p>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-4 text-muted">Nothing below 7.5. Keep your answers this specific.</p>
          )}
        </div>
        <div>
          <h2 className="text-lg font-semibold">Worth noting</h2>
          <ul className="mt-4 grid gap-3 text-[15px]">
            {r.strengths?.map((s) => (
              <li key={s}>
                Strong <span className="font-medium">{s}</span>
              </li>
            ))}
            {contradictions.map((c, i) => (
              <li key={i} className="text-flag">
                You said {String(c.said)} but your profile says {String(c.profile)}.
              </li>
            ))}
            {r.delivery && (
              <li className="text-muted">
                Pace {r.delivery.avg_words_per_minute} words per minute, {r.delivery.filler_total} filler words,{" "}
                {r.delivery.long_pauses} long pauses
              </li>
            )}
          </ul>
          {own && (
            <ButtonLink href={`/practice/${session.pack_slug}`} className="mt-6">
              Practise again
            </ButtonLink>
          )}
        </div>
      </section>

      <section>
        <div className="mb-6 flex flex-wrap items-baseline justify-between gap-4 border-b border-line pb-3">
          <h2 className="text-lg font-semibold">Your answers, marked up</h2>
          <Legend />
        </div>
        <ol className="grid gap-12">
          {session.turns.filter((t) => t.answer_text).map((t) => (
            <TurnBlock key={t.id} turn={t} />
          ))}
        </ol>
      </section>

      <footer className="border-t border-line pt-6 text-sm text-muted">
        <p>{r.disclaimer}</p>
        <p className="mt-1">
          Scored by {r.judge === "mock" ? "the built-in rules (demo mode, no AI model)" : r.judge} plus rule-based checks.{" "}
          <Link href="/dashboard" className="underline underline-offset-4">
            Back to progress
          </Link>
        </p>
      </footer>
    </article>
  );
}

function TurnBlock({ turn }: { turn: Turn }) {
  const sc = turn.scores as Scores | null;
  const [open, setOpen] = useState(false);
  return (
    <li className="grid gap-6 md:grid-cols-[1fr_15rem]">
      <div>
        <p className="text-sm font-medium text-interviewer">{turn.is_follow_up ? "Follow-up" : "Interviewer"}</p>
        <p className="mt-1 font-voice text-2xl leading-snug">{turn.question_text}</p>
        <p className="mt-4 text-sm font-medium text-candidate">
          You {turn.answer_mode === "voice" ? "said" : "wrote"}
        </p>
        <p className="mt-1 max-w-[68ch] font-voice text-lg leading-relaxed">
          <MarkedText text={turn.answer_text ?? ""} highlights={sc?.highlights} />
        </p>
        {turn.has_audio && (
          <audio controls preload="none" src={`/api/turns/${turn.id}/audio`} className="mt-3 h-9 w-full max-w-md">
            Your browser can&apos;t play this recording.
          </audio>
        )}
        <Comments turnId={turn.id} />
      </div>
      <aside className="text-sm md:border-l md:border-line md:pl-5">
        {sc ? (
          <>
            <p className={`font-voice text-4xl tabular-nums ${scoreTone(sc.total)}`}>
              {sc.total.toFixed(1)}
              <span className="text-base text-muted">/10</span>
            </p>
            {sc.improvement && <p className="mt-2">{sc.improvement}</p>}
            <button onClick={() => setOpen(!open)} aria-expanded={open} className="mt-3 text-muted underline underline-offset-4">
              {open ? "Hide" : "Why this score"}
            </button>
            {open && (
              <dl className="mt-3 grid gap-3">
                {Object.entries(sc.subscores).map(([k, v]) => (
                  <div key={k}>
                    <dt className="font-medium">
                      {LABELS[k]} <span className={`tabular-nums ${scoreTone(v)}`}>{v ?? "n/a"}</span>
                    </dt>
                    {(sc.evidence[k] ?? []).map((e, i) => (
                      <dd key={i} className="text-muted">
                        {e}
                      </dd>
                    ))}
                  </div>
                ))}
                {sc.judge_note && <p className="text-muted italic">{sc.judge_note}</p>}
              </dl>
            )}
          </>
        ) : (
          <p className="text-muted">Not scored yet.</p>
        )}
      </aside>
    </li>
  );
}

function Comments({ turnId }: { turnId: number }) {
  const qc = useQueryClient();
  const key = ["comments", turnId];
  const q = useQuery({ queryKey: key, queryFn: () => api<Comment[]>(`/turns/${turnId}/comments`) });
  const [body, setBody] = useState("");
  const [open, setOpen] = useState(false);
  const add = useMutation({
    mutationFn: () => api<Comment>(`/turns/${turnId}/comments`, { method: "POST", json: { body } }),
    onSuccess: () => {
      setBody("");
      setOpen(false);
      void qc.invalidateQueries({ queryKey: key });
    },
  });
  return (
    <div className="mt-4 text-[15px]">
      {q.data?.map((c) => (
        <p key={c.id} className="mt-2 border-l-2 border-interviewer pl-3">
          <span className="font-medium">{c.author_name}</span>
          {c.author_role === "coach" && <span className="text-muted"> (coach)</span>}: {c.body}
        </p>
      ))}
      {open ? (
        <form
          className="mt-3 grid max-w-xl gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (body.trim()) add.mutate();
          }}
        >
          <label htmlFor={`c-${turnId}`} className="sr-only">
            Comment
          </label>
          <textarea id={`c-${turnId}`} rows={2} value={body} maxLength={2000} onChange={(e) => setBody(e.target.value)}
            className={inputClass} autoFocus />
          <ErrorNote error={add.error} />
          <div className="flex gap-3">
            <Button type="submit" busy={add.isPending} disabled={!body.trim()}>
              Add comment
            </Button>
            <Button type="button" variant="quiet" onClick={() => setOpen(false)}>
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <button onClick={() => setOpen(true)} className="mt-2 text-sm text-muted underline-offset-4 hover:underline">
          Add a comment
        </button>
      )}
    </div>
  );
}
