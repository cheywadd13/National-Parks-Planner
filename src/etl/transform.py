"""Strict source-to-table transformations with explicit monthly grain."""

from calendar import monthrange
import numpy as np
import pandas as pd

from ..database import COLUMNS, KEY


def unique_rows(frame, keys):
    frame = frame.drop_duplicates().copy()
    if frame[keys].isna().any().any() or frame.duplicated(keys).any():
        raise ValueError(f"Missing or conflicting keys in {keys}")
    return frame.sort_values(keys).reset_index(drop=True)


def numeric(series, field):
    values = pd.to_numeric(series.astype("string").str.replace(",", "", regex=False).str.strip(),
                           errors="coerce")
    if values.isna().any() or not np.isfinite(values.astype(float)).all():
        raise ValueError(f"Missing or non-finite {field}")
    return values


def monthly_keys(frame, start_year=2005, end_year=2025):
    frame = frame.copy()
    frame["park_code"] = frame["park_code"].astype("string").str.strip().str.upper()
    if frame["park_code"].isna().any() or not frame["park_code"].str.fullmatch(r"[A-Z0-9]{4}").all():
        raise ValueError("Invalid park code")
    for field in ["year", "month"]:
        values = numeric(frame[field], field)
        if values.mod(1).ne(0).any():
            raise ValueError(f"Fractional {field}")
        frame[field] = values.astype(int)
    if not frame["month"].between(1, 12).all():
        raise ValueError("Invalid calendar month")
    return frame.loc[frame["year"].between(start_year, end_year)].copy()


def parks_from_metadata(frame):
    result = frame.rename(columns={"parkCode": "park_code", "fullName": "park_name", "states": "state"})
    result = result[COLUMNS["parks"]].copy()
    for field in ["park_code", "park_name", "state"]:
        result[field] = result[field].astype("string").str.strip()
        if result[field].isna().any() or result[field].eq("").any():
            raise ValueError(f"Missing {field}")
    result["park_code"] = result["park_code"].str.upper()
    if not result["park_code"].str.fullmatch(r"[A-Z0-9]{4}").all():
        raise ValueError("Invalid park code")
    for field, bounds in [("latitude", (-90, 90)), ("longitude", (-180, 180))]:
        result[field] = numeric(result[field], field)
        if not result[field].between(*bounds).all():
            raise ValueError(f"Out-of-range {field}")
    return unique_rows(result, ["park_code"])


def visitation_from_nps(frame, start_year=2005, end_year=2025, component_code=None):
    # Accept the retained long query-builder export and the Colab monthly-wide reports.
    result = frame.rename(columns={"UnitCode": "park_code", "Year": "year", "Month": "month",
                                   "RecreationVisits": "recreation_visits"}).copy()
    if "month" not in result:
        months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                  "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
        if not component_code:
            raise ValueError("A component code is required for a single-park wide NPS report")
        result = result.melt(id_vars=["year"], value_vars=months,
                             var_name="month_name", value_name="recreation_visits")
        result["park_code"] = component_code
        result["month"] = result["month_name"].map({name: i+1 for i, name in enumerate(months)})
    result = monthly_keys(result, start_year, end_year)
    result["recreation_visits"] = numeric(result["recreation_visits"], "recreation_visits")
    if result["recreation_visits"].lt(0).any() or result["recreation_visits"].mod(1).ne(0).any():
        raise ValueError("Visits must be non-negative integer counts")
    result["recreation_visits"] = result["recreation_visits"].astype("int64")
    return unique_rows(result[COLUMNS["visitation"]], KEY)


def combine_seki(visitation):
    components = visitation.loc[visitation["park_code"].isin(["SEQU", "KICA"])]
    if components.empty:
        raise ValueError("SEQU and KICA source components are required")
    wide = components.pivot(index=["year", "month"], columns="park_code", values="recreation_visits")
    if set(wide.columns) != {"SEQU", "KICA"} or wide.isna().any().any():
        raise ValueError("Both SEQU and KICA are required for every component month")
    combined = wide.sum(axis=1).rename("recreation_visits").reset_index()
    combined["park_code"] = "SEKI"
    existing = visitation.loc[visitation["park_code"].eq("SEKI")]
    if not existing.empty:
        matched = combined.merge(existing, on=KEY, how="outer", suffixes=("_expected", "_existing"))
        if not matched["recreation_visits_expected"].eq(matched["recreation_visits_existing"]).all():
            raise ValueError("Existing SEKI source rows conflict with the component sum")
    others = visitation.loc[~visitation["park_code"].isin(["SEQU", "KICA", "SEKI"])]
    return unique_rows(pd.concat([others, combined[COLUMNS["visitation"]]], ignore_index=True), KEY)


def weather_from_monthly(frame, start_year=2005, end_year=2025):
    frame = frame.rename(columns={"UnitCode": "park_code", "Year": "year", "Month": "month",
                                  "Avg_Temp_C": "avg_temp_c", "Total_Precip_mm": "total_precip_mm",
                                  "Total_Snowfall_cm": "total_snowfall_cm"})
    result = monthly_keys(frame, start_year, end_year)
    for field in COLUMNS["weather"][3:]:
        result[field] = numeric(result[field], field).astype(float)
        if field != "avg_temp_c" and result[field].lt(0).any():
            raise ValueError(f"Negative {field}")
    return unique_rows(result[COLUMNS["weather"]], KEY)


def weather_from_daily(payload, park_code):
    expected_units = {"temperature_2m_mean": "°C", "precipitation_sum": "mm", "snowfall_sum": "cm"}
    if any(payload.get("daily_units", {}).get(field) != unit for field, unit in expected_units.items()):
        raise ValueError("Daily weather units do not match Celsius, mm, cm")
    daily = pd.DataFrame(payload["daily"])
    dates = pd.to_datetime(daily["time"], format="%Y-%m-%d", errors="raise")
    if dates.duplicated().any() or dates.isna().any():
        raise ValueError("Duplicate or missing weather dates")
    expected = pd.date_range(dates.min(), dates.max(), freq="D")
    if sorted(dates.tolist()) != expected.tolist():
        raise ValueError("Daily series contains a missing date or entire month")
    daily["year"], daily["month"] = dates.dt.year, dates.dt.month
    for field in expected_units:
        daily[field] = numeric(daily[field], field).astype(float)
        if field != "temperature_2m_mean" and daily[field].lt(0).any():
            raise ValueError(f"Negative {field}")
    groups = daily.groupby(["year", "month"])
    for (year, month), group in groups:
        if len(group) != monthrange(year, month)[1]:
            raise ValueError(f"Incomplete daily coverage for {year}-{month:02}")
    monthly = groups.agg(
        avg_temp_c=("temperature_2m_mean", "mean"),
        total_precip_mm=("precipitation_sum", "sum"),
        total_snowfall_cm=("snowfall_sum", "sum"),
    ).reset_index()
    monthly["park_code"] = park_code
    return weather_from_monthly(monthly, int(dates.dt.year.min()), int(dates.dt.year.max()))
