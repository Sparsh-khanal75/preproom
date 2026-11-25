import type { components } from "./api-types";

type S = components["schemas"];
export type User = S["UserOut"];
export type PackSummary = S["PackSummary"];
export type PackDetail = S["PackDetail"];
export type ProfileOut = S["ProfileOut"];
export type Session = S["SessionOut"];
export type Turn = S["TurnOut"];
export type SessionSummary = S["SessionSummary"];
export type Progress = S["ProgressOut"];
export type Candidate = S["CandidateOut"];
export type Comment = S["CommentOut"];

export type Highlight = { text: string; kind: "detail" | "contradiction" | "generic" | "language"; note?: string };
export type Scores = {
  total: number;
  subscores: Record<string, number | null>;
  evidence: Record<string, string[]>;
  flags: Array<Record<string, unknown> & { type: string }>;
  highlights?: Highlight[];
  strength?: string;
  improvement?: string;
  judge?: string;
  judge_note?: string;
};
export type Report = {
  overall: number | null;
  band?: string;
  subscores?: Record<string, number>;
  strengths?: string[];
  fixes?: Array<{ area: string; score: number; tip: string }>;
  flags?: Array<Record<string, unknown> & { type: string; question?: string }>;
  delivery?: { avg_words_per_minute: number; filler_total: number; long_pauses: number } | null;
  practise_again?: string[];
  judge?: string;
  answered?: number;
  disclaimer?: string;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: unknown,
  ) {
    super(message);
  }
}

function messageFrom(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors
    return detail.map((d: { msg?: string; loc?: unknown[] }) => `${d.loc?.slice(-1)[0] ?? "field"}: ${d.msg}`).join("; ");
  }
  if (detail && typeof detail === "object" && "message" in detail) return String((detail as { message: string }).message);
  return status >= 500 ? "The server had a problem. Try again in a moment." : `Request failed (${status})`;
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  const res = await fetch(`/api${path}`, {
    credentials: "same-origin",
    ...rest,
    headers: json !== undefined ? { "Content-Type": "application/json", ...headers } : headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, messageFrom(body.detail, res.status), body.detail);
  return body as T;
}

export const LABELS: Record<string, string> = {
  consistency: "Consistency",
  specificity: "Specificity",
  relevance: "Relevance",
  fluency: "Fluency",
  language: "Language",
};
