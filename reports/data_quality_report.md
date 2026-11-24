# Live data quality report

Snapshot 2026-11-19 14:58:40.038322+00:00.

Source live Supabase PostgreSQL. Transaction read-only is on. Database writes 0. Schema changes 0.

| Check | Status | Evidence |
| --- | --- | --- |
| parks: unique keys | PASS | 0 |
| parks: required values | PASS | {"park_code": 0, "park_name": 0, "state": 0, "latitude": 0, "longitude": 0} |
| parks: longitude domain | PASS | 0 |
| parks: latitude domain | PASS | 0 |
| visitation: unique keys | PASS | 0 |
| visitation: required values | PASS | {"park_code": 0, "year": 0, "month": 0, "recreation_visits": 0} |
| visitation: foreign keys | PASS | [] |
| visitation: date domain | PASS | 0 |
| visitation: recreation_visits domain | PASS | 0 |
| weather: unique keys | PASS | 0 |
| weather: required values | PASS | {"park_code": 0, "year": 0, "month": 0, "avg_temp_c": 0, "total_precip_mm": 0, "total_snowfall_cm": 0} |
| weather: foreign keys | PASS | [] |
| weather: date domain | PASS | 0 |
| weather: total_snowfall_cm domain | PASS | 0 |
| weather: avg_temp_c domain | PASS | 0 |
| weather: total_precip_mm domain | PASS | 0 |
| Expected inventory | PASS | 63 |
| Joined visitation cardinality | PASS | {"complete_joined": 15863, "visitation_rows": 15863, "weather_rows": 15876} |
| Complete weather grid | PASS | 15876 |
| Complete visitation grid | WARN | [{"park_code": "CHIS", "year": 2005, "month": 12, "missing_visitation": true, "missing_weather": false}, {"park_code": "NPSA", "year": 2005, "month": 1, "missing_visitation": true, "missing_weather": false}, {"park_code": "NPSA", "year": 2005, "month": 2, "missing_visitation": true, "missing_weather": false}, {"park_code": "NPSA", "year": 2005, "month": 3, "missing_visitation": true, "missing_weather": false}, {"park_code": "NPSA", "year": 2005, "month": 4, "missing_visitation": true, "missing_weather": false}, {"park_code": "NPSA", "year": 2005, "month": 5, "missing_visitation": true, "missing_weather": false}, {"park_code": "NPSA", "year": 2005, "month": 6, "missing_visitation": true, "missing_weather": false}, {"park_code": "NPSA", "year": 2005, "month": 7, "missing_visitation": true, "missing_weather": false}, {"park_code": "NPSA", "year": 2005, "month": 8, "missing_visitation": true, "missing_weather": false}, {"park_code": "NPSA", "year": 2005, "month": 9, "missing_visitation": true, "missing_weather": false}, {"park_code": "NPSA", "year": 2005, "month": 10, "missing_visitation": true, "missing_weather": false}, {"park_code": "NPSA", "year": 2005, "month": 11, "missing_visitation": true, "missing_weather": false}, {"park_code": "NPSA", "year": 2005, "month": 12, "missing_visitation": true, "missing_weather": false}] |
| Retained NPS direct-code reconciliation | PASS | {"matched_rows": 15611, "differences": 0} |
| SEKI equals SEQU + KICA | PASS | {"months": 252, "mismatches": 0} |
| Source-backed visitation gaps | PASS | [] |
| SQL suitability equals application | PASS | {"rows_compared": 756, "mismatching_rows": 0} |
| Suitability bounds | PASS | {"scored_months": 756, "min": 19.252480519480518, "max": 96.79875000000001} |
| Weather SQL means equal charts | PASS | {"rows_compared": 756, "mismatching_rows": 0} |
| Least crowded SQL ranks independently reconciled | PASS | {"rows_compared": 190, "mismatching_rows": 0} |
| Season totals reconcile to complete calendar years | PASS | {"complete_park_years": 1321, "season_rows": 5284} |
| October discovery filter | PASS | {"matching_parks": 7} |
| ETL rerun idempotency | PASS | "270575187f4c2bebb45691f5a2569cc026cff611d09d5cf5fc4551d659c681fb" |
| Retained monthly weather matches live | WARN | [{"field": "avg_temp_c", "overlap_rows": 4536, "rows_different_above_1e_8": 3085, "mean_absolute_difference": 0.007146932747617516, "maximum_absolute_difference": 0.041935483870967794}, {"field": "total_precip_mm", "overlap_rows": 4536, "rows_different_above_1e_8": 464, "mean_absolute_difference": 0.07052469135802482, "maximum_absolute_difference": 13.400000000000006}, {"field": "total_snowfall_cm", "overlap_rows": 4536, "rows_different_above_1e_8": 206, "mean_absolute_difference": 0.01387345679012348, "maximum_absolute_difference": 2.380000000000024}] |
| Annual change SQL independently reconciled | PASS | {"rows_compared": 1321, "mismatching_rows": 0} |
| Representative daily weather reaggregation | PASS | {"park_code": "ACAD", "year": 2025, "daily_rows": 365, "monthly_rows": 12, "raw_snapshot": "639127d3b0eb10720edb349a546c7af68bb8ac3cf1379f72344ea89182e6d336.json", "all_months_matched": true, "differences": {"avg_temp_c": {"maximum_absolute_difference": 5.3290705182007514e-14, "months_different_above_1e_8": 0}, "total_precip_mm": {"maximum_absolute_difference": 0.0, "months_different_above_1e_8": 0}, "total_snowfall_cm": {"maximum_absolute_difference": 0.0, "months_different_above_1e_8": 0}}, "database_writes": 0, "interpretation": "Fresh reanalysis may be revised since original ingestion. Original daily payloads are unavailable."} |

## Evidence limits

A complete joined row count does not imply a complete time grid. See 06_coverage_gaps.csv.
Daily raw responses from the original collection are unavailable. A fresh representative
Open-Meteo response is checked separately. Revised source data can differ from archived inputs.
SEKI component equality confirms arithmetic for the retained NPS export. It does not establish unique visitor counts.
Partial monthly weather exports remain partial and are never loaded by this audit.
ETL staging is immutable and locally idempotent. Live changes are reported for approval.
