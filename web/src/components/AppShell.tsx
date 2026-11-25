"use client";

import { useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { api, type User } from "@/lib/api";
import { useRequireUser } from "@/lib/hooks";

import { Loading } from "./ui";

const NAV: Array<{ href: string; label: string; roles?: User["role"][] }> = [
  { href: "/dashboard", label: "Progress" },
  { href: "/practice", label: "Practise" },
  { href: "/coach", label: "Candidates", roles: ["coach", "admin"] },
  { href: "/admin", label: "Admin", roles: ["admin"] },
  { href: "/settings", label: "Settings" },
];

export function Wordmark() {
  return (
    <Link href="/" className="font-voice text-2xl font-semibold tracking-tight">
      PrepRoom
    </Link>
  );
}

export function AppShell({ children, roles }: { children: React.ReactNode; roles?: User["role"][] }) {
  const me = useRequireUser(roles);
  const path = usePathname();
  const router = useRouter();
  const qc = useQueryClient();

  async function signOut() {
    await api("/auth/logout", { method: "POST" });
    qc.clear();
    router.replace("/login");
  }

  if (!me.data) return <div className="mx-auto max-w-5xl px-6"><Loading /></div>;
  const user = me.data;
  return (
    <div className="min-h-dvh">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4">
        Skip to content
      </a>
      <header className="border-b border-line bg-sheet">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-8 gap-y-3 px-6 py-4">
          <Wordmark />
          <nav aria-label="Main" className="flex flex-wrap gap-x-5 gap-y-2 text-[15px]">
            {NAV.filter((n) => !n.roles || n.roles.includes(user.role)).map((n) => (
              <Link
                key={n.href}
                href={n.href}
                aria-current={path.startsWith(n.href) ? "page" : undefined}
                className={clsx(
                  "py-1 text-muted hover:text-ink",
                  path.startsWith(n.href) && "font-medium text-ink shadow-[inset_0_-2px_0_var(--color-interviewer)]",
                )}
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-4 text-sm text-muted">
            <span>
              {user.name}
              {user.role !== "candidate" && <span className="ml-1">({user.role})</span>}
            </span>
            <button onClick={signOut} className="underline-offset-4 hover:text-ink hover:underline">
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-5xl px-6 py-10">
        {children}
      </main>
    </div>
  );
}
