"""
generate_data.py
-----------------
Creates a realistic demo QC/review log in the EXACT schema supplied by the client:

  ENTRY_ID, Date, Monday No, IB Number, Campaign Name, Type, Owner, Peer 1, Peer 2,
  Errors, Bucket, Comments, Owner Points, Peer 1 Points, Peer 2 Points

Point convention (from the client's sample rows):
  - No Error                      -> Owner 10, Peer 1 0, Peer 2 0
  - Error caught by Peer 1        -> Owner 0,  Peer 1 10, Peer 2 0
  - Error caught by Peer 2        -> Owner 0,  Peer 1 0,  Peer 2 10

Run:  python generate_data.py   ->  writes review_log.csv
"""
import random
from datetime import date, timedelta

import pandas as pd

random.seed(11)

PEOPLE = ["RN", "MG", "BM", "KB", "YS", "HM", "RV", "AK", "KN", "KJ", "SP", "AD"]
# two PODs (teams) in the account; each pod is self-contained for clean per-pod boards
POD_ROSTER = {
    "CP":  ["RN", "MG", "BM", "KB", "YS", "HM"],
    "NCP": ["RV", "AK", "KN", "KJ", "SP", "AD"],
}
# hidden owner quality (higher -> fewer errors) and peer sharpness (higher -> more catches)
OWNER_Q = {p: random.uniform(0.55, 0.9) for p in PEOPLE}
PEER_SHARP = {p: random.uniform(0.5, 0.9) for p in PEOPLE}

CAMPAIGNS = [
    ("SUPP0000333", "ib7897", "Supplier"), ("SUPP0000412", "ib7901", "Supplier"),
    ("CAMP0000101", "ib7920", "BAU"), ("PROMO0000210", "ib7955", "Promo"),
    ("SUPP0000501", "ib8003", "Supplier"), ("ADHOC0000077", "ib8010", "Adhoc"),
]
BUCKETS_ERR = ["Minor Error", "Major Error", "Brief Interpretation Error"]
BUCKET_W = [0.5, 0.32, 0.18]
ERROR_TEXT = {
    "Minor Error": ["Treatment label wrong", "Typo in subject line", "Wrong image alt text",
                    "Formatting off"],
    "Major Error": ["Retargeting error", "Wrong dates considered", "Audience mismatch",
                    "Broken offer link"],
    "Brief Interpretation Error": ["Logic wrong", "Messed up segment logic",
                                   "Misread the brief", "Wrong success metric"],
}
COMMENTS = ["", "Fixed in second pass", "Confirmed with owner", "Escalated to lead",
            "Minor rework", "Good catch"]

MONTH_STARTS = [date(2026, 6, 1), date(2026, 7, 6), date(2026, 8, 3)]  # first Mondays


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


rows = []
eid = 0
for mstart in MONTH_STARTS:
    for wk in range(4):
        monday = mstart + timedelta(weeks=wk)
        monday_no = int(monday.strftime("%Y%m%d"))
        for pod, roster in POD_ROSTER.items():
            for _ in range(random.randint(9, 13)):  # reviews this week, this pod
                eid += 1
                d = monday + timedelta(days=random.randint(0, 4))
                camp, ib, ctype = random.choice(CAMPAIGNS)
                owner, peer1, peer2 = random.sample(roster, 3)

                clean = random.random() < OWNER_Q[owner]
                if clean:
                    bucket, err, op, p1, p2 = "No Error", "", 10, 0, 0
                    comment = ""
                else:
                    bucket = random.choices(BUCKETS_ERR, BUCKET_W)[0]
                    err = random.choice(ERROR_TEXT[bucket])
                    comment = random.choice(COMMENTS)
                    if random.random() < 0.5 + 0.4 * (PEER_SHARP[peer1] - PEER_SHARP[peer2]):
                        op, p1, p2 = 0, 10, 0
                    else:
                        op, p1, p2 = 0, 0, 10

                rows.append({
                    "ENTRY_ID": eid,
                    "Date": d.strftime("%d/%m/%Y"),
                    "Monday No": monday_no,
                    "IB Number": ib,
                    "Campaign Name": camp,
                    "Type": ctype,
                    "POD": pod,
                    "Owner": owner,
                    "Peer 1": peer1,
                    "Peer 2": peer2,
                    "Errors": err,
                    "Bucket": bucket,
                    "Comments": comment,
                    "Owner Points": op,
                    "Peer 1 Points": p1,
                    "Peer 2 Points": p2,
                })

df = pd.DataFrame(rows)
df.to_csv("review_log.csv", index=False)
print(f"Wrote review_log.csv ({len(df)} rows)")
print(df.groupby("POD").size().to_string())
print(df["Bucket"].value_counts().to_string())
