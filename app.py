"""
QC Competition Dashboard  \u2014  League of Loyalty
=================================================
A gamified, production-ready competition dashboard for QC/review activity.

Data workflow is unchanged: the app reads a CSV and reflects the latest data on
(re)load. Two clearly separated methodologies:
  \u2022 Weekly    \u2014 raw points, ranked within each role (Owner / Peer 1 / Peer 2)
  \u2022 Monthly / Quarterly \u2014 band-wise Z-score \u2192 a fair 0-100 metric (z_score_points)

Run:  streamlit run app.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import logic
import avatars
from logic import BANDS, BAND_META, BUCKETS, BUCKET_COLOR

DATA_PATH = Path(__file__).parent / "review_log.csv"
PROFILE_PATH = Path(__file__).parent / "player_profiles.csv"

GOLD, PARCHMENT, MUTED, BG_PANEL = "#C8AA6E", "#F0E6D2", "#A09B8C", "#102A43"
DASH = "\u2014"
POD_COLOR = {"CP": "#59C3FF", "NCP": "#FF9F1C"}   # distinct name colours per pod
BAND_COLORS = {b: BAND_META[b]["color"] for b in BANDS}
SEQ = [GOLD, "#5B8DEF", "#4CC9B0", "#B57BE0", "#E8734A", "#F4CE00"]
BAR_SEQ = ["#F4CE00", "#59C3FF", "#FF6B6B", "#3FA34D", "#9B5DE5",
           "#FF9F1C", "#2EC4B6", "#F15BB5", "#00BBF9", "#E86A17"]


def _dark(hex_color: str, f: float = 0.66) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"


def _rgba(hex_color: str, a: float = 0.16) -> str:
    """Plotly properties (e.g. fillcolor) reject 8-digit hex; emit rgba() instead."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


st.set_page_config(page_title="QC Competition \u2014 League of Loyalty",
                   page_icon="\U0001F3C6", layout="wide",
                   initial_sidebar_state="expanded")


# ---------------------------------------------------------------- data (cached)
@st.cache_data(ttl=3600, show_spinner=False)
def get_data() -> pd.DataFrame:
    """Load + prepare the CSV. Cached so filters/interactions never re-read disk."""
    return logic.load_and_prepare(str(DATA_PATH))


@st.cache_data(ttl=3600, show_spinner=False)
def get_profiles() -> pd.DataFrame:
    """Editable roster (roles + avatars). Cached; cleared by the Refresh button."""
    return logic.load_profiles(str(PROFILE_PATH))


@st.cache_data(show_spinner=False)
def fair_cached(_df, period_col, period_val, pod, campaigns, types, buckets):
    """Z-score leaderboard for a period, via the single filter pipeline (POD first).
    Keyed on scalar filters only (df not hashed) so it recomputes only when a
    filter actually changes."""
    sub = logic.filter_data(_df, pod, campaigns, types, buckets)
    sub = sub[sub[period_col] == period_val]
    return logic.fair_leaderboard(sub)


# ---------------------------------------------------------------- ui helpers
def style_fig(fig, height=320, legend=True):
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(color=PARCHMENT, size=13),
        margin=dict(l=10, r=10, t=30, b=10), height=height,
        title=dict(text="", font=dict(color=PARCHMENT, size=15)),  # empty text, never 'undefined'
        showlegend=legend, legend=dict(bgcolor="rgba(0,0,0,0)"))
    fig.update_xaxes(gridcolor="#1e3a5f", zerolinecolor="#1e3a5f")
    fig.update_yaxes(gridcolor="#1e3a5f", zerolinecolor="#1e3a5f")
    return fig


