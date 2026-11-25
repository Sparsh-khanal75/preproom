"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { LABELS } from "@/lib/api";

import { scoreTone } from "./ui";

/** Five sub-scores as labelled bars; a sub-score that doesn't apply (fluency for typed answers) says so. */
export function SubscoreBars({ subscores }: { subscores: Record<string, number | null | undefined> }) {
  return (
    <dl className="grid gap-2.5">
      {Object.keys(LABELS).map((k) => {
        const v = subscores[k];
        return (
          <div key={k} className="grid grid-cols-[7.5rem_1fr_2.5rem] items-center gap-3 text-sm">
            <dt className="text-muted">{LABELS[k]}</dt>
            <dd className="h-1.5 rounded-full bg-line" aria-hidden={v == null}>
              {v != null && (
                <div
                  className="h-1.5 rounded-full bg-ink"
                  style={{ width: `${v * 10}%` }}
                  role="meter"
                  aria-valuemin={0}
                  aria-valuemax={10}
                  aria-valuenow={v}
                  aria-label={LABELS[k]}
                />
              )}
            </dd>
            <dd className={`text-right tabular-nums ${scoreTone(v)}`}>{v != null ? v.toFixed(1) : "—"}</dd>
          </div>
        );
      })}
    </dl>
  );
}

export function TrendChart({ points }: { points: Array<{ date: string; overall: number | null; pack: string }> }) {
  const data = points.map((p, i) => ({
    n: i + 1,
    overall: p.overall,
    label: new Date(p.date).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    pack: p.pack,
  }));
  return (
    <div className="h-56 w-full" role="img" aria-label={`Score trend across ${points.length} interviews`}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -16 }}>
          <CartesianGrid stroke="var(--color-line)" vertical={false} />
          <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "var(--color-muted)", fontSize: 12 }} />
          <YAxis domain={[0, 100]} ticks={[0, 50, 65, 80, 100]} tickLine={false} axisLine={false}
            tick={{ fill: "var(--color-muted)", fontSize: 12 }} />
          <Tooltip
            formatter={(v) => [`${v}`, "Score"]}
            labelFormatter={(_, p) => (p[0]?.payload as { pack?: string })?.pack ?? ""}
            contentStyle={{ borderRadius: 8, border: "1px solid var(--color-line)", fontSize: 13 }}
          />
          <Line type="monotone" dataKey="overall" stroke="var(--color-interviewer)" strokeWidth={2.5}
            dot={{ r: 4, fill: "var(--color-interviewer)" }} activeDot={{ r: 6 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
