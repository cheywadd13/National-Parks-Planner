"""Allowlisted, parameterized read-only retrieval for the travel assistant."""

import pandas as pd
from .database import open_readonly, WEATHER, VISITS
from .recommendations import suitability


HISTORY_SQL = """
SELECT w.park_code, w.year, w.month, w.avg_temp_c, w.total_precip_mm,
       w.total_snowfall_cm, v.recreation_visits
FROM public.weather AS w
LEFT JOIN public.visitation AS v
  ON (w.park_code,w.year,w.month)=(v.park_code,v.year,v.month)
WHERE w.year BETWEEN %s AND %s
  AND (%s::text IS NULL OR w.park_code = %s)
ORDER BY w.park_code,w.year,w.month
LIMIT 50001
"""


def historical_rows(dsn, start, end, code=None):
    """Only this fixed SELECT reaches PostgreSQL. Model text is never SQL."""
    import re
    if type(start) is not int or type(end) is not int or not 1900 <= start <= end <= 2100:
        raise ValueError("Invalid historical year range")
    if code is not None and not re.fullmatch(r"[A-Z0-9]{4}", code):
        raise ValueError("Invalid park code")
    with open_readonly(dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = 15000")
            cursor.execute(HISTORY_SQL, (start, end, code, code))
            rows = cursor.fetchall()
    if len(rows) > 50000:
        raise ValueError("Result exceeds the bounded retrieval size")
    return pd.DataFrame(rows, columns=["park_code", "year", "month", *WEATHER, VISITS])


def evidence_rows(history, parks, plan, preferences):
    """Deterministic statistics/ranking: only complete paired years are scored."""
    intent = plan["intent"]
    profiles = suitability(history, tuple(preferences["temperature"]),
                           preferences["weather"], preferences["crowds"], preferences["minimum_years"])
    rows = profiles.loc[profiles.eligible].copy()
    codes = plan["park_codes"]
    if codes:
        rows = rows.loc[rows.park_code.isin(codes)]
    if plan["months"]:
        rows = rows.loc[rows.month.isin(plan["months"])]
    if intent == "mild_weather":
        rows = rows.loc[rows.avg_temp_c.between(*preferences["temperature"])]
        order, ascending = ["weather_score", "park_code", "month"], [False, True, True]
    elif intent == "quiet_parks":
        # Absolute median visits across parks; within-park percentiles stay visible separately.
        order, ascending = [VISITS, "park_code", "month"], [True, True, True]
    elif intent == "compare_months":
        order, ascending = ["park_code", "month"], [True, True]
    else:
        order, ascending = ["score", "park_code", "month"], [False, True, True]
    names = parks.set_index("park_code").park_name.to_dict()
    rows = rows.sort_values(order, ascending=ascending).head(6 if intent == "compare_months" else 3)
    result = []
    for _, row in rows.iterrows():
        result.append({"park_code": row.park_code, "park_name": names[row.park_code],
                       "month": int(row.month), "years": int(row.years),
                       "rank": int(row["rank"]),
                       "eligible_months": int(profiles.loc[profiles.park_code.eq(row.park_code), "eligible"].sum()),
                       **{field: round(float(row[field]), 2) for field in
                          [*WEATHER, VISITS, "crowd_percentile", "weather_score", "crowd_score", "score"]}})
    return result
