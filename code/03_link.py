#!/usr/bin/env python3
"""03_link.py - attach tract geocodes, subsidy, LIHTC and health linkages to the property table.

Inputs : data/interim/*.csv (from 02), data/raw/hud_gis/*.csv, data/raw/census/*.zip, data/raw/cdc/*.csv
Outputs: data/processed/ahcp_properties.csv, ahcp_inspections.csv.gz, ahcp_snapshots.csv.gz,
         ahcp_tract_health.csv, ahcp_ph_legacy_crosswalk.csv; data/interim/link_counts.json
"""
import json, os, re, shutil
import numpy as np, pandas as pd
from scipy.spatial import cKDTree
from ahcp_geo import TractIndex

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW, INT, OUT = [os.path.join(ROOT, "data", x) for x in ("raw", "interim", "processed")]
os.makedirs(OUT, exist_ok=True)
LIHTC_MAX_M = 50.0     # proximity threshold for the geographic LIHTC match
LEGACY_MAX_M = 50.0    # proximity threshold for pre-AMP -> AMP candidate crosswalk
C = {}

prop = pd.read_csv(os.path.join(INT, "properties_core.csv"), dtype=str)
for c in ["latitude", "longitude"]: prop[c] = pd.to_numeric(prop[c])
C["properties"] = len(prop)

# ---------- address normalisation ------------------------------------------------------------------------
SUF = {"STREET": "ST", "AVENUE": "AVE", "AV": "AVE", "BOULEVARD": "BLVD", "DRIVE": "DR", "ROAD": "RD", "LANE": "LN", "COURT": "CT",
       "PLACE": "PL", "CIRCLE": "CIR", "TERRACE": "TER", "PARKWAY": "PKWY", "HIGHWAY": "HWY", "SQUARE": "SQ", "TRAIL": "TRL",
       "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW",
       "FIRST": "1ST", "SECOND": "2ND", "THIRD": "3RD", "FOURTH": "4TH", "FIFTH": "5TH", "SAINT": "ST", "MOUNT": "MT"}
UNIT = re.compile(r"\b(APT|APARTMENT|UNIT|STE|SUITE|BLDG|BUILDING|#)\b.*$")


def norm_addr(a):
    if not isinstance(a, str) or not a.strip(): return ""
    a = re.sub(r"[.,']", "", a.upper()); a = UNIT.sub("", a); a = re.sub(r"[^A-Z0-9 ]", " ", a)
    return " ".join(SUF.get(t, t) for t in a.split())


def house_no(a):
    m = re.match(r"^(\d+)", a or ""); return m.group(1) if m else ""


def xy(lat, lon):  # local equirectangular metres; adequate for <100 m comparisons
    lat = np.asarray(lat, float); lon = np.asarray(lon, float)
    return np.c_[lon * 111320.0 * np.cos(np.radians(lat)), lat * 110540.0]


prop["addr_norm"] = prop.address.map(norm_addr)
prop["house_no"] = prop.addr_norm.map(house_no)

# ---------- 1. census tract (2020) by point-in-polygon -----------------------------------------------------
idx = TractIndex(os.path.join(RAW, "census", "ahcp_cb_2020_us_tract_500k.zip"))
C["tract_polygons"] = len(idx.geoid)
has = prop.latitude.notna() & prop.longitude.notna()
res = [idx.locate(lo, la) if h else ("", "no_coordinates", np.nan) for la, lo, h in zip(prop.latitude, prop.longitude, has)]
prop["tract_geoid_2020"] = [r[0] or pd.NA for r in res]
prop["tract_method"] = [r[1] or "outside_all_tracts" for r in res]
prop["tract_snap_m"] = [r[2] if r[1] == "nearest_vertex" else np.nan for r in res]
C["tract_method"] = prop.tract_method.value_counts().to_dict()
cmp = prop[prop.tract_geoid_2020.notna() & prop.county_fips.notna()]
agree = cmp.tract_geoid_2020.str[:5] == cmp.county_fips
C["tract_county_check_n"] = int(len(cmp)); C["tract_county_agree"] = int(agree.sum())
C["tract_county_disagree_by_state"] = cmp[~agree].state_abbr.value_counts().head(8).to_dict()
prop["tract_county_agrees"] = np.where(prop.tract_geoid_2020.notna() & prop.county_fips.notna(),
                                       (prop.tract_geoid_2020.str[:5] == prop.county_fips).astype(int), np.nan)

# ---------- 2. subsidy linkage from HUD eGIS layers ---------------------------------------------------------
def rd(name):
    d = pd.read_csv(os.path.join(RAW, "hud_gis", name), dtype=str)
    return d.apply(lambda s: s.str.strip()).replace({"": pd.NA})


