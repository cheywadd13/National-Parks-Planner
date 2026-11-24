"""Destination-guide UI with cited NPS content and reviewed hike cards."""

from datetime import datetime
from html import escape
import json
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from .nps_api import fetch_profile, fetch_alerts
from .recommendations import convert_temperature
from .trails import load_trails, filter_trails, month_context, crowd_category

DATA = Path(__file__).resolve().parents[1] / "data"


@st.cache_data(show_spinner=False)
def profile_catalog():
    return json.loads((DATA / "park_profiles.json").read_text(encoding="utf-8"))["profiles"]


@st.cache_data(ttl=86400, max_entries=128, show_spinner=False)
def current_profile(code, api_key):
    fallback = profile_catalog().get(code, {})
    if not api_key:
        return fallback, None
    try:
        profile = fetch_profile(code, api_key)
        profile["images"] = profile.get("images") or fallback.get("images", [])
        profile["description"] = profile.get("description") or fallback.get("description", "")
        profile["highlights"] = fallback.get("highlights", [])
        profile["activities"] = profile.get("activities") or fallback.get("activities", [])
        return profile, None
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return fallback, "Official API refresh unavailable; showing the dated NPS website snapshot."


@st.cache_data(ttl=300, max_entries=128, show_spinner=False)
def current_alerts(code, api_key):
    if not api_key:
        return {"status": "unavailable", "alerts": [], "checked_at": None}
    try:
        return fetch_alerts(code, api_key)
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return {"status": "unavailable", "alerts": [], "checked_at": None}


def display_date(value):
    if not value:
        return "date unavailable"
    return datetime.fromisoformat(value).strftime("%b %d, %Y · %H:%M UTC")


def activity_names(profile):
    return {row["name"] for row in profile.get("activities", [])}


def render_alerts(code, profile, api_key):
    result = current_alerts(code, api_key)
    state_key = f"last_official_alerts_{code}"
    if result["status"] == "ok":
        st.session_state[state_key] = result
    elif state_key in st.session_state:
        result = {**st.session_state[state_key], "status": "stale"}
    with st.expander("Official alerts & access", expanded=True):
        if result["status"] == "unavailable":
            st.info("Current official alerts are unavailable in this preview. Check the NPS park website before travel.")
        else:
            if result["status"] == "stale":
                st.warning("Alert refresh failed. These are previously retrieved notices.")
            st.caption("NPS API checked " + display_date(result["checked_at"]))
            if not result["alerts"]:
                st.write("The NPS API returned no notices. Individual trail access still needs an official conditions check.")
            for notice in result["alerts"]:
                st.markdown(f'**{notice["category"]} · {notice["title"]}**')
                st.write(notice["description"])
                if notice["url"]:
                    st.link_button("Read official notice", notice["url"])
        if profile.get("official_url"):
            st.link_button("Check the official NPS park website", profile["official_url"])


def render_activities(profile):
    records = profile.get("activities", [])
    unique = {}
    for row in records:
        unique.setdefault(row["name"], row)
    if not unique:
        st.info("Activity details are still incomplete for this record. Explore the official NPS park page.")
        return
    st.caption("NPS-listed activities. Operating dates, permits and current access are listed on the official activity pages.")
    columns = st.columns(3)
    for index, row in enumerate(unique.values()):
        with columns[index % 3]:
            with st.container(border=True):
                st.markdown(f'**{row["name"]}**')
                st.write(row.get("source_label", row["name"]))
                st.link_button("Explore with NPS", row["url"])


def render_hikes(code, profile):
    all_trails = load_trails()
    park_trails = [trail for trail in all_trails if trail["park_code"] == code]
    total_parks = len({trail["park_code"] for trail in all_trails})
    st.caption(f"Reviewed catalog · {len(all_trails)} routes across {total_parks} parks · "
               f"{len(park_trails)} routes documented for this park. Coverage is incomplete.")
    if not park_trails:
        st.info("No trail data available for this park in the reviewed catalog. This is a coverage gap, not evidence that the park has no hiking routes.")
        hiking = next((row for row in profile.get("activities", []) if row["name"] == "Hiking"), None)
        if hiking:
            st.link_button("Browse the official NPS hiking guide", hiking["url"])
        return
    controls = st.columns([1, 1])
    ratings = sorted({trail.get("difficulty") or "Not reported" for trail in park_trails})
    difficulty = controls[0].selectbox("Hiking difficulty", ["Any", *ratings], key=f"difficulty_{code}")
    maximum = controls[1].number_input("Maximum route distance (miles)", .5, 100., 20., .5, key=f"distance_{code}")
    include_unknown = st.checkbox("Include hikes with unreported distance", value=True, key=f"unknown_distance_{code}")
    records = filter_trails(all_trails, code, difficulty, maximum, include_unknown)
    st.caption("Lengths retain the source's round-trip, loop, or one-way basis. Published durations are estimates. A specific difficulty also matches explicitly published ranges containing that grade; unrated routes are not assigned a grade.")
    if not records:
        st.info(f"No matching trails. {len(park_trails)} reviewed records exist for this park, but the current difficulty/distance/unknown-distance filters exclude them. Choose Any difficulty or increase the distance limit.")
    columns = st.columns(2)
    for index, trail in enumerate(records):
        with columns[index % 2]:
            with st.container(border=True):
                st.subheader(trail["name"])
                st.caption(trail.get("difficulty") or "Difficulty not reported by this source")
                distance = trail.get("distance_miles")
                distance_text = (f'{distance:g} mi / {distance * 1.609344:.1f} km · {trail["distance_basis"]}'
                                 if distance is not None else "Distance unreported or unresolved")
                st.markdown(f"**{distance_text}**")
                st.write(trail.get("duration") or "Hiking duration not reported")
                st.write(trail["description"])
                with st.expander("Trailhead, elevation & restrictions"):
                    st.write("Trailhead · " + trail["trailhead"])
                    elevation = trail.get("elevation_ft")
                    if elevation is None:
                        st.write("Elevation gain · not reported")
                    else:
                        st.write(f'{trail["elevation_kind"]} · {elevation:g} ft / {elevation * .3048:.0f} m')
                    if trail.get("measurement_note"):
                        st.caption(trail["measurement_note"])
                    if trail.get("season_note"):
                        st.write("Seasonal guidance · " + trail["season_note"])
                    st.write(trail["restrictions"])
                    st.caption(trail["permit_note"])
                st.link_button("Official trail guide ↗", trail["source_url"])
                st.caption("Source checked " + display_date(trail["checked_at"]))


