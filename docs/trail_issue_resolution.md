# Trail lookup investigation and resolution

Investigated November 22, 2026. Supabase access was read-only throughout; no
schema, privileges or records were changed.

## What caused the reported response

The exact question asked about Zion in October, historical weather/crowds, and
Moderate hikes. Retained conversation evidence showed that the LLM returned
only `intent=hikes`, `park_codes=[ZION]`, `months=[10]`, `difficulty=Moderate`.
The single-intent application consequently discarded the historical visit
question. The original local catalog had only two Zion records: an Easy route
and an unrated route. Neither met a Moderate filter. This was an actual
coverage gap, not a wrong Zion foreign key or failed Supabase trail query.

The generic empty-state text was misleading: month/year controls were suggested
even though the local trail search did not apply those controls. It did not
distinguish absent park coverage from excluded records.

## Database and relationship checks

Fresh inspection found the project's `parks`, `weather`, and `visitation`
tables, but no public trail/hike table or view and no trail/hike column. The
assistant obtains routes from `data/trails.json`, not PostgreSQL. There is no
database trail FK to inspect; the catalog's park-code relationship is an
application join validated against live `parks` codes. All catalog codes match,
and trail IDs have no duplicates. Existing monthly-table FKs remain intact.
Other course tables in the shared public schema were not modified or queried
for their records.

`reports/trail_diagnostics_before.json` retains the 16-route baseline.
`reports/trail_diagnostics.json` records the updated 17-route catalog, six
covered park codes, zero orphan codes and zero duplicate IDs. Four fixed
historical-query scenarios reconciled against existing analytics. Three more
live combined-request checks verified that weather/crowd results survive both
missing coverage and difficulty exclusions.

## Implemented corrections

- Added `visit_and_hikes`, preserving the requested park, month and difficulty.
  A deterministic guard preserves both parts when a supported model plan
  mistakenly chooses only hiking or timing for an explicitly combined request.
- Added per-park `no_data`, `no_matches` and `matched` diagnostics. Messages show
  actual catalog counts, applied difficulty, available labels and alternatives.
  Missing grades remain unknown. Grade matching handles case/whitespace and
  explicitly published ranges without inferring a rating from distance.
- Fixed a separately observed national-comparison bug: the model chose ACAD,
  ARCH and BADL for an unqualified national October question. National requests
  now clear unrequested park restrictions. Explicit park names take precedence
  over the discovery selection. This fix is covered by regression tests.
- Added official NPS Watchman Trail to the **local** catalog: Moderate, 3.3 miles
  round trip, published duration 1–2 hours. Full-route elevation gain remains
  unknown; accessibility segment gains are not represented as a full-route sum.
  No-reservation wording is not treated as proof of no permits or current access.
- Added a review-gated, idempotent local ingestion command and immutable source
  hash. Run `python -m src.etl.collect_verified_trails` to reproduce it. Changed
  source facts trigger human review rather than silent replacement.
- Added explicit real-API receipts for future successful calls, storing only
  response ID, model/tier, tokens, intent and time. Keys, prompts and travel
  preferences are not written to the receipt. Runtime receipts are Git-ignored.

## Verified Zion result

For 2005–2025, preferred temperature 15–24 °C, weather/crowd weights 65/35, and
minimum three paired years, October has 21 paired years and ranks 1 of 12:
median point temperature 11.44 °C, precipitation 20.6 mm, snowfall 0 cm,
314,966 median recreation visits, crowd percentile 45.45, suitability 76.87/100.
The temperature is below the stated preferred range. A high relative score
does not establish trail conditions, safety or access. Watchman is returned by
the Moderate route filter. Full evidence is in
`reports/trail_fix_live_verification.json`.

## Real OpenAI calls: what is proven

Five live GPT-6 Luna Standard interpretations were observed in the retained app
conversation; provider usage was not fabricated by the answer renderer. A newly submitted Badlands July-versus-October comparison used 1,028
input tokens and 37 output tokens, service tier `default`. Its figures came
from a live parameterized Supabase query even though Badlands has no catalog
routes. See `reports/openai_verification.json`.

The LLM generated structured request plans. The displayed sentences, statistics,
coverage notices and recommendations are rendered by Python from retrieved
evidence. They are not free-form LLM-authored answers. Successful API usage also
does not prove every plan was correct: the earlier scope and compound-intent
errors were found in these very conversations.

The previous release did not retain provider response IDs. The new receipt
path records them on subsequent successful calls. The corrected full question has now also succeeded end to end: the user confirmed it worked, and the provider receipt records `resp_091180e458086bf9016b03c1a4809087d2a01e3be52edc4527`, GPT-6 Luna, Standard/default, completed, intent `visit_and_hikes`, 1,086 input tokens and 37 output tokens. Live Supabase and automated routing/coverage tests independently verify the factual path.

## Remaining coverage and authoritative sources

The local catalog covers only six of 63 reporting records; 57 remain without
reviewed route records. Badlands is one such gap, not a park without hiking.
Its official NPS trail page is a suitable next ingestion source. The NPS
`thingstodo` and `places` endpoints are authoritative discovery sources, but are
not assumed to be a complete structured national trail database. Review each
route's published fields, preserve source URLs/retrieval times and nulls, and
respect NPS/third-party reuse notices. No commercial trail data was scraped.

Sources: [Watchman Trail](https://www.nps.gov/thingstodo/hike-watchman-trail.htm),
[Badlands official hiking routes](https://www.nps.gov/badl/planyourvisit/hiking-in-badlands.htm),
[NPS API documentation](https://www.nps.gov/subjects/developer/api-documentation.htm).
