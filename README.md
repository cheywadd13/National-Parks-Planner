# National Parks Explorer

## When should you visit, and what can you do there?

A forest-themed Streamlit travel planner combining historical weather, recreation visitation, official park guides, reviewed hikes, and an optional API-powered travel assistant. Project for **Databases for Data Science** and **Programming for Data Science**. AI-assisted development is disclosed in the reports.

![Actual park guide](docs/screenshots/park-guide.jpg)

## Features

- Interactive PyDeck discovery map with park, state, activity, and seasonal filters.
- Official NPS descriptions, credited photography, activities, source links, and optional current alerts.
- Reviewed hiking cards with published difficulty, distance, duration, restrictions, and explicit unknown fields.
- Historical monthly temperature, precipitation, snowfall, and recreation visitation charts using Plotly.
- Transparent best-month rankings with adjustable comfort range, historical years, and weather/crowd weights.
- Two- or three-park comparisons, descriptive statistics, missingness, seasonal outlier sensitivity, and raw/month-adjusted Spearman correlations.
- Optional conversational travel assistant that turns questions into validated query plans and retrieves verified results through predefined read-only Supabase queries.

**Coverage:** 63 park reporting records, 2005–2025; 15,876 weather park-months and 15,863 visitation park-months. There are 13 missing visitation months, retained as gaps. This is not a claim of 63 distinct officially designated National Parks. The reviewed trail catalog has **17 routes across six park codes**, not comprehensive nationwide trail coverage.

## Quick start

Use Python 3.11. From the repository root:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and replace placeholders locally:

```toml
DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require"
OPENAI_API_KEY = ""
OPENAI_MODEL = "gpt-6-luna"
NPS_API_KEY = ""
```

Use your Supabase PostgreSQL connection string, preferably for a dedicated SELECT-only role. Environment variables with the same names are supported and take precedence. Do not commit real configuration. The app opens read-only repeatable-read database transactions and never runs schema migrations or ETL writes automatically.

`DATABASE_URL` enables live historical data. For explicitly labeled local exploration only, `PARKS_CSV_DIR` can point to a folder containing `parks_supabase.csv`, `visitation_supabase.csv`, and `weather_supabase.csv`. Partial historical exports are **not** a replacement for the complete database; historical assistant queries require live Supabase.

The optional NPS key enables official refresh and alerts. Without it, dated cached official content is used and unavailable live information is labeled. The OpenAI key can alternatively be entered in the assistant's **masked, session-only setup field** and forgotten from the session. Other application features work without an LLM key.

## Architecture

```text
NPS metadata / visitation + Open-Meteo
                  |
       src/etl: extraction, provenance, validation, staging
                  |
       Supabase PostgreSQL historical source tables
                  |
       src/database.py + src/travel_queries.py (read-only)
                  |
       analytics / recommendations / EDA / content modules
                  |
       app.py + Plotly + PyDeck + optional assistant UI
```

| Component | Files and responsibility |
| --- | --- |
| Application | `app.py`, `.streamlit/config.toml`: navigation, filters, theme |
| Data access | `src/database.py`, `src/travel_queries.py`: validated joins and predefined parameterized queries |
| Analysis | `src/analytics.py`, `src/eda.py`, `src/recommendations.py`: summaries, outliers, correlations, scoring |
| Visualization | `src/visualizations.py`: interactive weather, visitation, comparison and EDA charts |
| Official content | `src/nps_api.py`, `src/park_profiles.py`, `src/trails.py`, `data/`: cached profiles and reviewed trail records |
| LLM | `src/assistant.py`, `src/assistant_ui.py`: API request, strict plan validation, session preferences, evidence rendering |
| ETL | `src/etl/`: archived API acquisition, source transformations, idempotent staging and change plans |
| Database evidence | `sql/01`–`09`, `docs/schema_review.md`, `docs/erd.svg`, `reports/`: queries, schema and reconciliation |

