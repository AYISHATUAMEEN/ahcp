#!/usr/bin/env python3
"""02_build_panel.py - harmonize every HUD physical-inspection score vintage and reconstruct inspection histories.

Inputs : data/raw/hud_pis/ahcp_{ph,mf}_{vintage}.{xlsx,txt}   (see code/sources.json)
Outputs: data/interim/snapshots.csv.gz      one row per source row (property x vintage listing), harmonized
         data/interim/inspections.csv       one row per unique inspection
         data/interim/properties_core.csv   one row per property, attributes from its latest vintage
         data/interim/build_counts.json     row counts at every stage (read by 04_qa.py)
"""
import json, os, re
import numpy as np, pandas as pd
import ahcp_load as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "interim"); os.makedirs(OUT, exist_ok=True)
counts = {}

# First dates on which each program's inspections could be NSPIRE (HUD implementation dates).
NSPIRE_START = {"PH": pd.Timestamp("2023-07-01"), "MF": pd.Timestamp("2023-10-01")}


def s(x):  # clean string column
    x = x.astype("string").str.strip()
    return x.mask(x.isin(["", "nan", "None", "<NA>"]))


def digits(x, width):
    x = s(x).str.replace(r"\.0$", "", regex=True)
    return x.where(x.isna(), x.str.zfill(width))


raw = L.read_all()
counts["raw_rows_by_file"] = {f"{p}_{v}": int(n) for (p, v), n in raw.groupby(["program", "vintage"]).size().items()}
counts["raw_rows"] = int(len(raw))

d = pd.DataFrame({"program": raw.program, "vintage": raw.vintage.astype(int), "source_row": raw.source_row})
d["source_file"] = ["ahcp_%s_%d.%s" % (p.lower(), v, "txt" if v == 2011 else "xlsx") for p, v in zip(raw.program, raw.vintage)]
d["inspection_id"] = s(raw.inspection_id).str.replace(r"\.0$", "", regex=True)
d["property_id"] = s(raw.property_id).str.replace(r"\.0$", "", regex=True).str.upper()
for c in ["property_name", "address", "city", "cbsa_name", "county_name", "pha_name"]:
    d[c] = s(raw[c]).str.replace(r"\s+", " ", regex=True)
d["state_abbr"] = s(raw.state_abbr).str.upper()
d["state_fips"] = digits(raw.state_fips, 2)
d["county_fips3"] = digits(raw.county_code, 3)
d["cbsa_code"] = digits(raw.cbsa_code, 5)
d.loc[d.cbsa_code == "99999", "cbsa_code"] = pd.NA
z = s(raw.zip).str.replace(r"\.0$", "", regex=True).str.replace(r"\D", "", regex=True)
z = z.mask(z == "")
# 9-digit ZIP+4 (2011 file) -> first five; short values lost leading zeros in the 2025/2026 workbooks -> left-pad
d["zip5"] = z.str.zfill(5).mask((z.str.len() == 9).fillna(False), z.str[:5])
d["latitude"] = pd.to_numeric(raw.latitude, errors="coerce")
d["longitude"] = pd.to_numeric(raw.longitude, errors="coerce")
d["location_quality"] = s(raw.location_quality)
d["pha_code"] = s(raw.pha_code).str.upper()
d["inspection_score"] = pd.to_numeric(raw.inspection_score, errors="coerce")
d["inspection_date"] = pd.to_datetime(raw.inspection_date.astype(str), errors="coerce", format="mixed").dt.normalize()
d["protocol_hud"] = s(raw.protocol_hud).str.upper()

counts["rows_missing_score"] = int(d.inspection_score.isna().sum())
counts["rows_missing_date"] = int(d.inspection_date.isna().sum())
counts["rows_missing_property_id"] = int(d.property_id.isna().sum())
d = d[d.property_id.notna() & d.inspection_date.notna() & d.inspection_score.notna()].copy()
counts["rows_after_required_fields"] = int(len(d))

# ---- identifiers -------------------------------------------------------------------------------------------
d["ahcp_property_id"] = d.program + ":" + d.property_id
amp = d.property_id.str.fullmatch(r"[A-Z]{2}\d{9}")
d["id_scheme"] = np.where(d.program == "MF", "REMS_PROPERTY_ID", np.where(amp.fillna(False), "PIC_AMP_DEVELOPMENT", "PIC_PRE_AMP_PROJECT"))
legacy_key = d.program + ":L:" + d.property_id + ":" + d.inspection_date.dt.strftime("%Y%m%d")
# The 2011 file has no inspection IDs; three property-days carry two different scores. Both are kept: the second gets "#2".
seq = d.sort_values("source_row").groupby(["program", "vintage", "property_id", "inspection_date"]).cumcount()
legacy_key = legacy_key + np.where(seq.reindex(d.index) > 0, "#" + (seq.reindex(d.index) + 1).astype(str), "")
d["ahcp_inspection_id"] = (d.program + ":" + d.inspection_id).fillna(legacy_key)
# A HUD inspection ID occasionally appears under two properties (a joint inspection). Each property keeps its own row:
# the key gains an "@property" suffix and the inspection is flagged shared_inspection_id = 1.
npid = d.groupby("ahcp_inspection_id").property_id.transform("nunique")
d["shared_inspection_id"] = (npid > 1).astype(int)
d.loc[npid > 1, "ahcp_inspection_id"] = d.ahcp_inspection_id + "@" + d.property_id

