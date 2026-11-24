# Evidence-grounded conversational travel assistant

The assistant has two bounded API stages. First, OpenAI interprets natural language into an allowlisted plan. Python validates park codes, activities, months, difficulty and temperatures, and applies named-park and national-scope guards. Broader park-planning questions route to general retrieval rather than a generic unsupported message.

Second, `src/conversation.py` assembles dated NPS descriptions and activities, reviewed trails, optional live alerts, and relevant historical statistics. The model receives this evidence plus the last six bounded conversation messages and writes a short explanation with evidence IDs. The app validates response shape, source IDs, numeric strings and URLs. Official links are attached from retrieved evidence, never model-generated. Numeric validation cannot establish semantic correctness of every claim; the visible evidence remains authoritative.

The underlying tools remain fixed Python functions. `travel_queries.historical_rows` executes a parameterized SELECT in a read-only repeatable-read PostgreSQL transaction with TLS, timeout and row bounds. Historical comparisons use the existing tested recommendation calculations. No unrestricted SQL, schema modification, DB writes, predictive model, or live weather claim is introduced.

## Reliability and privacy

Default model: gpt-6-luna with Standard processing and reasoning off. Interpretation is capped at 384 output tokens; explanation at 650. At most one synthesis retry follows explicit HTTP 429/502/503/504 responses. A timeout is not retried automatically because an unknown original request could have been billed. There is no automatic model fallback. The 20-request session guard is not an account spending limit.

The API key lives in a masked widget and a separate non-widget session key, so navigation does not discard it. Forget removes both. Browser/server restarts end the session; no key is persisted to disk. Keys travel only in Authorization headers. The DSN never enters prompts. Public park evidence and short conversational context do go to OpenAI. store=false does not supersede provider retention policy.

If a provider call is unavailable, activity and context-aware park retrieval can show clearly labeled deterministic source facts. If generated prose fails evidence checks, the app shows verified facts and explicitly identifies that fallback. Planning and explanation receipts are distinct. Existing historical statistics remain usable when reviewed trail coverage is missing.

## Tests

The full November 24 suite passed 62 tests with no failures, errors or skips, including live read-only Supabase checks, invalid citations/links/numbers, transient errors and timeout behavior, fallback labeling, and key retention across page navigation. Provider unit tests are mocked. Successful live planning and synthesis for camping and a combined Zion question are documented separately with provider response IDs in reports/conversation_live_verification.json. See reports/conversation_tests.json for automated checks.
