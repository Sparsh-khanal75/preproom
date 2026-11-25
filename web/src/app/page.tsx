import Link from "next/link";

import { Wordmark } from "@/components/AppShell";
import { MarkedText } from "@/components/MarkedText";
import { ButtonLink } from "@/components/ui";
import type { Highlight } from "@/lib/api";

const SAMPLE_ANSWER =
  "My father will pay the tuition fee of £25,000 from his savings, and I have an education loan from Nabil Bank. " +
  "I have always been passionate about this field since my childhood.";
const SAMPLE_MARKS: Highlight[] = [
  { text: "£25,000", kind: "contradiction", note: "Your profile says £21,500" },
  { text: "Nabil Bank", kind: "detail" },
  { text: "passionate about", kind: "generic", note: "Sounds memorised" },
];

const TYPES = [
  ["Student visa credibility", "Course, university, funding and career-plan questions, checked against the facts you give."],
  ["University admission", "Motivation, fit with the programme, and the project you are proudest of."],
  ["Job interview, behavioural", "Teamwork, mistakes and results, judged on the STAR structure."],
  ["Technical concepts", "Explain TLS, SQL injection or an incident response out loud, the way a screening call asks."],
];

const SCORES = [
  ["Consistency", "Do names, numbers and dates match your profile?"],
  ["Specificity", "Did you give modules, figures and examples, or generic lines?"],
  ["Relevance", "Did you answer the question that was asked?"],
  ["Fluency", "Pace, long pauses and filler words, measured from your recording."],
  ["Language", "Grammar and clarity, with the exact phrase to fix."],
];

export default function Landing() {
  return (
    <div className="bg-sheet">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-6">
        <Wordmark />
        <nav className="flex items-center gap-5 text-[15px]">
          <Link href="/login" className="hover:underline underline-offset-4">
            Sign in
          </Link>
          <ButtonLink href="/register">Create account</ButtonLink>
        </nav>
      </header>

      <main>
        <section className="mx-auto grid max-w-5xl gap-14 px-6 pb-20 pt-10 lg:grid-cols-[1fr_1.1fr] lg:items-center">
          <div>
            <h1 className="font-voice text-5xl leading-[1.08] font-medium sm:text-6xl">
              Rehearse the interview before it counts.
            </h1>
            <p className="mt-6 max-w-[34rem] text-lg leading-relaxed text-muted">
              An AI interviewer asks your questions out loud, follows up when you are vague, and marks up exactly
              what to fix. It runs on free, open-source models on your own computer.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-5">
              <ButtonLink href="/register" className="px-5 py-2.5 text-base">
                Start practising
              </ButtonLink>
              <Link href="/login" className="text-[15px] underline-offset-4 hover:underline">
                I already have an account
              </Link>
            </div>
          </div>

          <figure aria-label="Example of a marked-up answer" className="rounded-xl border border-line bg-paper p-6 sm:p-8">
            <p className="text-sm font-medium text-interviewer">Interviewer</p>
            <p className="mt-1 font-voice text-question">How will you pay your tuition fees and living costs?</p>
            <p className="mt-6 text-sm font-medium text-candidate">You</p>
            <p className="mt-1 font-voice text-xl leading-relaxed">
              <MarkedText text={SAMPLE_ANSWER} highlights={SAMPLE_MARKS} />
            </p>
            <figcaption className="mt-6 grid gap-2 border-t border-line pt-4 text-sm">
              <p>
                <span className="font-medium text-flag">£25,000</span> doesn&apos;t match the £21,500 in your profile. An
                officer will notice.
              </p>
              <p>
                <span className="font-medium text-flag">&ldquo;Passionate about&rdquo;</span> sounds memorised. Say why, in
                your own words.
              </p>
              <p className="text-muted">Follow-up: &ldquo;What exactly is the fee, and how much have you paid?&rdquo;</p>
            </figcaption>
          </figure>
        </section>

        <section className="border-t border-line bg-paper">
          <div className="mx-auto grid max-w-5xl gap-12 px-6 py-16 md:grid-cols-2">
            <div>
              <h2 className="text-2xl font-semibold">Pick the interview you are facing</h2>
              <ul className="mt-6 divide-y divide-line">
                {TYPES.map(([name, desc]) => (
                  <li key={name} className="py-4">
                    <p className="font-medium">{name}</p>
                    <p className="mt-1 text-muted">{desc}</p>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-sm text-muted">Coaches can add their own interview types as a simple YAML file.</p>
            </div>
            <div>
              <h2 className="text-2xl font-semibold">Every score shows its evidence</h2>
              <dl className="mt-6 divide-y divide-line">
                {SCORES.map(([name, desc]) => (
                  <div key={name} className="grid grid-cols-[8rem_1fr] gap-4 py-4">
                    <dt className="font-medium">{name}</dt>
                    <dd className="text-muted">{desc}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-5xl px-6 py-16">
          <p className="max-w-[44rem] font-voice text-2xl leading-snug">
            PrepRoom never writes answers for you. It helps you tell your own true story clearly, because that is
            what interviewers are trained to look for.
          </p>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-5xl flex-wrap justify-between gap-4 px-6 py-6 text-sm text-muted">
          <p>Open source. Runs on Ollama and Whisper, free.</p>
          <p>Scores are practice estimates, not predictions of a real decision.</p>
        </div>
      </footer>
    </div>
  );
}
