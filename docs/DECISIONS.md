# Design decisions

**Packs as YAML, not code.** Each interview type differs in questions, follow-up rules, required profile fields and rubric weights, not in logic. Keeping them as validated data means a coach can add a pack without a deploy, and the engine stays generic.

**Postgres as the job queue.** Transcription and scoring take seconds, so they run off the request path. A `jobs` table with `SELECT ... FOR UPDATE SKIP LOCKED` gives at-least-once delivery, retries and backoff without adding Redis or Celery. At this scale it is simpler to run and to test. If throughput ever needed it, the `enqueue`/`claim` interface is small enough to swap.

**Rules first, LLM second.** Contradictions with the candidate's own documents are the most important finding and must not be hallucinated, so they come from deterministic checks. The LLM adds what rules can't: relevance, tone and grammar. Its output is schema-validated and its quotes are verified against the answer.

**One follow-up per question.** Real interviewers press, but an endless loop of "be more specific" is discouraging. One follow-up keeps sessions to a predictable length.

**Fluency only for voice.** Scoring typed answers on fluency would be meaningless, so it is left out and the remaining weights are renormalised rather than giving a fake number.

**Cookie auth through a same-origin rewrite.** The browser talks to `/api` on the web origin, which Next rewrites to the API. The session cookie stays httpOnly and SameSite=Lax with no CORS credentials needed in production.

**Mock providers are first class.** Tests, CI and demos run with deterministic mock LLM and speech providers, so the full pipeline is exercised without downloading models.
