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

import pandas as pd
import plotly.express as px
import streamlit as st

import logic
import avatars
from logic import BANDS, BAND_META, BUCKETS, BUCKET_COLOR

DATA_PATH = Path(__file__).parent / "review_log.csv"

GOLD, PARCHMENT, MUTED, BG_PANEL = "#C8AA6E", "#F0E6D2", "#A09B8C", "#102A43"
DASH = "\u2014"
BAND_COLORS = {b: BAND_META[b]["color"] for b in BANDS}
SEQ = [GOLD, "#5B8DEF", "#4CC9B0", "#B57BE0", "#E8734A", "#F4CE00"]
BAR_SEQ = ["#F4CE00", "#59C3FF", "#FF6B6B", "#3FA34D", "#9B5DE5",
           "#FF9F1C", "#2EC4B6", "#F15BB5", "#00BBF9", "#E86A17"]


def _dark(hex_color: str, f: float = 0.66) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"

st.set_page_config(page_title="QC Competition \u2014 League of Loyalty",
                   page_icon="\U0001F3C6", layout="wide",
                   initial_sidebar_state="expanded")


# ---------------------------------------------------------------- data (cached)
@st.cache_data(ttl=3600, show_spinner=False)
def get_data() -> pd.DataFrame:
    """Load + prepare the CSV. Cached so filters/interactions never re-read disk."""
    return logic.load_and_prepare(str(DATA_PATH))


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
        margin=dict(l=10, r=10, t=44, b=10), height=height,
        title_font=dict(color=PARCHMENT, size=15),
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
pods = logic.list_pods(df)
months, weeks, quarters = logic.list_months(df), logic.list_weeks(df), logic.list_quarters(df)
campaigns_all, types_all = logic.list_campaigns(df), logic.list_types(df)
participants_all = logic.list_participants(df)

with st.sidebar:
    st.markdown(f'<div style="font-weight:800;color:{GOLD};font-size:1.1rem;">'
                f'\U0001F3C6 League of Loyalty</div>', unsafe_allow_html=True)
    st.caption("QC competition dashboard")
    st.divider()

    page = st.radio("Go to", [
        "\U0001F3E0 Overview", "\U0001F4C5 Weekly Competition",
        "\U0001F4C8 Monthly Competition", "\U0001F5D3\uFE0F Quarterly Competition",
        "\U0001F464 Participant Analytics", "\U0001F41E Error Analytics",
        "\U0001F4D8 About Competition"],
        label_visibility="collapsed")

    st.divider()
    # POD is the highest-level filter: it selects the base dataset before anything else.
    pod_options = ["All PODs"] + pods
    sel_pod = st.selectbox("\U0001F3E2 POD (team)", pod_options, index=0,
                           help="Highest-level filter. Everything below applies within "
                                "the selected POD.")

    st.markdown("**Filters**")
    sel_month = st.selectbox("Month", months, index=len(months) - 1,
                             help="Drives the Monthly competition and monthly KPIs.")
    sel_week = st.selectbox("Week", weeks, index=len(weeks) - 1,
                            help="A week = the Monday-commencing period. Drives Weekly.")
    sel_quarter = st.selectbox("Quarter", quarters, index=len(quarters) - 1,
                               help="Drives the Quarterly competition.")
    sel_campaign = st.multiselect("Campaign", campaigns_all, help="Empty = all campaigns.")
    sel_type = st.multiselect("Type", types_all, help="Empty = all types.")
    sel_bucket = st.multiselect("Error Bucket", BUCKETS, help="Empty = all buckets.")
    sel_participant = st.selectbox("Participant", participants_all,
                                   help="Used on Participant Analytics.")
    top_n = st.slider("Top N", 3, 25, 10, help="Rows shown per leaderboard.")

    st.divider()
    st.markdown("**Bands**")
    for b in BANDS:
        st.markdown(band_badge(b), unsafe_allow_html=True)

    st.divider()
    st.caption(f"Data updated: {df['Date'].max():%d %b %Y}")
    # Refresh is intentionally DISABLED for now (kept in place, same look).
    # To restore later: on click call `st.cache_data.clear(); st.rerun()`.
    st.button("\U0001F504 Refresh data", use_container_width=True)