The PostgreSQL tables are `parks` (primary key `park_code`) and `weather`/`visitation` (composite primary keys `park_code, year, month`, foreign keys to parks). The schema review documents normalization strengths and the multi-state membership tradeoff; proposed normalization is **not** applied to the live database. Reviewed trails are a local JSON catalog linked by park code, not a table claimed to exist in Supabase.

## Data sources and reproducibility

- [NPS developer API](https://www.nps.gov/subjects/developer/api-documentation.htm): JSON park metadata, activities, images, and optional alerts. Snapshot fallback retains source URLs and dates.
- [NPS Visitor Use Statistics](https://irma.nps.gov/Stats/): recreation visitation, transformed from monthly source reports to park/year/month records.
- [Open-Meteo historical weather](https://open-meteo.com/en/docs/historical-weather-api): daily JSON; temperature means and precipitation/snowfall totals aggregated by month.
- Official NPS hiking pages: reviewed routes only, with provenance and unreported details preserved as unknown. See `data/trails.json` and `src/etl/collect_verified_trails.py`.

Raw responses and provenance are retained under `reports/`. Content hashes and deterministic staging prevent repeated runs from creating duplicate artifacts. See [ETL lineage](docs/etl_lineage.md), [schema review](docs/schema_review.md), [quality report](reports/data_quality_report.md), and [trail investigation](docs/trail_issue_resolution.md). Original R/Colab source files are referenced by hashes and reviewed lineage; some historical original daily responses were never retained. Reproducibility of those past responses is therefore limited.

Run the reusable ETL without database writes:

```bash
python -m src.etl.pipeline --metadata metadata.csv --visitation visitation.csv --weather-monthly monthly_weather.csv --output staging
```

Optional `--compare-live` reads the database and reports a change plan. It does not load records. No live schema or data changes are authorized by release preparation.

## Recommendations and EDA

Monthly historical summaries use paired available observations and displayed year/sample counts. Suitability combines temperature comfort, precipitation, snowfall, and relative within-park crowd measures. User-adjustable weights express preferences, not probabilities. See `src/recommendations.py` and [project report](docs/project_report.pdf) for the exact implementation and limitations.

Missing observations are not filled with zero. Seasonal Tukey 1.5-IQR flags require at least eight observations and a positive IQR within park/calendar month. Default summaries retain flagged observations; sensitivity summaries expose their effect. Correlation is descriptive and is shown before and after month demeaning.

Verified example: Yellowstone's 2005–2025 July mean is 896,346 recreation visits and November mean is 16,475. Temperature/visitation Spearman correlation is 0.855 raw and 0.074 after month demeaning, based on 252 paired months. This illustrates strong seasonal confounding, not causation.

![Actual EDA view](docs/screenshots/eda-yellowstone.jpg)

## Optional LLM integration

The application uses the OpenAI **Responses API** through `requests`. The default remains `gpt-6-luna`, Standard processing (`service_tier="default"`) with reasoning off. Each question uses up to two requests: a strict interpretation plan (384 output tokens) and an evidence-grounded explanation (650 output tokens). Only explicit temporary synthesis HTTP errors can retry once. Timeouts are not automatically retried; there is no automatic model fallback. A 20-request conversation guard is not an account spending cap.

Python validates the interpreted request and uses predefined read-only, parameterized query functions. Broader park questions retrieve official descriptions, activities, reviewed trails, available alerts, and relevant historical statistics. The model then writes a concise explanation using only that evidence and citation IDs. Unknown citations, model-generated URLs, and new numeric strings fail validation and fall back to clearly labeled source facts. These checks reduce hallucination risk; they are not a proof of every sentence's factual accuracy. The model never runs SQL or writes to Supabase.

A short recent conversation and current preferences accompany each request. A masked session key survives navigation using separate in-memory state, and the Forget button removes it. It is never written to disk. Browser/server restarts still end that session. Questions and retrieved public park facts go to OpenAI; database credentials do not. `store=false` does not override provider retention policies.

Activity and park-evidence fallbacks are explicitly labeled if API interpretation is unavailable. An interpretation receipt and an explanation receipt are displayed separately, so a real API call cannot be confused with application-rendered fallback text. Historical statistics require live Supabase; incomplete CSV exports are not sent as substitute statistics. Real API evidence and test reports are in `reports/`; automated provider tests are mocked. See [conversation architecture](docs/assistant_architecture.md).

## Testing and release evidence

```bash
python -m unittest discover -s tests -v
```

The **November 24 complete release run passed 62 tests, zero failures, errors or skips**, including read-only live Supabase tests and local UI regressions. See `reports/conversation_tests.json` for the current run; `reports/final_release_tests.json` retains the earlier baseline and application code hashes. Enable `RUN_LIVE_DB_TESTS=1` and `DATABASE_URL` for live checks. Set `PARKS_CSV_DIR` to retained exports for the opt-in UI checks; both local exports and a live connection were available during the full release run. Without these settings, integration checks skip explicitly. CI runs the credential-free subset and must not be described as the full live release check.

Feature verification includes every navigation page, filters and units, activity-filter recovery, recommendation edge cases, assistant follow-ups, query scope and compound intents, trail relationships, missing information, and source/query parity. Map rendering and external live services also depend on browser/network availability; native browser automation was unavailable for a fresh final screenshot pass. Retained screenshots are actual app captures.

## Reports and presentation

- [Database project report](docs/project_report.pdf), [database rubric checklist](docs/rubric_checklist.md), [ER diagram](docs/erd.svg), [advanced SQL](sql/)
- [Programming report — 3 pages](docs/programming_report.pdf), [Programming checklist](docs/programming_checklist.md), [live demo plan](docs/programming_demo.md)
- [Programming final PowerPoint](presentations/National_Parks_Programming_Final.pptx): 12 editable slides, speaker notes, actual screenshots, native EDA charts and credits; approximately 13 minutes including demo
- [Release readiness review](docs/release_readiness.md), [publication guide](docs/publish_github.md)

## Limitations and deployment status

Historical monthly means are not current conditions, forecasts, or safety guidance. Park-wide recreation visits are not unique visitors or trail traffic. Weather represents one geographic point. `SEKI` combines Sequoia and Kings Canyon visitation but uses one weather point. Activity listings and trail coverage are incomplete; difficulty wording follows the official source. Check official pages for current access and permits.

Private repository: https://github.com/cheywadd13/National-Parks-Planner. Streamlit Community Cloud deployment is not yet completed. The app works locally; no hosted URL is claimed. After approved publication, configure `app.py` as the Cloud entry point and enter credentials in Cloud's secure secrets settings, never in the repository. Do not expose the student project's database owner credential in a public deployment; provision a SELECT-only credential first. Predictive ML, visitation forecasting, and itinerary generation are not implemented.

## Attribution

Official content and photographs retain NPS credit/source links. Third-party content rights are source-specific; do not assume every image on an NPS site is public domain. Open-Meteo attribution and terms apply to its data. The presentation source manifest includes photograph credits, URLs and chart values. This educational project is not affiliated with or endorsed by the National Park Service.

## Activity assistant correction

Activity-discovery questions now return verified NPS park options for climbing, hiking, camping and kayaking, with official links. Adding a month enables a live read-only weather/crowd comparison. A clearly labeled deterministic activity fallback works without a key or during API failure; it is never represented as a live LLM response. The activity-focused release passed 49 tests; the subsequent conversational release passed 62. See [activity fix and demo guidance](docs/activity_assistant_fix.md), `reports/activity_fix_tests.json`, and `reports/activity_fix_verification.json`.

## Version-control provenance

The original local development commits are retained in a Git bundle included with the submission. If the connected GitHub API is used to import development phases, their GitHub timestamps reflect the actual import date; original commit IDs, dates and messages remain in the local bundle. No teammate activity or semester-long commit history is fabricated.

Live conversational verification: both camping discovery and a combined Zion weather/crowd/hiking question completed through real planning and explanation API calls. See `reports/conversation_live_verification.json`. Source code and documentation are published privately; hosting remains a separate step.
