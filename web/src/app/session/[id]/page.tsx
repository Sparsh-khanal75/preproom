"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { AppShell } from "@/components/AppShell";
import { ErrorNote, Loading, Spinner } from "@/components/ui";
import { api, type Session } from "@/lib/api";

import { InterviewRoom } from "./InterviewRoom";
import { ReportView } from "./ReportView";

export default function SessionPage() {
  return (
    <AppShell>
      <Content />
    </AppShell>
  );
}

function Content() {
  const { id } = useParams<{ id: string }>();
  const q = useQuery({
    queryKey: ["session", id],
    queryFn: () => api<Session>(`/sessions/${id}`),
    // poll while the worker is transcribing or scoring
    refetchInterval: (query) => (["processing", "scoring"].includes(query.state.data?.status ?? "") ? 1500 : false),
  });
  if (q.isPending) return <Loading />;
  if (q.error) return <ErrorNote error={q.error} />;
  const s = q.data;
  if (s.status === "active" || s.status === "processing") return <InterviewRoom session={s} />;
  if (s.status === "scoring")
    return (
      <div className="max-w-xl py-16">
        <p className="font-voice text-3xl">That&apos;s the end of the interview.</p>
        <p className="mt-4 text-muted">
          <Spinner label="Scoring your answers. With a local model this can take a minute or two." />
        </p>
      </div>
    );
  return <ReportView session={s} />;
}
