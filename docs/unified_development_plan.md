# Phased implementation proposal

Historical planning document from before implementation. The current release,
selected GPT-6 Luna Standard configuration, tests and remaining submission tasks
are documented in README and `programming_checklist.md`.

This proposal follows the November 21 audit in `dual_course_audit.md`. It is ready for review; no application changes, database changes, paid API calls or GitHub publication were performed for this audit.

## Phase 0 — Protect and consolidate

Inventory and hash both copies, preserve the prior verified application, choose one canonical Git working tree, and record existing changes honestly as a baseline. Ignore secrets, connection files, environment files and transient logs. Scan tracked files and repository artifacts before any publication. A retrospective initial commit must not be described as a historical development record.

Acceptance: one clearly identified source tree; backup; reproducible setup; baseline unit/UI and read-only live tests pass; recorded source mode and test timestamp. Existing comparison, maps, rankings, SQL and data-quality evidence remain accessible.

## Phase 1 — Complete park-information release

Finish testing the already-written NPS adapters, guide and snapshot transformations. Verify official URLs, photo credits, positive activity evidence, unknown trail fields and route distance basis. Exercise API pagination, timeouts, malformed payloads, empty alerts versus unavailable alerts, and stale-data labels. Add selected-park guide access from the map and preserve the discovery map as the main entry experience. Verify Desktop and packaged copies match the release before refreshing the preview.

Proposed tests: `tests/test_park_content.py` and expanded `tests/test_app.py`; all prior tests rerun. Acceptance: selected park clearly shows description, credited photo when available, official links, activities, reviewed hike cards, seasonal explanations and honest coverage/source timestamps. Live alerts require a real NPS key; snapshot fallback must be explicit.

## Phase 2 — Complete mandatory EDA

Add missingness coverage, per-park/calendar-month statistical outlier flags with sample counts, and sensitivity summaries. Retain plausible extreme weather/visitation observations; never delete them just because an IQR rule flags them. Reject impossible values at ingestion; preserve unexplained values for review. Explain why seasonal peaks and pandemic-era changes may be genuine signals. Keep median-based recommendation behavior unchanged unless explicitly justified and reconciled.

Add filtered, computed narratives for descriptive statistics and raw versus season-adjusted Spearman associations. Include insufficient/constant data states, denominators and noncausal interpretation.

Acceptance: known-data tests in proposed `tests/test_eda.py`, correlations and flags reproducible, results change correctly with park/year controls, existing score reconciliation still passes.

## Phase 3 — Database mastery evidence

Retain current read-only audit and eight advanced queries. Prepare executable but unapplied migration proposals for `state`/`park_state`, domain constraints and a SELECT-only application role. For new content propose `source_artifact`, `park_profile`, `park_image`, `activity`, `park_activity`, `trail`, `trail_source` and `park_alert`, each with stable source IDs, timestamps and FK relationships. Keep source assertions/measurement types separate from unreported values; alert history must not imply current status after expiry. Add source provenance and content freshness dictionary. Model route variants explicitly where distance/difficulty differs.

Build an idempotent transactional loader and exercise it only against an isolated disposable database: same input twice produces no extra rows; conflicting rows are surfaced; rollback and FK failure are tested. Produce dry-run migration/load diffs. The existing live schema and records stay untouched pending explicit approval.

Acceptance: isolated loading tests, proposed ERD/DDL, query explanations, measured plans and SQL/Python result reconciliation. If live normalization is not approved, disclose the remaining strict-3NF limitation rather than claiming mastery was achieved.

## Phase 4 — Grounded in-app LLM

Implement after the park-information experience is verified. Use the OpenAI Responses API through a replaceable provider adapter. Proposed initial model: `gpt-6.1-terra`, subject to an account-access and factual-grounding evaluation. Model choice stays configurable. No external search/vector service is required for this bounded corpus.

Application flow:

1. Capture user question and validated session preferences: parks, month/year range, temperature range, difficulty and crowd/weather weights.
2. Classify into a bounded supported intent with structured arguments. Reject invalid months, codes, unbounded rows and unsupported requests.
3. Execute predefined functions such as `least_visited_in_month`, `mild_weather_parks`, `verified_hikes` and `compare_month_suitability`. Database values are bound parameters; schema identifiers and query shapes are fixed. No model-authored SQL, writes or database credential exposure.
4. Compute rankings/statistics in tested code/SQL and assemble evidence with record IDs, units, observation counts, analysis years, timestamps and official links. Query each many-to-many relation independently or preaggregate before joining to prevent inflated totals.
5. Ask the model to explain only the retrieved evidence. Render authoritative fact tables and citations directly from the application. Validate structured references and numeric claims against evidence; suppress unsupported claims and show a grounded fallback when validation fails. Prompt instructions alone cannot guarantee factuality.
6. Retain bounded conversation/preferences in Streamlit session state. Treat retrieved text as data, never as instructions. Clear missing fields stay missing. Closures and permits require current official evidence; absent evidence means unavailable, not open/no permit.