def epoch(s): return pd.to_datetime(pd.to_numeric(s, errors="coerce"), unit="ms").dt.strftime("%Y-%m-%d")


mfa = rd("ahcp_hud_mf_assisted.csv"); mfa["hud_layer"] = "mf_assisted"
mfi = rd("ahcp_hud_mf_insured.csv"); mfi["hud_layer"] = "mf_insured"
C["mf_assisted_rows"] = len(mfa); C["mf_insured_rows"] = len(mfi)
C["mf_assisted_dup_ids"] = int(mfa.PROPERTY_ID.duplicated().sum()); C["mf_insured_dup_ids"] = int(mfi.PROPERTY_ID.duplicated().sum())
mf = pd.concat([mfa, mfi], ignore_index=True)
both = mf.groupby("PROPERTY_ID").hud_layer.agg(lambda x: "mf_assisted+mf_insured" if x.nunique() > 1 else x.iloc[0])
mf = mf.drop_duplicates("PROPERTY_ID", keep="first").set_index("PROPERTY_ID")  # assisted layer wins when in both
mf["hud_layer"] = both
units = lambda s: pd.to_numeric(s, errors="coerce").replace(0, np.nan)
sub_mf = pd.DataFrame({
    "hud_layer": mf.hud_layer, "subsidy_category": mf.PROPERTY_CATEGORY_NAME, "subsidy_program_type": mf.PROGRAM_TYPE1,
    "total_units": units(mf.TOTAL_UNIT_COUNT), "assisted_units": units(mf.TOTAL_ASSISTED_UNIT_COUNT),
    "contract_number": mf.CONTRACT1, "contract_count": pd.to_numeric(mf.CONTRACT_COUNT, errors="coerce"),
    "contract_expiration_date": epoch(mf.EXPIRATION_DATE1), "fha_number": mf.PRIMARY_FHA_NUMBER,
    "is_insured": mf.IS_INSURED_IND, "is_section8": mf.IS_SEC8_IND, "is_202_811": mf.IS_202_811_IND,
    "is_rad_conversion": mf.IS_SEC8_RAD_DEMO_CONV_IND, "has_active_assistance": mf.HAS_ACTIVE_ASSISTANCE_IND,
    "client_group": mf.CLIENT_GROUP_NAME, "pct_occupied": units(mf.PCT_OCCUPIED), "hud_taxcredit_flag": mf.TAXCREDIT1,
    "tract_geoid_2010_hud": mf.TRACT_LEVEL, "hud_layer_updated": epoch(mf.LAST_UPDT_DTTM)})
sub_mf.index = "MF:" + sub_mf.index
ph = rd("ahcp_hud_ph_developments.csv"); C["ph_dev_rows"] = len(ph); C["ph_dev_dup_ids"] = int(ph.DEVELOPMENT_CODE.duplicated().sum())
ph = ph.drop_duplicates("DEVELOPMENT_CODE").set_index("DEVELOPMENT_CODE")
sub_ph = pd.DataFrame({
    "hud_layer": "ph_developments", "subsidy_category": "Public Housing", "subsidy_program_type": "Public Housing",
    "total_units": units(ph.TOTAL_UNITS), "assisted_units": units(ph.ACC_UNITS), "pct_occupied": units(ph.PCT_OCCUPIED),
    "ph_scattered_site": ph.SCATTERED_SITE_IND, "tract_geoid_2010_hud": ph.TRACT_LEVEL, "hud_layer_updated": epoch(ph.LAST_UPDT_DTTM)})
sub_ph.index = "PH:" + sub_ph.index
sub = pd.concat([sub_mf, sub_ph]); sub.index.name = "ahcp_property_id"
sub["tract_geoid_2010_hud"] = sub.tract_geoid_2010_hud.where(sub.tract_geoid_2010_hud.str.len() == 11)
prop = prop.merge(sub.reset_index(), on="ahcp_property_id", how="left")
prop["hud_layer"] = prop.hud_layer.fillna("not_in_current_hud_layers")
C["subsidy_layer"] = {"|".join(k): int(v) for k, v in prop.groupby(["program", "hud_layer"]).size().items()}
cur = prop[prop.in_latest_vintage == "1"]
C["subsidy_match_latest_vintage"] = {p: [int((g.hud_layer != "not_in_current_hud_layers").sum()), int(len(g))] for p, g in cur.groupby("program")}

