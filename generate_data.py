"""
generate_data.py
-----------------
Seeds two editable CSVs:
  * player_profiles.csv  -> POD, Name, Role, Gender, Archetype  (roster / roles / avatars)
  * review_log.csv       -> the QC review events used for the competition

Both are meant to be hand-editable afterwards: change a role or archetype in
player_profiles.csv (or edit review_log.csv) and just Refresh the dashboard. Re-running
this script regenerates fresh mock data.
"""
import random
from datetime import date, timedelta

import pandas as pd
import avatars

random.seed(7)

# ---- finalised rosters: (Name, Role, Gender) per POD ------------------------
CP = [
    ("CY", "Owner", "F"), ("NS", "Owner", "F"), ("KB", "Owner", "M"), ("SP", "Owner", "M"),
    ("SV", "Owner", "M"), ("AD", "Owner", "M"), ("KY", "Owner", "M"), ("KN", "Owner", "F"),
    ("NJ", "Owner", "F"), ("HM", "Owner", "M"), ("GR", "Owner", "M"), ("JR", "Owner", "M"),
    ("RN", "Owner", "M"),
    ("ASU", "Peer 1", "M"), ("MG", "Peer 1", "F"), ("RV", "Peer 1", "F"), ("YS", "Peer 1", "M"),
    ("SUK", "Peer 1", "M"), ("VI", "Peer 1", "M"), ("DH", "Peer 1", "M"), ("AZ", "Peer 1", "M"),
    ("PK", "Peer 1", "M"), ("RB", "Peer 1", "M"),
    ("KJ", "Peer 2", "M"), ("RD", "Peer 2", "M"), ("NV", "Peer 2", "F"), ("BM", "Peer 2", "M"),
    ("AK", "Peer 2", "M"),
]
NCP = [
    ("KJ", "Owner", "M"), ("AP", "Owner", "F"), ("RJ", "Owner", "M"), ("HA", "Owner", "M"),
    ("BM", "Owner", "M"), ("AM", "Owner", "M"),
    ("NV", "Peer 1", "F"), ("SA", "Peer 1", "F"), ("SH", "Peer 1", "M"),
    ("AU", "Peer 2", "F"), ("ED", "Peer 2", "F"), ("SC", "Peer 2", "M"), ("AR", "Peer 2", "M"),
    ("PV", "Peer 2", "M"),
]
ROSTERS = {"CP": CP, "NCP": NCP}

# ---- write player_profiles.csv (archetypes spread within each pod) ----------
arch_pool = avatars.list_archetypes()
prof_rows = []
for pod, roster in ROSTERS.items():
    for i, (name, role, gender) in enumerate(roster):
        prof_rows.append({"POD": pod, "Name": name, "Role": role,
                          "Gender": gender, "Archetype": arch_pool[i % len(arch_pool)]})
profiles = pd.DataFrame(prof_rows)
profiles.to_csv("player_profiles.csv", index=False)
print(f"Wrote player_profiles.csv ({len(profiles)} players)")

# ---- campaigns --------------------------------------------------------------
CAMPAIGNS = [
    ("SUPP0000501", "ib8003", "Supplier"), ("LIQ0000733", "ib7503", "Liquor"),
    ("SUPP0000502", "ib8107", "Supplier"), ("LIQ0000740", "ib7590", "Liquor"),
    ("SUPP0000615", "ib8210", "Supplier"), ("PROMO00088", "ib8320", "Promo"),
]
MINOR = ["Treatment/offer label", "Wrong offer IDs", "Wrong segment cutoffs",
         "Incorrect compensation", "SKU table segments", "Missing output in comments"]
MAJOR = ["Promo SKUs not checked in SKU", "Wrong time periods used",
         "SKUs not checked for targeting", "Improper RFC", "Retargeting slip",
         "Segmentation error in TXN_BRND_MEMBER_SMY"]
BRIEF = ["Brief misinterpreted", "Logic diverges from brief", "Misread brief scope"]
COMMENTS = ["Reworked and reissued", "Flagged to owner", "Corrected before send",
            "Discussed in standup", "Fixed in QC pass"]
ERR_TEXT = {"Minor Error": MINOR, "Major Error": MAJOR, "Brief Interpretation Error": BRIEF}
# playbook: catching peer's reward depends on bucket + which peer caught it
PEER_PTS = {"Brief Interpretation Error": (7, 10), "Major Error": (5, 6), "Minor Error": (3, 4)}
BUCKET_W = [0.5, 0.32, 0.18]  # Minor, Major, Brief

owner_quality = {(p, n): random.uniform(0.55, 0.9)
                 for p, r in ROSTERS.items() for (n, role, g) in r if role == "Owner"}

MONTH_STARTS = [date(2026, 6, 1), date(2026, 7, 6), date(2026, 8, 3)]  # Mondays-ish

rows, eid = [], 0
for mstart in MONTH_STARTS:
    for wk in range(4):
        monday = mstart + timedelta(weeks=wk)
        monday_no = int(monday.strftime("%Y%m%d"))
        for pod, roster in ROSTERS.items():
            owners = [n for (n, r, g) in roster if r == "Owner"]
            p1s = [n for (n, r, g) in roster if r == "Peer 1"]
            p2s = [n for (n, r, g) in roster if r == "Peer 2"]
            for _ in range(random.randint(10, 15)):
                eid += 1
                d = monday + timedelta(days=random.randint(0, 4))
                camp, ib, ctype = random.choice(CAMPAIGNS)
                owner = random.choice(owners); peer1 = random.choice(p1s); peer2 = random.choice(p2s)
                if random.random() < owner_quality[(pod, owner)]:
                    bucket, err, comment, op, q1, q2 = "No Error", "", "", 10, 0, 0
                else:
                    bucket = random.choices(list(PEER_PTS), BUCKET_W)[0]
                    err = random.choice(ERR_TEXT[bucket]); comment = random.choice(COMMENTS)
                    v1, v2 = PEER_PTS[bucket]
                    op = 0
                    if random.random() < 0.5:
                        q1, q2 = v1, 0
                    else:
                        q1, q2 = 0, v2
                rows.append({
                    "ENTRY_ID": eid, "Date": d.strftime("%d/%m/%Y"), "Monday No": monday_no,
                    "IB Number": ib, "Campaign Name": camp, "Type": ctype, "POD": pod,
                    "Owner": owner, "Peer 1": peer1, "Peer 2": peer2, "Errors": err,
                    "Bucket": bucket, "Comments": comment,
                    "Owner Points": op, "Peer 1 Points": q1, "Peer 2 Points": q2,
                })

df = pd.DataFrame(rows)
df.to_csv("review_log.csv", index=False)
print(f"Wrote review_log.csv ({len(df)} rows)")
print(df.groupby("POD").size().to_string())
print(df["Bucket"].value_counts().to_string())
