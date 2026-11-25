"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { AppShell } from "@/components/AppShell";
import { Button, ErrorNote, Field, Loading, PageTitle, inputClass } from "@/components/ui";
import { api, type User } from "@/lib/api";

export default function Settings() {
  return (
    <AppShell>
      <Content />
    </AppShell>
  );
}

function Content() {
  const qc = useQueryClient();
  const coaches = useQuery({ queryKey: ["coach-access"], queryFn: () => api<User[]>("/coach-access") });
  const [email, setEmail] = useState("");
  const grant = useMutation({
    mutationFn: () => api<User>("/coach-access", { method: "POST", json: { coach_email: email } }),
    onSuccess: () => {
      setEmail("");
      void qc.invalidateQueries({ queryKey: ["coach-access"] });
    },
  });
  const revoke = useMutation({
    mutationFn: (id: number) => api(`/coach-access/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["coach-access"] }),
  });

  return (
    <div className="max-w-2xl">
      <PageTitle title="Settings" />
      <section>
        <h2 className="text-lg font-semibold">Share your practice with a coach</h2>
        <p className="mt-2 text-muted">
          A coach you add can see your interviews, listen to your recordings and leave comments. Nobody else can.
          You can remove access at any time.
        </p>
        <form
          className="mt-6 flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            grant.mutate();
          }}
        >
          <div className="min-w-64 flex-1">
            <Field label="Coach's email" htmlFor="coach-email">
              <input id="coach-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className={inputClass} />
            </Field>
          </div>
          <Button type="submit" busy={grant.isPending}>
            Share with coach
          </Button>
        </form>
        <div className="mt-3">
          <ErrorNote error={grant.error ?? revoke.error} />
        </div>
        {coaches.isPending ? (
          <Loading />
        ) : coaches.data?.length ? (
          <ul className="mt-6 divide-y divide-line border-y border-line">
            {coaches.data.map((c) => (
              <li key={c.id} className="flex items-center justify-between py-3">
                <span>
                  {c.name} <span className="text-muted">{c.email}</span>
                </span>
                <Button variant="danger" onClick={() => revoke.mutate(c.id)} disabled={revoke.isPending}>
                  Remove access
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-6 text-muted">You haven&apos;t shared your practice with anyone.</p>
        )}
      </section>
    </div>
  );
}
