"""
logic.py
---------
All data computations for the QC Competition dashboard. Pure pandas/numpy — no
Streamlit — so it is fully testable on its own. app.py wraps these with caching.

Two independent, clearly separated methodologies:
  * WEEKLY  -> raw points, ranked within each responsibility (Owner/Peer 1/Peer 2).
  * MONTHLY / QUARTERLY -> band-wise Z-score normalised to a 0-100 fair metric,
    so people are compared only against peers doing the same role.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

# ---- Domain metadata (single place so the UI stays consistent) ---------------
BANDS = ["Owner", "Peer 1", "Peer 2"]
NAME_COL = {"Owner": "Owner", "Peer 1": "Peer 1", "Peer 2": "Peer 2"}
POINT_COL = {"Owner": "Owner Points", "Peer 1": "Peer 1 Points", "Peer 2": "Peer 2 Points"}
BAND_META = {
    "Owner":  {"color": "#5B8DEF", "emoji": "\U0001F6E1\uFE0F"},
    "Peer 1": {"color": "#C8AA6E", "emoji": "\U0001F50D"},
    "Peer 2": {"color": "#4CC9B0", "emoji": "\U0001F3AF"},
}
BUCKETS = ["No Error", "Minor Error", "Major Error", "Brief Interpretation Error"]
BUCKET_COLOR = {
    "No Error": "#4CC9B0", "Minor Error": "#F4CE00",
    "Major Error": "#E8734A", "Brief Interpretation Error": "#B57BE0",
}
_CANON_BUCKET = {b.lower(): b for b in BUCKETS}

# Playbook scoring grid: (event / bucket, Owner, Peer 1, Peer 2).
# em-dash = not applicable; unicode minus for penalties.
_D = "\u2014"      # —  (N/A)
_M = "\u2212"      # −  (minus, so the UI can colour penalties red)
SCORING_RULES = [
    ("Perfect deliverable (passes both peer checks)", "+10", _D, _D),
    ("Brief Interpretation Error caught", _D, "+7", "+10"),
    ("Major Error caught", _D, "+5", "+6"),
    ("Minor Error caught", _D, "+3", "+4"),
    ("Incorrectly flagged error", _D, _M + "3", _M + "4"),
    ("Client escalation", _M + "20", _M + "30", _M + "50"),
]

ROLE_CANON = {"owner": "Owner", "peer 1": "Peer 1", "peer1": "Peer 1",
              "peer 2": "Peer 2", "peer2": "Peer 2"}


def load_profiles(path: str) -> pd.DataFrame:
    """Editable roster: POD, Name, Role, Gender, Archetype. Drives roles + avatars.
    Add a row for a new player and refresh; roles/avatars can be edited freely."""
    p = pd.read_csv(path)
    p.columns = p.columns.str.strip()
    p["POD"] = p["POD"].astype(str).str.strip().str.upper()
    p["Name"] = p["Name"].astype(str).str.strip().str.upper()
    p["Role"] = p["Role"].map(lambda x: ROLE_CANON.get(str(x).strip().lower(), "Owner"))
    p["Gender"] = (p["Gender"].astype(str).str.strip().str.upper().str[:1]
                   .replace({"": "M", "N": "M"}))
    p["Archetype"] = p["Archetype"].astype(str).str.strip().str.lower()
    return p.drop_duplicates(["POD", "Name"]).reset_index(drop=True)


def profile_map(profiles: pd.DataFrame) -> dict:
    """(POD, NAME) -> {role, gender, archetype}."""
    return {(r.POD, r.Name): {"role": r.Role, "gender": r.Gender, "archetype": r.Archetype}
            for r in profiles.itertuples(index=False)}


def roster_players(profiles: pd.DataFrame, pod=None):
    p = profiles if not pod or pod in ("All", "ALL") else profiles[profiles["POD"] == pod]
    return p.sort_values(["POD", "Role", "Name"]).reset_index(drop=True)


# ---- Loading & preparation ---------------------------------------------------
def load_and_prepare(path: str) -> pd.DataFrame:
    """Read the CSV and add derived period/label columns. Ingestion stays CSV-driven."""
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    if "comments" in df.columns and "Comments" not in df.columns:
        df = df.rename(columns={"comments": "Comments"})

    # POD is the highest-level grouping (e.g. CP / NCP). Default to one pod if absent,
    # so the app keeps working on datasets that don't have the column yet.
    if "POD" in df.columns:
        df["POD"] = (df["POD"].astype(str).str.strip().str.upper()
                     .replace({"": "UNASSIGNED", "NAN": "UNASSIGNED", "NONE": "UNASSIGNED"}))
    else:
        df["POD"] = "ALL"

    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

    # participant names -> stripped uppercase; blanks -> NA
    for c in ["Owner", "Peer 1", "Peer 2"]:
        df[c] = (df[c].astype(str).str.strip().str.upper()
                 .replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA}))

    # points -> numeric, missing -> 0
    for c in POINT_COL.values():
        df[c] = pd.to_numeric(df.get(c), errors="coerce").fillna(0).astype(int)

    # bucket -> canonical 4 categories; blank -> No Error
    def canon(x):
        s = str(x).strip()
        return _CANON_BUCKET.get(s.lower(), "No Error") if s and s.lower() != "nan" \
            else "No Error"
    df["Bucket"] = df["Bucket"].map(canon) if "Bucket" in df.columns else "No Error"

    for c in ["Campaign Name", "Type", "IB Number", "Errors"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().replace({"nan": ""})

    # derived period columns
    dt = df["Date"]
    df["month_key"] = dt.dt.to_period("M").astype(str)
    df["month_label"] = dt.dt.strftime("%b %Y")
    q = dt.dt.to_period("Q")
    df["quarter_key"] = q.astype(str)
    df["quarter_label"] = "Q" + dt.dt.quarter.astype("Int64").astype(str) + " " + \
        dt.dt.year.astype("Int64").astype(str)
    week_start = dt - pd.to_timedelta(dt.dt.weekday, unit="D")
    df["week_start"] = week_start
    df["week_label"] = "W/C " + week_start.dt.strftime("%d %b %Y")

    df["has_error"] = df["Bucket"].ne("No Error")
    df["total_points"] = df[list(POINT_COL.values())].sum(axis=1)
    return df.sort_values("Date").reset_index(drop=True)


# ---- Filtering & option lists ------------------------------------------------
def filter_data(df: pd.DataFrame, pod=None, campaigns=(), types=(), buckets=()) -> pd.DataFrame:
    """The single filtering pipeline every page consumes.

    Hierarchy: POD (highest level) -> Campaign -> Type -> Error Bucket.
    Period slicing (Month/Week/Quarter) is applied by each page on top of this,
    and Participant / Top N are display-level. Keeping one pipeline avoids
    duplicated filtering logic across pages.
    """
    out = df
    if pod and pod not in ("All", "ALL", None):
        out = out[out["POD"] == pod]
    if campaigns:
        out = out[out["Campaign Name"].isin(campaigns)]
    if types:
        out = out[out["Type"].isin(types)]
    if buckets:
        out = out[out["Bucket"].isin(buckets)]
    return out


# Backwards-compatible alias (no POD) — kept so older callers don't break.
def filter_rows(df, campaigns=(), types=(), buckets=()):
    return filter_data(df, None, campaigns, types, buckets)


def _ordered(df, label_col, order_col):
    return (df[[label_col, order_col]].dropna().drop_duplicates()
            .sort_values(order_col)[label_col].tolist())


def list_pods(df):      return sorted(df["POD"].dropna().unique().tolist())
def list_months(df):    return _ordered(df, "month_label", "month_key")
def list_quarters(df):  return _ordered(df, "quarter_label", "quarter_key")
def list_weeks(df):     return _ordered(df, "week_label", "week_start")
def list_campaigns(df): return sorted(df["Campaign Name"].dropna().unique().tolist())
def list_types(df):     return sorted(df["Type"].dropna().unique().tolist())


def list_participants(df):
    names = pd.concat([df["Owner"], df["Peer 1"], df["Peer 2"]]).dropna().unique()
    return sorted(names.tolist())


# ---- Core aggregation --------------------------------------------------------
def band_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """Long format (POD, name, band, points, reviews) summed per person-in-role.
    POD is carried so the same abbreviation in two pods stays two separate players."""
    parts = []
    for band in BANDS:
        ncol, pcol = NAME_COL[band], POINT_COL[band]
        sub = df[["POD", ncol, pcol]].dropna(subset=[ncol])
        if sub.empty:
            continue
        g = (sub.groupby(["POD", ncol])[pcol]
             .agg(points="sum", reviews="size").reset_index()
             .rename(columns={ncol: "name"}))
        g["band"] = band
        parts.append(g)
    if not parts:
        return pd.DataFrame(columns=["POD", "name", "band", "points", "reviews"])
    return pd.concat(parts, ignore_index=True)[["POD", "name", "band", "points", "reviews"]]


# ---- WEEKLY: raw points within each role -------------------------------------
def weekly_boards(df_week: pd.DataFrame) -> pd.DataFrame:
    """Raw-points leaderboard, ranked within each band. No normalisation."""
    agg = band_aggregate(df_week)
    if agg.empty:
        return agg.assign(rank=pd.Series(dtype=int))
    agg["rank"] = (agg.groupby("band")["points"]
                   .rank(method="min", ascending=False).astype(int))
    return agg.sort_values(["band", "rank", "name"]).reset_index(drop=True)


def weekly_player_totals(df_week: pd.DataFrame) -> pd.DataFrame:
    """Total points each person earned this week across all roles, for the arcade
    standings. Returns POD, name, points, band (primary role that week), rank."""
    agg = band_aggregate(df_week)
    if agg.empty:
        return pd.DataFrame(columns=["POD", "name", "points", "band", "rank"])
    tot = agg.groupby(["POD", "name"], as_index=False)["points"].sum()
    primary = (agg.sort_values("points", ascending=False)
               .drop_duplicates(["POD", "name"])[["POD", "name", "band"]])
    out = tot.merge(primary, on=["POD", "name"], how="left")
    out = out.sort_values("points", ascending=False).reset_index(drop=True)
    out["rank"] = out["points"].rank(method="min", ascending=False).astype(int)
    return out


# ---- MONTHLY / QUARTERLY: band-wise Z-score fair metric ----------------------
def zscore_leaderboard(long_df: pd.DataFrame) -> pd.DataFrame:
    """Band-wise Z-score normalised to 0-100 (z_score_points), the fair metric."""
    cols = ["overall_rank", "band_rank", "POD", "name", "band", "points",
            "band_avg_points", "band_std_points", "band_z_score",
            "z_score_points", "band_percentile", "raw_rank", "reviews"]
    df = long_df.copy()
    if df.empty:
        return pd.DataFrame(columns=cols)

    # clean
    if "POD" not in df.columns:
        df["POD"] = "ALL"
    df["name"] = df["name"].astype(str).str.strip().str.upper()
    df = df[df["band"].isin(BANDS)].copy()
    df["points"] = pd.to_numeric(df["points"], errors="coerce").fillna(0)
    if df.empty:
        return pd.DataFrame(columns=cols)

    # band statistics (population std so a single participant -> std 0 -> z 0)
    stats = (df.groupby("band")["points"]
             .agg(band_avg_points="mean",
                  band_std_points=lambda s: float(np.std(s, ddof=0)),
                  band_count="count").reset_index())
    df = df.merge(stats, on="band", how="left")

    # band-wise z; single participant or zero std -> 0
    std = df["band_std_points"]
    z = (df["points"] - df["band_avg_points"]) / std.replace(0, np.nan)
    df["band_z_score"] = np.where((std > 0) & (df["band_count"] > 1), z, 0.0)
    df["band_z_score"] = df["band_z_score"].fillna(0.0)

    # normalise all z-scores to 0-100; identical -> everyone 100
    zmin, zmax = df["band_z_score"].min(), df["band_z_score"].max()
    df["z_score_points"] = 100.0 if zmax == zmin else \
        (df["band_z_score"] - zmin) / (zmax - zmin) * 100
    df["z_score_points"] = df["z_score_points"].round(1)

    # ranks / percentile (fair metric drives everything; raw kept for transparency)
    df["overall_rank"] = df["z_score_points"].rank(method="min", ascending=False).astype(int)
    df["band_rank"] = (df.groupby("band")["z_score_points"]
                       .rank(method="min", ascending=False).astype(int))
    df["band_percentile"] = (df.groupby("band")["z_score_points"]
                             .rank(pct=True).mul(100).round(1))
    df["raw_rank"] = df["points"].rank(method="min", ascending=False).astype(int)

    df["band_avg_points"] = df["band_avg_points"].round(1)
    df["band_std_points"] = df["band_std_points"].round(2)
    df["band_z_score"] = df["band_z_score"].round(2)
    df["points"] = df["points"].astype(int)
    return df[cols].sort_values("overall_rank").reset_index(drop=True)


def fair_leaderboard(df_period: pd.DataFrame) -> pd.DataFrame:
    """Convenience: aggregate a period-sliced frame and run the Z-score pipeline."""
    return zscore_leaderboard(band_aggregate(df_period))


# ---- Overview KPIs -----------------------------------------------------------
def total_participants(df) -> int:
    return int(pd.concat([df["Owner"], df["Peer 1"], df["Peer 2"]]).dropna().nunique())


def active_counts(df) -> dict:
    return {b: int(df[NAME_COL[b]].dropna().nunique()) for b in BANDS}


def weekly_champion(df_week):
    agg = band_aggregate(df_week)
    if agg.empty:
        return None
    top = agg.sort_values("points", ascending=False).iloc[0]
    return {"pod": top["POD"], "name": top["name"], "band": top["band"],
            "points": int(top["points"])}


def monthly_champion(df_month):
    lb = fair_leaderboard(df_month)
    if lb.empty:
        return None
    top = lb.iloc[0]
    return {"pod": top["POD"], "name": top["name"], "band": top["band"],
            "z": float(top["z_score_points"]), "points": int(top["points"])}


def band_moments(lb: pd.DataFrame) -> pd.DataFrame:
    """Per-band mean/std/count of raw points — feeds the bell-curve chart."""
    if lb.empty:
        return pd.DataFrame(columns=["band", "mean", "std", "n"])
    g = (lb.groupby("band")
         .agg(mean=("band_avg_points", "first"), std=("band_std_points", "first"),
              n=("name", "count")).reset_index())
    return g


def weekly_errors_by_owner(df_week: pd.DataFrame) -> pd.DataFrame:
    """Errors made this week, attributed to the owner of the deliverable."""
    return owner_errors(df_week).rename(columns={"Owner": "name"})


# ---- Participant analytics ---------------------------------------------------
def participant_points_by(df: pd.DataFrame, name: str, label_col: str) -> pd.DataFrame:
    """Points a participant earned (any role) per period label."""
    name = name.upper()
    frames = []
    for band in BANDS:
        ncol, pcol = NAME_COL[band], POINT_COL[band]
        sub = df[df[ncol] == name]
        if not sub.empty:
            frames.append(sub[[label_col, pcol]].rename(columns={pcol: "points"}))
    if not frames:
        return pd.DataFrame(columns=[label_col, "points"])
    out = pd.concat(frames).dropna(subset=[label_col])
    out = out.groupby(label_col, as_index=False)["points"].sum()
    return out


def participant_summary(df: pd.DataFrame, name: str) -> dict:
    name = name.upper()
    per_band, total, reviews = {}, 0, 0
    for band in BANDS:
        ncol, pcol = NAME_COL[band], POINT_COL[band]
        sub = df[df[ncol] == name]
        pts = int(sub[pcol].sum())
        per_band[band] = {"points": pts, "reviews": int(len(sub))}
        total += pts
        reviews += int(len(sub))
    return {"name": name, "total": total, "reviews": reviews, "by_band": per_band}


# ---- Error analytics ---------------------------------------------------------
def bucket_distribution(df) -> pd.DataFrame:
    vc = df["Bucket"].value_counts()
    return pd.DataFrame({"Bucket": BUCKETS,
                         "count": [int(vc.get(b, 0)) for b in BUCKETS]})


def errors_over_time(df, label_col="week_label", order_col="week_start") -> pd.DataFrame:
    err = df[df["has_error"]].dropna(subset=[label_col, order_col])
    if err.empty:
        return pd.DataFrame(columns=[label_col, "errors"])
    out = (err.groupby([label_col, order_col]).size().reset_index(name="errors")
           .sort_values(order_col))
    return out


def _clean_key(series: pd.Series) -> pd.Series:
    """Drop NaN/blank grouping keys so charts never show an 'Undefined' category."""
    s = series.astype("string").str.strip()
    return s.replace({"": pd.NA, "nan": pd.NA, "none": pd.NA, "None": pd.NA})


def campaign_errors(df) -> pd.DataFrame:
    err = df[df["has_error"]].copy()
    err["Campaign Name"] = _clean_key(err["Campaign Name"])
    err = err.dropna(subset=["Campaign Name"])
    return (err.groupby("Campaign Name").size().reset_index(name="errors")
            .sort_values("errors", ascending=False))


def owner_errors(df) -> pd.DataFrame:
    err = df[df["has_error"]].copy()
    err["Owner"] = _clean_key(err["Owner"])
    err = err.dropna(subset=["Owner"])
    return (err.groupby("Owner").size().reset_index(name="errors")
            .sort_values("errors", ascending=False))


def peer_catches(df) -> pd.DataFrame:
    """How many errors each peer caught (rows where that peer earned the points)."""
    p1 = df[df["Peer 1 Points"] > 0].copy()
    p1["Peer 1"] = _clean_key(p1["Peer 1"])
    p2 = df[df["Peer 2 Points"] > 0].copy()
    p2["Peer 2"] = _clean_key(p2["Peer 2"])
    c1 = p1.dropna(subset=["Peer 1"]).groupby("Peer 1").size()
    c2 = p2.dropna(subset=["Peer 2"]).groupby("Peer 2").size()
    out = (c1.add(c2, fill_value=0).reset_index())
    out.columns = ["name", "catches"]
    out["catches"] = out["catches"].astype(int)
    return out.sort_values("catches", ascending=False)