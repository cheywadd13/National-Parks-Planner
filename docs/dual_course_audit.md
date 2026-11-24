# Unified project: audit against both course requirements

Audit date: November 21, 2026. This is a source-code and retained-evidence audit, not an instructor grade or a fresh live-database certification.

## Authoritative inputs and scope

- Databases: supplied **Final Project Complete Guide — Bring Your Own Data**, including the six-category mastery descriptors, submission instructions and milestones.
- Programming: **Final Year-End Project Programming for Data Science Oct 2026.pdf**, pages 1–3.
- User direction: one application/repository, preserve existing features and Supabase, no forecasting, no live writes/schema changes without explicit approval. The latest request reinstates the in-app LLM assistant.

The course documents establish assessment requirements; their examples are not additional implementation instructions. Optional itineraries, exhaustive nationwide trail coverage, and predictive ML are not mandatory rubric items. The user excludes predictive ML. A direct in-app LLM API integration is the selected target even though Programming page 2 lists local-model and explicitly disclosed subscription-based alternatives. Merely using Codex to develop this project should not be presented as the completed in-app assistant.

## Evidence boundaries

Two project copies exist: the Desktop project and `outputs/National Parks Explorer`. The latter includes new park-guide modules and snapshots that have not yet completed regression testing or been synchronized to the Desktop preview. Neither inspected directory is a Git repository. Do not claim that the preview contains every working-copy change.

`reports/verification_summary.json` records **19 passing tests**, including live checks, on November 19. It predates the new park-guide changes. The latest `work/guide_regression_tests.log` contains no conclusive final suite summary, so those changes remain unverified. No tests or database audit were rerun for this document-only audit.

Retained database evidence: 63 reporting records, 15,863 visitation months, 15,876 weather months; 13 source-aligned visitation gaps; 252/252 SEKI component sums match. These are dated audit findings, not a new query result. The old local exports are incomplete and differ from live weather values.

Status: **Evidence** = implementation plus retained verification; **Partial** = material gaps or unverified changes; **Missing** = not found; **External** = submission/personal action cannot be inferred. P0 = submission-critical; P1 = mandatory completion; P2 = mastery/polish; P3 = optional.

## Database requirements matrix

All paths below are relative to the project root. Proposed files/tests are explicitly marked.

