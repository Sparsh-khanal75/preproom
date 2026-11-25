"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";

import { AppShell } from "@/components/AppShell";
import { ProgressView } from "@/components/ProgressView";
import { ErrorNote, Loading, PageTitle } from "@/components/ui";
import { api, type Candidate, type Progress } from "@/lib/api";

export default function CandidatePage() {
  return (
    <AppShell roles={["coach", "admin"]}>
      <Content />
    </AppShell>
  );
}

function Content() {
  const { id } = useParams<{ id: string }>();
  const list = useQuery({ queryKey: ["candidates"], queryFn: () => api<Candidate[]>("/coach/candidates") });
  const q = useQuery({ queryKey: ["progress", id], queryFn: () => api<Progress>(`/coach/candidates/${id}/progress`) });
  const c = list.data?.find((x) => String(x.id) === id);
  return (
    <>
      <p className="mb-2 text-sm">
        <Link href="/coach" className="text-muted underline-offset-4 hover:underline">
          All candidates
        </Link>
      </p>
      <PageTitle title={c?.name ?? "Candidate"} />
      {q.isPending ? <Loading /> : q.error ? <ErrorNote error={q.error} /> : <ProgressView data={q.data} own={false} />}
    </>
  );
}