# ---------- 3. LIHTC linkage ---------------------------------------------------------------------------------
li = rd("ahcp_hud_lihtc.csv"); C["lihtc_rows"] = len(li)
li["addr_norm"] = li.STD_ADDR.fillna(li.PROJ_ADD).map(norm_addr); li["house_no"] = li.addr_norm.map(house_no)
li["zip5"] = li.STD_ZIP5.fillna(li.PROJ_ZIP).str[:5].str.zfill(5)
li["lat"] = pd.to_numeric(li.LAT, errors="coerce"); li["lon"] = pd.to_numeric(li.LON, errors="coerce")
li["yr_pis"] = pd.to_numeric(li.YR_PIS, errors="coerce").where(lambda s: s.between(1987, 2030))
li["li_units"] = pd.to_numeric(li.LI_UNITS, errors="coerce")
# (a) exact normalised address + ZIP
key_l = li[(li.addr_norm != "") & li.house_no.ne("") & li.zip5.notna()].assign(k=lambda d: d.addr_norm + "|" + d.zip5)
amap = key_l.groupby("k").HUD_ID.agg(list).to_dict()
pk = prop.addr_norm + "|" + prop.zip5.fillna("")
m_addr = [amap.get(k, []) if hn else [] for k, hn in zip(pk, prop.house_no)]
# (b) proximity + same house number
lg = li[li.lat.notna() & li.lon.notna()].reset_index(drop=True)
tree = cKDTree(xy(lg.lat, lg.lon))
pxy = xy(prop.latitude.fillna(0), prop.longitude.fillna(0))
near = tree.query_ball_point(pxy, r=LIHTC_MAX_M * 1.25)  # slack for the flat-earth approximation, re-checked below
ids, how, dist = [], [], []
lg_hn, lg_id, lg_xy = lg.house_no.values, lg.HUD_ID.values, xy(lg.lat, lg.lon)
for i, (a, nb, ok, hn) in enumerate(zip(m_addr, near, has, prop.house_no)):
    g = []
    if ok and hn:
        for j in nb:
            dd = float(np.hypot(*(lg_xy[j] - pxy[i])))
            if dd <= LIHTC_MAX_M and lg_hn[j] == hn: g.append((dd, lg_id[j]))
    if a:
        ids.append(sorted(set(a) | {x[1] for x in g})); how.append("address_zip"); dist.append(np.nan)
    elif g:
        ids.append(sorted({x[1] for x in g})); how.append("proximity_house_number"); dist.append(round(min(x[0] for x in g), 1))
    else:
        ids.append([]); how.append("none"); dist.append(np.nan)
lix = li.drop_duplicates("HUD_ID").set_index("HUD_ID")
prop["lihtc_match_type"] = how
prop["lihtc_n_projects"] = [len(x) for x in ids]
prop["lihtc_hud_ids"] = [";".join(x) if x else pd.NA for x in ids]
prop["lihtc_match_dist_m"] = dist
prop["lihtc_earliest_yr_pis"] = [np.nanmin(lix.loc[x, "yr_pis"].values) if x and lix.loc[x, "yr_pis"].notna().any() else np.nan for x in ids]
prop["lihtc_li_units_total"] = [np.nansum(lix.loc[x, "li_units"].values) if x and lix.loc[x, "li_units"].notna().any() else np.nan for x in ids]
C["lihtc_match_type"] = {"|".join(k): int(v) for k, v in prop.groupby(["program", "lihtc_match_type"]).size().items()}
t = prop[prop.hud_taxcredit_flag.isin(["Y", "N"])]
C["lihtc_vs_hud_flag"] = pd.crosstab(t.hud_taxcredit_flag, t.lihtc_match_type != "none").rename(columns={True: "linked", False: "not_linked"}).to_dict("index")

# ---------- 4. candidate crosswalk: pre-AMP public housing project -> AMP development ----------------------
old = prop[prop.id_scheme == "PIC_PRE_AMP_PROJECT"]; new = prop[prop.id_scheme == "PIC_AMP_DEVELOPMENT"]
rows = []
new_by_pha = {k: g for k, g in new.groupby("pha_code")}
for r in old.itertuples():
    g = new_by_pha.get(r.pha_code)
    if g is None: continue
    hit = {}
    if r.addr_norm and r.house_no:
        for nid in g[(g.addr_norm == r.addr_norm) & (g.zip5 == r.zip5)].ahcp_property_id: hit[nid] = ("address_zip", np.nan)
    if not np.isnan(r.latitude):
        gg = g[g.latitude.notna()]
        if len(gg):
            dd = np.hypot(*(xy(gg.latitude, gg.longitude) - xy([r.latitude], [r.longitude])).T)
            for nid, x in zip(gg.ahcp_property_id[dd <= LEGACY_MAX_M], dd[dd <= LEGACY_MAX_M]):
                hit[nid] = (("address_zip+" if nid in hit else "") + "proximity", round(float(x), 1))
    for nid, (mth, x) in hit.items(): rows.append((r.ahcp_property_id, nid, r.pha_code, mth, x))
