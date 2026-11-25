import type { Highlight } from "@/lib/api";

const PRIORITY: Record<Highlight["kind"], number> = { contradiction: 0, generic: 1, language: 2, detail: 3 };

export type Segment = { text: string; mark?: Highlight };

/** Split text into plain and highlighted segments. Overlaps resolve by priority, then earliest start. */
export function segment(text: string, highlights: Highlight[] = []): Segment[] {
  const lower = text.toLowerCase();
  const spans: Array<{ start: number; end: number; h: Highlight }> = [];
  for (const h of [...highlights].sort((a, b) => PRIORITY[a.kind] - PRIORITY[b.kind])) {
    const needle = h.text.toLowerCase().trim();
    if (needle.length < 2) continue;
    let from = 0;
    while (true) {
      const i = lower.indexOf(needle, from);
      if (i < 0) break;
      const end = i + needle.length;
      if (!spans.some((s) => i < s.end && end > s.start)) {
        spans.push({ start: i, end, h });
        break; // first free occurrence is enough
      }
      from = i + 1;
    }
  }
  spans.sort((a, b) => a.start - b.start);
  const out: Segment[] = [];
  let pos = 0;
  for (const s of spans) {
    if (s.start > pos) out.push({ text: text.slice(pos, s.start) });
    out.push({ text: text.slice(s.start, s.end), mark: s.h });
    pos = s.end;
  }
  if (pos < text.length) out.push({ text: text.slice(pos) });
  return out;
}

const TITLE: Record<Highlight["kind"], string> = {
  detail: "Concrete detail",
  contradiction: "Doesn't match your profile",
  generic: "Generic phrase",
  language: "Language",
};

export function MarkedText({ text, highlights }: { text: string; highlights?: Highlight[] }) {
  return (
    <>
      {segment(text, highlights).map((s, i) =>
        s.mark ? (
          <span
            key={i}
            className={`mark mark-${s.mark.kind}`}
            title={s.mark.note ? `${TITLE[s.mark.kind]}: ${s.mark.note}` : TITLE[s.mark.kind]}
          >
            {s.text}
          </span>
        ) : (
          <span key={i}>{s.text}</span>
        ),
      )}
    </>
  );
}

export function Legend() {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted" aria-label="Transcript marks">
      <li>
        <span className="mark mark-detail">underlined green</span> concrete detail
      </li>
      <li>
        <span className="mark mark-contradiction">amber</span> contradicts your profile
      </li>
      <li>
        <span className="mark mark-generic">wavy</span> generic phrase
      </li>
      <li>
        <span className="mark mark-language">dotted</span> language note
      </li>
    </ul>
  );
}