Proposed files: `src/travel_queries.py`, `src/assistant.py`, `tests/test_travel_queries.py`, `tests/test_assistant.py`, chat view in `app.py`.

Acceptance: all four sample questions answered from independently checked facts; follow-ups work; no-key mode leaves the rest of the app working; mocked timeouts/rate limits/invalid JSON/injection and unavailable facts tested; one real, low-volume successful API interaction demonstrated before claiming this requirement complete. Do not show a canned response as a live LLM call.

### Provider, configuration and expected cost

Official pricing checked November 21, 2026: GPT-6.1 Terra standard text input **$1 per million tokens**, output **$5 per million tokens**. Example assumption: 3,000 input tokens plus 1,000 total billed output tokens costs **$0.008 per answer**, or **$0.80 for 100** / **$8 for 1,000** answers. This is an arithmetic estimate, not a spending cap. Multiple routing calls, follow-up context, reasoning tokens and retries increase use. Track actual provider usage; bound context/output, retries and per-session calls. Set provider spend controls appropriate to the account. Hosting and existing Supabase usage are separate.

Credentials: existing `DATABASE_URL`; new server-side `OPENAI_API_KEY`; optional `OPENAI_MODEL`; `NPS_API_KEY` for live official profiles/alerts. Store in environment or Streamlit secrets, never source control or chat transcripts. Verify account billing/access before enabling paid calls. Keep the assistant disabled without its key and provide factual non-LLM controls.

Sources: [model capabilities and prices](https://developers.openai.com/api/docs/models/gpt-6.1-terra), [API quickstart and server-side configuration](https://developers.openai.com/api/docs/quickstart). Recheck rates and model availability at implementation time. The Programming rubric's permitted alternatives remain possible, but the latest user request specifically selects direct in-app integration.

## Phase 5 — Submission-ready artifacts

Update README with architecture, sources, API setup/costs, source modes, reproducible commands, tests and limitations. Update database report/checklist and ERD to actual final behavior. Create a separate 2–3 page Programming PDF/Word report with final screenshots, objectives, methods, measured results and truthful collaboration/lessons. Verify pagination and visual layout after rendering. Locate or complete the individual's five-database comparison workbook without asserting an unverified prior submission.

Create `docs/programming_demo.md`: 12 minutes planned plus 3 minutes buffer. Suggested timing: purpose (1), external acquisition/storage (1.5), park/map/hikes (2), EDA/missing/outliers/correlation (2.5), grounded assistant including follow-up (2), database live status and code/Git evidence (1), limitations/results (2). Rehearse to at most 15 minutes; maintain clearly labeled source snapshots for outages and disclose any feature not live.

Create `docs/database_presentation.md`: purpose/source complexity → model/normalization → ETL/idempotency → substantive SQL → derived-result reconciliation → live app → tradeoffs. Confirm presentation timing with that course; do not assume Programming's 15-minute rule applies. Record no final videos yet.

Acceptance: clean clone/setup test; all prior/new tests pass with dated evidence; secrets absent from tracked files; local/live demonstration verified; GitHub and report access checked; report not over 3 pages; both submission checklists complete. Publishing the repository must use the user's intended account/repository and deliberate visibility.

## Phase 6 — Optional enhancements

Expand reviewed trail coverage, accessibility, richer comparison and only then optional evidence-grounded itinerary generation. No predictive ML or visitation forecasting in any phase.

## Approval and information still needed

The user requested review before implementation and implementation of approved improvements. Approve this application-only phased scope before Phase 0 changes. Live schema/privilege changes and data loading require a separate explicit approval after reviewing concrete migration/load diffs. No approval for those changes is implied by approval of the application plan.

Before publishing/submission: identify the intended GitHub account/repository/visibility; confirm solo/team status and real contributions; locate the student's database-selection workbook and submitted milestones. Before live LLM/NPS tests: configure keys securely. These details need not block local deterministic implementation after plan approval.