# exact duplicate listings inside one file
dup = d.duplicated(["program", "vintage", "ahcp_inspection_id", "inspection_score"], keep="first")
counts["within_file_duplicate_rows_dropped"] = int(dup.sum())
d = d[~dup].copy()
counts["snapshot_rows"] = int(len(d))
d = d.sort_values(["program", "property_id", "vintage", "inspection_date", "source_row"]).reset_index(drop=True)

snap_cols = ["ahcp_property_id", "ahcp_inspection_id", "program", "vintage", "source_file", "source_row", "property_id", "id_scheme",
             "inspection_id", "inspection_date", "inspection_score", "protocol_hud", "property_name", "address", "city", "state_abbr",
             "state_fips", "county_fips3", "county_name", "zip5", "cbsa_code", "cbsa_name", "latitude", "longitude", "location_quality",
             "pha_code", "pha_name"]
d[snap_cols].to_csv(os.path.join(OUT, "snapshots.csv.gz"), index=False, date_format="%Y-%m-%d", compression={"method": "gzip", "mtime": 0})

# ---- one row per inspection --------------------------------------------------------------------------------
d = d.sort_values(["ahcp_inspection_id", "vintage", "source_row"])
g = d.groupby("ahcp_inspection_id", sort=False)
last = g.tail(1).set_index("ahcp_inspection_id")  # values as stated in the most recent vintage listing the inspection
insp = pd.DataFrame({
    "ahcp_property_id": last.ahcp_property_id, "program": last.program, "property_id": last.property_id,
    "inspection_id": last.inspection_id, "inspection_date": last.inspection_date, "inspection_score": last.inspection_score,
    "protocol_hud": g.protocol_hud.last(),  # last non-null
    "first_vintage": g.vintage.min(), "last_vintage": g.vintage.max(), "n_vintages": g.vintage.nunique(),
    "score_min_across_vintages": g.inspection_score.min(), "score_max_across_vintages": g.inspection_score.max(),
    "date_earliest_across_vintages": g.inspection_date.min(),
    "shared_inspection_id": g.shared_inspection_id.max(),
})
insp["score_conflict"] = (insp.score_min_across_vintages != insp.score_max_across_vintages).astype(int)
insp["date_conflict_days"] = (insp.inspection_date - insp.date_earliest_across_vintages).dt.days
insp = insp.reset_index()

# protocol: HUD's own flag where the 2025/2026 files carry one; otherwise inferred
nspire_id = insp.inspection_id.fillna("").str.startswith("INSP-")
before = insp.inspection_date < insp.program.map(NSPIRE_START)
insp["protocol"] = insp.protocol_hud
insp["protocol_source"] = np.where(insp.protocol_hud.notna(), "hud_flag", pd.NA)
m = insp.protocol.isna() & nspire_id
insp.loc[m, ["protocol", "protocol_source"]] = ["NSPIRE", "inferred_id_prefix"]
m = insp.protocol.isna() & before
insp.loc[m, ["protocol", "protocol_source"]] = ["UPCS", "inferred_pre_nspire_date"]
m = insp.protocol.isna()
insp.loc[m, ["protocol", "protocol_source"]] = ["UNKNOWN", "not_determinable"]
insp["score_scale"] = np.where(insp.last_vintage == 2011, "decimal_0_100", "integer_0_100")
insp["inspection_year"] = insp.inspection_date.dt.year

insp = insp.sort_values(["program", "property_id", "inspection_date", "ahcp_inspection_id"]).reset_index(drop=True)
gp = insp.groupby("ahcp_property_id", sort=False)
insp["inspection_seq"] = gp.cumcount() + 1
insp["prev_inspection_date"] = gp.inspection_date.shift(1)
insp["prev_inspection_score"] = gp.inspection_score.shift(1)
insp["prev_protocol"] = gp.protocol.shift(1)
insp["days_since_prev"] = (insp.inspection_date - insp.prev_inspection_date).dt.days
insp["score_change"] = insp.inspection_score - insp.prev_inspection_score
insp["protocol_change"] = ((insp.prev_protocol.notna()) & (insp.prev_protocol != insp.protocol)).astype(int)

