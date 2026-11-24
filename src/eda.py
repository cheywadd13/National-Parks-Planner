"""Season-aware descriptive diagnostics; flags never remove source records."""

import numpy as np
import pandas as pd
from .analytics import METRICS


def diagnostics(history, minimum_group=8):
    """Flag Tukey 1.5-IQR extremes within park/calendar month (n >= 8).

    A zero-IQR group is not statistically screened. NaN values remain missing.
    Valid extremes are retained, so flags are investigative, not cleaning labels.
    """
    rows = []
    for metric in METRICS:
        values = pd.to_numeric(history[metric], errors="coerce").replace([np.inf, -np.inf], np.nan)
        groups = history.assign(_value=values).groupby(["park_code", "month"])["_value"]
        count = groups.transform("count")
        q1 = groups.transform(lambda x: x.quantile(.25))
        q3 = groups.transform(lambda x: x.quantile(.75))
        iqr = q3 - q1
        screened = values.notna() & count.ge(minimum_group) & iqr.gt(0)
        flagged = screened & ((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr))
        keep = values.loc[~flagged]
        rows.append({"metric": metric, "observed": int(values.count()),
                     "missing": int(values.isna().sum()), "screened": int(screened.sum()),
                     "flagged": int(flagged.sum()), "mean_all": values.mean(),
                     "mean_without_flags": keep.mean(), "median_all": values.median()})
    return pd.DataFrame(rows)


def findings(history):
    """Compute statements for the selected window instead of canned findings."""
    visits = history.groupby("month")["recreation_visits"].mean().dropna()
    if visits.empty:
        return ["There are no observed visitation values in this selection."]
    from calendar import month_name
    peak, quiet = int(visits.idxmax()), int(visits.idxmin())
    return [f"Highest observed calendar-month mean: {month_name[peak]} ({visits.loc[peak]:,.0f} recreation visits).",
            f"Lowest observed calendar-month mean: {month_name[quiet]} ({visits.loc[quiet]:,.0f} recreation visits).",
            "These are park-wide recreation visits, not unique visitors or individual trail traffic."]
