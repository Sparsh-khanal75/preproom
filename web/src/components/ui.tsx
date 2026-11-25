import clsx from "clsx";
import Link from "next/link";
import { forwardRef } from "react";

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "quiet" | "danger"; busy?: boolean };

export const Button = forwardRef<HTMLButtonElement, BtnProps>(function Button(
  { variant = "primary", busy, className, children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-[15px] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "bg-ink text-white hover:bg-interviewer",
        variant === "quiet" && "text-ink underline-offset-4 hover:underline",
        variant === "danger" && "text-danger underline-offset-4 hover:underline",
        className,
      )}
      {...rest}
    >
      {busy && <Spinner />}
      {children}
    </button>
  );
});

export function ButtonLink({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) {
  return (
    <Link
      href={href}
      className={clsx(
        "inline-flex items-center justify-center rounded-md bg-ink px-4 py-2 text-[15px] font-medium text-white transition-colors hover:bg-interviewer",
        className,
      )}
    >
      {children}
    </Link>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span role="status" className="inline-flex items-center gap-2">
      <span className="size-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden />
      {label && <span>{label}</span>}
      {!label && <span className="sr-only">Loading</span>}
    </span>
  );
}

export function Field({
  label,
  hint,
  error,
  children,
  htmlFor,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
  htmlFor: string;
}) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium">
        {label}
      </label>
      {children}
      {hint && !error && <p className="text-sm text-muted">{hint}</p>}
      {error && (
        <p className="text-sm text-danger" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export const inputClass =
  "w-full rounded-md border border-line bg-sheet px-3 py-2 text-[15px] placeholder:text-muted/70 focus:border-interviewer focus:outline-none";

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <p role="alert" className="rounded-md border border-danger/30 bg-white px-3 py-2 text-sm text-danger">
      {msg}
    </p>
  );
}

export function PageTitle({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <h1 className="text-3xl font-semibold">{title}</h1>
      {children}
    </div>
  );
}

export function Loading() {
  return (
    <div className="py-24 text-muted">
      <Spinner label="Loading" />
    </div>
  );
}

export function scoreTone(v: number | null | undefined, max = 10) {
  if (v === null || v === undefined) return "text-muted";
  const r = v / max;
  return r >= 0.75 ? "text-candidate" : r >= 0.55 ? "text-ink" : "text-flag";
}