# ---- single filtering pipeline: POD -> campaign/type/bucket (period per page) --
POD = None if sel_pod == "All PODs" else sel_pod
CAMPS = tuple(sorted(sel_campaign))
TYPES = tuple(sorted(sel_type))
BUCKS = tuple(sorted(sel_bucket))
fdf = logic.filter_data(df, POD, CAMPS, TYPES, BUCKS)  # base frame every page consumes
POD_LABEL = sel_pod


SEASON_NAMES = ["Platinum", "Gold", "Diamond"]
SEASON_COLOR = {"Platinum": "#7FB2D9", "Gold": "#E8C35A", "Diamond": "#7BE0D0"}
LEAGUE_NAMES = {1: "Vanguard League", 2: "Tempest League",
                3: "Ascension League", 4: "Apex League"}
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
                      for c, a in [("Event / Bucket", "left"), ("Owner", "center"),
                                   ("Peer 1", "center"), ("Peer 2", "center")]) + "</tr>")
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
    return (f'<div style="border:1px solid {color}55;background:{color}12;border-radius:12px;'
            f'padding:10px 12px;height:100%;">'
            f'<div style="color:{color};font:800 0.85rem system-ui;letter-spacing:0.5px;'
            f'margin-bottom:4px;">{title}</div>'
            f'<ul style="margin:0;padding-left:18px;">{lis}</ul></div>')


def page_about():
    st.markdown("### \U0001F4D8 About Competition")
    st.caption("How the game works \u2014 seasons, leagues, and how points are scored.")

    # ---- Seasons & Leagues ----
    a, b = st.columns(2)
    with a, st.container(border=True):
        st.markdown("#### \U0001F5D3\uFE0F Seasons")
        st.markdown("**1 month = 1 Season.** There are **3 seasons**:")
        chips = "".join(
            f'<span style="display:inline-block;background:{SEASON_COLOR[s]}22;'
            f'color:{SEASON_COLOR[s]};border:1px solid {SEASON_COLOR[s]}88;border-radius:20px;'
            f'padding:4px 14px;margin:3px 6px 3px 0;font:800 0.85rem system-ui;">{s}</span>'
            for s in SEASON_NAMES)
        st.markdown(chips, unsafe_allow_html=True)
        mapping = ", ".join(f"{m} = {SEASON_NAMES[i]}"
                            for i, m in enumerate(logic.list_months(df)[:3]))
        if mapping:
            st.caption("This dataset: " + mapping)
    with b, st.container(border=True):
        st.markdown("#### \U0001F3C5 Leagues")
        st.markdown("**1 quarter = 1 League.** There are **4 leagues** across the year:")
        chips = "".join(
            f'<span style="display:inline-block;background:{GOLD}1e;color:{GOLD};'
            f'border:1px solid {GOLD}77;border-radius:20px;padding:4px 14px;'
            f'margin:3px 6px 3px 0;font:800 0.85rem system-ui;">Q{q} \u00b7 {n}</span>'
            for q, n in LEAGUE_NAMES.items())
        st.markdown(chips, unsafe_allow_html=True)
        st.caption("Each league aggregates that quarter's results into one fair ranking.")

    st.divider()
    # ---- The three competitions ----
    st.markdown("#### \U0001F3AE The three competitions")
    c1, c2, c3 = st.columns(3)
    with c1, st.container(border=True):
        st.markdown("**\U0001F4C5 Weekly**")
        st.markdown("- Compete **only within your role**.\n- Ranking = **raw points**.\n"
                    "- Owner vs Owner \u00b7 Peer 1 vs Peer 1 \u00b7 Peer 2 vs Peer 2.")
    with c2, st.container(border=True):
        st.markdown("**\U0001F4C8 Monthly (Season)**")
        st.markdown("- Compared **within your role** first.\n- Band **averages** \u2192 "
                    "**Z-scores** \u2192 a **0\u2013100** score.\n- Overall rank from "
                    "`z_score_points` (fair across roles).")
    with c3, st.container(border=True):
        st.markdown("**\U0001F3C5 Quarterly (League)**")
        st.markdown("- **Same fair method** as Monthly.\n- Uses **quarter-level** "
                    "aggregated data.\n- Rewards consistency all league long.")

    st.divider()
    # ---- Defect Bucketing Criteria ----
    st.markdown("#### \U0001F3AF Defect Bucketing Criteria")
    st.caption("A perfect deliverable rewards the Owner. Catching a real error rewards the "
               "peer who caught it \u2014 the higher the bucket, the more it's worth.")
    st.markdown(_scoring_table_html(), unsafe_allow_html=True)
    st.markdown("")
    e1, e2, e3 = st.columns(3)
    with e1:
        st.markdown(_error_catalog_html("\U0001F7E3 Brief Interpretation (highest)",
                    BUCKET_COLOR["Brief Interpretation Error"], BRIEF_ERRORS),
                    unsafe_allow_html=True)
    with e2:
        st.markdown(_error_catalog_html("\U0001F7E0 Major Errors",
                    BUCKET_COLOR["Major Error"], MAJOR_ERRORS), unsafe_allow_html=True)
    with e3:
        st.markdown(_error_catalog_html("\U0001F7E1 Minor Errors",
                    BUCKET_COLOR["Minor Error"], MINOR_ERRORS), unsafe_allow_html=True)


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
        f'\U0001F3C6 SERVICE DESK CUP</div>'
        f'<div style="color:{PARCHMENT};font:800 1.5rem system-ui;letter-spacing:1px;'
        f'line-height:1.1;">WEEKLY ARCADE STANDINGS</div>'
        f'<div style="color:{MUTED};font-size:0.8rem;">{pod_label} \u00b7 {week_label}</div></div>'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;">{chips}</div></div>')


