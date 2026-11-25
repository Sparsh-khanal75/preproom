"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { AppShell } from "@/components/AppShell";
import { ErrorNote, Loading, PageTitle } from "@/components/ui";
import { api, type PackSummary } from "@/lib/api";

const CATEGORY: Record<string, string> = { visa: "Visa", admission: "Admission", job: "Job", custom: "Custom" };

export default function Practice() {
  return (
    <AppShell>
      <Content />
    </AppShell>
  );
}

function Content() {
  const q = useQuery({ queryKey: ["packs"], queryFn: () => api<PackSummary[]>("/packs") });
  return (
    <>
      <PageTitle title="Which interview are you preparing for?" />
      {q.isPending ? (
        <Loading />
      ) : q.error ? (
        <ErrorNote error={q.error} />
      ) : (
        <ul className="max-w-3xl divide-y divide-line border-y border-line">
          {q.data.filter((p) => p.active).map((p) => (
            <li key={p.slug}>
              <Link href={`/practice/${p.slug}`} className="group grid gap-1 py-5 sm:grid-cols-[1fr_auto] sm:gap-6">
                <div>
                  <p className="text-lg font-medium group-hover:text-interviewer">{p.name}</p>
                  <p className="mt-1 max-w-[60ch] text-muted">{p.description}</p>
                </div>
                <p className="text-sm text-muted sm:text-right">
                  {CATEGORY[p.category] ?? p.category}
                  <br className="hidden sm:block" /> {p.session_length} questions
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
