"use client";

import Link from "next/link";

import { LABELS, type Progress } from "@/lib/api";

import { SubscoreBars, TrendChart } from "./Scores";
import { ButtonLink, scoreTone } from "./ui";

const STATUS: Record<string, string> = { active: "In progress", processing: "In progress", scoring: "Scoring", done: "Scored" };

export function ProgressView({ data, own }: { data: Progress; own: boolean }) {
  const t = data.totals as { sessions_done: number; best: number | null; latest: number | null; improvement: number | null;
    filler_words: number; avg_wpm: number | null };

  if (!data.sessions.length) {
    return (
      <div className="max-w-xl py-10">
        <p className="font-voice text-2xl">{own ? "Your first mock interview takes about 15 minutes." : "No interviews yet."}</p>
        {own && (
          <>
            <p className="mt-3 text-muted">
              Choose the interview you are preparing for, fill in your details once, and answer out loud.
            </p>
            <ButtonLink href="/practice" className="mt-6">
              Choose an interview
            </ButtonLink>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="grid gap-12">
      <section aria-label="Summary" className="grid grid-cols-2 gap-6 sm:grid-cols-4">
        <Stat label="Latest score" value={t.latest} tone />
        <Stat label="Best score" value={t.best} tone />
        <Stat
          label="Change since first"
          value={t.improvement === null ? null : `${t.improvement > 0 ? "+" : ""}${t.improvement}`}
        />
        <Stat label="Interviews scored" value={t.sessions_done} />
      </section>

      {data.trend.length >= 2 && (
        <section>
          <h2 className="mb-4 text-lg font-semibold">Score over time</h2>
          <TrendChart points={data.trend as Array<{ date: string; overall: number | null; pack: string }>} />
          <p className="mt-2 text-sm text-muted">65 is &ldquo;nearly there&rdquo;; 80 and above is ready.</p>
        </section>
      )}

      <section className="grid gap-10 md:grid-cols-[1fr_1fr]">
        <div>
          <h2 className="mb-4 text-lg font-semibold">Average by skill</h2>
          <SubscoreBars subscores={data.subscore_averages} />
        </div>
        <div>
          <h2 className="mb-4 text-lg font-semibold">{own ? "Focus next on" : "Weakest areas"}</h2>
          {data.weakest.length ? (
            <ul className="grid gap-2">
              {data.weakest.map((k) => (
                <li key={k} className="font-voice text-xl">
                  {LABELS[k] ?? k}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted">Finish an interview to see this.</p>
          )}
          {t.avg_wpm && (
            <p className="mt-4 text-sm text-muted">
              Speaking pace averages {t.avg_wpm} words per minute; {t.filler_words} filler words across voice answers.
            </p>
          )}
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Interviews</h2>
        <table className="w-full text-left text-[15px]">
          <thead className="text-sm text-muted">
            <tr className="border-b border-line">
              <th className="py-2 font-normal">Interview</th>
              <th className="py-2 font-normal">Date</th>
              <th className="py-2 font-normal">Status</th>
              <th className="py-2 text-right font-normal">Score</th>
            </tr>
          </thead>
          <tbody>
            {data.sessions.map((s) => (
              <tr key={s.id} className="border-b border-line">
                <td className="py-3">
                  <Link href={`/session/${s.id}`} className="underline-offset-4 hover:underline">
                    {s.pack_name}
                  </Link>
                </td>
                <td className="py-3 text-muted">{new Date(s.started_at).toLocaleDateString()}</td>
                <td className="py-3 text-muted">{STATUS[s.status] ?? s.status}</td>
                <td className={`py-3 text-right tabular-nums ${scoreTone(s.overall_score, 100)}`}>
                  {s.overall_score ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number | string | null; tone?: boolean }) {
  return (
    <div>
      <p className="text-sm text-muted">{label}</p>
      <p className={`mt-1 font-voice text-4xl tabular-nums ${tone && typeof value === "number" ? scoreTone(value, 100) : ""}`}>
        {value ?? "—"}
      </p>
    </div>
  );
}