def _stage(players):
    backdrop = avatars.backdrop_data_uri()
    maxp = max(int(players["points"].max()), 1)
    cols = []
    for _, r in players.iterrows():
        name, pts, rank = r["name"], int(r["points"]), int(r["rank"])
        color = BAR_SEQ[(rank - 1) % len(BAR_SEQ)]
        h = int(30 + max(pts, 0) / maxp * 175)
        av = avatars.avatar_data_uri(name)
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
            f'border-radius:8px;padding:2px 7px;color:{PARCHMENT};font:700 11px system-ui;'
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


def _champ_box(category, color, pair, band):
    if pair and pair[0]:
        name, pts_s, av = pair[0], str(pair[1]), avatars.avatar_data_uri(pair[0])
    else:
        name, pts_s, av = DASH, DASH, avatars.avatar_data_uri("?")
    return (
        f'<div style="border:1px solid {color}66;'
        f'background:linear-gradient(180deg,{color}22,{color}0c);border-radius:12px;'
        f'padding:8px 10px;margin-bottom:9px;display:flex;align-items:center;gap:10px;">'
        f'<img src="{av}" width="42" style="image-rendering:pixelated;'
        f'filter:drop-shadow(0 2px 2px #0007);"/>'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="color:{color};font:800 0.62rem system-ui;letter-spacing:1px;">{category}</div>'
        f'<div style="color:{PARCHMENT};font:800 1rem system-ui;line-height:1.15;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>'
        f'<div style="color:{MUTED};font:600 0.72rem system-ui;">{band}</div></div>'
        f'<div style="text-align:right;"><div style="color:{color};font:800 1.15rem system-ui;">'
        f'{pts_s}</div><div style="color:#8aa0b4;font:700 0.55rem system-ui;letter-spacing:1px;">'
        f'PTS</div></div></div>')


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
        s = wb[wb["band"] == b].sort_values("rank")
        return (s.iloc[0]["name"], int(s.iloc[0]["points"])) if not s.empty else None

    mc = logic.monthly_champion(mo_df)
    ql = logic.fair_leaderboard(q_df)
    qtop = ql.iloc[0] if not ql.empty else None

    stage_col, right_col = st.columns([2.6, 1], gap="medium")
    with stage_col:
        n = min(10, len(totals))
        if n == 0:
            no_data("No games recorded this week \u2014 try another week or POD.")
        else:
            st.markdown(_stage(totals.head(n)), unsafe_allow_html=True)
            st.caption(f"\U0001F3AE Top {n} by **total points earned this week** "
                       "(all roles combined). Bars scale to weekly points.")
    with right_col:
        st.markdown("##### \U0001F3C5 Champions")
        html = (
            _champ_box("WEEKLY TOP OWNER", "#5B8DEF", band_top("Owner"), "Owner")
            + _champ_box("WEEKLY TOP PEER 1", "#C8AA6E", band_top("Peer 1"), "Peer 1")
            + _champ_box("WEEKLY TOP PEER 2", "#4CC9B0", band_top("Peer 2"), "Peer 2")
            + _champ_box("MONTHLY TOP PERSON", "#9B5DE5",
                         (mc["name"], mc["points"]) if mc else None,
                         mc["band"] if mc else "\u2014")
            + _champ_box("QUARTERLY TOP PERSON", "#FF7B54",
                         (qtop["name"], int(qtop["points"])) if qtop is not None else None,
                         qtop["band"] if qtop is not None else "\u2014"))
        st.markdown(html, unsafe_allow_html=True)


