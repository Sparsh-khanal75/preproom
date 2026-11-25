"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { AppShell } from "@/components/AppShell";
import { Button, ErrorNote, Field, Loading, inputClass } from "@/components/ui";
import { api, type PackDetail, type ProfileOut, type Session } from "@/lib/api";

export default function PackSetup() {
  return (
    <AppShell>
      <Content />
    </AppShell>
  );
}

function Content() {
  const { slug } = useParams<{ slug: string }>();
  const pack = useQuery({ queryKey: ["pack", slug], queryFn: () => api<PackDetail>(`/packs/${slug}`) });
  const profile = useQuery({ queryKey: ["profile", slug], queryFn: () => api<ProfileOut>(`/profiles/${slug}`) });
  if (pack.isPending || profile.isPending) return <Loading />;
  if (pack.error || profile.error) return <ErrorNote error={pack.error ?? profile.error} />;
  return <ProfileForm pack={pack.data} initial={profile.data.data as Record<string, unknown>} />;
}

function ProfileForm({ pack, initial }: { pack: PackDetail; initial: Record<string, unknown> }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [missing, setMissing] = useState<string[]>([]);

  const start = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const saved = await api<ProfileOut>(`/profiles/${pack.slug}`, { method: "PUT", json: { data } });
      qc.setQueryData(["profile", pack.slug], saved);
      if (saved.missing.length) {
        setMissing(saved.missing);
        throw new Error(`Fill in: ${saved.missing.join(", ")}`);
      }
      return api<Session>("/sessions", { method: "POST", json: { pack: pack.slug } });
    },
    onSuccess: (s) => router.push(`/session/${s.id}`),
  });

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const data: Record<string, unknown> = {};
    for (const field of pack.profile_fields) {
      const v = String(f.get(field.id) ?? "");
      data[field.id] = field.type === "list" ? v.split("\n").map((s) => s.trim()).filter(Boolean) : v;
    }
    start.mutate(data);
  }

  return (
    <div className="grid gap-12 lg:grid-cols-[1fr_18rem]">
      <form onSubmit={onSubmit} className="grid max-w-2xl gap-6">
        <div>
          <h1 className="text-3xl font-semibold">{pack.name}</h1>
          <p className="mt-3 text-muted">
            The interviewer checks your answers against these details, so enter them exactly as they appear in your
            application. You only fill this in once.
          </p>
        </div>
        {pack.profile_fields.map((f) => {
          const v = initial[f.id];
          const value = Array.isArray(v) ? v.join("\n") : v == null ? "" : String(v);
          const err = missing.includes(f.label) ? "Required for this interview" : undefined;
          const common = { id: f.id, name: f.id, defaultValue: value, required: f.required, placeholder: f.placeholder,
            className: inputClass, "aria-invalid": err ? true : undefined };
          return (
            <Field key={f.id} label={f.required ? f.label : `${f.label} (optional)`} htmlFor={f.id} hint={f.help} error={err}>
              {f.type === "textarea" || f.type === "list" ? (
                <textarea rows={f.type === "list" ? 3 : 3} maxLength={2000} {...common} />
              ) : f.type === "select" ? (
                <select {...common}>
                  <option value="">Choose…</option>
                  {f.options.map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              ) : (
                <input type={f.type === "number" ? "text" : "text"} inputMode={f.type === "number" ? "decimal" : undefined}
                  maxLength={200} {...common} />
              )}
            </Field>
          );
        })}
        <ErrorNote error={start.error} />
        <div className="flex items-center gap-4">
          <Button type="submit" busy={start.isPending}>
            Save and start the interview
          </Button>
          <span className="text-sm text-muted">{pack.session_length} questions, about 15 minutes</span>
        </div>
      </form>

      <aside className="h-fit border-l-2 border-interviewer pl-5 text-[15px] leading-relaxed">
        <p className="font-medium">Before you start</p>
        <p className="mt-2 text-muted">{pack.honesty_note}</p>
        <p className="mt-4 font-medium">Your interviewer</p>
        <p className="mt-2 font-voice text-lg italic text-muted">{pack.persona}</p>
      </aside>
    </div>
  );
}
