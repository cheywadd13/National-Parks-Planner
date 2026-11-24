# Rubric requirements and evidence checklist

The weights below are the supplied rubric weights. No numerical grade is
estimated because the instructor's detailed performance descriptors and
grading decisions are unavailable.

| Weight | Requirement | Evidence in repository | Current status | Recommended improvement |
| --- | --- | --- | --- | --- |
| 30% | Key-based relational design | reports/catalog.json; docs/current_schema.mmd; docs/schema_review.md | Verified PKs, FKs and indexes | Add approved domain constraints |
| 30% | Third normal form | docs/schema_review.md; docs/proposed_normalization.mmd | Monthly relations meet intended 3NF; multi-state membership remains a normalization gap | Approve park_state decomposition before claiming complete strict 3NF |
| 30% | Professional ERD and tradeoffs | docs/erd.svg; current_schema.mmd; schema_review.md | Complete for the current live schema | Implement proposed relationships only after approval |
| 30% | Joins, aggregations, CTEs, windows, calculations | sql/01 through sql/08; sql/README.md | Eight queries executed and preserved | Use selected query results in the presentation/demo |
| 30% | Query performance and access design | reports/query_plans.json; reports/catalog.json | One representative plan recorded; existing PK indexes documented | Benchmark deployment workload; approve dedicated SELECT role |
| 25% | Multi-source acquisition and lineage | docs/etl_lineage.md; src/etl/extract.py; reports/audit_results.json source hashes | Original scripts reviewed; HTTP capture functions implemented | Retain raw acquisition payloads for every future ingestion |
| 25% | Cleaning, mapping, aggregation and integration | src/etl/transform.py; tests/test_etl.py | Strict transformations tested | Review any rejected records before loading |
| 25% | Repeatable and idempotent processing | src/etl/pipeline.py; reports/etl_staging; etl_change_plan.json | Identical staging reruns verified; no DB write path | Owner-approved transactional loader is a future task if needed |
| 25% | Historical weather reproducibility | reports/weather_validation | Fresh ACAD 2025 daily aggregation matches all 12 stored months | Original full daily archive unavailable; collect immutable future snapshots |
| 20% | Duplicate, null, domain and FK validation | src/audit.py; reports/data_quality_report.md; audit_results.json | All observed duplicate/null/domain/FK checks pass | Add persistence-layer domain enforcement after approval |
| 20% | Date grid and join cardinality | reports/06_coverage_gaps.csv; coverage_by_park.csv | Complete weather; 13 visitation gaps documented and source-aligned | Preserve gaps unless an authoritative corrected source is obtained |
| 20% | SEKI accuracy | reports/08_seki_reconciliation.csv | 252 of 252 component sums match | Retain components and dated identity mapping |
| 20% | Correct derived scores, statistics and filters | reports/audit_results.json; tests/test_database_evidence.py | SQL/Python reconciliation plus unit and live application checks | Explain preference thresholds and denominators during presentation |
| 15% | Useful live application | app.py; src/database.py; tests/test_app.py | Phase 1 map, filters, ranking, charts, comparison and EDA preserved; live mode verified | Use live source status and refresh for demonstrations |
| 15% | Professional visual presentation | app.py; credited cover photo; docs/erd.svg; docs/project_report.pdf | Existing interface preserved; report and ERD added | Capture final presentation screenshots if needed |
| 5% | Database research and selection | docs/project_report.md and PDF, references | PostgreSQL/Supabase rationale and alternatives documented | Tailor discussion to instructor's preferred comparison depth |
| 5% | Written explanation | docs/project_report.md and PDF; schema, SQL and ETL guides | Complete narrative and reproducible commands | Add student name/course details before submission |

## Approval-dependent work

Live schema normalization, CHECK and NOT NULL changes, privileges/RLS changes,
and any database loading require owner approval. Current artifacts contain
recommendations and read-only evidence. Forecasting remains outside this work.
