# Database rubric gap analysis

Audit based on the Desktop project, the Colab Python export, the R collection
script, and a read-only PostgreSQL 17.11 catalog inspection.

| Priority | Rubric area | Existing evidence | Gap | Authorized improvement |
| --- | --- | --- | --- | --- |
| 1 | Design and querying, 30% | Three tables, composite monthly PKs, two validated FKs, three unique B-tree indexes | Multi-valued state field, missing domain checks, no ERD, most analysis in pandas | Document functional dependencies, current and proposed ERDs, catalog evidence, parameterized analytical SQL and parity tests |
| 1 | ETL, 25% | R API collection and Colab integration/backfill | Interactive paths, missing Python weather helper, no immutable daily archive, race-prone pre-insert checks, incomplete provenance | Strict reusable transformations, raw response capture, manifests, deterministic local staging and read-only load planning |
| 1 | Derived information, 20% | Seasonal summaries and transparent suitability | SQL parity unverified, SEKI totals not independently reconciled, 13 visitation gaps unexplained | Compare source records and SQL with pandas, validate coverage and aggregation, report discrepancies explicitly |
| 2 | Usefulness and sizzle, 15% | Phase 1 map, filters, charts, recommendations, comparison, EDA | Live source mode needs visible evidence, validation must preserve UI | Source status, read-only live AppTest, chart and filter reconciliation |
| 2 | Database selection, 5% | Supabase PostgreSQL connected | Alternatives and workload rationale undocumented | Compare PostgreSQL, SQLite, MySQL, document stores and flat files |
| 2 | Written explanation, 5% | Setup README and in-app methodology | No integrated technical report or evidence checklist | Project report, ETL lineage, SQL guide, quality report and rubric checklist |

## Initial live findings

The database has 63 park records, 15,863 visitation rows, and 15,876 weather
rows. PKs are parks(park_code), visitation(park_code, year, month), and
weather(park_code, year, month). Both monthly tables have validated park-code
FKs. Only the three PK indexes exist. Measures and most park attributes are
nullable, and domain CHECK constraints are absent. RLS is disabled on these
tables and the supplied role can write. Application transactions explicitly
request read-only access. Role/privilege changes require owner approval.

The monthly relations satisfy 3NF under the intended dependency from the full
monthly key to the measurements. The parks relation stores state lists such
as CA,NV and ID,MT,WY. A strict atomic-state interpretation needs a separate
park_state relation before claiming the complete logical design is in 3NF.

## Implementation order

1. Capture catalog, raw-source and coverage evidence.
2. Add reusable ETL and strict idempotent local staging with no database loader.
3. Add analytical SQL with independent result reconciliation.
4. Run live data, source, recommendation and application validations.
5. Publish the ERD, quality report, project report and rubric checklist.

Schema migrations, privilege changes and future forecasting remain subject to
the user's separately stated approval requirements.
