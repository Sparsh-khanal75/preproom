"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { AppShell } from "@/components/AppShell";
import { ErrorNote, Loading, PageTitle, scoreTone } from "@/components/ui";
import { api, type Candidate } from "@/lib/api";

export default function Coach() {
  return (
    <AppShell roles={["coach", "admin"]}>
      <Content />
    </AppShell>
  );
}

function Content() {
  const q = useQuery({ queryKey: ["candidates"], queryFn: () => api<Candidate[]>("/coach/candidates") });
  return (
    <>
      <PageTitle title="Your candidates" />
      {q.isPending ? (
        <Loading />
      ) : q.error ? (
        <ErrorNote error={q.error} />
      ) : !q.data.length ? (
        <div className="max-w-xl">
          <p className="font-voice text-2xl">No candidates have shared their practice with you yet.</p>
          <p className="mt-3 text-muted">
            Ask candidates to open Settings and add your email address. They stay in control and can remove your
            access at any time.
          </p>
        </div>
      ) : (
        <table className="w-full max-w-4xl text-left text-[15px]">
          <thead className="text-sm text-muted">
            <tr className="border-b border-line">
              <th className="py-2 font-normal">Candidate</th>
              <th className="py-2 font-normal">Interviews</th>
              <th className="py-2 text-right font-normal">Latest</th>
              <th className="py-2 text-right font-normal">Average</th>
            </tr>
          </thead>
          <tbody>
            {q.data.map((c) => (
              <tr key={c.id} className="border-b border-line">
                <td className="py-3">
                  <Link href={`/coach/${c.id}`} className="font-medium underline-offset-4 hover:underline">
                    {c.name}
                  </Link>
                  <span className="block text-sm text-muted">{c.email}</span>
                </td>
                <td className="py-3 tabular-nums">{c.sessions}</td>
                <td className={`py-3 text-right tabular-nums ${scoreTone(c.last_score, 100)}`}>{c.last_score ?? "—"}</td>
                <td className="py-3 text-right tabular-nums">{c.average_score ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