| ID / weight | Requirement | Existing evidence / status | Missing functionality or evidence | Proposed implementation, files and tests | Priority |
| --- | --- | --- | --- | --- | --- |
| D1 / 5% | Individually compare chosen database plus four alternatives; good/poor fits and common uses; project-specific justification | `docs/project_report.md` discusses alternatives; Partial | Required completed comparison `.xlsx` and individual submission not found | Locate student's original template/submission first; prepare accurate five-database workbook if absent; check all required columns; do not invent past submission | P0 |
| D2 / 30% | Relational model fits data and serves questions | `docs/schema_review.md`, `docs/erd.svg`, `reports/catalog.json`; Evidence | Refresh catalog before final submission | Retain one park to many monthly facts and independent source coverage; read-only catalog comparison in `src/audit.py` | P1 |
| D3 / 30% | Third normal form | Monthly relations satisfy intended functional dependencies; Partial | Multi-state strings are a strict 1NF/3NF gap under membership semantics | Proposed `state` and `park_state` decomposition already documented; submit migration design for separate approval; never certify current full schema as strict 3NF | P0 |
| D4 / 30% | Integrity: PK, FK, constraints and indexes | Validated PKs/FKs and PK B-tree indexes in catalog; Partial | Domain CHECKs absent, non-key columns nullable; inspected role has write privileges | Approval-only domain constraints and dedicated SELECT role; retain read-only transaction protection; proposed catalog tests verify approved changes | P1 |
| D5 / 30% | Substantive joins, grouping and derived SQL | `sql/01`–`sql/08`, query outputs and `sql/README.md`; Evidence | New park content currently JSON, not relational tables | Preserve eight queries; add proposed activity/trail joins only with approved content schema, or disclose app-layer join | P1 |
| D6 / 30% mastery | Advanced database techniques and design tradeoffs | CTEs, window functions, ranking, `reports/query_plans.json`; Evidence | Only one representative performance plan | Benchmark actual park/month/discovery workloads; explain why extra indexes may be unnecessary at this scale | P2 |
| D7 / 25% | At least two meaningful sources and reason to use database | NPS visitation/metadata plus Open-Meteo; `docs/etl_lineage.md`; Evidence | New NPS content not yet integrated into final documentation | Document API JSON vs NPS CSV/HTML, identifiers, units, point-weather and reporting grains | P1 |
| D8 / 25% | Meaningful integration/transformation rather than raw copying | `src/etl/transform.py`, original Python/R review, `tests/test_etl.py`; Evidence | New content transforms need tests | Preserve key mapping, SEKI sum, daily-to-monthly aggregation; proposed `tests/test_park_content.py` checks provenance and missing fields | P1 |
| D9 / 25% mastery | Working loading process reruns without corruption/duplicates | Historical load scripts plus immutable, repeatable staging/change plans; Partial | Reusable pipeline deliberately has no database loader; local staging alone does not prove idempotent live loading | Build/test transactional loader against an isolated disposable PostgreSQL instance; produce dry-run diff; execute against live only after explicit approval | P0 |
| D10 / 20% | Useful, correct derived information | Scores, crowd ranks, climatology, seasonal sums; SQL/Python reconciliation in audit; Evidence | Reconcile after any scoring/query change | Retain paired-year denominators, ties, insufficient-data states, weight normalization; `tests/test_phase1.py`, `tests/test_database_evidence.py` | P1 |
| D11 / 20% mastery | Missing, duplicate, join and aggregation issues handled throughout | `src/audit.py`, quality report, SEKI reconciliation; Evidence | New trail/activity joins need cardinality checks | Check uniqueness by source ID, many-to-many fan-out prevention, missing measurements and timestamp validity; proposed content tests | P1 |
| D12 / 15% | Useful interactive application queries database live | `src/database.py`, existing app and dated live tests; Evidence | Fresh demo-mode verification and preview sync needed | Ensure DATABASE_URL mode, remove CSV override, show source/time; rerun live tests without credential output | P0 |
| D13 / 15% mastery | Exceptional polish, clarity, usability | PyDeck, Plotly, filters, recommendations and comparison; Partial | Park-guide changes not release-tested; mobile/map behavior needs visual QA | Verify all views, park selection, photos, attribution, accessibility and responsive layout; `tests/test_app.py` plus visual checks | P1 |
| D14 / 5% | Written purpose, pipeline/model/results/app connections and reasons | `docs/project_report.md` and seven-page PDF; Evidence for previous version | Must match final unified architecture and current limits | Update database report, ERD and rubric checklist after implementation; evaluate alternatives and tradeoffs | P1 |
| D15 / 5% mastery | Evaluate limitations and plausible alternatives | Schema/ETL/score/point-weather limitations documented; Evidence | Add API caching, incomplete trail coverage, LLM grounding/cost tradeoffs | Extend report and source documentation using measured final behavior | P2 |
| D16 / submission | One accessible final URL by Dec 11; app/code and written explanation | Local files present; External | Repository/landing URL and access not verified | Prepare repository with reproducible setup; validate instructor access; link final report and runnable app | P0 |
| D17 / milestones | Oct 30 readiness; Nov 3 database selection/team acknowledgment; Nov 5/19 milestones; weekly check-ins; Dec 3 working app | Local technical artifacts exist; External | Canvas/check-in completion unknown | Student confirms submission history; prepare remaining Dec 3 checkpoint evidence without inventing attendance | P1 |
| D18 / presentation | Dec 8 video if choosing video, or in-person alternative | Existing artifacts can support presentation; Missing plan | No final presentation plan verified | Create separate database story emphasizing model, ETL, substantive SQL, reconciliation and tradeoffs; do not generate video | P1 |

## Programming requirements matrix

