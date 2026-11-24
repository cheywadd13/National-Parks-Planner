"""Seasonal summaries, preference scoring, and association estimates."""

from calendar import month_abbr

import numpy as np
import pandas as pd

from .database import VISITS, WEATHER

METRICS = WEATHER + [VISITS]
MONTHS = pd.Index(range(1, 13), name="month")


def monthly_profile(history, statistic="mean"):
    groups = history.groupby("month")[METRICS]
    profile = groups.agg(statistic).reindex(MONTHS)
    counts = groups.count().reindex(MONTHS, fill_value=0)
    profile = profile.join(counts.add_suffix("_n")).reset_index()
    profile["month_name"] = profile["month"].map(lambda value: month_abbr[value])
    peak = profile[VISITS].max()
    profile["relative_visits"] = profile[VISITS].div(peak).mul(100) if peak > 0 else np.nan
    return profile


def rank_months(history, weather_weight=0.65, ideal_temp=19, minimum_years=3):
    # Every component uses the same observed years within a month.
    complete = history.dropna(subset=METRICS)
    profile = monthly_profile(complete, "median")
    profile["years"] = profile[f"{VISITS}_n"]
    eligible = profile["years"].ge(minimum_years)
    scoring = profile.loc[eligible]
    temp = 100 * (1 - (scoring["avg_temp_c"] - ideal_temp).abs().div(25)).clip(0, 1)
    dry = 100 * (1 - scoring["total_precip_mm"].div(200)).clip(0, 1)
    low_snow = 100 * (1 - scoring["total_snowfall_cm"].div(60)).clip(0, 1)
    profile["weather_score"] = 0.60 * temp + 0.25 * dry + 0.15 * low_snow
    # Average ranks handle ties. A lone month receives a neutral crowd score.
    visits = scoring[VISITS]
    crowd = 100 * (len(visits) - visits.rank()) / (len(visits) - 1) if len(visits) > 1 else visits * 0 + 50
    profile["crowd_score"] = crowd
    profile["score"] = weather_weight * profile["weather_score"] + (1 - weather_weight) * crowd
    profile["rank"] = profile["score"].rank(method="min", ascending=False).astype("Int64")
    return profile.sort_values(["rank", "month"], na_position="last")


def associations(history):
    """Pairwise within-park rank correlations and season-adjusted correlations."""
    rows = []
    for metric in WEATHER:
        pair = history[["month", metric, VISITS]].dropna()
        groups = pair.groupby("month")[[metric, VISITS]]
        repeated = groups.transform("size").ge(2)
        anomalies = (pair[[metric, VISITS]] - groups.transform("mean")).loc[repeated]
        coefficients = []
        for frame in (pair, anomalies):
            values = frame[[metric, VISITS]]
            coefficients.append(values.rank().corr().iloc[0, 1] if len(values) >= 3 else np.nan)
        rows.append({"metric": metric, "paired_months": len(pair), "spearman": coefficients[0],
                     "anomaly_pairs": len(anomalies), "anomaly_spearman": coefficients[1]})
    return pd.DataFrame(rows)