cw = pd.DataFrame(rows, columns=["ahcp_property_id_legacy", "ahcp_property_id_amp_candidate", "pha_code", "match_method", "distance_m"])
cw["n_candidates_for_legacy"] = cw.groupby("ahcp_property_id_legacy").ahcp_property_id_amp_candidate.transform("size")
cw.to_csv(os.path.join(OUT, "ahcp_ph_legacy_crosswalk.csv"), index=False)
uniq = cw[cw.n_candidates_for_legacy == 1].set_index("ahcp_property_id_legacy").ahcp_property_id_amp_candidate
prop["amp_candidate_id"] = prop.ahcp_property_id.map(uniq)
C["legacy_projects"] = len(old); C["legacy_with_any_candidate"] = int(cw.ahcp_property_id_legacy.nunique())
C["legacy_with_unique_candidate"] = int(len(uniq)); C["legacy_pha_absent_from_amp"] = int((~old.pha_code.isin(new.pha_code)).sum())

# ---------- 5. CDC PLACES tract health ------------------------------------------------------------------------
pl = pd.read_csv(os.path.join(RAW, "cdc", "ahcp_cdc_places_tract_2025.csv"), dtype=str)
pl = pl.rename(columns={"tractfips": "tract_geoid_2020", "mobility_crudeprev_": "mobility_crudeprev"})
pl["tract_geoid_2020"] = pl.tract_geoid_2020.str.zfill(11)
C["places_tracts"] = len(pl)
# Connecticut: PLACES 2025 reports tracts under the 2022 planning-region county equivalents (09110-09190). The 6-digit
# tract code is unchanged and unique statewide, so CT tracts are re-keyed on that suffix. Elsewhere the two keys are equal.
ct = pl[pl.tract_geoid_2020.str[:2] == "09"]
assert ct.tract_geoid_2020.str[5:].is_unique
ctmap = dict(zip(ct.tract_geoid_2020.str[5:], ct.tract_geoid_2020))
is_ct = prop.tract_geoid_2020.str[:2].eq("09").fillna(False)
prop["tract_geoid_places"] = prop.tract_geoid_2020.where(~is_ct, prop.tract_geoid_2020.str[5:].map(ctmap))
C["places_ct_rekeyed"] = int((is_ct & prop.tract_geoid_places.notna()).sum()); C["places_ct_total"] = int(is_ct.sum())
pl = pl.rename(columns={"tract_geoid_2020": "tract_geoid_places"})
used = pl[pl.tract_geoid_places.isin(prop.tract_geoid_places.dropna())].drop(columns=["stateabbr", "countyname", "countyfips"])
used = used.rename(columns={c: "places_" + c.replace("_crudeprev", "") for c in used.columns if c != "tract_geoid_places"})
npr = prop.groupby("tract_geoid_places").size().rename("n_ahcp_properties")
used = used.merge(npr, on="tract_geoid_places").sort_values("tract_geoid_places")
used.to_csv(os.path.join(OUT, "ahcp_tract_health.csv"), index=False)
prop["places_tract_matched"] = np.where(prop.tract_geoid_2020.notna(), prop.tract_geoid_places.isin(pl.tract_geoid_places).astype(int), np.nan)
C["places_tracts_used"] = len(used)
C["places_property_match"] = [int((prop.places_tract_matched == 1).sum()), int(prop.tract_geoid_2020.notna().sum())]
C["places_unmatched_by_state"] = prop[prop.places_tract_matched == 0].state_abbr.value_counts().head(8).to_dict()

# ---------- write -------------------------------------------------------------------------------------------
prop = prop.drop(columns=["addr_norm", "house_no"])
for c in ["total_units", "assisted_units", "contract_count", "lihtc_earliest_yr_pis", "lihtc_li_units_total", "tract_county_agrees", "places_tract_matched"]:
    prop[c] = prop[c].astype("Int64")
prop.to_csv(os.path.join(OUT, "ahcp_properties.csv"), index=False)
pd.read_csv(os.path.join(INT, "inspections.csv"), dtype=str).to_csv(os.path.join(OUT, "ahcp_inspections.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
shutil.copy(os.path.join(INT, "snapshots.csv.gz"), os.path.join(OUT, "ahcp_snapshots.csv.gz"))
C["property_columns"] = len(prop.columns)
json.dump(C, open(os.path.join(INT, "link_counts.json"), "w"), indent=1, default=int)
print(json.dumps(C, indent=1, default=int))
