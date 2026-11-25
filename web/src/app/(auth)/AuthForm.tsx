"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Wordmark } from "@/components/AppShell";
import { Button, ErrorNote, Field, inputClass } from "@/components/ui";
import { api, type User } from "@/lib/api";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const params = useSearchParams();
  const qc = useQueryClient();
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const user = await api<User>(`/auth/${mode}`, {
        method: "POST",
        json: { email: f.get("email"), password: f.get("password"), ...(mode === "register" && { name: f.get("name") }) },
      });
      qc.setQueryData(["me"], user);
      const next = params.get("next");
      router.replace(next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard");
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  const register = mode === "register";
  return (
    <div className="grid min-h-dvh place-items-center px-6 py-12">
      <div className="w-full max-w-sm">
        <Wordmark />
        <h1 className="mt-10 text-2xl font-semibold">{register ? "Create your account" : "Sign in"}</h1>
        <p className="mt-2 text-muted">
          {register ? "Free, and your recordings stay on your server." : "Welcome back. Pick up where you left off."}
        </p>
        <form onSubmit={onSubmit} className="mt-8 grid gap-5" noValidate={false}>
          {register && (
            <Field label="Name" htmlFor="name">
              <input id="name" name="name" required maxLength={120} autoComplete="name" className={inputClass} />
            </Field>
          )}
          <Field label="Email" htmlFor="email">
            <input id="email" name="email" type="email" required autoComplete="email" className={inputClass} />
          </Field>
          <Field label="Password" htmlFor="password" hint={register ? "At least 10 characters." : undefined}>
            <input
              id="password"
              name="password"
              type="password"
              required
              minLength={register ? 10 : 1}
              autoComplete={register ? "new-password" : "current-password"}
              className={inputClass}
            />
          </Field>
          <ErrorNote error={error} />
          <Button type="submit" busy={busy}>
            {register ? "Create account" : "Sign in"}
          </Button>
        </form>
        <p className="mt-6 text-sm text-muted">
          {register ? "Already have an account? " : "New to PrepRoom? "}
          <Link href={register ? "/login" : "/register"} className="text-ink underline underline-offset-4">
            {register ? "Sign in" : "Create an account"}
          </Link>
        </p>
      </div>
    </div>
  );
}