insp_cols = ["ahcp_inspection_id", "ahcp_property_id", "program", "property_id", "inspection_id", "inspection_date", "inspection_year",
             "inspection_score", "score_scale", "protocol", "protocol_source", "inspection_seq", "prev_inspection_date",
             "prev_inspection_score", "days_since_prev", "score_change", "protocol_change", "first_vintage", "last_vintage", "n_vintages",
             "score_conflict", "score_min_across_vintages", "score_max_across_vintages", "date_conflict_days", "shared_inspection_id"]
insp[insp_cols].to_csv(os.path.join(OUT, "inspections.csv"), index=False, date_format="%Y-%m-%d")
counts["inspections"] = int(len(insp))
counts["inspections_by_program"] = {k: int(v) for k, v in insp.program.value_counts().items()}
counts["inspections_by_protocol_source"] = {f"{a}|{b}": int(n) for (a, b), n in insp.groupby(["protocol", "protocol_source"]).size().items()}
counts["score_conflicts"] = int(insp.score_conflict.sum())
counts["date_conflicts"] = int((insp.date_conflict_days != 0).sum())
counts["date_conflicts_over_1_day"] = int((insp.date_conflict_days.abs() > 1).sum())
counts["shared_inspection_ids"] = int(insp.shared_inspection_id.sum())

# ---- one row per property ----------------------------------------------------------------------------------
d = d.sort_values(["ahcp_property_id", "vintage", "inspection_date", "source_row"])
gl = d.groupby("ahcp_property_id", sort=False)
attrs = ["property_name", "address", "city", "state_abbr", "state_fips", "county_fips3", "county_name", "zip5", "cbsa_code", "cbsa_name",
         "latitude", "longitude", "location_quality", "pha_code", "pha_name"]
prop = gl[attrs].last()  # last non-null value per attribute, i.e. from the most recent vintage that states it
prop["program"] = gl.program.first(); prop["property_id"] = gl.property_id.first(); prop["id_scheme"] = gl.id_scheme.first()
prop["first_vintage"] = gl.vintage.min(); prop["last_vintage"] = gl.vintage.max(); prop["n_vintages"] = gl.vintage.nunique()
prop["vintages_listed"] = gl.vintage.agg(lambda v: ";".join(str(x) for x in sorted(set(v))))
prop["n_names"] = gl.property_name.nunique(); prop["n_addresses"] = gl.address.nunique()
latest_v = max(L.VINTAGES)
prop["in_latest_vintage"] = (prop.last_vintage == latest_v).astype(int)
gi = insp.groupby("ahcp_property_id")
prop["n_inspections"] = gi.size()
prop["first_inspection_date"] = gi.inspection_date.min(); prop["last_inspection_date"] = gi.inspection_date.max()
li = insp.sort_values("inspection_date").groupby("ahcp_property_id").tail(1).set_index("ahcp_property_id")
prop["last_inspection_score"] = li.inspection_score; prop["last_protocol"] = li.protocol
prop["n_upcs"] = gi.protocol.agg(lambda x: int((x == "UPCS").sum())); prop["n_nspire"] = gi.protocol.agg(lambda x: int((x == "NSPIRE").sum()))
prop["has_both_protocols"] = ((prop.n_upcs > 0) & (prop.n_nspire > 0)).astype(int)
prop["county_fips"] = (prop.state_fips + prop.county_fips3).where(prop.state_fips.notna() & prop.county_fips3.notna())
for c in ["n_inspections", "n_upcs", "n_nspire"]: prop[c] = prop[c].astype("Int64")
prop = prop.reset_index()
pcols = ["ahcp_property_id", "program", "property_id", "id_scheme"] + attrs[:5] + ["county_fips", "county_fips3"] + attrs[6:] + \
        ["first_vintage", "last_vintage", "n_vintages", "vintages_listed", "in_latest_vintage", "n_names", "n_addresses", "n_inspections",
         "n_upcs", "n_nspire", "has_both_protocols", "first_inspection_date", "last_inspection_date", "last_inspection_score", "last_protocol"]
prop[pcols].to_csv(os.path.join(OUT, "properties_core.csv"), index=False, date_format="%Y-%m-%d")
counts["properties"] = int(len(prop))
counts["properties_by_program_scheme"] = {f"{a}|{b}": int(n) for (a, b), n in prop.groupby(["program", "id_scheme"]).size().items()}
counts["properties_missing_coordinates"] = int(prop.latitude.isna().sum())
json.dump(counts, open(os.path.join(OUT, "build_counts.json"), "w"), indent=1)
print(json.dumps(counts, indent=1))