# ============================================================= WEEKLY
def page_weekly():
    st.markdown("### \U0001F4C5 Weekly Competition")
    st.caption(f"{POD_LABEL} \u00b7 {sel_week} \u00b7 raw points, ranked **within each "
               "role**. No Z-score here \u2014 this is the simple weekly race.")
    if fdf.empty:
        no_data("No records for this POD and filter combination.")
        return
    wk_df = fdf[fdf["week_label"] == sel_week]
    boards = logic.weekly_boards(wk_df)
    if boards.empty:
        no_data("No reviews match the current filters for this week.")
        return

    cols = st.columns(3)
    for col, band in zip(cols, BANDS):
        with col:
            st.markdown(band_badge(band), unsafe_allow_html=True)
            sub = (boards[boards["band"] == band]
                   .sort_values(["rank", "name"]).head(top_n).copy())
            sub["medal"] = sub["rank"].apply(medal)
            leaderboard_table(
                sub[["medal", "name", "points", "reviews"]],
                {"medal": st.column_config.TextColumn("Rank", width="small"),
                 "name": st.column_config.TextColumn("Name"),
                 "points": st.column_config.ProgressColumn(
                     "Points", format="%d", min_value=0,
                     max_value=int(max(sub["points"].max(), 1))),
                 "reviews": st.column_config.NumberColumn("Reviews", width="small")})

    st.divider()
    left, right = st.columns(2)
    with left:
        st.markdown("**Weekly points trend** (by band)")
        trend = (fdf.melt(id_vars=["week_label", "week_start"],
                          value_vars=[logic.POINT_COL[b] for b in BANDS],
                          var_name="band_col", value_name="pts"))
        trend["band"] = trend["band_col"].map({logic.POINT_COL[b]: b for b in BANDS})
        trend = (trend.groupby(["week_start", "week_label", "band"], as_index=False)["pts"]
                 .sum().sort_values("week_start"))
        fig = px.line(trend, x="week_label", y="pts", color="band", markers=True,
                      color_discrete_map=BAND_COLORS)
        show(style_fig(fig, 320))
    with right:
        st.markdown("**Weekly participation summary**")
        part = pd.DataFrame({
            "band": BANDS,
            "participants": [int(wk_df[logic.NAME_COL[b]].dropna().nunique()) for b in BANDS],
            "reviews": [int(wk_df[logic.NAME_COL[b]].dropna().shape[0]) for b in BANDS],
        })
        fig = px.bar(part, x="band", y="reviews", color="band", text="reviews",
                     color_discrete_map=BAND_COLORS)
        fig.update_traces(textposition="outside")
        show(style_fig(fig, 320, legend=False))
        st.caption("Participants active per role this week: " +
                   " \u00b7 ".join(f"{b}: {n}" for b, n in
                                   zip(part["band"], part["participants"])))


