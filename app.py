"""Streamlit entry point for National Parks Explorer."""

import os
import re
import logging
from html import escape
from calendar import month_name

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from src.park_profiles import render_park_guide, profile_catalog, activity_names
from src.assistant_ui import render_assistant
from src.eda import diagnostics, findings
from src.recommendations import suitability, normalize_weights, discovery_candidates, convert_temperature
from src.analytics import METRICS, associations, monthly_profile
from src.database import VISITS, read_csv_directory, read_postgres, prepare
from src.methodology import METHOD, SCORING, SEKI
from src.visualizations import LABELS, VIEWS, monthly_chart, park_map, rank_chart, style

st.set_page_config(page_title="National Parks Explorer", page_icon="🌲", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1320px; padding-top: 3.5rem;}
.park-hero {background: linear-gradient(110deg,#102d22,#2b644c);
color: #f9f6eb; padding: clamp(1.2rem,3vw,2rem); border-radius: 1.5rem;
margin: 0 0 1.1rem; border-bottom: 5px solid #9bbb91;}
.park-hero h1 {color: #fff9ea; font: 700 clamp(2rem,5vw,3.6rem) Georgia,serif;
line-height:1.08; margin:0; padding:0;}
.match-card {background:#fffdf7; border:1px solid #d9e3d7; border-radius:18px;
padding:1.1rem 1.25rem; height:100%; border-top:4px solid #769b74;}
.match-card h3 {font-family:Georgia,serif; font-size:1.3rem; margin:.2rem 0 .8rem;}
.match-card .score {font-size:2rem; font-weight:700; color:#174e3a;}
.match-card p {color:#4d6256; margin:.4rem 0; font-size:.95rem;}
[data-testid="stPlotlyChart"] {background:#fffdf7; border:1px solid #e1e7dd;
border-radius:16px; padding:.4rem;}
[data-baseweb="tab-list"] {gap:1rem;}
@media (max-width:640px) {.block-container {padding-left:1rem; padding-right:1rem;}
.park-hero {padding:1.8rem 1.4rem;} .match-card {margin-bottom:.6rem;}}
.destination-photo {width:100%;height:360px;object-fit:cover;border-radius:20px;}
@media(max-width:640px){.destination-photo{height:230px;}}
.park-hero p {margin:.65rem 0 0; font-size:1.15rem; color:#e1eddb;}
[data-testid="stMetric"] {background:#eaf0e6; border:1px solid #d5e0d2;
border-radius:1rem; padding:.75rem 1rem;}
</style>
<div class="park-hero"><h1>National Parks Explorer</h1><p>Park guides, verified hikes, and the seasons that suit you.</p></div>
""", unsafe_allow_html=True)


def setting(name):
    if os.getenv(name):
        return os.environ[name]
    try:
        return st.secrets.get(name)
    except StreamlitSecretNotFoundError:
        return None


@st.cache_data(ttl=600, show_spinner="Loading park records…")
def load_data(dsn, directory):
    return prepare(read_csv_directory(directory) if directory else read_postgres(dsn))


directory = os.getenv("PARKS_CSV_DIR")
dsn = None if directory else setting("DATABASE_URL")
if not (dsn or directory):
    st.info("Set DATABASE_URL or configure .streamlit/secrets.toml to connect to Supabase.")
    st.stop()
try:
    parks, history, invalid, orphans = load_data(dsn, directory)
except ValueError as error:
    logging.getLogger(__name__).warning("Source validation failed (%s)", type(error).__name__)
    st.error(f"Data validation failed ({type(error).__name__}). Check source columns and key uniqueness.")
    st.stop()
except Exception as error:
    logging.getLogger(__name__).warning("Data load failed (%s)", type(error).__name__)
    st.error(f"Could not load the data ({type(error).__name__}). Check the connection or CSV directory.")
    st.stop()
if parks.empty or history.empty:
    st.info("No park history is available in this source.")
    st.stop()

if directory:
    st.info("Local CSV mode. Coverage reflects the exports in the configured folder.")
else:
    st.sidebar.caption("Source · live Supabase PostgreSQL · read-only snapshot · cached up to 10 minutes")
    if st.sidebar.button("Refresh live data"):
        load_data.clear()
        st.rerun()


names = parks.set_index("park_code")["park_name"].to_dict()
states = sorted({state.strip() for cell in parks["state"] for state in re.split(r"[,;/]", cell)})
st.sidebar.header("Plan your visit")
unit = st.sidebar.radio("Temperature units", ["°C", "°F"], horizontal=True)
temp_min, temp_max = (-25, 45) if unit == "°C" else (-13, 113)
preferred = st.sidebar.slider("Comfortable temperature range", temp_min, temp_max,
                              (15, 24) if unit == "°C" else (59, 75), key=f"comfort_{unit}")
comfort_c = tuple(convert_temperature(value, unit, True) for value in preferred)
with st.sidebar.expander("Suitability preferences", expanded=True):
    weather_weight = st.slider("Weather importance", 0, 100, 65)
    crowd_weight = st.slider("Avoiding crowds importance", 0, 100, 35)
    minimum_years = st.number_input("Minimum paired years", 1, 21, 3)
if weather_weight + crowd_weight == 0:
    st.warning("Give at least one preference a positive weight.")
    st.stop()
normalized = normalize_weights(weather_weight, crowd_weight)
st.sidebar.caption(f"Normalized weights · weather {normalized[0]:.0%} · crowds {normalized[1]:.0%}")
st.sidebar.caption("Park activities come from official NPS pages. Historical suitability uses weather and crowd preferences.")
if invalid or orphans:
    st.sidebar.caption(f"Ignored {invalid:,} invalid values and {orphans:,} unmatched monthly rows.")
first, last = int(history["year"].min()), int(history["year"].max())
if first == last:
    st.sidebar.caption(f"Historical year {first}")
    years = (first, last)
else:
    years = st.sidebar.slider("Historical years", first, last, (first, last))
window = history.loc[history["year"].between(*years)]
@st.cache_data(show_spinner=False, max_entries=16)
def calculate_scores(data, comfort, weather, crowds, minimum):
    return suitability(data, comfort, weather, crowds, minimum)

scores = calculate_scores(window, comfort_c, weather_weight, crowd_weight, int(minimum_years))
st.caption("Historical planning · " + str(years[0]) + "–" + str(years[1]) + " · " +
           str(len(parks)) + " park records")

page = st.radio("View", ["Park guide", "Explore", "Visit rankings", "Compare", "Data & methods", "Travel assistant"],
                horizontal=True, label_visibility="collapsed", key="page")


def label(code):
    return f"{names[code]} ({code})"


def seki_note(codes):
    if "SEKI" in codes:
        st.caption(SEKI)


def display_profile(profile):
    profile = profile.copy()
    profile["avg_temp_c"] = convert_temperature(profile["avg_temp_c"], unit)
    return profile


def draw_profile(profile, fields, compare=False):
    for chart_group in (fields[:2], fields[2:]):
        if chart_group:
            columns = st.columns(len(chart_group))
            for column, metric in zip(columns, chart_group):
                column.plotly_chart(monthly_chart(display_profile(profile), metric, compare, unit),
                                    width="stretch", key=f"season_{metric}")


def park_filter():
    filters = st.columns([2, 1])
    phrase = filters[0].text_input("Search by park name or code").strip()
    state = filters[1].selectbox("State or territory", [None] + states,
                                 format_func=lambda value: value or "All states and territories")
    catalog = profile_catalog()
    all_activities = sorted({name for profile in catalog.values() for name in activity_names(profile)})
    selected_activities = st.multiselect("Activities you want to do", all_activities,
                                        key="activity_choices",
                                        help="Matches use confirmed official listings; missing listings do not establish that an activity is unavailable.")
    activity_mode = st.radio("Match selected activities", ["Any selected activity", "All selected activities"],
                             horizontal=True) if selected_activities else "Any selected activity"
    matching = parks
    st.caption("Activity listings are incomplete for some parks. Unlisted activities remain unconfirmed.")
    if phrase:
        matches = parks["park_name"].str.contains(phrase, case=False, regex=False)
        matches |= parks["park_code"].str.contains(phrase, case=False, regex=False)
        matching = matching.loc[matches.reindex(matching.index)]
    if state:
        matching = matching.loc[matching["state"].map(
            lambda value: state in [part.strip() for part in re.split(r"[,;/]", value)]
        )]
    before_activities = matching
    if selected_activities:
        wanted = set(selected_activities)
        matching = matching.loc[matching["park_code"].map(
            lambda code: wanted.issubset(activity_names(catalog.get(code, {})))
            if activity_mode == "All selected activities"
            else bool(wanted & activity_names(catalog.get(code, {}))))]
        if matching.empty and not before_activities.empty:
            st.info("Your name and state filters match parks, but the saved official activity listings do not confirm this activity selection. Clear activities or choose Any selected activity.")
        if len(before_activities) == 1:
            confirmed = activity_names(catalog.get(before_activities.iloc[0]["park_code"], {}))
            unconfirmed = sorted(wanted - confirmed)
            if unconfirmed:
                st.caption("Not confirmed in this park's saved listings: " + ", ".join(unconfirmed)
                           + ". This does not mean these activities are unavailable; check the official park website.")
        st.button("Clear activity filters", on_click=lambda: st.session_state.update(activity_choices=[]))
    with st.expander("Seasonal discovery filters"):
        travel_month = st.selectbox("Preferred travel month", range(13),
                                    format_func=lambda value: month_name[value] if value else "Any month")
        climate_filter = st.checkbox("Apply historical climate and crowd limits")
        climate = st.columns(3)
        temperature_limits = climate[0].slider("Historical temperature range", temp_min, temp_max,
                                               (temp_min, temp_max), key=f"filter_temp_{unit}")
        precipitation = climate[1].slider("Maximum monthly precipitation (mm)", 0, 1500, 1500)
        crowd_limit = climate[2].slider("Maximum crowd percentile", 0, 100, 100)
        st.caption("Crowd percentiles compare months within each park. 0 is its quietest season, 100 its busiest.")
    if climate_filter or travel_month:
        bounds = tuple(convert_temperature(value, unit, True) for value in temperature_limits) if climate_filter else (-float("inf"), float("inf"))
        candidates = discovery_candidates(scores, travel_month, bounds,
                                           precipitation if climate_filter else float("inf"),
                                           crowd_limit if climate_filter else 100)
        matching = matching.loc[matching["park_code"].isin(candidates["park_code"])]
    return matching


matching = park_filter() if page in ("Park guide", "Explore") else parks
if matching.empty:
    st.info("No park matches these filters.")
    st.stop()

if page in ("Park guide", "Explore", "Visit rankings"):
    available = matching["park_code"].tolist()
    saved = st.session_state.get("selected_park")
    if saved not in available:
        saved = "ACAD" if "ACAD" in available else available[0]
        st.session_state["selected_park"] = saved
    if st.session_state.get("park") != saved:
        st.session_state["park"] = saved
    if page == "Explore":
        visible = matching.dropna(subset=["latitude", "longitude"])
        st.caption(f"{len(visible):,} of {len(parks):,} park records mapped. Select a marker to open its profile.")
        region_by_state = {"AK": "Alaska", "HI": "Hawaiʻi", "AS": "American Samoa", "VI": "U.S. Virgin Islands"}
        matching_states = matching["state"].unique()
        suggested_region = region_by_state.get(matching_states[0], "Lower 48") if len(matching_states) == 1 else "Lower 48"
        region = st.selectbox("Map region", list(VIEWS), index=list(VIEWS).index(suggested_region),
                              key=f"region_{suggested_region}")
        map_key = f"map_{region}"

        def choose_marker():
            points = st.session_state[map_key].selection["objects"].get("park-points", [])
            if points and points[0]["park_code"] in available:
                st.session_state["selected_park"] = points[0]["park_code"]

        st.pydeck_chart(park_map(matching, saved, region), height=495,
                        key=map_key, on_select=choose_marker, selection_mode="single-object")

    def choose_park():
        st.session_state["selected_park"] = st.session_state["park"]

    code = st.selectbox("Selected park", available, format_func=label, key="park", on_change=choose_park)
    record = parks.loc[parks["park_code"].eq(code)].iloc[0]
    park_history = window.loc[window["park_code"].eq(code)]
    st.header(names[code])
    location = f'{record["latitude"]:.3f}°, {record["longitude"]:.3f}°' if pd.notna(
        record[["latitude", "longitude"]]).all() else "Coordinates unavailable"
    st.caption(f'{record["state"]} · {location} · {years[0]}–{years[1]}')
    seki_note([code])
    st.caption("Weather models a single geographic coordinate. Conditions vary with location and elevation.")
    park_scores = scores.loc[scores["park_code"].eq(code)].dropna(subset=["score"])
    if not park_scores.empty:
        best_month = park_scores.sort_values(["score", "month"], ascending=[False, True]).iloc[0]
        st.success(f'Your seasonal match · {best_month["month_name"]} · {best_month["score"]:.1f}/100 suitability · {best_month["years"]} paired years')

if page in ("Park guide", "Explore"):
    render_park_guide(code, scores, comfort_c, unit, setting("NPS_API_KEY"))
    st.subheader("Historical weather & park visitation")
    profile = monthly_profile(park_history)
    complete = park_history.dropna(subset=METRICS)
    metrics = st.columns(3)
    temperature = park_history["avg_temp_c"].mean()
    metrics[0].metric("Mean observed temperature", f"{convert_temperature(temperature, unit):.1f} {unit}" if pd.notna(temperature) else "—")
    visits = park_history[VISITS].mean()
    metrics[1].metric("Mean observed monthly visits", f"{visits:,.0f}" if pd.notna(visits) else "—")
    metrics[2].metric("Complete park-months", f"{len(complete):,}")
    seasonal = st.columns(2)
    for column, metric, title, suffix in [
        (seasonal[0], "total_precip_mm", "Mean monthly precipitation", "mm"),
        (seasonal[1], "total_snowfall_cm", "Mean monthly snowfall", "cm"),
    ]:
        value = park_history[metric].mean()
        column.metric(title, f"{value:.1f} {suffix}" if pd.notna(value) else "—")
    st.subheader("Weather and visitation by month")
    st.caption("Each point averages the available observations for that calendar month.")
    draw_profile(profile, METRICS)
    with st.expander("Observations per calendar month"):
        counts = profile.set_index("month_name")[[f"{metric}_n" for metric in METRICS]]
        st.dataframe(counts.rename(columns={f"{metric}_n": LABELS[metric] for metric in METRICS}))

elif page == "Visit rankings":
    st.subheader("Find your next park")
    travel_month = st.selectbox("Travel month for park recommendations", range(13),
                                format_func=lambda value: month_name[value] if value else "Any month")
    top = scores.dropna(subset=["score"])
    if travel_month:
        top = top.loc[top["month"].eq(travel_month)]
    top = top.sort_values(["score", "park_code", "month"], ascending=[False, True, True])
    top = top.drop_duplicates("park_code").head(5).copy()
    top["Park"] = top["park_code"].map(names)
    if top.empty:
        st.info("No park-month has enough complete years for these preferences.")
    else:
        for column, (_, match) in zip(st.columns(min(3, len(top))), top.head(3).iterrows()):
            with column:
                st.markdown(
                    f'<div class="match-card"><h3>{escape(match["Park"])}</h3>'
                    f'<span class="score">{match["score"]:.0f}</span> / 100'
                    f'<p>{escape(match["month_name"])} · {int(match["years"])} paired years</p>'
                    f'<p>{convert_temperature(match["avg_temp_c"], unit):.1f} {unit} · '
                    f'{match["recreation_visits"]:,.0f} median visits</p></div>',
                    unsafe_allow_html=True,
                )
        st.dataframe(display_profile(top)[["Park", "month_name", "score", "years", "avg_temp_c",
                             "total_precip_mm", "total_snowfall_cm", "recreation_visits",
                             "crowd_percentile"]].rename(columns={
                                 "avg_temp_c": f"Median temperature ({unit})",
                                 "score": "Suitability / 100", "years": "Paired years",
                                 "total_precip_mm": "Precipitation (mm)", "total_snowfall_cm": "Snow (cm)",
                                 "recreation_visits": "Median visits", "crowd_percentile": "Crowd percentile",
                             }).round(1), hide_index=True, width="stretch")
    st.caption("Suitability is a configurable historical index. Cross-park crowd scores describe relative seasonality.")
    ranked = scores.loc[scores["park_code"].eq(code)].sort_values(["rank", "month"], na_position="last")
    eligible = ranked.dropna(subset=["score"])
    if eligible.empty:
        st.info("No month meets the coverage threshold. Try a wider year range or fewer required years.")
    else:
        best = eligible.iloc[0]
        tied = eligible.loc[eligible["rank"].eq(1), "month_name"].tolist()
        st.subheader("Top match · " + " / ".join(tied))
        st.write(
            f'{best["month_name"]} scores **{best["score"]:.1f}/100** with a weather score of '
            f'{best["weather_score"]:.1f} and a crowd score of {best["crowd_score"]:.1f}. '
            f'Across {best["years"]} paired years, median conditions were {convert_temperature(best["avg_temp_c"], unit):.1f} {unit}, '
            f'{best["total_precip_mm"]:.1f} mm of precipitation, and '
            f'{best["total_snowfall_cm"]:.1f} cm of snow, with {best[VISITS]:,.0f} recreation visits.'
        )
        st.plotly_chart(rank_chart(eligible), width="stretch")
        if len(eligible) < 12:
            st.caption(f"{len(eligible)} of 12 calendar months meet the selected coverage threshold.")

    cols = ["rank", "month_name", "score", "weather_score", "crowd_score", "years", *METRICS]
    headings = {"rank": "Rank", "month_name": "Month", "score": "Visit score",
                "weather_score": "Weather score", "crowd_score": "Crowd score",
                "years": "Paired years", **{metric: "Median " + LABELS[metric].replace("°C", unit).lower() for metric in METRICS}}
    st.dataframe(display_profile(ranked)[cols].round(1).rename(columns=headings), hide_index=True, width="stretch")
    with st.expander("How the rankings work"):
        st.markdown(SCORING)

elif page == "Compare":
    options = parks["park_code"].tolist()
    defaults = [code for code in ("ACAD", "ARCH") if code in options]
    codes = st.multiselect("Choose two or three park records", options,
                           default=defaults or options[:2], max_selections=3, format_func=label)
    if len(codes) < 2:
        st.info("Choose at least two park records to compare.")
        st.stop()
    seki_note(codes)
    st.caption("Profiles use the selected years and each park’s available observations.")
    relative = st.toggle("Show visitation relative to each park’s peak month")
    profiles = []
    summary = []
    for code in codes:
        rows = window.loc[window["park_code"].eq(code)]
        profile = monthly_profile(rows)
        profile["park_code"] = code
        profiles.append(profile)
        peak = profile.loc[profile[VISITS].eq(profile[VISITS].max()), "month_name"]
        summary.append({
            "Park": label(code), "Peak visitation month": ", ".join(peak) or "—",
            f"Mean temperature ({unit})": convert_temperature(rows["avg_temp_c"].mean(), unit),
            "Mean precipitation (mm)": rows["total_precip_mm"].mean(),
            "Mean snowfall (cm)": rows["total_snowfall_cm"].mean(),
            "Mean monthly visits": rows[VISITS].mean(),
            "Weather months": len(rows.dropna(subset=METRICS[:-1])),
            "Visitation months": rows[VISITS].count(),
        })
    st.dataframe(pd.DataFrame(summary).round(1), hide_index=True, width="stretch")
    draw_profile(pd.concat(profiles, ignore_index=True),
                 [*METRICS[:-1], "relative_visits" if relative else VISITS], compare=True)

elif page == "Travel assistant":
    render_assistant(parks, window, dsn, {
        "temperature": list(comfort_c), "weather": weather_weight, "crowds": crowd_weight,
        "minimum_years": int(minimum_years), "years": list(years),
        "selected_park": st.session_state.get("selected_park", "ACAD"),
    }, setting("OPENAI_API_KEY"), setting("NPS_API_KEY"), setting("OPENAI_MODEL"))

else:
    st.subheader("Data coverage")
    columns = st.columns(3)
    columns[0].metric("Park records", f"{len(parks):,}")
    columns[1].metric("Visitation park-months", f"{window[VISITS].count():,}")
    columns[2].metric("Complete park-months", f"{len(window.dropna(subset=METRICS)):,}")
    coverage = (window.dropna(subset=METRICS).groupby("year").size()
                .reindex(range(years[0], years[1] + 1), fill_value=0)
                .rename("Paired observations").rename_axis("Year").reset_index())
    st.plotly_chart(style(px.bar(coverage, x="Year", y="Paired observations",
                                color_discrete_sequence=["#24694f"])), width="stretch")
    st.subheader("Seasonality and weather associations")
    code = st.selectbox("Park for exploratory analysis", parks["park_code"].tolist(), format_func=label)
    seki_note([code])
    rows = window.loc[window["park_code"].eq(code)]
    st.subheader("What the selected data shows")
    for finding in findings(rows):
        st.markdown("- " + finding)
    st.subheader("Missing values & unusual observations")
    diagnostic = diagnostics(rows)
    diagnostic["metric"] = diagnostic["metric"].map(LABELS)
    st.dataframe(diagnostic.round(2), hide_index=True, width="stretch")
    st.caption("Diagnostics use database units: °C, mm, cm and recreation visits. Tukey flags use 1.5 × IQR within each park/calendar month, with at least 8 observed years and a positive IQR. Unscreened values are not assumed typical. Plausible extremes are retained; the mean without flags is a sensitivity comparison only. The recommendation engine remains unchanged and uses paired-year medians. Missing values are preserved, never imputed as zero.")
    stats = display_profile(rows)[METRICS].describe().T.set_axis([LABELS[metric].replace("°C", unit) for metric in METRICS])
    st.dataframe(stats.round(2), width="stretch")
    draw_profile(monthly_profile(rows), [VISITS])
    metric = st.selectbox("Weather metric", METRICS[:-1], format_func=LABELS.get)
    paired = rows.dropna(subset=[metric, VISITS])
    if paired.empty:
        st.info("No paired observations are available for this weather metric.")
    else:
        st.plotly_chart(style(px.scatter(display_profile(paired), x=metric, y=VISITS, color="year",
                                         labels={**{key: value.replace("°C", unit) for key, value in LABELS.items()}, "year": "Year"}, hover_data=["month"],
                                         color_continuous_scale="Greens"), 380), width="stretch")
    results = associations(rows)
    results["metric"] = results["metric"].map(LABELS)
    st.dataframe(results.rename(columns={
        "metric": "Weather variable", "paired_months": "Paired observations",
        "spearman": "Spearman ρ", "anomaly_pairs": "Season-adjusted observations",
        "anomaly_spearman": "Season-adjusted Spearman ρ",
    }).round(3), hide_index=True, width="stretch")
    st.caption("Undefined correlations appear blank when there are too few pairs or a variable is constant.")
    st.info("Interpretation: raw correlations include the shared annual cycle of weather and visits. Season-adjusted correlations subtract each calendar month's mean and use months with repeated years. Differences can indicate seasonal confounding; neither measure establishes causation. Pandemic disruptions, park access, geography and visitor behavior can affect both series.")
    st.markdown(METHOD)
    st.caption(SEKI)
    with st.expander("Recommendation scoring formula"):
        st.markdown(SCORING)

