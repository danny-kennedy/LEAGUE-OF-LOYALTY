# League of Loyalty — QC Competition Dashboard

A gamified, production-ready Streamlit dashboard for QC / review competitions. It reads a
single CSV review log and turns it into three clearly separated competitions:

- **Weekly** — a raw-points race, ranked *within each role* (Owner / Peer 1 / Peer 2).
- **Monthly** — a *fair* race using a band-wise **Z-score** normalised to 0–100.
- **Quarterly** — the same Z-score fairness, aggregated across the quarter.

The data workflow is unchanged and **CSV-driven**: update the CSV, reload, and the app
reflects the latest data.

---

## 1. Data schema

The app reads `review_log.csv`. Each row is one QC/review activity.

```
ENTRY_ID, Date, Monday No, IB Number, Campaign Name, Type, POD,
Owner, Peer 1, Peer 2, Errors, Bucket, Comments,
Owner Points, Peer 1 Points, Peer 2 Points
```

- **POD** is the team/pod (e.g. `CP`, `NCP`) and is the **highest-level filter** — the
  whole dashboard re-scopes to the selected POD before any other filter is applied. If the
  column is absent, the app falls back to a single `ALL` pod so nothing breaks.
- **Bucket** is one of: `No Error`, `Minor Error`, `Major Error`, `Brief Interpretation Error`.
- Points are summed per person **per role** to build the leaderboards
  (`Total Owner Points = sum of Owner Points grouped by Owner`, etc.).

Weeks are derived from `Date` (the Monday of each week), which matches the `Monday No`
concept. Months and quarters are also derived from `Date`.

To regenerate the demo data: `python generate_data.py`.

---

## 2. The two methodologies (why rankings differ)

**Weekly — raw.** Owners, Peer 1 and Peer 2 only compete against their own role. Points are
summed and ranked directly. Answers: *who scored most this week in their role?*

**Monthly / Quarterly — fair (Z-score).** Roles have different opportunities to earn points,
so raw points are never compared across bands. For each band we compute the average and
standard deviation, then a band-wise Z-score:

```
Z = (points − band_average) / band_std_dev
```

- A band with one participant, or zero standard deviation, gets Z = 0.
- All Z-scores are normalised to a 0–100 metric, **`z_score_points`** (if every Z-score is
  identical, everyone gets 100).
- `z_score_points` drives `overall_rank`, `band_rank` and `band_percentile`. **Raw points
  are kept for transparency only.**

Answers: *who outperformed others in their own role by the most?*

The final fair table contains: `overall_rank, band_rank, name, band, points,
band_avg_points, band_std_points, band_z_score, z_score_points, band_percentile`
(plus `raw_rank` and `reviews` for the raw-vs-fair comparisons).

---

## 3. Pages & filters

**Pages:** Overview (gamified arcade) · Weekly Competition · Monthly Competition ·
Quarterly Competition · Participant Analytics · Error Analytics · About Competition.

**Gamified Overview.** The Overview is an arcade "Service Desk Cup" scene: the top 10
players by **total weekly points** stand as pixel-art game characters on colour-coded podium
bars scaled to their score, over a pixel backdrop. Each player gets a unique, procedurally
generated character avatar (deterministic from their name, in `avatars.py` — no external
assets). A right-hand panel shows five champions, each in its own colour: Weekly Top Owner,
Weekly Top Peer 1, Weekly Top Peer 2, Monthly Top Person, Quarterly Top Person — with avatar,
name, band and points.

**About Competition** explains the game: 1 month = 1 **Season** (Platinum, Gold, Diamond),
1 quarter = 1 **League** (Vanguard, Tempest, Ascension, Apex), the weekly/monthly/quarterly
scoring philosophies, and the full **Defect Bucketing Criteria** table plus the Minor / Major /
Brief-Interpretation error catalogs.

**Filters (one pipeline, applied in this order):** POD → Month / Week / Quarter → Campaign →
Type → Error Bucket → Participant → Top N. POD is the top-level selector; every KPI, table,
chart and leaderboard re-scopes to it. If a selection has no records, the page shows a clean
"No data available" message instead of erroring.

> **Refresh button:** it is intentionally **disabled for now** (kept in the same place, same
> look). Clicking it does not reload the CSV or recompute anything. To restore later, have
> its click handler call `st.cache_data.clear()` then `st.rerun()` (a one-line change,
> flagged in `app.py`).

---

## 4. Project files

```
comp_dashboard/
├── app.py                 # Streamlit UI (6 pages, Plotly charts)
├── logic.py               # all calculations (pure pandas/numpy — weekly + Z-score)
├── review_log.csv         # the data the dashboard reads
├── generate_data.py       # regenerates demo data in the exact schema
├── validate_app.py        # dev-only smoke test (runs every page against the data)
├── requirements.txt       # streamlit, pandas, plotly
└── .streamlit/
    └── config.toml        # dark/gold Hextech theme
```

---

## 5. Run it on your computer (step by step, no prior Streamlit needed)

1. **Install Python 3.10+** from <https://www.python.org/downloads/> (tick “Add Python to
   PATH”). Check: `python --version`.
2. Open a terminal and move into the folder: `cd path/to/comp_dashboard`.
3. Create a virtual environment: `python -m venv .venv`, then activate it
   (`source .venv/bin/activate` on macOS/Linux, `.venv\Scripts\activate` on Windows).
4. Install dependencies: `pip install -r requirements.txt`.
5. Start the app: `streamlit run app.py`. It opens at `http://localhost:8501`.
   Stop it with `Ctrl + C`.

---

## 6. Put it online — Streamlit Community Cloud (free)

1. Create a **GitHub** account and sign in to **Streamlit Community Cloud**
   (<https://share.streamlit.io>) with it. Install Git if needed (`git --version`).
2. Create a new GitHub repository.
3. From the project folder, push the code:
   ```bash
   git init
   git add .
   git commit -m "QC competition dashboard"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
4. On <https://share.streamlit.io>: **Create app → Deploy from GitHub**, choose your repo,
   branch `main`, main file `app.py`, then **Deploy**. You get a public
   `…streamlit.app` URL.
5. To update, push again (`git add . && git commit -m "update" && git push`) — it redeploys
   automatically. Keep any private credentials in **App → Settings → Secrets**, not in git.

For an internal rollout you can self-host instead:
`streamlit run app.py --server.port 8501 --server.address 0.0.0.0` behind a reverse proxy.

---

## 7. Performance & caching

- The CSV load + preparation is cached with `@st.cache_data`, so filters and page switches
  never re-read the disk.
- The Z-score leaderboard is cached and keyed on the active filters, so it only recomputes
  when a filter actually changes.
- Charts use Plotly with the mode-bar disabled and modest data sizes to stay lightweight on
  deployment. Calculations live in `logic.py` (never inside chart rendering).

---

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `command not found: streamlit` | Activate the virtual environment, then reinstall requirements. |
| `python: command not found` | Use `python3`. |
| Numbers look stale | The refresh button is paused by design; reload the page or update the CSV and redeploy. |
| Deploy fails on Cloud | Ensure `requirements.txt` is in the repo root and main file is `app.py`. |
| Theme not applied online | Commit `.streamlit/config.toml` to the repo. |
