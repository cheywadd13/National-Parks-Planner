"""User-facing documentation shared across analytical views."""

SEKI = ("SEKI combines NPS monthly recreation visits reported separately for Sequoia (SEQU) "
        "and Kings Canyon (KICA). Weather represents one geographic point for the combined record.")

SCORING = """
Scores range from 0 to 100 and form a configurable suitability index.
Each calendar month uses medians over years with temperature, precipitation,
snowfall, and visitation all present. Months below the minimum paired-year
threshold remain unscored.

- Temperature receives 100 inside your comfortable range. Outside that range,
  it declines linearly to zero at a 25 °C departure from the nearest boundary.
- Precipitation declines from 100 at 0 mm to zero at 200 mm. Snowfall declines
  from 100 at 0 cm to zero at 60 cm.
- Weather weights those three components at 60%, 25%, and 15%.
- Crowd percentile ranks median visits across all eligible calendar months
  within the same park, before discovery filters. Ties use average ranks.
  A lone eligible month receives a neutral percentile of 50.
- Crowd score is 100 minus crowd percentile. Your weather and crowd weights
  are divided by their sum, then applied to these component scores.
- A preferred travel month limits candidate months. Activity scoring requires
  verified activity records, which the current database does not contain.

The dry, low-snow preference and thresholds are explicit planning choices.
Cross-park rankings compare preferences and each park's seasonal crowd position.
Recreation visit totals remain visible for interpreting the scale of visitation.
The index has no calibrated probability interpretation. Sparse local CSV exports
can leave some park records without eligible months.
"""

METHOD = """
#### Sources and transformations

Park names, codes and coordinates come from the project's NPS park inventory.
Monthly recreation visits come from the [NPS Visitor Use Statistics portal](https://irma.nps.gov/Stats/).
The Colab preparation script reshapes the monthly NPS report and combines the two
SEKI component codes. Weather comes from the
[Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api).
The project averages daily mean temperature and sums daily precipitation and snowfall
to monthly totals at the stored park coordinates. The source project targets 2005–2025.

The app queries the three PostgreSQL tables in a single read-only snapshot. It
joins monthly records by park code, year, and month. Exact duplicate rows are
collapsed and conflicting keys trigger a data error. Missing, non-finite, and
negative precipitation, snow, or visit values are excluded from the applicable
calculations. Valid extremes and recorded zeros are retained. Rows without a
matching park are counted and excluded. Profiles average each variable across
its available years, and recommendation medians use complete monthly observations.

#### Interpretation

Rows in the park inventory are reporting records. Recreation visits count
entries under NPS reporting rules and serve as a proxy for crowds. Changes in
counting procedures, closures, access, or reporting coverage can affect results.
Weather is gridded historical data at one location per record. Elevation and
conditions can vary widely within a park, and monthly summaries hide daily
spikes. The rankings describe selected historical years and preferences.
Season-adjusted Spearman correlations center each variable by its calendar-month
mean using paired observations. Calendar months need at least two paired years
for this calculation. Associations can reflect weather, access, long-term
trends, holidays, and other factors.
"""
