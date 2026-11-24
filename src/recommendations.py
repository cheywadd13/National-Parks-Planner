"""Transparent historical park-month suitability with explicit evidence counts."""

import numpy as np
import pandas as pd
from .analytics import METRICS, monthly_profile


def normalize_weights(weather, crowds):
    values = np.asarray([weather, crowds], dtype=float)
    if not np.isfinite(values).all() or (values < 0).any() or values.sum() <= 0:
        raise ValueError("Choose non-negative weights with a positive total.")
    return values / values.sum()


def suitability(history, temperature=(15, 24), weather=65, crowds=35, minimum_years=3):
    low, high = temperature
    if not np.isfinite([low, high]).all() or low > high:
        raise ValueError("Temperature bounds must be finite and ordered.")
    if not isinstance(minimum_years, int) or minimum_years < 1:
        raise ValueError("Minimum years must be a positive integer.")
    weights = normalize_weights(weather, crowds)
    profiles = []
    for code, records in history.groupby("park_code", sort=True):
        profile = monthly_profile(records.dropna(subset=METRICS), "median")
        profile["park_code"] = code
        profile["years"] = profile["recreation_visits_n"]
        profile["eligible"] = profile["years"].ge(minimum_years)
        # Reference includes every sufficiently observed month before discovery filtering.
        eligible = profile.loc[profile["eligible"]]
        visits = eligible["recreation_visits"]
        percentile = (visits.rank(method="average") - 1) / (len(visits) - 1) if len(visits) > 1 else visits * 0 + .5
        profile["crowd_percentile"] = percentile * 100
        deviation = (low - eligible["avg_temp_c"]).clip(lower=0) + (eligible["avg_temp_c"] - high).clip(lower=0)
        profile["temperature_score"] = 100 * (1 - deviation / 25).clip(0, 1)
        profile["precipitation_score"] = 100 * (1 - eligible["total_precip_mm"] / 200).clip(0, 1)
        profile["snow_score"] = 100 * (1 - eligible["total_snowfall_cm"] / 60).clip(0, 1)
        profile["weather_score"] = .60 * profile["temperature_score"] + .25 * profile["precipitation_score"] + .15 * profile["snow_score"]
        profile["crowd_score"] = 100 - profile["crowd_percentile"]
        profile["score"] = weights[0] * profile["weather_score"] + weights[1] * profile["crowd_score"]
        profile["rank"] = profile["score"].rank(method="min", ascending=False).astype("Int64")
        profiles.append(profile)
    if not profiles:
        return pd.DataFrame(columns=["park_code", "month", "score", "eligible"])
    return pd.concat(profiles, ignore_index=True)


def discovery_candidates(scores, month, temperature, precipitation, crowd_percentile):
    """Apply discovery constraints after full-year seasonality has been scored."""
    low, high = temperature
    mask = scores["eligible"] & scores["avg_temp_c"].between(low, high)
    mask &= scores["total_precip_mm"].le(precipitation)
    mask &= scores["crowd_percentile"].le(crowd_percentile)
    if month:
        mask &= scores["month"].eq(month)
    return scores.loc[mask].sort_values(["score", "park_code", "month"], ascending=[False, True, True])


def convert_temperature(value, unit="°C", to_celsius=False):
    if unit == "°F":
        return (value - 32) / 1.8 if to_celsius else value * 1.8 + 32
    return value
