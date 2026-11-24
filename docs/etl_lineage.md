# ETL lineage and reproducibility

## Reviewed source artifacts

The source files remain in the parent project directory. reports/audit_results.json
records their SHA-256 hashes. The notebook available for review is the exported
databasesproject_nationalparks.py, rather than an executed .ipynb with outputs.

| Source | Original collection and transformation | Integration evidence |
| --- | --- | --- |
| NPS park metadata | R script lines 14-61 requests /api/v1/parks; lines 87-133 select National Park, National Park & Preserve, National Parks, plus NPSA and REDW, retaining codes, names, state lists and coordinates | national_parks_information.csv maps exactly to all 63 live park records |
| NPS visitation | R script lines 65-79 reads the query-builder export; Colab lines 349-491 reshape individual monthly-wide reports, strip thousands separators and convert years/months | Retained long export reconciles 15,611 direct-code rows with live visitation |
| SEKI | R lines 123-126 identify component mapping; Colab lines 591-649 sums SEQU and KICA by year and month and inserts SEKI | All 252 live SEKI months equal both retained components summed |
| Open-Meteo weather | R lines 300-349 request daily temperature, precipitation and snow at park coordinates, timezone auto, 2005-2025; aggregate temperature means and amount totals; R persists partial progress | Live weather has 15,876 rows; retained partial monthly file has 4,536 |
| Supabase integration | Colab lines 55-75 paginate tables; lines 150-225 fetch Arches and insert new monthly rows; lines 255-280 backfill selected parks; final join uses park/year/month | Monthly PKs and FKs enforce integration grain |

Early R exploration copies SEKI weather to SEQU and KICA for a comparison.
The final database uses a single SEKI inventory and weather record. Those
exploratory copies are excluded from the reusable transformation.

## Original workflow gaps

The R script uses file.choose and in-memory state. Its monthly aggregation
uses na.rm=TRUE, so incomplete daily months can produce understated totals.
The exported Colab references download_park_weather without its definition
and contains notebook-only shell syntax. Its pagination has no ordering or
single-snapshot guarantee. Its select-existing-then-insert pattern can race
during concurrent reruns. Original daily weather responses, retrieval times
and exact model versions were not retained. None of these historical source
scripts is executed by the audit, because several cells perform inserts.

## Reusable workflow

1. Capture raw source CSV bytes or HTTPS response payloads under content hashes.
   Request parameters, retrieval UTC time and returned daily units accompany
   fresh API snapshots. NPS keys are passed in headers and omitted from manifests.
2. Canonicalize code case and whitespace. Parse counts after removing comma
   separators. Enforce valid monthly keys, integer visits, numeric finite values,
   nonnegative totals, and valid coordinates. Conflicting duplicate keys fail.
3. Require both SEQU and KICA for every observed component month and sum them.
   Validate any existing source SEKI row against that sum.
4. For daily weather, reject duplicate dates, missing values, mismatched units
   and partial months. Average daily mean temperature and sum precipitation
   and snowfall only after these checks pass.
5. Join against the normalized inventory and reject unmapped source codes.
   Preserve the original raw inputs and a manifest alongside deterministic CSVs.
6. Name staged runs by the hash of their canonical outputs. Identical reruns
   reuse the same immutable files and produce no appended duplicates.
7. Compare staged tables to a live read-only snapshot. Report new, unchanged,
   conflicting and existing-only rows. This pipeline has no database write path.

Existing live PKs already prevent duplicate logical keys. If an owner later
approves a database loader, it should use a transaction and PK-based
ON CONFLICT DO NOTHING for explicitly approved new rows, preserve existing
records, and report skipped/conflicting keys. Source revisions require a
separate reviewed correction policy. A client-side existence check alone is
insufficient for concurrent-load idempotency.

## Reproduce local staging

From the app directory, after installing requirements, set source paths in
PowerShell. The output contains archived copies of the three supplied CSVs.

~~~powershell
$source = 'C:\Users\cheye\Desktop\DB for DS 26'
python -m src.etl.pipeline --metadata "$source\national_parks_information.csv" --visitation "$source\Query Builder for Public Use Statistics (1979 - Last Calendar Year).csv" --weather-monthly "$source\national_parks_weather_2005_2025_partial.csv" --output work/etl
~~~

Add --compare-live with DATABASE_URL set to generate a read-only change plan.
The older weather export contains different values from the live series.
The plan is review evidence and does not authorize replacing live weather.

## Fresh API capture

collect_park_metadata requires NPS_API_KEY and paginates until the reported total.
collect_weather needs park coordinates and full-month date bounds. Reprocessing
an archived payload supports deterministic replay. A fresh request may return
revised data and therefore has its own timestamped manifest.

~~~powershell
python -m src.etl.verify_weather --park-code ACAD --year 2025
~~~

The representative check archives 365 daily observations, recomputes 12 monthly
rows and compares them with live Acadia weather. All 12 months match within
1e-8 in the recorded run. This verifies one complete year and the new aggregation
path. Original daily inputs for all other park-years remain unavailable.

[Open-Meteo historical weather documentation](https://open-meteo.com/en/docs/historical-weather-api)
and [NPS visitor-use reporting](https://www.nps.gov/subjects/socialscience/visitor-use-statistics.htm).
