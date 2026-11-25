"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { AppShell } from "@/components/AppShell";
import { Button, ErrorNote, Loading, PageTitle, inputClass } from "@/components/ui";
import { api, type PackSummary, type User } from "@/lib/api";

const TEMPLATE = `id: my-interview
name: My interview type
category: custom
description: What this interview practises.
persona: A friendly interviewer who asks one question at a time.
session_length: 3
profile_fields:
  - {id: company, label: Company, entity: true}
questions:
  - {id: why, text: "Why {company}?", topic: motivation, expects: [mission, team]}
  - {id: proud, text: What are you proudest of?, topic: impact}
  - {id: next, text: Where do you want to be in three years?, topic: goals}
rubric: {specificity: 0.4, relevance: 0.4, language: 0.2}
`;

export default function Admin() {
  return (
    <AppShell roles={["admin"]}>
      <PageTitle title="Admin" />
      <div className="grid gap-16">
        <Packs />
        <Users />
      </div>
    </AppShell>
  );
}

function Packs() {
  const qc = useQueryClient();
  const packs = useQuery({ queryKey: ["packs"], queryFn: () => api<PackSummary[]>("/packs") });
  const [yaml, setYaml] = useState(TEMPLATE);
  const upload = useMutation({
    mutationFn: () => api<PackSummary>("/packs", { method: "POST", json: { yaml } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["packs"] }),
  });
  const toggle = useMutation({
    mutationFn: (p: PackSummary) => api(`/packs/${p.slug}/active?active=${!p.active}`, { method: "PATCH" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["packs"] }),
  });
  return (
    <section className="grid gap-8 lg:grid-cols-2">
      <div>
        <h2 className="text-lg font-semibold">Interview types</h2>
        {packs.isPending ? (
          <Loading />
        ) : (
          <ul className="mt-4 divide-y divide-line border-y border-line">
            {packs.data?.map((p) => (
              <li key={p.slug} className="flex items-center justify-between gap-4 py-3">
                <span>
                  <span className={p.active ? "" : "text-muted line-through"}>{p.name}</span>
                  <span className="block text-sm text-muted">{p.builtin ? "Built in" : "Custom"}, {p.question_count} questions</span>
                </span>
                <Button variant="quiet" onClick={() => toggle.mutate(p)}>
                  {p.active ? "Hide" : "Show"}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          upload.mutate();
        }}
        className="grid gap-3"
      >
        <label htmlFor="pack-yaml" className="text-lg font-semibold">
          Add an interview type
        </label>
        <p className="text-sm text-muted">Paste a pack in YAML. It is validated before it is saved.</p>
        <textarea id="pack-yaml" rows={16} value={yaml} onChange={(e) => setYaml(e.target.value)} spellCheck={false}
          className={`${inputClass} font-mono text-sm`} />
        <ErrorNote error={upload.error} />
        {upload.isSuccess && <p className="text-sm text-candidate">Saved {upload.data.name}.</p>}
        <Button type="submit" busy={upload.isPending} className="justify-self-start">
          Validate and save
        </Button>
      </form>
    </section>
  );
}

function Users() {
  const qc = useQueryClient();
  const users = useQuery({ queryKey: ["users"], queryFn: () => api<User[]>("/admin/users") });
  const setRole = useMutation({
    mutationFn: ({ id, role }: { id: number; role: string }) =>
      api(`/admin/users/${id}/role`, { method: "PATCH", json: { role } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
  return (
    <section>
      <h2 className="text-lg font-semibold">People</h2>
      <ErrorNote error={setRole.error} />
      {users.isPending ? (
        <Loading />
      ) : (
        <table className="mt-4 w-full max-w-3xl text-left text-[15px]">
          <tbody>
            {users.data?.map((u) => (
              <tr key={u.id} className="border-b border-line">
                <td className="py-3">
                  {u.name} <span className="block text-sm text-muted">{u.email}</span>
                </td>
                <td className="py-3 text-right">
                  <label className="sr-only" htmlFor={`role-${u.id}`}>
                    Role for {u.name}
                  </label>
                  <select id={`role-${u.id}`} value={u.role} onChange={(e) => setRole.mutate({ id: u.id, role: e.target.value })}
                    className={`${inputClass} w-auto`}>
                    <option value="candidate">Candidate</option>
                    <option value="coach">Coach</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
