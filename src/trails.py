"""Reviewed trail records and historical planning context."""

import json
import math
import re
from pathlib import Path

from .nps_api import official_url

DATA = Path(__file__).resolve().parents[1] / "data"


def load_trails():
    records = json.loads((DATA / "trails.json").read_text(encoding="utf-8"))["trails"]
    seen = set()
    for record in records:
        if not re.fullmatch(r"[A-Z0-9]{4}", record.get("park_code", "")):
            raise ValueError("Invalid trail park code")
        if record["trail_id"] in seen or not official_url(record["source_url"]):
            raise ValueError("Invalid or duplicate trail identity/source")
        seen.add(record["trail_id"])
        for field in ["distance_miles", "elevation_ft"]:
            value = record.get(field)
            if value is not None and (not math.isfinite(float(value)) or float(value) < 0):
                raise ValueError(f"Invalid {field}")
    return records


def difficulty_matches(published, requested):
    """Match a source label or an explicitly published range, never infer grades."""
    want = " ".join(str(requested or "Any").casefold().split())
    label = " ".join(str(published or "Not reported").casefold().split())
    return want == "any" or label == want or want in re.split(r"\s+(?:to|or)\s+|\s*[/–-]\s*", label)


def filter_trails(records, park_code, difficulty="Any", maximum_distance=20, include_unknown=True):
    park_code = str(park_code).strip().upper()
    filtered = []
    for row in records:
        if row["park_code"] != park_code:
            continue
        rating = row.get("difficulty") or "Not reported"
        if not difficulty_matches(rating, difficulty):
            continue
        distance = row.get("distance_miles")
        if distance is None:
            if not include_unknown:
                continue
        elif distance > maximum_distance:
            continue
        filtered.append(row)
    return filtered


def search_trails(records, park_codes, difficulty="Any"):
    """Distinguish missing coverage from excluded records for each requested park."""
    coverage, matches = [], []
    for code in park_codes:
        code = code.strip().upper()
        available = [r for r in records if r["park_code"] == code]
        selected = filter_trails(records, code, difficulty, maximum_distance=1000)
        matches.extend(selected)
        coverage.append({"park_code": code, "catalog_count": len(available),
                         "matched_count": len(selected),
                         "unrated_count": sum(not r.get("difficulty") for r in available),
                         "available_difficulties": sorted({r.get("difficulty") or "Not reported" for r in available}),
                         "status": "no_data" if not available else "no_matches" if not selected else "matched",
                         "alternatives": [{k: r.get(k) for k in ["name", "difficulty", "source_url"]} for r in available[:3]]})
    return {"kind": "hikes", "rows": matches[:3], "coverage": coverage,
            "filters": {"park_codes": park_codes, "difficulty": difficulty},
            "source": "Reviewed local NPS trail catalog (data/trails.json), not a Supabase trail table",
            "message": "Showing up to three matching reviewed trails. Coverage is incomplete. Published difficulty ranges may include the requested grade; unknown ratings are excluded from a specific-grade search. Current permits and access need official confirmation."}


def crowd_category(percentile):
    if percentile is None or not math.isfinite(float(percentile)):
        return "Insufficient data"
    if percentile <= 33:
        return "Quieter season"
    if percentile <= 67:
        return "Typical season"
    return "Busier season"


def month_context(row, comfortable):
    def finite(field):
        value = row.get(field)
        return value is not None and math.isfinite(float(value))
    messages = []
    if finite("avg_temp_c"):
        temp = float(row["avg_temp_c"])
        if comfortable[0] <= temp <= comfortable[1]:
            messages.append("The historical median temperature falls inside your preferred range.")
        else:
            direction = "cooler" if temp < comfortable[0] else "warmer"
            messages.append(f"The historical median temperature is {direction} than your preferred range.")
    if finite("total_precip_mm"):
        messages.append(f'Historical median monthly precipitation is {row["total_precip_mm"]:.1f} mm.')
    if finite("total_snowfall_cm"):
        snow = float(row["total_snowfall_cm"])
        messages.append(f"Historical median monthly snowfall is {snow:.1f} cm.")
    return messages
