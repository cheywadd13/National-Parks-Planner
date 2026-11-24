"""Reaggregate one fresh archived daily series and compare with stored months."""

import argparse
import json
import os
from pathlib import Path

from ..database import read_postgres
from .extract import collect_weather
from .transform import weather_from_daily


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--park-code", default="ACAD")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--output", default="reports/weather_validation")
    args = parser.parse_args()
    output = Path(args.output)
    frames = read_postgres(os.environ["DATABASE_URL"])
    park = frames["parks"].loc[frames["parks"].park_code.eq(args.park_code.upper())]
    if len(park) != 1:
        raise ValueError("Choose an existing park code")
    park = park.iloc[0]
    payload, raw = collect_weather(park, f"{args.year}-01-01", f"{args.year}-12-31",
                                   output/"raw")
    daily = payload["daily"]
    if min(daily["time"]) != f"{args.year}-01-01" or max(daily["time"]) != f"{args.year}-12-31":
        raise ValueError("Weather response does not cover the requested year")
    monthly = weather_from_daily(payload, park.park_code)
    current = frames["weather"].loc[frames["weather"].park_code.eq(park.park_code)
                                   & frames["weather"].year.eq(args.year)]
    compared = monthly.merge(current, on=["park_code","year","month"], how="outer",
                             suffixes=("_fresh","_stored"), validate="one_to_one", indicator=True)
    differences = {}
    for field in ["avg_temp_c","total_precip_mm","total_snowfall_cm"]:
        difference = compared[f"{field}_fresh"]-compared[f"{field}_stored"]
        compared[f"{field}_difference"] = difference
        differences[field] = {"maximum_absolute_difference":float(difference.abs().max()),
                              "months_different_above_1e_8":int(difference.abs().gt(1e-8).sum())}
    compared.to_csv(output/"monthly_comparison.csv",index=False)
    result = {"park_code":park.park_code,"year":args.year,"daily_rows":len(daily["time"]),
              "monthly_rows":len(monthly),"raw_snapshot":raw.name,
              "all_months_matched":bool(compared["_merge"].eq("both").all()),
              "differences":differences,"database_writes":0,
              "interpretation":"Fresh reanalysis may be revised since original ingestion. Original daily payloads are unavailable."}
    (output/"verification.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
