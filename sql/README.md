# Verified PostgreSQL query collection

Each file is a parameterized SELECT with psycopg named placeholders. The
src.audit runner binds values separately from SQL and executes every file in
one read-only, repeatable-read transaction. SQL Editor users must replace
placeholders with reviewed literals because the Editor does not bind psycopg
parameters. Example settings are recorded in reports/query_parameters.json.

| Query | Question and method | Verification |
| --- | --- | --- |
| 01_park_history | What weather and visits correspond to each observed month for a selected park? Three-table join on the full key and parameterized year range | PK/FK cardinality and live app data, EXPLAIN ANALYZE plan |
| 02_least_crowded | Which calendar months have the lowest historical median visits? Grouped medians, coverage HAVING, RANK and peak window | All 190 top-three rank rows match independent pandas ranks, including ties |
| 03_seasonal_visitation | How does visitation distribute across seasons? CTEs, complete-year selection, CASE season, derived annual shares | All seasonal totals reconcile to complete-year totals |
| 04_weather_climatology | What conditions are typical for each park and calendar month? Averages, support counts and sample standard deviation | All 756 profiles match application weather chart means |
| 05_suitability | Which month best matches the user's preferences? Paired-year medians, CTE pipeline, average tie ranks, window counts and derived weighted scores | All 756 default scores, ranks, medians, crowd percentiles and support counts match Python |
| 06_coverage_gaps | Which expected park-months are absent? generate_series grid and anti-join logic | Identifies 13 missing visitation keys and zero missing weather keys |
| 07_annual_change | How did complete-year visits change from the previous year? LAG and gap-aware growth | Independent annual sums and growth comparison |
| 08_seki_reconciliation | Does SEKI equal SEQU plus KICA? Bound raw components, grouped sums and FULL JOIN | All 252 component sums match the database exactly |

## Interpretation and denominator choices

Least-crowded medians use all valid visitation rows independently of weather.
Suitability uses only months with all four inputs and a minimum count of paired
years. These queries can rank different samples when weather is absent.

Season totals and annual growth exclude incomplete park-years. Winter means
January, February and December within the same calendar year. A zero annual
denominator or non-adjacent previous year produces NULL growth.

Crowd percentiles compare eligible months within one park before any discovery
filter. SQL uses the midpoint of a tied rank block to match pandas average ranks.
PERCENT_RANK by itself would assign the first rank of a tie block and would
disagree with the current application. The final score blends explicit weather
preferences and seasonal crowd position. It expresses a configurable index.

Query 05 retains all twelve months for every park, leaving insufficiently
observed months unscored. Valid temperatures may be negative. SQL excludes
missing or non-finite weather and negative totals to match application cleaning.

Query 08 requires the retained component data as JSON because SEQU and KICA
are source codes rather than separate live park records. The ETL validator
checks component uniqueness and completeness before binding that JSON.

## Result artifacts

reports/01_park_history.csv through reports/08_seki_reconciliation.csv preserve
the results of the same transaction. reports/catalog.json documents constraints,
indexes and access. reports/query_plans.json records one read-only plan
measurement. JSON inputs, credentials, hosts and passwords are excluded from
published parameters.

~~~powershell
python -m src.audit --source-directory 'C:\Users\cheye\Desktop\DB for DS 26'
~~~
