"use client";

import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/AppShell";
import { ProgressView } from "@/components/ProgressView";
import { ButtonLink, ErrorNote, Loading, PageTitle } from "@/components/ui";
import { api, type Progress } from "@/lib/api";

export default function Dashboard() {
  return (
    <AppShell>
      <Content />
    </AppShell>
  );
}

function Content() {
  const q = useQuery({ queryKey: ["progress"], queryFn: () => api<Progress>("/progress") });
  return (
    <>
      <PageTitle title="Your progress">
        <ButtonLink href="/practice">New interview</ButtonLink>
      </PageTitle>
      {q.isPending ? <Loading /> : q.error ? <ErrorNote error={q.error} /> : <ProgressView data={q.data} own />}
    </>
  );
}