def show(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def band_badge(band: str) -> str:
    c = BAND_META[band]["color"]
    return (f'<span style="background:{c}22;color:{c};border:1px solid {c}66;'
            f'padding:2px 9px;border-radius:10px;font-size:0.78rem;font-weight:700;'
            f'white-space:nowrap;">{BAND_META[band]["emoji"]} {band}</span>')


def medal(rank: int) -> str:
    return {1: "\U0001F947", 2: "\U0001F948", 3: "\U0001F949"}.get(int(rank), f"#{int(rank)}")


def fmt_pts(x) -> str:
    """Points are normalised per campaign, so they can be fractional. Show a whole
    number when it is one (10), otherwise one decimal (7.5)."""
    x = float(x)
    return str(int(round(x))) if abs(x - round(x)) < 1e-9 else f"{x:.1f}"


def banner():
    st.markdown(
        f'<div style="border:1px solid {GOLD}55;border-radius:14px;padding:16px 22px;'
        f'background:linear-gradient(100deg,#0A1428 0%,{BG_PANEL} 70%,#123 100%);'
        f'margin-bottom:6px;">'
        f'<div style="color:{GOLD};letter-spacing:3px;font-size:0.72rem;font-weight:700;">'
        f'MU SIGMA \u00b7 QUALITY CHAMPIONSHIP</div>'
        f'<div style="color:{PARCHMENT};font-size:1.9rem;font-weight:800;letter-spacing:1px;'
        f'line-height:1.15;">LEAGUE OF LOYALTY</div>'
        f'<div style="color:{MUTED};font-size:0.92rem;">QC Competition Dashboard \u2014 '
        f'raw weekly races and fair, band-normalised monthly &amp; quarterly rankings</div>'
        f'</div>', unsafe_allow_html=True)


def champion_card(col, title, name, subtitle, accent=GOLD):
    with col, st.container(border=True):
        st.markdown(f'<div style="color:{accent};font-size:0.72rem;letter-spacing:1px;'
                    f'font-weight:700;">{title}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:1.15rem;font-weight:700;color:{PARCHMENT};'
                    f'line-height:1.3;">{name or DASH}</div>', unsafe_allow_html=True)
        st.caption(subtitle)


def leaderboard_table(dfin, columns_config, height=None):
    """Render a dataframe. Robust against a missing height: never lets None reach
    st.dataframe (newer Streamlit rejects it). Falls back to a content-fit height."""
    if not isinstance(height, int) or isinstance(height, bool) or height <= 0:
        rows = len(dfin) if dfin is not None else 0
        height = int(min(max(rows, 1), 25) * 35 + 42)  # header + rows, capped
    st.dataframe(dfin, hide_index=True, use_container_width=True,
                 height=height, column_config=columns_config)


def no_data(msg="No data available for the current selection."):
    st.info("\U0001F4ED  " + msg)


# ---------------------------------------------------------------- load + sidebar
df = get_data()
PROFILE = get_profiles()
PMAP = logic.profile_map(PROFILE)
pods = logic.list_pods(df)
months, weeks, quarters = logic.list_months(df), logic.list_weeks(df), logic.list_quarters(df)
campaigns_all, types_all = logic.list_campaigns(df), logic.list_types(df)


# ---- per-player avatar / role / pod-colour helpers --------------------------
def player_meta(pod, name):
    m = PMAP.get((str(pod).upper(), str(name).upper()))
    if m:
        return m
    arch = avatars.list_archetypes()[avatars._seed(f"{pod}|{name}") % len(avatars.list_archetypes())]
    return {"role": "Owner", "gender": "M", "archetype": arch}


def av_uri(pod, name, scale=6):
    m = player_meta(pod, name)
    return avatars.avatar_data_uri(m["archetype"], m["gender"], f"{pod}|{name}", scale)


def av_name(pod, name):
    m = player_meta(pod, name)
    return avatars.archetype_display(m["archetype"], m["gender"])


def role_of(pod, name):
    return player_meta(pod, name)["role"]


def pod_color(pod):
    return POD_COLOR.get(str(pod).upper(), GOLD)


def name_html(pod, name, size="1rem"):
    return (f'<span style="color:{pod_color(pod)};font:800 {size} system-ui;">{name}</span>'
            f'<span style="color:{MUTED};font-size:0.62rem;"> {pod}</span>')


with st.sidebar:
    st.markdown(f'<div style="font-weight:800;color:{GOLD};font-size:1.1rem;">'
                f'\U0001F3C6 League of Loyalty</div>', unsafe_allow_html=True)
    st.caption("One Goal | One Team | Zero Error Delivery")
    st.divider()

    page = st.radio("Go to", [
        "\U0001F3E0 Overview", "\U0001F4C5 Weekly Competition",
        "\U0001F4C8 Monthly Competition", "\U0001F5D3\uFE0F Quarterly Competition",
        "\U0001F464 Participant Analytics", "\U0001F41E Error Analytics",
        "\U0001F4D8 About Competition"],
        label_visibility="collapsed")

    st.divider()
    pod_options = ["All PODs"] + pods
    sel_pod = st.selectbox("\U0001F3E2 POD (team)", pod_options, index=0,
                           help="Highest-level filter. Everything below applies within "
                                "the selected POD.")
    POD = None if sel_pod == "All PODs" else sel_pod

    st.markdown("**Filters**")
    sel_month = st.selectbox("Month (Season)", months, index=len(months) - 1)
    sel_week = st.selectbox("Week", weeks, index=len(weeks) - 1)
    sel_quarter = st.selectbox("Quarter", quarters, index=len(quarters) - 1)
    sel_campaign = st.multiselect("Campaign", campaigns_all, help="Empty = all campaigns.")
    sel_type = st.multiselect("Type", types_all, help="Empty = all types.")
    sel_bucket = st.multiselect("Error Bucket", BUCKETS, help="Empty = all buckets.")

    _pp = PROFILE if POD is None else PROFILE[PROFILE["POD"] == POD]
    _pp = _pp.sort_values(["POD", "Name"])
    player_options = [f"{r.Name} \u00b7 {r.POD}" for r in _pp.itertuples(index=False)]
    sel_player = st.selectbox("Player", player_options,
                              help="Used on Participant Analytics.") if player_options else None

    st.divider()
    st.caption(f"Data updated: {df['Date'].max():%d %b %Y}")
    if st.button("\U0001F504 Refresh data", use_container_width=True,
                 help="Reload player_profiles.csv and review_log.csv from disk."):
        st.cache_data.clear()
        st.rerun()


# ---- single filtering pipeline: POD -> campaign/type/bucket (period per page) --
CAMPS = tuple(sorted(sel_campaign))
TYPES = tuple(sorted(sel_type))
BUCKS = tuple(sorted(sel_bucket))
fdf = logic.filter_data(df, POD, CAMPS, TYPES, BUCKS)  # base frame every page consumes
POD_LABEL = sel_pod
if sel_player:
    sel_player_name, sel_player_pod = [s.strip() for s in sel_player.split("\u00b7")]
else:
    sel_player_name, sel_player_pod = None, None


SEASON_NAMES = ["Dawn", "Eclipse", "Ascension"]
SEASON_COLOR = {"Dawn": "#F4A259", "Eclipse": "#7B6CF6", "Ascension": "#4CC9B0"}
MINOR_ERRORS = [
    "Treatment / offer label", "Wrong offer IDs", "Wrong segment cutoffs",
    "Incorrect compensation", "SKU table segments", "Not pasting output in comments",
    "IPI_CAT-related errors in TXN_BRND table", "Wrong values pasted in counts-mail Excel"]
MAJOR_ERRORS = [
    "Failed to check promo SKUs existing in the stock-keeping unit",
    "Wrong time periods used", "Failed to check SKUs for targeting", "Improper RFC",
    "Anything related to retargeting", "Segmentation errors in TXN_BRND_MEMBER_SMY",
    "Considering wrong visits in CAMP_SMY table"]
BRIEF_ERRORS = ["Anything related to the brief and its logical interpretation"]


def _scoring_table_html():
    head = (f'<tr style="background:{_dark(GOLD,0.5)};">'
            + "".join(f'<th style="padding:8px 10px;text-align:{a};color:{PARCHMENT};'
                      f'font:800 0.8rem system-ui;">{c}</th>'
                      for c, a in [("Event / Error bucket", "left"), ("L1 (Owner)", "center"),
                                   ("L2 (Peer 1)", "center"), ("L3 (Peer 2)", "center")]) + "</tr>")
    bucket_hex = {"Brief Interpretation Error": BUCKET_COLOR["Brief Interpretation Error"],
                  "Major Error": BUCKET_COLOR["Major Error"],
                  "Minor Error": BUCKET_COLOR["Minor Error"]}
    rows = ""
    for i, (event, l1, l2, l3) in enumerate(logic.SCORING_RULES):
        dot = ""
        for b, hexc in bucket_hex.items():
            if event.startswith(b):
                dot = (f'<span style="display:inline-block;width:9px;height:9px;'
                       f'border-radius:2px;background:{hexc};margin-right:7px;"></span>')
        bg = "#ffffff08" if i % 2 else "#ffffff02"
        rows += (f'<tr style="background:{bg};">'
                 f'<td style="padding:7px 10px;color:{PARCHMENT};font:600 0.82rem system-ui;">'
                 f'{dot}{event}</td>'
                 + "".join(f'<td style="padding:7px 10px;text-align:center;font:800 0.82rem '
                           f'system-ui;color:{"#FF8A8A" if str(v).startswith(chr(8722)) else PARCHMENT};">'
                           f'{v}</td>' for v in (l1, l2, l3)) + "</tr>")
    return (f'<table style="width:100%;border-collapse:collapse;border:1px solid #ffffff1f;'
            f'border-radius:12px;overflow:hidden;">{head}{rows}</table>')


def _error_catalog_html(title, color, items):
    lis = "".join(f'<li style="margin:3px 0;color:{PARCHMENT};font:600 0.8rem system-ui;">{x}</li>'
                  for x in items)
    return (f'<div style="flex:1 1 260px;min-width:230px;box-sizing:border-box;'
            f'border:1px solid {color}66;background:{color}14;border-radius:12px;padding:10px 12px;">'
            f'<div style="color:{color};font:800 0.85rem system-ui;letter-spacing:0.5px;'
            f'margin-bottom:4px;">{title}</div>'
            f'<ul style="margin:0;padding-left:18px;">{lis}</ul></div>')


def _roster_card(pod, name, role=None):
    m = player_meta(pod, name)
    c = pod_color(pod)
    aname = avatars.archetype_display(m["archetype"], m["gender"])
    role_line = (f'<div style="color:{MUTED};font:600 0.6rem system-ui;">{role}</div>'
                 if role else "")
    return (f'<div style="width:98px;text-align:center;background:#0b1b2c;border:1px solid {c}44;'
            f'border-radius:10px;padding:8px 4px;">'
            f'<img src="{av_uri(pod, name)}" width="46" style="image-rendering:pixelated;'
            f'filter:drop-shadow(0 2px 2px #0007);"/>'
            f'<div style="color:{c};font:800 0.82rem system-ui;">{name}</div>'
            f'<div style="color:{MUTED};font-size:0.58rem;">POD {pod}</div>'
            f'{role_line}'
            f'<div style="color:{PARCHMENT};font:700 0.66rem system-ui;">{aname}</div></div>')


def roster_gallery(profiles, show_role=True):
    blocks = []
    for pod in sorted(profiles["POD"].unique()):
        sub = profiles[profiles["POD"] == pod].sort_values(["Role", "Name"])
        cards = "".join(_roster_card(pod, r.Name, r.Role if show_role else None)
                        for r in sub.itertuples(index=False))
        blocks.append(
            f'<div style="margin:10px 0 4px;color:{pod_color(pod)};font:800 0.82rem system-ui;'
            f'letter-spacing:1px;">\u25B8 POD {pod} \u00b7 {len(sub)} players</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:8px;">{cards}</div>')
    return "".join(blocks)


def page_about():
    st.markdown("### \U0001F4D8 About Competition")
    st.caption("How the game works \u2014 seasons and how points are scored.")

    with st.container(border=True):
        st.markdown("#### \U0001F5D3\uFE0F Seasons")
        st.markdown("**1 month = 1 Season.** There are **3 seasons**:")
        chips = "".join(
            f'<span style="display:inline-block;background:{SEASON_COLOR[s]}22;'
            f'color:{SEASON_COLOR[s]};border:1px solid {SEASON_COLOR[s]}88;border-radius:20px;'
            f'padding:4px 16px;margin:3px 8px 3px 0;font:800 0.9rem system-ui;">{s}</span>'
            for s in SEASON_NAMES)
        st.markdown(chips, unsafe_allow_html=True)
        mapping = ", ".join(f"{m} = {SEASON_NAMES[i]}"
                            for i, m in enumerate(logic.list_months(df)[:len(SEASON_NAMES)]))
        if mapping:
            st.caption("This dataset maps to: " + mapping)

    st.markdown("#### \U0001F3AE The three competitions")
    c1, c2, c3 = st.columns(3)
    with c1, st.container(border=True):
        st.markdown("**\U0001F4C5 Weekly**")
        st.markdown("- Compete **only within your role**.\n- Ranking = **raw points**.\n"
                    "- Owner vs Owner \u00b7 Peer 1 vs Peer 1 \u00b7 Peer 2 vs Peer 2.")
    with c2, st.container(border=True):
        st.markdown("**\U0001F4C8 Monthly (Season)**")
        st.markdown("- Compared **within your role** first.\n- Band **averages** \u2192 "
                    "**Z-scores** \u2192 a **0\u2013100** score.\n- Overall rank from the "
                    "fair score, not raw points.")
    with c3, st.container(border=True):
        st.markdown("**\U0001F5D3\uFE0F Quarterly**")
        st.markdown("- **Same fair method** as Monthly.\n- Uses **quarter-level** "
                    "aggregated data.\n- Rewards consistency across the whole quarter.")

    st.divider()
    st.markdown("#### \U0001F3AF Defect Bucketing Criteria")
    st.caption("A perfect deliverable rewards the Owner. Catching a real error rewards the "
               "peer who caught it \u2014 the higher the bucket, the more it's worth.")
    catalogs = (
        _error_catalog_html("\U0001F7E3 Brief Interpretation (highest)",
                            BUCKET_COLOR["Brief Interpretation Error"], BRIEF_ERRORS)
        + _error_catalog_html("\U0001F7E0 Major Errors",
                              BUCKET_COLOR["Major Error"], MAJOR_ERRORS)
        + _error_catalog_html("\U0001F7E1 Minor Errors",
                              BUCKET_COLOR["Minor Error"], MINOR_ERRORS))
    # One dark panel behind everything so the light text stays readable in BOTH themes
    # (dark theme is unchanged — the navy panel matches the roster cards on this page).
    st.markdown(
        '<div style="background:#0b1b2c;border:1px solid #ffffff14;border-radius:14px;'
        'padding:14px 16px;">' + _scoring_table_html()
        + '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:14px;">'
        + catalogs + '</div></div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("#### \U0001F579\uFE0F The Roster")
    st.caption("Every player, their role, and their unique game character "
               "(from player_profiles.csv \u2014 edit a row to change a role or avatar).")
    st.markdown(roster_gallery(PROFILE, show_role=True), unsafe_allow_html=True)


# ============================================================= OVERVIEW (arcade)
def _overview_header(pod_label, week_label, reviews, players, points, errors):
    chips = "".join(
        f'<div style="text-align:center;background:#0b1b2c;border:1px solid #ffffff1f;'
        f'border-radius:10px;padding:6px 12px;min-width:70px;">'
        f'<div style="color:{PARCHMENT};font:800 1.2rem system-ui;">{v}</div>'
        f'<div style="color:#8aa0b4;font:700 0.56rem system-ui;letter-spacing:1px;">{k}</div>'
        f'</div>'
        for k, v in [("REVIEWS", reviews), ("PLAYERS", players),
                     ("POINTS", points), ("ERRORS", errors)])
    return (
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'gap:12px;flex-wrap:wrap;background:linear-gradient(90deg,#0A1428,{BG_PANEL});'
        f'border:1px solid {GOLD}55;border-radius:14px;padding:12px 18px;margin-bottom:12px;">'
        f'<div><div style="color:{GOLD};font:800 0.7rem system-ui;letter-spacing:3px;">'
        f'\U0001F3C6 LOYALTY PACIFIC</div>'
        f'<div style="color:{PARCHMENT};font:800 1.5rem system-ui;letter-spacing:1px;'
        f'line-height:1.1;">WEEKLY STANDINGS</div>'
        f'<div style="color:{MUTED};font-size:0.8rem;">{pod_label} \u00b7 {week_label}</div></div>'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;">{chips}</div></div>')


def _stage(players):
    backdrop = avatars.backdrop_data_uri("arcade")
    maxp = max(float(players["points"].max()), 1.0)
    cols = []
    for _, r in players.iterrows():
        pod, name, rank = r["POD"], r["name"], int(r["rank"])
        ptsf = float(r["points"]); pts = fmt_pts(ptsf)
        color = BAR_SEQ[(rank - 1) % len(BAR_SEQ)]
        h = int(30 + max(ptsf, 0) / maxp * 175)
        av = av_uri(pod, name)
        plate = (medal(rank) + " " if rank <= 3 else "") + name
        cols.append(
            f'<div style="display:flex;flex-direction:column;align-items:center;'
            f'justify-content:flex-end;flex:1 1 0;min-width:0;">'
            f'<div style="font:800 15px system-ui;color:#fff;text-shadow:0 1px 2px #000a;">{pts}</div>'
            f'<img src="{av}" width="46" style="image-rendering:pixelated;'
            f'filter:drop-shadow(0 3px 2px #0007);margin-bottom:-3px;"/>'
            f'<div style="width:44px;height:{h}px;border-radius:6px 6px 0 0;'
            f'background:linear-gradient(180deg,{color},{_dark(color)});'
            f'box-shadow:0 0 0 2px #00000022,inset 0 2px 0 #ffffff66;display:flex;'
            f'justify-content:center;"><div style="color:#ffffffdd;font:800 11px system-ui;'
            f'margin-top:4px;">{rank}</div></div>'
            f'<div style="margin-top:5px;background:#0b1b2cd9;border:1px solid {color}99;'
            f'border-radius:8px;padding:2px 7px;color:{pod_color(pod)};font:800 11px system-ui;'
            f'white-space:nowrap;max-width:82px;overflow:hidden;text-overflow:ellipsis;">'
            f'{plate}</div></div>')
    return (
        f'<div style="position:relative;height:430px;border-radius:14px;overflow:hidden;'
        f'background-image:url({backdrop});background-size:cover;'
        f'background-position:center bottom;image-rendering:pixelated;'
        f'border:2px solid #0d2033;">'
        f'<div style="position:absolute;left:0;right:0;bottom:12px;display:flex;'
        f'align-items:flex-end;justify-content:space-around;gap:6px;padding:0 12px;">'
        f'{"".join(cols)}</div></div>')


def _champ_box(category, color, entry, band, tied=None):
    """entry = (pod, name, points) or None. tied = list of (pod, name) sharing #1."""
    if entry and entry[1]:
        pod, name, pts_s = entry[0], entry[1], fmt_pts(entry[2])
        av = av_uri(pod, name)
        name_c = pod_color(pod)
        pod_tag = f'<span style="color:{MUTED};font-size:0.6rem;"> {pod}</span>'
    else:
        pod, name, pts_s, name_c, pod_tag = "", DASH, DASH, PARCHMENT, ""
        av = avatars.avatar_data_uri("knight", "M", "?")

    tie_pill, sub = "", (f'<div style="color:{MUTED};font:600 0.72rem system-ui;">{band}</div>')
    if tied and len(tied) > 1:
        names = [t[1] for t in tied]
        shown = ", ".join(names[:4]) + (f" +{len(names) - 4}" if len(names) > 4 else "")
        tie_pill = (f'<span style="background:{color}2e;border:1px solid {color}88;color:{color};'
                    f'font:800 0.55rem system-ui;border-radius:9px;padding:1px 6px;margin-left:6px;'
                    f'white-space:nowrap;">\U0001F91D {len(names)}-WAY TIE</span>')
        sub = (f'<div style="color:{MUTED};font:600 0.66rem system-ui;white-space:nowrap;'
               f'overflow:hidden;text-overflow:ellipsis;" title="{", ".join(names)}">'
               f'\U0001F91D {band} \u00b7 {shown}</div>')
    return (
        f'<div style="border:1px solid {color}66;'
        f'background:linear-gradient(180deg,{color}22,{color}0c);border-radius:12px;'
        f'padding:8px 10px;margin-bottom:9px;display:flex;align-items:center;gap:10px;">'
        f'<img src="{av}" width="42" style="image-rendering:pixelated;'
        f'filter:drop-shadow(0 2px 2px #0007);"/>'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="color:{color};font:800 0.62rem system-ui;letter-spacing:1px;">{category}</div>'
        f'<div style="font:800 1rem system-ui;line-height:1.15;color:{name_c};'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}{pod_tag}{tie_pill}</div>'
        f'{sub}</div>'
        f'<div style="text-align:right;"><div style="color:{color};font:800 1.15rem system-ui;">'
        f'{pts_s}</div><div style="color:#8aa0b4;font:700 0.55rem system-ui;letter-spacing:1px;">'
        f'PTS</div></div></div>')


def _tie_group(dfin, rank_col):
    """Return ((pod,name,points) winner, [(pod,name), ...] all sharing the top rank)."""
    if dfin.empty:
        return None, None
    tr = dfin[rank_col].min()
    grp = dfin[dfin[rank_col] == tr].sort_values(["POD", "name"])
    first = grp.iloc[0]
    return ((first["POD"], first["name"], float(first["points"])),
            grp[["POD", "name"]].values.tolist())


def page_overview():
    reviews = len(fdf)
    players = logic.total_participants(fdf)
    points = int(fdf[[logic.POINT_COL[b] for b in BANDS]].to_numpy().sum())
    errors = int(fdf["has_error"].sum())
    st.markdown(_overview_header(POD_LABEL, sel_week, f"{reviews:,}", players,
                                 f"{points:,}", errors), unsafe_allow_html=True)
    if fdf.empty:
        no_data("No records for this POD and filter combination.")
        return

    wk_df = fdf[fdf["week_label"] == sel_week]
    mo_df = fdf[fdf["month_label"] == sel_month]
    q_df = fdf[fdf["quarter_label"] == sel_quarter]
    totals = logic.weekly_player_totals(wk_df)

    wb = logic.weekly_boards(wk_df)

    def band_top(b):
        return _tie_group(wb[wb["band"] == b], "rank")

    mlb = logic.fair_leaderboard(mo_df)
    qlb = logic.fair_leaderboard(q_df)
    o_entry, o_tie = band_top("Owner")
    p1_entry, p1_tie = band_top("Peer 1")
    p2_entry, p2_tie = band_top("Peer 2")
    m_entry, m_tie = _tie_group(mlb, "overall_rank")
    q_entry, q_tie = _tie_group(qlb, "overall_rank")

    def band_of(entry, lb):
        if not entry:
            return "\u2014"
        row = lb[(lb["POD"] == entry[0]) & (lb["name"] == entry[1])]
        return row.iloc[0]["band"] if not row.empty else "\u2014"

    stage_col, right_col = st.columns([2.6, 1], gap="medium")
    with stage_col:
        n = min(10, len(totals))
        if n == 0:
            no_data("No games recorded this week \u2014 try another week or POD.")
        else:
            st.markdown(_stage(totals.head(n)), unsafe_allow_html=True)
            st.caption(f"\U0001F3AE Top {n} by **total points earned this week** "
                       "(all roles combined). Owners score 10 per clean campaign; peers score "
                       "by catching errors \u2014 so with no errors this week, peers sit at 0.")
    with right_col:
        st.markdown("##### \U0001F3C5 Champions")
        html = (
            _champ_box("WEEKLY TOP OWNER", "#5B8DEF", o_entry, "Owner", o_tie)
            + _champ_box("WEEKLY TOP PEER 1", "#C8AA6E", p1_entry, "Peer 1", p1_tie)
            + _champ_box("WEEKLY TOP PEER 2", "#4CC9B0", p2_entry, "Peer 2", p2_tie)
            + _champ_box("MONTHLY TOP PERSON", "#9B5DE5", m_entry, band_of(m_entry, mlb), m_tie)
            + _champ_box("QUARTERLY TOP PERSON", "#FF7B54", q_entry, band_of(q_entry, qlb), q_tie))
        st.markdown(html, unsafe_allow_html=True)

    # ---- full detail: every participant this week (podium only shows top 10) ----
    with st.expander("\U0001F4CB Show detailed table \u2014 every participant this week"):
        det = logic.band_aggregate(wk_df)
        if det.empty:
            st.info("No participants recorded for this week.")
        else:
            det = det.rename(columns={"name": "Name", "band": "Role", "reviews": "Campaigns",
                                      "raw_points": "Raw", "points": "Pts/camp"})
            det = det.sort_values(["Role", "Pts/camp", "Name"], ascending=[True, False, True])
            st.caption("Each person in each role they played this week. **Pts/camp** = points "
                       "\u00f7 campaigns (the fair, normalised score); **Raw** = the un-normalised "
                       "total. Owners bank 10 per clean campaign; peers earn only by catching errors.")
            leaderboard_table(
                det[["Name", "POD", "Role", "Campaigns", "Raw", "Pts/camp"]],
                {"Name": st.column_config.TextColumn("Name"),
                 "POD": st.column_config.TextColumn("POD", width="small"),
                 "Role": st.column_config.TextColumn("Role"),
                 "Campaigns": st.column_config.NumberColumn("Campaigns", format="%d"),
                 "Raw": st.column_config.NumberColumn("Raw pts", format="%d"),
                 "Pts/camp": st.column_config.ProgressColumn(
                     "Pts / campaign", format="%.1f", min_value=0,
                     max_value=float(max(det["Pts/camp"].max(), 1)))})


# ============================================================= WEEKLY (arena lanes)
def _weekly_lane(band, sub):
    backdrop = avatars.backdrop_data_uri("stadium")
    bc = BAND_COLORS[band]
    emoji = BAND_META[band]["emoji"]
    cards = []
    for _, r in sub.iterrows():
        pod, name, pts, rank = r["POD"], r["name"], fmt_pts(r["points"]), int(r["rank"])
        cards.append(
            f'<div style="min-width:74px;text-align:center;flex:0 0 auto;">'
            f'<div style="color:#fff;font:800 12px system-ui;text-shadow:0 1px 2px #000;">{medal(rank)}</div>'
            f'<img src="{av_uri(pod, name)}" width="44" style="image-rendering:pixelated;'
            f'filter:drop-shadow(0 2px 2px #0007);"/>'
            f'<div style="color:{pod_color(pod)};font:800 12px system-ui;white-space:nowrap;">{name}</div>'
            f'<div style="margin-top:2px;display:inline-block;background:{bc}26;border:1px solid {bc}88;'
            f'color:{bc};font:800 11px system-ui;border-radius:10px;padding:1px 8px;">{pts}</div></div>')
    row = "".join(cards) or '<div style="color:#eee;padding:14px;">No players this week</div>'
    return (
        f'<div style="position:relative;border-radius:12px;overflow:hidden;border:1px solid {bc}55;'
        f'margin-bottom:10px;background-image:url({backdrop});background-size:cover;'
        f'background-position:center;image-rendering:pixelated;">'
        f'<div style="background:linear-gradient(90deg,#0A1428e6,#0A142855);padding:8px 12px;">'
        f'<span style="color:{bc};font:800 0.85rem system-ui;letter-spacing:1px;">'
        f'{emoji} {band.upper()} LEADERBOARD</span>'
        f'<span style="color:{MUTED};font-size:0.7rem;"> \u00b7 {len(sub)} players \u00b7 '
        f'ranked by weekly points</span></div>'
        f'<div style="display:flex;gap:10px;overflow-x:auto;padding:10px 12px 12px;'
        f'align-items:flex-end;">{row}</div></div>')


def page_weekly():
    st.markdown("### \U0001F4C5 Weekly Competition")
    st.caption(f"{POD_LABEL} \u00b7 {sel_week} \u00b7 **points per campaign** (a clean campaign "
               "= 10), ranked **within each role**. Scores are normalised by the number of "
               "campaigns each person handled, so doing more campaigns is never a penalty and "
               "everyone is compared fairly.")
    if fdf.empty:
        no_data("No records for this POD and filter combination.")
        return
    wk_df = fdf[fdf["week_label"] == sel_week]
    boards = logic.weekly_boards(wk_df)
    if boards.empty:
        no_data("No reviews match the current filters for this week.")
        return

    st.markdown("#### \U0001F3DF\uFE0F Weekly Arena")
    for band in BANDS:
        sub = boards[boards["band"] == band].sort_values(["rank", "name"])
        st.markdown(_weekly_lane(band, sub), unsafe_allow_html=True)
    st.caption("Scroll a lane sideways to see every player. "
               f"Name colour marks the POD (CP = {POD_COLOR['CP']}, NCP = {POD_COLOR['NCP']}).")

    with st.expander("\U0001F4CB Detailed weekly tables"):
        st.caption("Full roster for each role \u2014 everyone is listed, including anyone "
                   "with no activity this week (shown as 0).")
        roster = PROFILE if POD is None else PROFILE[PROFILE["POD"] == POD]
        cols = st.columns(3)
        for col, band in zip(cols, BANDS):
            with col:
                st.markdown(f"**{BAND_META[band]['emoji']} {band}**")
                board = boards[boards["band"] == band][["POD", "name", "points"]]
                rb = (roster[roster["Role"] == band][["POD", "Name"]]
                      .rename(columns={"Name": "name"}))
                full = rb.merge(board, on=["POD", "name"], how="left")
                full["points"] = full["points"].fillna(0).round(1)
                full = full.sort_values(["points", "name"], ascending=[False, True])
                full["rank"] = full["points"].rank(method="min", ascending=False).astype(int)
                full["medal"] = full["rank"].apply(medal)
                leaderboard_table(
                    full[["medal", "name", "POD", "points"]],
                    {"medal": st.column_config.TextColumn("Rank", width="small"),
                     "name": st.column_config.TextColumn("Name"),
                     "POD": st.column_config.TextColumn("POD", width="small"),
                     "points": st.column_config.ProgressColumn(
                         "Pts/camp", format="%.1f", min_value=0,
                         max_value=float(max(full["points"].max(), 1)))})

    st.divider()
    st.markdown("#### \U0001F4C8 Weekly points trend (by role)")
    trend = fdf.melt(id_vars=["week_label", "week_start"],
                     value_vars=[logic.POINT_COL[b] for b in BANDS],
                     var_name="band_col", value_name="pts")
    trend["Role"] = trend["band_col"].map({logic.POINT_COL[b]: b for b in BANDS})
    trend = (trend.dropna(subset=["Role"])
             .groupby(["week_start", "week_label", "Role"], as_index=False)["pts"].sum()
             .sort_values("week_start"))
    fig = px.line(trend, x="week_label", y="pts", color="Role", markers=True,
                  color_discrete_map=BAND_COLORS,
                  labels={"week_label": "", "pts": "Points"})
    fig.update_traces(line=dict(width=3), marker=dict(size=8))
    fig.update_layout(legend_title_text="Role")
    show(style_fig(fig, 420))

    st.divider()
    st.markdown("#### \U0001F4A5 Weekly Errors made (by player)")
    st.caption("Errors on each owner's deliverables this week (lower is better).")
    we = logic.weekly_errors_by_owner(wk_df)
    if we.empty:
        st.success("Clean sheet \u2014 no errors recorded this week!")
    else:
        we = we.sort_values("errors", ascending=False)
        fig = px.bar(we, x="name", y="errors", text="errors",
                     labels={"name": "", "errors": "Errors"})
        fig.update_traces(textposition="outside", cliponaxis=False,
                          marker_color="#E8734A")
        fig.update_layout(showlegend=False, yaxis_title="Errors")
        show(style_fig(fig, 320, legend=False))


# ============================================================= FAIR (shared)
FAIR_PALETTE = {
    "cosmos": ["#7B6CF6", "#4CC9B0", "#F4A259", "#59C3FF", "#B57BE0", "#F15BB5", "#00BBF9", "#9B5DE5"],
    "lava":   ["#FF7B2E", "#FFB03A", "#FF5252", "#FFD23F", "#E8734A", "#FF9F1C", "#D33F3F", "#FFC15E"],
}


def _fair_stage(rows, theme, title, accent):
    backdrop = avatars.backdrop_data_uri(theme)
    palette = FAIR_PALETTE.get(theme, BAR_SEQ)
    maxv = max(float(rows["z_score_points"].max()), 1.0)
    cols = []
    for _, r in rows.iterrows():
        pod, name = r["POD"], r["name"]
        z, rank = float(r["z_score_points"]), int(r["overall_rank"])
        raw = int(r.get("raw_points", r["points"]))
        color = palette[(rank - 1) % len(palette)]
        h = int(28 + z / maxv * 168)
        plate = (medal(rank) + " " if rank <= 3 else "") + name
        cols.append(
            f'<div style="display:flex;flex-direction:column;align-items:center;'
            f'justify-content:flex-end;flex:1 1 0;min-width:0;">'
            f'<div style="font:800 14px system-ui;color:#fff;text-shadow:0 1px 2px #000a;">{z:.0f}</div>'
            f'<img src="{av_uri(pod, name)}" width="44" style="image-rendering:pixelated;'
            f'filter:drop-shadow(0 3px 2px #0007);margin-bottom:-3px;"/>'
            f'<div style="width:42px;height:{h}px;border-radius:6px 6px 0 0;'
            f'background:linear-gradient(180deg,{color},{_dark(color)});'
            f'box-shadow:0 0 0 2px #00000030,inset 0 2px 0 #ffffff55;display:flex;'
            f'justify-content:center;"><div style="color:#ffffffdd;font:800 11px system-ui;'
            f'margin-top:4px;">{rank}</div></div>'
            f'<div style="margin-top:5px;background:#0b1b2cd9;border:1px solid {color}99;'
            f'border-radius:8px;padding:1px 6px;color:{pod_color(pod)};font:800 11px system-ui;'
            f'white-space:nowrap;max-width:80px;overflow:hidden;text-overflow:ellipsis;">'
            f'{plate}</div>'
            f'<div style="color:{MUTED};font:600 0.55rem system-ui;">{raw} pts</div></div>')
    return (
        f'<div style="position:relative;height:360px;border-radius:14px;overflow:hidden;'
        f'background-image:url({backdrop});background-size:cover;background-position:center bottom;'
        f'image-rendering:pixelated;border:2px solid #0d2033;">'
        f'<div style="position:absolute;top:0;left:0;right:0;background:linear-gradient(90deg,'
        f'#0A1428e6,#0A142866);padding:8px 14px;">'
        f'<span style="color:{accent};font:800 0.95rem system-ui;letter-spacing:2px;">{title}</span>'
        f'<span style="color:{MUTED};font-size:0.72rem;"> \u00b7 bars scale to the fair '
        f'0\u2013100 score</span></div>'
        f'<div style="position:absolute;left:0;right:0;bottom:12px;display:flex;'
        f'align-items:flex-end;justify-content:space-around;gap:6px;padding:0 12px;">'
        f'{"".join(cols)}</div></div>')


def _zscore_explainer():
    return (
        '<div style="border:1px solid #C8AA6E44;background:#0b1b2c;border-radius:12px;'
        'padding:12px 16px;">'
        '<div style="color:#C8AA6E;font:800 0.85rem system-ui;margin-bottom:4px;">'
        '\U0001F4A1 What is a Z-score (in plain English)?</div>'
        '<div style="color:#F0E6D2;font:500 0.86rem system-ui;line-height:1.5;">'
        'Different roles get different chances to score \u2014 an Owner can bank +10 on every '
        'clean job, while a Peer only scores when they catch something. Comparing their raw '
        'points head-to-head wouldn\u2019t be fair. A <b>Z-score</b> fixes that: it measures '
        '<b>how far above or below your own role\u2019s average</b> you are, in "steps" of the '
        'group\u2019s normal spread. Zero means dead average for your role; positive means above '
        'average; negative means below. We then stretch everyone\u2019s Z-scores onto a friendly '
        '<b>0\u2013100 fair score</b>. So a Peer 2 who crushes it versus other Peer 2s can '
        'outrank an Owner \u2014 because each person is judged against their <i>own</i> peer group, '
        'not across roles.</div></div>')


_FAIR_PHRASE = {"cosmos": "SEASON LOADING", "lava": "LEAGUE QUEST CHARGING"}


def _progress_banner(theme, accent, have, need, unit):
    """Arcade-style 'data is filling up' meter shown while a season/league isn't complete."""
    filled = max(0, min(have, need))
    phrase = _FAIR_PHRASE.get(theme, "LOADING")
    seg = "".join(
        f'<div style="flex:1;height:15px;border-radius:4px;'
        f'background:{accent if i < filled else "#ffffff14"};'
        f'box-shadow:{("0 0 10px " + accent) if i < filled else "none"};"></div>'
        for i in range(need))
    pct = int(round(filled / max(need, 1) * 100))
    return (
        f'<div style="position:relative;border-radius:14px;overflow:hidden;border:2px solid {accent}66;'
        f'background:linear-gradient(90deg,#0A1428,{BG_PANEL});padding:14px 18px;margin-bottom:12px;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;'
        f'flex-wrap:wrap;">'
        f'<div><div style="color:{accent};font:800 1.05rem system-ui;letter-spacing:2px;">'
        f'\U0001F579\uFE0F {phrase}\u2026 <span style="font-size:0.7rem;color:{PARCHMENT};'
        f'letter-spacing:1px;">DATA TO BE UPDATED</span></div>'
        f'<div style="color:{PARCHMENT};font:600 0.82rem system-ui;margin-top:2px;">'
        f'<b>{filled} of {need} {unit}s collected!</b> Standings below are provisional and '
        f'will power up as each {unit} lands. \U0001F4BE Updates occur every Friday.</div></div>'
        f'<div style="text-align:center;"><div style="color:{accent};font:800 1.9rem system-ui;'
        f'line-height:1;">{pct}%</div><div style="color:{MUTED};font:700 0.55rem system-ui;'
        f'letter-spacing:1px;">CHARGED</div></div></div>'
        f'<div style="display:flex;gap:6px;margin-top:11px;">{seg}</div></div>')


def _coming_soon(theme, accent, label, phrase_extra=""):
    """Gamified 'level locked / coming soon' hero for a period with no data yet."""
    backdrop = avatars.backdrop_data_uri(theme)
    return (
        f'<div style="position:relative;height:300px;border-radius:14px;overflow:hidden;'
        f'background-image:url({backdrop});background-size:cover;background-position:center;'
        f'image-rendering:pixelated;border:2px solid #0d2033;display:flex;align-items:center;'
        f'justify-content:center;text-align:center;">'
        f'<div style="background:#0A1428d9;border:2px solid {accent}88;border-radius:16px;'
        f'padding:22px 30px;max-width:78%;">'
        f'<div style="font-size:2.4rem;line-height:1;">\U0001F512</div>'
        f'<div style="color:{accent};font:800 1.3rem system-ui;letter-spacing:2px;margin-top:6px;">'
        f'LEVEL LOCKED \u2014 COMING SOON</div>'
        f'<div style="color:{PARCHMENT};font:600 0.9rem system-ui;margin-top:6px;">'
        f'{label} hasn\u2019t collected enough data yet. {phrase_extra}Keep updating the weekly '
        f'review log \u2014 this arena unlocks automatically once the data is in. \U0001F3AE</div>'
        f'</div></div>')


def render_fair(period_col, period_val, label, theme, title, accent, progress=None):
    if fdf.empty:
        no_data("No records for this POD and filter combination.")
        return
    lb = fair_cached(df, period_col, period_val, POD, CAMPS, TYPES, BUCKS)

    provisional = False
    if progress:
        have, need, unit = progress
        if have < need:
            provisional = True
            st.markdown(_progress_banner(theme, accent, have, need, unit),
                        unsafe_allow_html=True)

    if lb.empty:
        # never blank: a gamified 'coming soon' hero instead of an empty page
        st.markdown(_coming_soon(theme, accent, label), unsafe_allow_html=True)
        return

    n = min(8, len(lb))
    st.markdown(_fair_stage(lb.head(n), theme, title, accent), unsafe_allow_html=True)
    prov_tag = " \u00b7 \U0001F7E1 provisional (season still filling)" if provisional else ""
    st.caption(f"\U0001F3AE Top {n} by **fair score**{prov_tag}. Name colour marks the POD "
               f"(CP = {POD_COLOR['CP']}, NCP = {POD_COLOR['NCP']}).")

    st.markdown(f"**\U0001F3C6 Overall Fair Leaderboard \u2014 {label}** "
                "&nbsp; (ranked by the 0\u2013100 fair score)")
    top = lb.copy()
    top["medal"] = top["overall_rank"].apply(medal)
    leaderboard_table(
        top[["medal", "name", "POD", "band", "z_score_points", "points", "raw_points",
             "band_percentile"]],
        {"medal": st.column_config.TextColumn("Rank", width="small"),
         "name": st.column_config.TextColumn("Name"),
         "POD": st.column_config.TextColumn("POD", width="small"),
         "band": st.column_config.TextColumn("Band"),
         "z_score_points": st.column_config.ProgressColumn(
             "Fair score", format="%.1f", min_value=0, max_value=100,
             help="Band-normalised 0-100. The official ranking metric."),
         "points": st.column_config.NumberColumn("Pts/camp", format="%.1f",
             help="Points per campaign (normalised)."),
         "raw_points": st.column_config.NumberColumn("Raw", help="Un-normalised total."),
         "band_percentile": st.column_config.NumberColumn("Band %ile", format="%.0f")},
        height=420)

    with st.expander("Band-wise rankings"):
        tabs = st.tabs([f"{BAND_META[b]['emoji']} {b}" for b in BANDS])
        for tab, band in zip(tabs, BANDS):
            with tab:
                bsub = lb[lb["band"] == band].sort_values("band_rank").copy()
                bsub["medal"] = bsub["band_rank"].apply(medal)
                leaderboard_table(
                    bsub[["medal", "name", "POD", "z_score_points", "points",
                          "band_avg_points", "band_percentile"]],
                    {"medal": st.column_config.TextColumn("Band rank", width="small"),
                     "name": st.column_config.TextColumn("Name"),
                     "POD": st.column_config.TextColumn("POD", width="small"),
                     "z_score_points": st.column_config.NumberColumn("Fair", format="%.1f"),
                     "points": st.column_config.NumberColumn("Pts/camp", format="%.1f"),
                     "band_avg_points": st.column_config.NumberColumn("Band avg", format="%.1f"),
                     "band_percentile": st.column_config.NumberColumn("%ile", format="%.0f")},
                    height=320)

    st.divider()
    st.markdown("#### \U0001F514 Band performance \u2014 Bell curve")
    st.caption("Each curve is a role's spread of points-per-campaign: the peak is the typical "
               "score for that role, and a wider curve means more spread. Fair scoring measures "
               "where you sit on your own role's curve.")
    mom = logic.band_moments(lb)
    fig = go.Figure()
    any_curve = False
    for _, m in mom.iterrows():
        mu = float(m["mean"]); sd = float(m["std"])
        if sd <= 0:
            sd = max(mu * 0.15, 1.0)          # single/identical scores: gentle placeholder
        xs = np.linspace(mu - 4 * sd, mu + 4 * sd, 100)
        ys = np.exp(-0.5 * ((xs - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name=str(m["band"]),
            line=dict(color=BAND_COLORS[m["band"]], width=3),
            fill="tozeroy", fillcolor=_rgba(BAND_COLORS[m["band"]], 0.15),
            hovertemplate="%{x:.0f} pts<extra>" + str(m["band"]) + "</extra>"))
        any_curve = True
    if any_curve:
        fig.update_layout(legend_title_text="Role", xaxis_title="Points per campaign",
                          yaxis_title="Relative frequency")
        fig.update_yaxes(showticklabels=False)
        show(style_fig(fig, 340))
        st.markdown(
            '<div style="background:#0b1b2c;border:1px solid #C8AA6E44;border-radius:12px;'
            'padding:10px 14px;">'
            '<div style="color:#C8AA6E;font:800 0.8rem system-ui;margin-bottom:3px;">'
            '\U0001F50E How to read this curve</div>'
            '<div style="color:#F0E6D2;font:500 0.84rem system-ui;line-height:1.5;">'
            'Pick your role\u2019s coloured curve. The <b>tall middle</b> is the score a typical '
            'person in that role gets \u2014 most people land near there. Being to the '
            '<b>right of the peak</b> means you scored <b>above average</b> for your role '
            '(great!); to the <b>left</b> means below average. A <b>wide, flat</b> curve means '
            'scores are spread out; a <b>tall, narrow</b> curve means everyone scores about the '
            'same. Fair scoring simply measures how far right (or left) of your own curve\u2019s '
            'peak you are \u2014 so you\u2019re only ever compared with people doing your job.</div>'
            '</div>', unsafe_allow_html=True)
    else:
        no_data("Not enough data to draw the distribution.")
    st.markdown(_zscore_explainer(), unsafe_allow_html=True)


def page_monthly():
    st.markdown("### \U0001F4C8 Monthly Competition")
    st.caption(f"{POD_LABEL} \u00b7 {sel_month} \u00b7 **fair** ranking via band-wise "
               "Z-score. A season is complete once 4 weeks of data are in.")
    have = logic.weeks_in_month(fdf, sel_month)
    render_fair("month_label", sel_month, sel_month, "cosmos",
                "\U0001F31F SEASON LEADERBOARD", "#B57BE0", progress=(have, 4, "week"))


def page_quarterly():
    st.markdown("### \U0001F5D3\uFE0F Quarterly Competition")
    st.caption(f"{POD_LABEL} \u00b7 {sel_quarter} \u00b7 the grand quest \u2014 same Z-score "
               "fairness as Monthly. A league is complete once 3 months of data are in.")
    have = logic.months_in_quarter(fdf, sel_quarter)
    render_fair("quarter_label", sel_quarter, sel_quarter, "lava",
                "\U0001F48D LORD OF THE RANKINGS", "#FF9F1C", progress=(have, 3, "month"))


# ============================================================= PARTICIPANT
def page_participant():
    st.markdown("### \U0001F464 Participant Analytics")
    if fdf.empty:
        no_data("No records for this POD and filter combination.")
        return
    name, ppod = sel_player_name, sel_player_pod
    if not name:
        no_data("No players available for the current POD selection.")
        return
    pdf = fdf[fdf["POD"] == ppod] if ppod else fdf
    c = pod_color(ppod)
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:14px;margin:2px 0 8px;">'
        f'<img src="{av_uri(ppod, name)}" width="62" style="image-rendering:pixelated;'
        f'filter:drop-shadow(0 3px 3px #0008);"/>'
        f'<div><div style="font:800 1.5rem system-ui;color:{c};">{name}'
        f'<span style="color:{MUTED};font-size:0.8rem;"> \u00b7 POD {ppod}</span></div>'
        f'<div style="color:{PARCHMENT};font:700 0.85rem system-ui;">'
        f'{role_of(ppod, name)} \u00b7 plays as {av_name(ppod, name)}</div></div></div>',
        unsafe_allow_html=True)

    summ = logic.participant_summary(pdf, name)
    if summ["reviews"] == 0:
        no_data(f"{name} has no activity in POD {ppod} for the current filters.")
        return

    m = st.columns(4)
    m[0].metric("Total points", f"{summ['total']:,}")
    errors_made = int(pdf[(pdf["Owner"] == name.upper()) & (pdf["has_error"])].shape[0])
    m[1].metric("Total Errors Made", errors_made,
                help="Deliverables owned by this person that a peer flagged as an error.")
    lb = fair_cached(df, "month_label", sel_month, POD, CAMPS, TYPES, BUCKS)
    mine = lb[(lb["name"] == name.upper()) & (lb["POD"] == ppod)]
    best_pct = float(mine["band_percentile"].max()) if not mine.empty else 0.0
    m[2].metric(f"Best band %ile \u00b7 {sel_month}",
                f"{best_pct:.0f}" if not mine.empty else DASH)
    m[3].metric("Primary role", role_of(ppod, name),
                help="This player's role from player_profiles.csv.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Weekly performance** (points earned, any role)")
        w = logic.participant_points_by(pdf, name, "week_label")
        wk_order = pdf[["week_label", "week_start"]].drop_duplicates()
        w = w.merge(wk_order, on="week_label", how="left").sort_values("week_start")
        if w.empty:
            st.info("No activity for this participant under the current filters.")
        else:
            fig = px.line(w, x="week_label", y="points", markers=True,
                          labels={"week_label": "", "points": "Points"})
            fig.update_traces(line_color=GOLD, marker_color=GOLD)
            show(style_fig(fig, 300, legend=False))
    with c2:
        st.markdown("**Monthly performance**")
        mth = logic.participant_points_by(pdf, name, "month_label")
        mo_order = pdf[["month_label", "month_key"]].drop_duplicates().sort_values("month_key")
        mth = mo_order.merge(mth, on="month_label", how="left").fillna({"points": 0})
        fig = px.bar(mth, x="month_label", y="points", text="points",
                     labels={"month_label": "", "points": "Points"})
        fig.update_traces(marker_color=GOLD, textposition="outside", cliponaxis=False)
        show(style_fig(fig, 300, legend=False))

    st.markdown("**Band average comparison** " + f"({sel_month})")
    rows = []
    for band in BANDS:
        me = mine[mine["band"] == band]
        if not me.empty:
            rows.append({"band": band, "who": "You", "points": int(me.iloc[0]["points"])})
            rows.append({"band": band, "who": "Band average",
                         "points": float(me.iloc[0]["band_avg_points"])})
    if rows:
        comp = pd.DataFrame(rows)
        fig = px.bar(comp, x="band", y="points", color="who", barmode="group",
                     color_discrete_map={"You": GOLD, "Band average": "#5B8DEF"},
                     labels={"band": "", "points": "Points"})
        fig.update_layout(legend_title_text="")
        show(style_fig(fig, 300))
    else:
        st.caption("No band-level entries for this participant in the selected month.")

    st.divider()
    st.markdown("#### \U0001F579\uFE0F All Players")
    st.caption("Every player with their unique game character and its name (archetype).")
    st.markdown(roster_gallery(PROFILE, show_role=False), unsafe_allow_html=True)


# ============================================================= ERROR ANALYTICS
def page_error():
    st.markdown("### \U0001F41E Error Analytics")
    st.caption(f"{POD_LABEL}"
               + (" \u00b7 filtered" if (CAMPS or TYPES or BUCKS) else ""))
    if fdf.empty:
        no_data("No records for this POD and filter combination.")
        return
    err = fdf[fdf["has_error"]]
    rate = (len(err) / len(fdf) * 100) if len(fdf) else 0
    m = st.columns(3)
    m[0].metric("Total Errors", f"{len(err):,}")
    m[1].metric("Error rate", f"{rate:.1f}%")
    m[2].metric("Clean reviews", f"{len(fdf) - len(err):,}")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Bucket distribution**")
        bd = logic.bucket_distribution(fdf)
        bd = bd[bd["count"] > 0]                      # never plot empty slices
        fig = px.pie(bd, names="Bucket", values="count", hole=0.5,
                     color="Bucket", color_discrete_map=BUCKET_COLOR)
        fig.update_traces(textinfo="percent", sort=False)
        fig.update_layout(legend_title_text="Bucket")
        show(style_fig(fig, 300))
    with c2:
        st.markdown("**Errors over time** (by week)")
        et = logic.errors_over_time(fdf)
        if et.empty:
            st.info("No errors under the current filters.")
        else:
            fig = px.line(et, x="week_label", y="errors", markers=True,
                          labels={"week_label": "", "errors": "Errors"})
            fig.update_traces(line_color="#E8734A", marker_color="#E8734A")
            show(style_fig(fig, 300, legend=False))

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Owner-wise errors** (errors on their work)")
        oe = logic.owner_errors(fdf)
        if oe.empty:
            st.info("No errors under the current filters.")
        else:
            fig = px.bar(oe, x="errors", y="Owner", orientation="h",
                         labels={"errors": "Errors", "Owner": ""})
            fig.update_traces(marker_color="#5B8DEF")
            fig.update_yaxes(autorange="reversed")
            show(style_fig(fig, 360, legend=False))
    with c4:
        st.markdown("**Peer-wise catches** (errors each peer caught)")
        pc = logic.peer_catches(fdf)
        if pc.empty:
            st.info("No catches under the current filters.")
        else:
            fig = px.bar(pc, x="name", y="catches", text="catches",
                         labels={"name": "", "catches": "Catches"})
            fig.update_traces(marker_color="#4CC9B0", textposition="outside",
                              cliponaxis=False)
            mx = int(pc["catches"].max())
            fig.update_yaxes(range=[0, mx * 1.20 + 1])   # headroom so labels aren't clipped
            show(style_fig(fig, 360, legend=False))


# ---------------------------------------------------------------- router
PAGES = {
    "\U0001F3E0 Overview": page_overview,
    "\U0001F4C5 Weekly Competition": page_weekly,
    "\U0001F4C8 Monthly Competition": page_monthly,
    "\U0001F5D3\uFE0F Quarterly Competition": page_quarterly,
    "\U0001F464 Participant Analytics": page_participant,
    "\U0001F41E Error Analytics": page_error,
    "\U0001F4D8 About Competition": page_about,
}
PAGES[page]()