# ============================================================= FAIR (shared)
def render_fair(period_col, period_val, label):
    if fdf.empty:
        no_data("No records for this POD and filter combination.")
        return
    lb = fair_cached(df, period_col, period_val, POD, CAMPS, TYPES, BUCKS)
    if lb.empty:
        no_data("No reviews match the current filters for this period.")
        return
    top = lb.head(top_n).copy()
    top["medal"] = top["overall_rank"].apply(medal)

    st.markdown(f"**\U0001F3C6 Overall Fair Leaderboard \u2014 {label}** "
                "&nbsp; (ranked by z_score_points)")
    leaderboard_table(
        top[["medal", "name", "band", "z_score_points", "points",
             "band_percentile", "raw_rank"]],
        {"medal": st.column_config.TextColumn("Rank", width="small"),
         "name": st.column_config.TextColumn("Name"),
         "band": st.column_config.TextColumn("Band"),
         "z_score_points": st.column_config.ProgressColumn(
             "Fair score", format="%.1f", min_value=0, max_value=100,
             help="Band-normalised 0-100. The official ranking metric."),
         "points": st.column_config.NumberColumn("Raw pts", help="Transparency only."),
         "band_percentile": st.column_config.NumberColumn("Band %ile", format="%.0f"),
         "raw_rank": st.column_config.NumberColumn("Raw rank")})

    with st.expander("Band-wise rankings"):
        tabs = st.tabs([f"{BAND_META[b]['emoji']} {b}" for b in BANDS])
        for tab, band in zip(tabs, BANDS):
            with tab:
                bsub = lb[lb["band"] == band].sort_values("band_rank").head(top_n).copy()
                bsub["medal"] = bsub["band_rank"].apply(medal)
                leaderboard_table(
                    bsub[["medal", "name", "z_score_points", "points",
                          "band_avg_points", "band_percentile"]],
                    {"medal": st.column_config.TextColumn("Band rank", width="small"),
                     "name": st.column_config.TextColumn("Name"),
                     "z_score_points": st.column_config.NumberColumn("Fair", format="%.1f"),
                     "points": st.column_config.NumberColumn("Raw pts"),
                     "band_avg_points": st.column_config.NumberColumn("Band avg", format="%.1f"),
                     "band_percentile": st.column_config.NumberColumn("%ile", format="%.0f")})

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Z-score distribution** (fair points by band)")
        fig = px.histogram(lb, x="z_score_points", color="band", nbins=20,
                           color_discrete_map=BAND_COLORS, barmode="overlay", opacity=0.7)
        show(style_fig(fig, 300))
    with c2:
        st.markdown("**Raw points vs Fair points**")
        fig = px.scatter(lb, x="points", y="z_score_points", color="band",
                         hover_name="name", color_discrete_map=BAND_COLORS)
        fig.update_traces(marker=dict(size=11, line=dict(width=1, color="#0A1428")))
        show(style_fig(fig, 300))

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Raw rank vs Fair rank**")
        st.caption("Points below the diagonal climbed under fair scoring; above it, fell.")
        fig = px.scatter(lb, x="raw_rank", y="overall_rank", color="band",
                         hover_name="name", color_discrete_map=BAND_COLORS)
        fig.update_traces(marker=dict(size=11, line=dict(width=1, color="#0A1428")))
        mx = int(max(lb["raw_rank"].max(), lb["overall_rank"].max()))
        fig.add_shape(type="line", x0=1, y0=1, x1=mx, y1=mx,
                      line=dict(color=MUTED, dash="dot"))
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(autorange="reversed")
        show(style_fig(fig, 320))
    with c4:
        st.markdown("**Band performance summary**")
        summ = (lb.groupby("band")
                .agg(participants=("name", "nunique"),
                     avg_points=("points", "mean"),
                     std_points=("band_std_points", "first")).reset_index())
        summ["avg_points"] = summ["avg_points"].round(1)
        leaderboard_table(
            summ, {"band": st.column_config.TextColumn("Band"),
                   "participants": st.column_config.NumberColumn("People"),
                   "avg_points": st.column_config.NumberColumn("Avg raw pts", format="%.1f"),
                   "std_points": st.column_config.NumberColumn("Std dev", format="%.2f")})
        st.caption("Fair scoring compares each person against their own band's average "
                   "and spread \u2014 not across bands.")


def page_monthly():
    st.markdown("### \U0001F4C8 Monthly Competition")
    st.caption(f"{POD_LABEL} \u00b7 {sel_month} \u00b7 **fair** ranking via band-wise "
               "Z-score (z_score_points). Raw points shown for transparency only.")
    render_fair("month_label", sel_month, sel_month)


def page_quarterly():
    st.markdown("### \U0001F5D3\uFE0F Quarterly Competition")
    st.caption(f"{POD_LABEL} \u00b7 {sel_quarter} \u00b7 same Z-score fairness as Monthly, "
               "aggregated across the quarter.")
    render_fair("quarter_label", sel_quarter, sel_quarter)


