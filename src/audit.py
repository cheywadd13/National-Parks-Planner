"""Read-only rubric verification. Produces catalog and analytical evidence."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .analytics import METRICS, monthly_profile
from .database import COLUMNS, KEY, open_readonly, read_tables, prepare
from .etl.pipeline import stage, plan_changes
from .etl.transform import visitation_from_nps
from .recommendations import suitability

ROOT = Path(__file__).resolve().parents[1]
CATALOG = {
    "columns": """SELECT table_name,column_name,data_type,is_nullable,column_default
      FROM information_schema.columns WHERE table_schema='public'
      AND table_name IN ('parks','visitation','weather') ORDER BY table_name,ordinal_position""",
    "constraints": """SELECT c.relname AS table_name,k.conname,k.contype,k.convalidated,
      pg_get_constraintdef(k.oid) AS definition FROM pg_constraint k
      JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='public' AND c.relname IN ('parks','visitation','weather')
      ORDER BY c.relname,k.conname""",
    "indexes": """SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public'
      AND tablename IN ('parks','visitation','weather') ORDER BY tablename,indexname""",
    "access": """SELECT c.relname AS table_name,c.relrowsecurity AS rls_enabled,
      has_table_privilege(c.oid,'SELECT') AS can_select,
      has_table_privilege(c.oid,'INSERT') AS can_insert,
      has_table_privilege(c.oid,'UPDATE') AS can_update,
      has_table_privilege(c.oid,'DELETE') AS can_delete FROM pg_class c
      JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'
      AND c.relname IN ('parks','visitation','weather') ORDER BY c.relname""",
    "session": """SELECT current_setting('server_version') AS postgres_version,
      current_setting('transaction_read_only') AS transaction_read_only,
      current_setting('transaction_isolation') AS isolation,transaction_timestamp() AS snapshot_utc""",
}


def query_frame(cursor, query, parameters=None):
    cursor.execute(query, parameters)
    return pd.DataFrame(cursor.fetchall(), columns=[column.name for column in cursor.description])


def compare_numeric(left, right, keys, fields, tolerance=1e-8):
    merged = left.merge(right, on=keys, how="outer", suffixes=("_left", "_right"), indicator=True,
                        validate="one_to_one")
    matches = merged["_merge"].eq("both")
    for field in fields:
        a = pd.to_numeric(merged[f"{field}_left"], errors="coerce").astype(float)
        b = pd.to_numeric(merged[f"{field}_right"], errors="coerce").astype(float)
        matches &= np.isclose(a, b, rtol=0, atol=tolerance, equal_nan=True)
    return {"rows_compared": len(merged), "mismatching_rows": int((~matches).sum())}


def run_audit(source_directory, output_directory, dsn):
    source, output = Path(source_directory), Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    raw_visits_path = source / "Query Builder for Public Use Statistics (1979 - Last Calendar Year).csv"
    source_visits = visitation_from_nps(pd.read_csv(raw_visits_path, dtype=str))
    components = source_visits.loc[source_visits.park_code.isin(["SEQU", "KICA"])]
    parameters = dict(start_year=2005, end_year=2025, minimum_years=3, park_code="ACAD",
                      top_n=3, temp_low=15, temp_high=24, weather_weight=65, crowd_weight=35,
                      components_json=components.to_json(orient="records"))
    catalog, results, plans = {}, {}, {}
    with open_readonly(dsn) as connection:
        frames = read_tables(connection)
        with connection.cursor() as cursor:
            for name, query in CATALOG.items():
                catalog[name] = query_frame(cursor, query).to_dict("records")
            for path in sorted((ROOT / "sql").glob("[0-9][0-9]_*.sql")):
                query = path.read_text(encoding="utf-8")
                result = query_frame(cursor, query, parameters)
                result.to_csv(output / f"{path.stem}.csv", index=False)
                results[path.stem] = result
            history_sql = (ROOT / "sql/01_park_history.sql").read_text(encoding="utf-8")
            cursor.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + history_sql, parameters)
            plans["park_history"] = cursor.fetchone()[0]
    (output / "catalog.json").write_text(json.dumps(catalog, indent=2, default=str), encoding="utf-8")
    (output / "query_plans.json").write_text(json.dumps(plans, indent=2, default=str), encoding="utf-8")
    (output / "query_parameters.json").write_text(
        json.dumps({key: value for key, value in parameters.items() if key != "components_json"}, indent=2),
        encoding="utf-8")

    checks = []
    def check(name, passed, detail, warning=False):
        checks.append({"check": name, "status": ("PASS" if passed else "WARN" if warning else "FAIL"),
                       "detail": detail})

    for table, frame in frames.items():
        keys = ["park_code"] if table == "parks" else KEY
        duplicates = int(frame.duplicated(keys).sum())
        missing = frame.isna().sum().to_dict()
        check(f"{table}: unique keys", duplicates == 0, duplicates)
        check(f"{table}: required values", sum(missing.values()) == 0, missing)
        if table != "parks":
            unknown = sorted(set(frame.park_code) - set(frames["parks"].park_code))
            check(f"{table}: foreign keys", not unknown, unknown)
            valid = frame.month.between(1, 12) & frame.year.between(2005, 2025)
            check(f"{table}: date domain", valid.all(), int((~valid).sum()))
        for field in set(COLUMNS[table]) - set(keys) - {"park_name", "state"}:
            values = pd.to_numeric(frame[field], errors="coerce").astype(float)
            valid = np.isfinite(values)
            if field == "latitude":
                valid &= values.between(-90, 90)
            elif field == "longitude":
                valid &= values.between(-180, 180)
            elif field != "avg_temp_c":
                valid &= values.ge(0)
            check(f"{table}: {field} domain", valid.all(), int((~valid).sum()))
    parks, history, invalid, orphan = prepare(frames)
    complete = history.dropna(subset=METRICS)
    check("Expected inventory", len(parks) == 63, len(parks))
    check("Joined visitation cardinality", len(complete) == len(frames["visitation"]),
          {"complete_joined": len(complete), "visitation_rows": len(frames["visitation"]),
           "weather_rows": len(frames["weather"])})
    check("Complete weather grid", len(frames["weather"]) == len(parks)*21*12, len(frames["weather"]))
    gaps = results["06_coverage_gaps"]
    check("Complete visitation grid", gaps.empty, gaps.to_dict("records"), warning=True)
    raw_compare = frames["visitation"].merge(
        source_visits, on=KEY, how="inner", suffixes=("_live", "_source"), validate="one_to_one")
    source_differences = raw_compare.loc[
        raw_compare.recreation_visits_live.ne(raw_compare.recreation_visits_source)]
    source_differences.to_csv(output / "source_visitation_differences.csv", index=False)
    check("Retained NPS direct-code reconciliation", source_differences.empty,
          {"matched_rows": len(raw_compare), "differences": len(source_differences)}, warning=True)
    seki = results["08_seki_reconciliation"]
    check("SEKI equals SEQU + KICA", len(seki)==252 and seki["difference"].eq(0).all(),
          {"months": len(seki), "mismatches": int((~seki["difference"].eq(0)).sum())})
    live_months = set(map(tuple, frames["visitation"][KEY].to_numpy()))
    raw_mapped = source_visits.copy()
    raw_mapped["park_code"] = raw_mapped["park_code"].replace({"SEQU": "SEKI", "KICA": "SEKI"})
    raw_months = set(map(tuple, raw_mapped[KEY].to_numpy()))
    missing_live = [row for row in gaps.to_dict("records") if
                    (row["park_code"], row["year"], row["month"]) in raw_months]
    check("Source-backed visitation gaps", not missing_live, missing_live, warning=True)

    scores = suitability(history)
    sql_scores = results["05_suitability"]
    score_fields = ["years", *METRICS, "crowd_percentile", "weather_score", "score", "rank"]
    score_comparison = compare_numeric(scores, sql_scores, ["park_code", "month"], score_fields)
    check("SQL suitability equals application", score_comparison["mismatching_rows"]==0, score_comparison)
    check("Suitability bounds", scores.score.dropna().between(0, 100).all(),
          {"scored_months": int(scores.score.count()), "min": scores.score.min(), "max": scores.score.max()})
    profiles=[]
    for code, rows in history.groupby("park_code"):
        profile=monthly_profile(rows)
        profile["park_code"]=code
        profiles.append(profile)
    profile = pd.concat(profiles, ignore_index=True)
    weather_compare = compare_numeric(profile, results["04_weather_climatology"],
                                      ["park_code", "month"], METRICS[:-1])
    check("Weather SQL means equal charts", weather_compare["mismatching_rows"]==0, weather_compare)
    visits = frames["visitation"]
    monthly = visits.groupby(["park_code","month"]).agg(
        median_visits=("recreation_visits","median"),years=("year","count")).reset_index()
    monthly = monthly.loc[monthly.years.ge(3)].copy()
    monthly["quiet_rank"] = monthly.groupby("park_code")["median_visits"].rank(method="min")
    monthly = monthly.loc[monthly.quiet_rank.le(3)]
    quiet_compare = compare_numeric(monthly,results["02_least_crowded"],["park_code","month"],
                                    ["median_visits","years","quiet_rank"])
    check("Least crowded SQL ranks independently reconciled",quiet_compare["mismatching_rows"]==0,quiet_compare)
    seasons=results["03_seasonal_visitation"].copy()
    grouped=seasons.groupby(["park_code","year"])
    annual=visits.groupby(["park_code","year"]).agg(annual=("recreation_visits","sum"),n=("month","count"))
    complete_annual=annual.loc[annual.n.eq(12),"annual"]
    season_totals=grouped.season_visits.sum()
    check("Season totals reconcile to complete calendar years",
          season_totals.equals(complete_annual) or
          (len(season_totals)==len(complete_annual) and season_totals.sub(complete_annual).eq(0).all()),
          {"complete_park_years": len(complete_annual), "season_rows": len(seasons)})
    # Explicitly verify chart inputs and discovery predicate.
    from .recommendations import discovery_candidates
    selected=discovery_candidates(scores,10,(15,24),100,50)
    manual=scores.loc[scores.eligible & scores.month.eq(10) & scores.avg_temp_c.between(15,24)
                      & scores.total_precip_mm.le(100) & scores.crowd_percentile.le(50)]
    check("October discovery filter",set(zip(selected.park_code,selected.month))==
          set(zip(manual.park_code,manual.month)),{"matching_parks":len(selected)})

    staging, staged = stage(source/"national_parks_information.csv", raw_visits_path,
                            source/"national_parks_weather_2005_2025_partial.csv",output/"etl_staging")
    repeated,_ = stage(source/"national_parks_information.csv", raw_visits_path,
                       source/"national_parks_weather_2005_2025_partial.csv",output/"etl_staging")
    check("ETL rerun idempotency",staging==repeated,staging.name)
    change_plan={name:plan_changes(frame,frames[name],["park_code"] if name=="parks" else KEY)
                 for name,frame in staged.items()}
    (output/"etl_change_plan.json").write_text(json.dumps(change_plan,indent=2),encoding="utf-8")
    retained_weather=staged["weather"].merge(frames["weather"],on=KEY,validate="one_to_one",
                                             suffixes=("_retained","_live"))
    weather_differences=[]
    for field in METRICS[:-1]:
        difference=retained_weather[f"{field}_retained"]-retained_weather[f"{field}_live"]
        weather_differences.append({"field":field,"overlap_rows":len(difference),
                                    "rows_different_above_1e_8":int(difference.abs().gt(1e-8).sum()),
                                    "mean_absolute_difference":difference.abs().mean(),
                                    "maximum_absolute_difference":difference.abs().max()})
    pd.DataFrame(weather_differences).to_csv(output/"retained_weather_comparison.csv",index=False)
    check("Retained monthly weather matches live",all(
        row["rows_different_above_1e_8"]==0 for row in weather_differences),
        weather_differences,warning=True)
    annual_sql=results["07_annual_change"]
    expected=complete_annual.rename("annual_visits").reset_index().sort_values(["park_code","year"])
    expected["previous_year"]=expected.groupby("park_code").year.shift()
    expected["previous_visits"]=expected.groupby("park_code").annual_visits.shift()
    expected["year_over_year_pct"]=(100*(expected.annual_visits-expected.previous_visits)/
                                    expected.previous_visits.replace(0,np.nan)).where(
                                        expected.year.eq(expected.previous_year+1))
    annual_check=compare_numeric(expected,annual_sql,["park_code","year"],
                                 ["annual_visits","year_over_year_pct"])
    check("Annual change SQL independently reconciled",annual_check["mismatching_rows"]==0,annual_check)
    source_hashes={path.name:sha256(path.read_bytes()).hexdigest() for path in [
        source/"National_Parks_r.R",source/"databasesproject_nationalparks.py",raw_visits_path,
        source/"national_parks_information.csv",source/"national_parks_weather_2005_2025_partial.csv"]}
    coverage=history.groupby("park_code").agg(
        observed_months=("month","count"),visitation_months=("recreation_visits","count"),
        weather_months=("avg_temp_c","count"))
    coverage.to_csv(output/"coverage_by_park.csv")
    weather_verification=output/"weather_validation/verification.json"
    if weather_verification.exists():
        verification=json.loads(weather_verification.read_text(encoding="utf-8"))
        verified=(verification["all_months_matched"] and verification["monthly_rows"]==12 and
                  all(item["months_different_above_1e_8"]==0 for item in verification["differences"].values()))
        check("Representative daily weather reaggregation",verified,verification)
    summary={"generated_utc":datetime.now(timezone.utc).isoformat(),"snapshot":catalog["session"][0],
             "source":"live Supabase PostgreSQL",
             "sql_hashes":{path.name:sha256(path.read_bytes()).hexdigest() for path in sorted((ROOT/"sql").glob("*.sql"))},
             "parameters":{k:v for k,v in parameters.items() if k!="components_json"},
             "row_counts":{name:len(frame) for name,frame in frames.items()},
             "joined_complete_rows":len(complete),"checks":checks,"source_hashes":source_hashes,
             "database_writes":0,"schema_changes":0,"etl_change_plan":change_plan,
             "scope_note":"Daily source aggregation requires archived daily data; original raw responses were not retained."}
    (output/"audit_results.json").write_text(json.dumps(summary,indent=2,default=str),encoding="utf-8")
    lines=["# Live data quality report","",f"Snapshot {summary['snapshot']['snapshot_utc']}.",
           "",f"Source {summary['source']}. Transaction read-only is on. Database writes 0. Schema changes 0.",
           "", "| Check | Status | Evidence |","| --- | --- | --- |"]
    for item in checks:
        detail=json.dumps(item["detail"],default=str).replace("|","/")
        lines.append(f"| {item['check']} | {item['status']} | {detail} |")
    lines += ["","## Evidence limits","",
              "A complete joined row count does not imply a complete time grid. See 06_coverage_gaps.csv.",
              "Daily raw responses from the original collection are unavailable. A fresh representative",
              "Open-Meteo response is checked separately. Revised source data can differ from archived inputs.",
              "SEKI component equality confirms arithmetic for the retained NPS export. It does not establish unique visitor counts.",
              "Partial monthly weather exports remain partial and are never loaded by this audit.",
              "ETL staging is immutable and locally idempotent. Live changes are reported for approval."]
    (output/"data_quality_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-directory",required=True)
    parser.add_argument("--output",default=str(ROOT/"reports"))
    args=parser.parse_args()
    result=run_audit(args.source_directory,args.output,os.environ["DATABASE_URL"])
    counts=pd.Series([item["status"] for item in result["checks"]]).value_counts().to_dict()
    print(json.dumps({"row_counts":result["row_counts"],"checks":counts},indent=2))
    if counts.get("FAIL"):
        raise SystemExit(1)


if __name__=="__main__":
    main()