The PDF assigns **20% each** to acquisition/EDA; code/documentation/GitHub; LLM; Streamlit; presentation. It provides no finer numerical subweights.

| ID / category | Requirement | Existing evidence / status | Missing functionality or evidence | Proposed implementation, files and tests | Priority |
| --- | --- | --- | --- | --- | --- |
| P1 / acquisition & EDA | Fetch real data from external API or permitted other source | Open-Meteo capture/reaggregation in `src/etl/extract.py`, `verify_weather.py`, retained response; Evidence | Final workflow needs a clear end-to-end demo | Demonstrate fetch → immutable raw JSON → validated transformation → stored result with timestamp/hash | P1 |
| P2 / acquisition & EDA | Document source and JSON/CSV/XML structure | `docs/etl_lineage.md`, source hashes; Partial | New NPS API/HTML and trail schema need documentation | Add source dictionary and response examples with licenses/provenance; avoid secret-bearing payloads | P1 |
| P3 / acquisition & EDA | Retrieval and storage logic in app or module | `src/etl`, snapshot data and raw archives; Evidence | NPS live responses currently cached, not durable API acquisition evidence | Add explicit local JSON capture command and fixture-backed tests; no live DB load | P1 |
| P4 / acquisition & EDA | Descriptive statistics and visualizations | `app.py` Data & methods, `src/analytics.py`, Plotly; Evidence | Could improve interpretation | Add computed, sample-aware findings beside charts; test on known synthetic data | P1 |
| P5 / acquisition & EDA | Identify and treat missing data | Coverage audit, complete-case scoring and counts; Evidence | Explain different missingness by metric inside EDA | Show missingness grid and documented preserve/exclude policy; never fill unknown visits with zero | P1 |
| P6 / acquisition & EDA | Identify and treat outliers | Domain validation and robust monthly medians; Partial | No explicit statistical outlier diagnostics found | Flag within-park/calendar-month IQR outliers where sample adequate; retain plausible extremes, distinguish invalid values; provide sensitivity comparison and proposed `tests/test_eda.py` | P0 |
| P7 / acquisition & EDA | Correlation analysis between key variables | Raw and month-demeaned Spearman in `associations()`; Evidence | Interpretation needs visible computed narrative and sample warnings | Explain seasonality/confounding and lack of causality; constant/small-sample tests; don't call seasonal adjustment causal | P1 |
| P8 / acquisition & EDA | Findings and summaries inside Streamlit | Descriptive/coverage/correlation tables and plots; Partial | Findings currently mostly left to user interpretation | Add concise factual findings derived from current filtered data; test changing years/park updates narrative | P1 |
| P9 / LLM | Meaningful interaction with LLM API or permitted alternative | No implemented LLM module found; Missing | Entire 20% category lacks application evidence | Optional-key Responses API adapter, evidence-grounded explanations and real successful demo; proposed `src/assistant.py`, `tests/test_assistant.py` | P0 |
| P10 / LLM + Streamlit | LLM directly integrated in application | Missing | Chat UI, follow-ups, preferences, evidence and failure states | Add Streamlit chat with session preference state, bounded context and clear source panel; optional unavailable state preserves all other views | P0 |
| P11 / user's grounding requirement | Predefined read-only parameterized queries; no invented facts | Existing DB snapshot reads are read-only; Missing assistant query API | Allowlisted query functions and grounding validation | Proposed `src/travel_queries.py`; parameter-bound SELECTs, allowlisted identifiers, validated arguments and row limits; tests for injection, nulls, empty results, sources and unsupported claims | P0 |
| P12 / Streamlit | Clean organized interface | Existing themed navigation, maps and cards; Partial | New destination-guide code unverified | Finish and verify park profile/activities/hikes before assistant; retain all existing views | P1 |
| P13 / Streamlit | Interactive filtering, visualization and querying | Search, state, years, preferences, comparison; Evidence | Activity filter needs regression tests | Tests across empty/single/multiple park selections, thresholds, units and activity intersections | P1 |
| P14 / Streamlit | Error handling, documentation and user guidance | DB validation, corrective scoring guidance; Partial | External API/assistant reliability not verified | Timeout/retry/cache/fallback tests; distinguish unavailable alerts from successful empty alerts; no fabricated offline LLM response | P0 |
| P15 / code & GitHub | Modular, readable, documented Python | `src/database.py`, analytics, visuals, ETL and tests; Evidence | New module docs and duplicated compatibility package need explanation | Document module boundaries, types where useful and compatibility imports; preserve behavior | P1 |
| P16 / code & GitHub | Mandatory Git/GitHub and meaningful commits per team member | Neither inspected project copy is a Git repo; Missing | Local history, remote, attribution and collaboration evidence | Establish one canonical repo, secret scan/ignore raw credentials, make real incremental commits; never fabricate prior history/contributions | P0 |
| P17 / code & GitHub | README purpose, setup, sources/APIs and run steps | `README.md`, requirements and secrets example; Partial | New NPS/LLM/EDA/release behavior absent | Update after each phase; verify clean-environment run and optional-key behavior | P1 |
| P18 / deliverable | GitHub repository contains source, applicable data and docs | Local project only; Missing | Accessible GitHub URL and curated contents | Package reproducible fixtures/provenance, licenses, reports, tests and lock/version strategy; verify remote access | P0 |
| P19 / deliverable | Working local or hosted Streamlit app with all required features | Previous app works; Partial | Latest release and LLM demo incomplete | Release candidate with smoke tests, fresh live checks and documented startup; hosting optional | P0 |
| P20 / report | Separate 2–3 page PDF/Word report with objectives, methodology, results | Database report is seven pages; Missing Programming report | Correct length, screenshots and actual results | Proposed `docs/programming_report.md` plus PDF; capture final UI screenshots; render and verify 2–3 pages | P0 |
| P21 / report | Reflection on collaboration and lessons | Missing verified account | Team membership and actual division of work unknown | Obtain truthful student account; disclose solo work if applicable and explain tools used; do not invent teammates | P1 |
| P22 / presentation | Class live demo/presentation max 15 minutes | No verified plan; Missing | Timed narrative and recovery plan | Proposed `docs/programming_demo.md`, 12-minute script plus 3-minute buffer; demonstrate acquisition, EDA, LLM and live data | P0 |
| P23 / submission | Submit GitHub and hosted URL if applicable, report in repo and portal | External | Portal completion/access unknown | Final submission checklist and working links; student submits to portal | P1 |