# ============================================================= PARTICIPANT
def page_participant():
    st.markdown("### \U0001F464 Participant Analytics")
    if fdf.empty:
        no_data("No records for this POD and filter combination.")
        return
    name = sel_participant
    st.markdown(f"**{name}** &nbsp;\u00b7&nbsp; {POD_LABEL}", unsafe_allow_html=True)
    summ = logic.participant_summary(fdf, name)
    if summ["reviews"] == 0:
        no_data(f"{name} has no activity in {POD_LABEL} for the current filters.")
        return

    m = st.columns(4)
    m[0].metric("Total points", f"{summ['total']:,}")
    errors_made = int(fdf[(fdf["Owner"] == name.upper()) & (fdf["has_error"])].shape[0])
    m[1].metric("Total Errors Made", errors_made,
                help="Deliverables owned by this person that a peer flagged as an error.")
    # band percentile + comparison from the selected month's fair board
    lb = fair_cached(df, "month_label", sel_month, POD, CAMPS, TYPES, BUCKS)
    mine = lb[lb["name"] == name.upper()]
    best_pct = float(mine["band_percentile"].max()) if not mine.empty else 0.0
    m[2].metric(f"Best band %ile \u00b7 {sel_month}",
                f"{best_pct:.0f}" if not mine.empty else DASH)
    primary = max(summ["by_band"], key=lambda b: summ["by_band"][b]["points"])
    m[3].metric("Primary role", primary,
                help="Role where this participant earns the most points.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Weekly performance** (points earned, any role)")
        w = logic.participant_points_by(fdf, name, "week_label")
        wk_order = fdf[["week_label", "week_start"]].drop_duplicates()
        w = w.merge(wk_order, on="week_label", how="left").sort_values("week_start")
        if w.empty:
            st.info("No activity for this participant under the current filters.")
        else:
            fig = px.line(w, x="week_label", y="points", markers=True)
            fig.update_traces(line_color=GOLD, marker_color=GOLD)
            show(style_fig(fig, 300, legend=False))
    with c2:
        st.markdown("**Monthly performance**")
        mth = logic.participant_points_by(fdf, name, "month_label")
        mo_order = fdf[["month_label", "month_key"]].drop_duplicates().sort_values("month_key")
        mth = mo_order.merge(mth, on="month_label", how="left").fillna({"points": 0})
        fig = px.bar(mth, x="month_label", y="points", text="points")
        fig.update_traces(marker_color=GOLD, textposition="outside")
        show(style_fig(fig, 300, legend=False))

    st.markdown("**Band average comparison** " + f"({sel_month})")
    rows = []
    for band in BANDS:
        me = mine[mine["band"] == band]
        if not me.empty:
            rows.append({"band": band, "who": "You",
                         "points": int(me.iloc[0]["points"])})
            rows.append({"band": band, "who": "Band average",
                         "points": float(me.iloc[0]["band_avg_points"])})
    if rows:
        comp = pd.DataFrame(rows)
        fig = px.bar(comp, x="band", y="points", color="who", barmode="group",
                     color_discrete_map={"You": GOLD, "Band average": "#5B8DEF"})
        show(style_fig(fig, 300))
    else:
        st.caption("No band-level entries for this participant in the selected month.")


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
        fig = px.pie(bd, names="Bucket", values="count", hole=0.5,
                     color="Bucket", color_discrete_map=BUCKET_COLOR)
        show(style_fig(fig, 300))
    with c2:
        st.markdown("**Errors over time** (by week)")
        et = logic.errors_over_time(fdf)
        if et.empty:
            st.info("No errors under the current filters.")
        else:
            fig = px.line(et, x="week_label", y="errors", markers=True)
            fig.update_traces(line_color="#E8734A", marker_color="#E8734A")
            show(style_fig(fig, 300, legend=False))

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Campaign-wise errors**")
        ce = logic.campaign_errors(fdf).head(top_n)
        fig = px.bar(ce, x="errors", y="Campaign Name", orientation="h")
        fig.update_traces(marker_color=GOLD)
        fig.update_yaxes(autorange="reversed")
        show(style_fig(fig, 320, legend=False))
    with c4:
        st.markdown("**Owner-wise errors** (errors on their work)")
        oe = logic.owner_errors(fdf).head(top_n)
        fig = px.bar(oe, x="errors", y="Owner", orientation="h")
        fig.update_traces(marker_color="#5B8DEF")
        fig.update_yaxes(autorange="reversed")
        show(style_fig(fig, 320, legend=False))

    st.markdown("**Peer-wise catches** (errors each peer caught)")
    pc = logic.peer_catches(fdf).head(top_n)
    fig = px.bar(pc, x="name", y="catches", text="catches")
    fig.update_traces(marker_color="#4CC9B0", textposition="outside")
    show(style_fig(fig, 300, legend=False))


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
