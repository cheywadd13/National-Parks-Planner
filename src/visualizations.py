"""Reusable PyDeck and Plotly figures."""

import pandas as pd
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go

PALETTE = ["#176b50", "#a45728", "#536fa0"]
VIEWS = {
    "Lower 48": (39, -97, 3.4),
    "Alaska": (63, -153, 3.1),
    "Hawaiʻi": (20.3, -156, 6),
    "American Samoa": (-14.25, -170.7, 8),
    "U.S. Virgin Islands": (18.34, -64.74, 8),
}
LABELS = {
    "avg_temp_c": "Mean monthly temperature (°C)",
    "total_precip_mm": "Monthly precipitation (mm)",
    "total_snowfall_cm": "Monthly snowfall (cm)",
    "recreation_visits": "Monthly recreation visits",
    "relative_visits": "Visits as % of park peak",
}


def park_map(parks, selected, region):
    plotted = parks.dropna(subset=["latitude", "longitude"]).copy()
    plotted["color"] = [[224, 158, 68, 255] if code == selected else [26, 105, 75, 225]
                        for code in plotted["park_code"]]
    lat, lon, zoom = VIEWS[region]
    return pdk.Deck(
        layers=[pdk.Layer(
            "ScatterplotLayer", plotted.to_dict("records"), id="park-points",
            get_position=["longitude", "latitude"], get_fill_color="color",
            get_radius=17000, radius_min_pixels=6, radius_max_pixels=14,
            stroked=True, get_line_color=[250, 248, 240], line_width_min_pixels=1,
            pickable=True, auto_highlight=True,
        )],
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom),
        map_provider="carto", map_style="light",
        tooltip={"text": "{park_name}\n{state} · {park_code}"},
    )


def style(figure, height=300):
    figure.update_layout(
        height=height, template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font_color="#23392f",
        margin=dict(l=12, r=12, t=16, b=16),
        legend=dict(orientation="h", y=-0.30, title_text=""),
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor="#dce6dc")
    return figure


def monthly_chart(profile, metric, compare=False, unit="°C"):
    labels = {"month_name": "Month", metric: LABELS[metric].replace("°C", unit), "park_code": "Park"}
    if compare:
        fig = px.line(profile, x="month_name", y=metric, color="park_code", markers=True,
                      labels=labels, color_discrete_sequence=PALETTE)
    elif metric == "avg_temp_c":
        fig = px.line(profile, x="month_name", y=metric, markers=True, labels=labels,
                      color_discrete_sequence=PALETTE)
    else:
        fig = px.bar(profile, x="month_name", y=metric, labels=labels,
                     color_discrete_sequence=PALETTE)
    fig.update_xaxes(title_text="")
    return style(fig)


def rank_chart(ranked):
    fig = go.Figure(go.Bar(
        x=ranked["month_name"], y=ranked["score"], marker_color=[
            "#c48b44" if pd.notna(rank) and rank == 1 else "#24694f" for rank in ranked["rank"]
        ],
        hovertemplate="%{x}<br>Score %{y:.1f}/100<extra></extra>",
    ))
    fig.update_yaxes(title_text="Visit score", range=[0, 100])
    return style(fig, 240)