def render_month_planning(code, scores, comfortable, unit):
    park_scores = scores.loc[scores.park_code.eq(code)].sort_values("month")
    eligible = park_scores.dropna(subset=["score"])
    if eligible.empty:
        st.info("The selected years do not provide enough paired observations for month recommendations.")
        return
    recommended = eligible.sort_values(["score", "month"], ascending=[False, True]).iloc[0]
    options = park_scores.month.tolist()
    month = st.selectbox("Month to explore", options, index=options.index(int(recommended["month"])),
                         format_func=lambda value: park_scores.loc[park_scores.month.eq(value), "month_name"].iloc[0],
                         key=f"guide_month_{code}")
    row = park_scores.loc[park_scores.month.eq(month)].iloc[0]
    if pd.isna(row["score"]):
        st.info("This calendar month does not meet the selected coverage threshold.")
        return
    st.markdown(f'**{row["month_name"]} · {crowd_category(row["crowd_percentile"])}**')
    cells = st.columns(3)
    cells[0].metric("Median temperature", f'{convert_temperature(row["avg_temp_c"], unit):.1f} {unit}')
    cells[1].metric("Median monthly visits", f'{row["recreation_visits"]:,.0f}')
    cells[2].metric("Seasonal crowd percentile", f'{row["crowd_percentile"]:.0f}/100')
    for message in month_context(row, comfortable):
        st.write(message)
    st.caption(f'{row["years"]} paired years in the selected window. Park-wide visitation is a crowd proxy; '
               "individual trail traffic is unmeasured. Historical monthly weather at one park coordinate "
               "does not establish trail conditions, access or safety.")
    st.write("Check each route's NPS seasonal guidance and current official alerts before choosing an outing.")
    table = eligible[["month_name", "score", "years", "crowd_percentile", "recreation_visits"]].copy()
    st.dataframe(table.rename(columns={"month_name": "Month", "score": "Historical suitability / 100",
                                       "years": "Paired years", "crowd_percentile": "Crowd percentile",
                                       "recreation_visits": "Median park visits"}).round(1),
                 hide_index=True, width="stretch")


def render_park_guide(code, scores, comfortable, unit, api_key=None):
    profile, error = current_profile(code, api_key)
    if not profile:
        st.info("Official destination information is temporarily unavailable.")
        return
    images = profile.get("images", [])
    if images:
        image = images[0]
        st.markdown(f'<img class="destination-photo" src="{escape(image["url"], quote=True)}" '
                    f'alt="{escape(image.get("alt", ""), quote=True)}">', unsafe_allow_html=True)
        st.caption(f'{image["caption"]} · {image["credit"]}')
        with st.expander("Photo source and reuse information"):
            st.link_button("NPS photograph source", image["source_url"])
            st.link_button("NPS image ownership policy", image["rights_url"])
            st.caption(image["rights_basis"])
    st.write(profile.get("description") or "Description not reported by this source.")
    st.caption(profile["source_kind"] + " · checked " + display_date(profile.get("checked_at")))
    st.link_button("Visit the official park website ↗", profile["official_url"])
    if error:
        st.caption(error)
    if st.button("Refresh official information", key=f"refresh_official_{code}"):
        current_profile.clear()
        current_alerts.clear()
        st.rerun()
    render_alerts(code, profile, api_key)
    activities, hikes, planning = st.tabs(["Activities & highlights", "Hikes & trail details", "When to visit"])
    with activities:
        render_activities(profile)
        highlights = profile.get("highlights", [])
        if highlights:
            st.markdown("**More from the park**")
            for row in highlights:
                st.link_button(row["title"], row["url"])
    with hikes:
        render_hikes(code, profile)
    with planning:
        render_month_planning(code, scores, comfortable, unit)