## Feature-specific readiness

- Existing map, year filters, weather/visitation charts, rankings and comparison are implemented; retained tests predate this content upgrade.
- Working-copy snapshots contain 63 park entries with 61 nonempty descriptions, 62 parks with credited NPS images, 53 with recognized official activity links, and 16 reviewed routes across six parks. This is incomplete trail coverage, not a national structured trail database. Missing details must remain unknown. The description count was corrected during the Programming release tests.
- `src/nps_api.py` and `src/park_profiles.py` implement optional live profile/alert reads and dated fallback snapshots. No NPS key is configured locally; live alert delivery is therefore not demonstrated.
- A recommendation is a transparent preference score based on historical monthly statistics. Park-wide visits do not measure trail traffic; point weather does not establish trail conditions or safety.
- SEKI is a combined reporting record, not two independently modeled parks. Preserve its source mapping and one-point-weather caveat throughout joins and assistant explanations.

## Highest-impact completion order

1. Stabilize the working-copy guide and establish one release-tested Git repository.
2. Close the Programming outlier/interpretation and in-app LLM gaps.
3. Resolve database 3NF/idempotent-loading gaps with a reviewed proposal and isolated tests; obtain approval before any live change.
4. Produce the distinct Programming report/demo and update the database report/checklist.
5. Verify real submission access and rehearse; optional itinerary work comes last.

No defensible numerical grade can be assigned from this audit. Strong existing database evidence does not substitute for the missing Programming LLM, Git history or presentation deliverables.
