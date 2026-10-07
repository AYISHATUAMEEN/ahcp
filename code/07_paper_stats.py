#!/usr/bin/env python3
"""07_paper_stats.py - statistics and LaTeX tables for the data-descriptor article.

Reads data/processed and data/raw; writes paper/paper_stats.json, paper/numbers.tex (one macro per number) and
paper/tables/*.tex. The manuscript never contains a hand-typed result.
"""
import json, os, re
import numpy as np, pandas as pd
import ahcp_load as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = os.path.join(ROOT, "data", "processed")
OUT = os.path.join(ROOT, "paper"); TB = os.path.join(OUT, "tables"); os.makedirs(TB, exist_ok=True)
S = json.load(open(os.path.join(OUT, "stats.json"))); LC = json.load(open(os.path.join(ROOT, "data", "interim", "link_counts.json")))
insp = pd.read_csv(os.path.join(P, "ahcp_inspections.csv.gz"), dtype={"inspection_id": str, "property_id": str}, parse_dates=["inspection_date", "prev_inspection_date"])
prop = pd.read_csv(os.path.join(P, "ahcp_properties.csv"), dtype=str)
snap = pd.read_csv(os.path.join(P, "ahcp_snapshots.csv.gz"), dtype=str, parse_dates=["inspection_date"])
snap["vintage"] = snap.vintage.astype(int); snap["inspection_score"] = snap.inspection_score.astype(float)
th = pd.read_csv(os.path.join(P, "ahcp_tract_health.csv"), dtype={"tract_geoid_places": str})
N = {}   # numbers -> macros
c = lambda x: f"{int(x):,}"
def _neg(s): return ("$-$" + s[1:]) if s.startswith("-") else s
f1 = lambda x: _neg(f"{x:.1f}"); f2 = lambda x: _neg(f"{x:.2f}")


def table(name, header, rows, align):
    with open(os.path.join(TB, name + ".tex"), "w") as fh:
        fh.write("\\begin{tabular}{" + align + "}\n\\toprule\n" + header + " \\\\\n\\midrule\n")
        for r in rows: fh.write(r if isinstance(r, str) else " & ".join(str(x) for x in r) + " \\\\\n")
        fh.write("\\bottomrule\n\\end{tabular}\n")


# ---- Table: source vintages ---------------------------------------------------------------------------------
rows = []
for v in sorted(L.VINTAGES):
    for p, lab in (("PH", "PH"), ("MF", "MF")):
        g = snap[(snap.vintage == v) & (snap.program == p)]
        mx = g.groupby("property_id").size().max()
        rows.append([v if p == "PH" else "", lab, c(len(g)), c(g.property_id.nunique()), g.inspection_date.min().strftime("%Y-%m"),
                     g.inspection_date.max().strftime("%Y-%m"), mx, "no" if g.inspection_id.isna().all() else "yes", "yes" if g.protocol_hud.notna().any() else "no"])
table("vintages", "Vintage & Prog. & Rows & Properties & First & Last & Max/prop. & ID & Protocol", rows, "llrrllrll")

# ---- vintage multiplicity and first appearance -----------------------------------------------------------------
nv = insp.n_vintages.value_counts().sort_index()
N["inspOneVintage"] = c(nv.get(1, 0)); N["inspMultiVintage"] = c((insp.n_vintages > 1).sum()); N["inspMaxVintages"] = int(insp.n_vintages.max())
N["pctOneVintage"] = f1(100 * nv.get(1, 0) / len(insp))
fv = insp.groupby(["first_vintage", "program"]).size().unstack(fill_value=0)
rows = [[v, c(fv.loc[v, "PH"]), c(fv.loc[v, "MF"]), c(fv.loc[v].sum()), f1(100 * fv.loc[v].sum() / len(insp))] for v in fv.index]
rows.append("\\midrule\n"); rows.append(["Total", c(fv.PH.sum()), c(fv.MF.sum()), c(len(insp)), "100.0"])
table("first_vintage", "First vintage & PH & MF & Total & \\%", rows, "lrrrr")
post = insp[insp.first_vintage > 2011]
N["inspPostLegacy"] = c(len(post)); N["inspLegacy"] = c((insp.first_vintage == 2011).sum())
N["inspPostOneVintage"] = c((post.n_vintages == 1).sum()); N["pctPostOneVintage"] = f1(100 * (post.n_vintages == 1).mean())

# ---- cross-vintage reconciliation ---------------------------------------------------------------------------------
multi = insp[insp.n_vintages > 1]
sc = insp[insp.score_conflict == 1].copy()
first_last = snap.sort_values(["ahcp_inspection_id", "vintage"]).groupby("ahcp_inspection_id").inspection_score.agg(["first", "last"])
d = (first_last["last"] - first_last["first"]).reindex(sc.ahcp_inspection_id)
N["scoreConfUp"] = c((d > 0).sum()); N["scoreConfDown"] = c((d < 0).sum()); N["scoreConfSame"] = c((d == 0).sum())
rng = sc.score_max_across_vintages - sc.score_min_across_vintages
N["scoreConfMedian"] = f1(rng.median()); N["scoreConfMax"] = f1(rng.max()); N["scoreConfPctMulti"] = f2(100 * len(sc) / len(multi))
N["scoreConfCrossSixty"] = c(((sc.score_min_across_vintages < 60) & (sc.score_max_across_vintages >= 60)).sum())
dc = insp[insp.date_conflict_days != 0]
N["dateConfOneDay"] = c((dc.date_conflict_days.abs() == 1).sum()); N["dateConfPctMulti"] = f2(100 * len(dc) / len(multi))
N["dateConfMaxDays"] = c(dc.date_conflict_days.abs().max())

# ---- descriptive statistics ---------------------------------------------------------------------------------
def era(r):
    if r.inspection_year <= 2009: return "2000--2009"
    if r.protocol == "NSPIRE": return "2023--2026"
    return "2012--2023"
insp["era"] = insp.apply(era, axis=1)
rows = []
for p in ("PH", "MF"):
    for e, pr in (("2000--2009", "UPCS"), ("2012--2023", "UPCS"), ("2023--2026", "NSPIRE")):
        g = insp[(insp.program == p) & (insp.era == e) & (insp.protocol == pr)].inspection_score
        rows.append([p, e, pr, c(len(g)), f1(g.mean()), f1(g.std()), f1(g.quantile(.10)), f1(g.median()), f1(g.quantile(.90)), f1(100 * (g < 60).mean()), f1(100 * (g >= 90).mean())])
        N[f"mean{p}{pr}{'A' if e.startswith('2000') else 'B'}"] = f1(g.mean()); N[f"fail{p}{pr}{'A' if e.startswith('2000') else 'B'}"] = f1(100 * (g < 60).mean())
table("descriptives", "Prog. & Period & Protocol & $n$ & Mean & SD & P10 & Median & P90 & $<$60 (\\%) & $\\geq$90 (\\%)", rows, "lllrrrrrrrr")
ns = insp[insp.protocol == "NSPIRE"].inspection_score
N["nspireAtFiftyNine"] = c((ns == 59).sum()); N["nspirePctFiftyNine"] = f1(100 * (ns == 59).mean()); N["nspireFiftyFiveToFiftyNine"] = f1(100 * ns.between(55, 59).mean())
N["nspireSixtyToSixtyFour"] = f1(100 * ns.between(60, 64).mean())
up = insp[(insp.protocol == "UPCS") & (insp.inspection_year >= 2013)].inspection_score
N["upcsAtFiftyNine"] = f1(100 * (up == 59).mean()); N["upcsFiftyFiveToFiftyNine"] = f1(100 * up.between(55, 59).mean()); N["upcsSixtyToSixtyFour"] = f1(100 * up.between(60, 64).mean())

# ---- inspections per property and intervals ---------------------------------------------------------------------------------
ni = prop.n_inspections.astype(int)
N["propOneInsp"] = c((ni == 1).sum()); N["pctPropOneInsp"] = f1(100 * (ni == 1).mean()); N["propMaxInsp"] = int(ni.max()); N["propMeanInsp"] = f2(ni.mean())
N["propSpanMedianYears"] = f1(((pd.to_datetime(prop.last_inspection_date) - pd.to_datetime(prop.first_inspection_date)).dt.days / 365.25).median())
iv = insp[insp.days_since_prev.notna()].copy(); iv["yrs"] = iv.days_since_prev / 365.25
def iv_era(r):
    y0 = r.prev_inspection_date.year; y1 = r.inspection_year
    if y1 <= 2009: return "Within 2000--2009"
    if y0 <= 2009: return "Across the 2010--2012 gap"
    if y1 <= 2019: return "Within 2013--2019"
    return "Ending 2020--2026"
iv["era"] = iv.apply(iv_era, axis=1)
rows = []
for e in ("Within 2000--2009", "Across the 2010--2012 gap", "Within 2013--2019", "Ending 2020--2026"):
    for p in ("PH", "MF"):
        g = iv[(iv.era == e) & (iv.program == p)].yrs
        rows.append([e if p == "PH" else "", p, c(len(g)), f2(g.quantile(.25)), f2(g.median()), f2(g.quantile(.75)), f1(100 * (g > 3.5).mean())])
        key = {"Within 2000--2009": "A", "Across the 2010--2012 gap": "G", "Within 2013--2019": "B", "Ending 2020--2026": "C"}[e]
        N[f"ivMed{p}{key}"] = f2(g.median()); N[f"ivLong{p}{key}"] = f1(100 * (g > 3.5).mean())
table("intervals", "Interval & Prog. & Pairs & P25 & Median & P75 & $>$3.5 y (\\%)", rows, "llrrrrr")

# ---- protocol transition (descriptive) ---------------------------------------------------------------------------------
pairs = insp[insp.prev_inspection_score.notna()].copy()
pairs["prev_protocol"] = np.where(pairs.protocol_change == 1, np.where(pairs.protocol == "NSPIRE", "UPCS", "NSPIRE"), pairs.protocol)
def tr(g):
    r = np.corrcoef(g.prev_inspection_score, g.inspection_score)[0, 1]
    return [c(len(g)), f1(g.prev_inspection_score.mean()), f1(g.inspection_score.mean()), f1(g.score_change.mean()), f1(g.score_change.std()), f2(r),
            f1(100 * ((g.prev_inspection_score >= 60) & (g.inspection_score < 60)).mean()), f1(100 * ((g.prev_inspection_score < 60) & (g.inspection_score >= 60)).sum() / max((g.prev_inspection_score < 60).sum(), 1))]
rows = []
sets = {"UU": pairs[(pairs.prev_protocol == "UPCS") & (pairs.protocol == "UPCS") & (pairs.prev_inspection_date.dt.year >= 2013)],
        "UN": pairs[(pairs.prev_protocol == "UPCS") & (pairs.protocol == "NSPIRE") & (pairs.prev_inspection_date.dt.year >= 2013)],
        "NN": pairs[(pairs.prev_protocol == "NSPIRE") & (pairs.protocol == "NSPIRE")]}
lab = {"UU": "UPCS $\\rightarrow$ UPCS", "UN": "UPCS $\\rightarrow$ NSPIRE", "NN": "NSPIRE $\\rightarrow$ NSPIRE"}
for k, g in sets.items():
    for p in ("PH", "MF"):
        gg = g[g.program == p]
        if len(gg) < 30: continue
        t = tr(gg); rows.append([lab[k] if p == "PH" or (k == "NN") else "", p] + t)
        N[f"tr{k}{p}N"] = t[0]; N[f"tr{k}{p}Delta"] = t[3]; N[f"tr{k}{p}R"] = t[5]; N[f"tr{k}{p}NewFail"] = t[6]
table("transitions", "Pair type & Prog. & Pairs & Prev. mean & Next mean & Mean $\\Delta$ & SD $\\Delta$ & $r$ & Pass$\\to$fail (\\%) & Fail$\\to$pass (\\%)", rows, "llrrrrrrrr")
N["trUNgapMedian"] = f2((sets["UN"].days_since_prev / 365.25).median()); N["trUUgapMedian"] = f2((sets["UU"].days_since_prev / 365.25).median())

# ---- property persistence across vintages ---------------------------------------------------------------------------------
vs = sorted(L.VINTAGES); rows = []
for a, b in zip(vs[1:-1], vs[2:]):
    r = [f"{a} $\\rightarrow$ {b}"]
    for p in ("PH", "MF"):
        A = set(snap[(snap.vintage == a) & (snap.program == p)].property_id); B = snap[(snap.vintage == b) & (snap.program == p)]
        kept = len(A & set(B.property_id))
        sa = snap[(snap.vintage == a) & (snap.program == p)].set_index("property_id").ahcp_inspection_id; sb = B.set_index("property_id").ahcp_inspection_id
        both = sa.index.intersection(sb.index); sa1 = sa[~sa.index.duplicated(keep="last")]; sb1 = sb[~sb.index.duplicated(keep="last")]
        newi = (sa1.reindex(both.unique()) != sb1.reindex(both.unique())).mean()
        r += [c(len(A)), f1(100 * kept / len(A)), f1(100 * newi)]
    rows.append(r)
table("persistence", "Vintage pair & PH props. & Retained (\\%) & New insp. (\\%) & MF props. & Retained (\\%) & New insp. (\\%)", rows, "lrrrrrr")

# ---- linkage ---------------------------------------------------------------------------------
n = len(prop); tm = LC["tract_method"]
N["tractContains"] = c(tm["contains"]); N["tractNearest"] = c(tm["nearest_vertex"]); N["tractOutside"] = c(tm["outside_all_tracts"]); N["tractNoCoord"] = c(tm["no_coordinates"])
N["tractPolygons"] = c(LC["tract_polygons"]); N["tractCountyN"] = c(LC["tract_county_check_n"]); N["tractCountyAgree"] = c(LC["tract_county_agree"])
x = prop[prop.tract_geoid_2010_hud.notna() & prop.tract_geoid_2020.notna()]
N["tractHudCompareN"] = c(len(x)); N["tractHudSameCode"] = f1(100 * (x.tract_geoid_2020 == x.tract_geoid_2010_hud).mean()); N["tractHudSameCounty"] = f2(100 * (x.tract_geoid_2020.str[:5] == x.tract_geoid_2010_hud.str[:5]).mean())
cur = prop[prop.in_latest_vintage == "1"]
N["curProps"] = c(len(cur)); N["curMF"] = c((cur.program == "MF").sum()); N["curPH"] = c((cur.program == "PH").sum())
lq = cur.location_quality.fillna("missing").value_counts()
N["lqRooftopPct"] = f1(100 * lq.get("R", 0) / len(cur)); N["lqZipCentroidPct"] = f1(100 * lq.get("T", 0) / len(cur)); N["lqZipFourPct"] = f1(100 * lq.get("4", 0) / len(cur)); N["lqBlockGroupPct"] = f1(100 * lq.get("B", 0) / len(cur))
N["curTractPct"] = f2(100 * cur.tract_geoid_2020.notna().mean()); N["curPlacesPct"] = f2(100 * (cur.places_tract_matched == "1").mean())
N["nStates"] = int(prop.state_abbr.nunique()); N["nTracts"] = c(prop.tract_geoid_2020.nunique()); N["nCounties"] = c(prop.tract_geoid_2020.str[:5].nunique()); N["nPHA"] = c(prop.pha_code.nunique())
fl = LC["lihtc_vs_hud_flag"]; y, nn_ = fl["Y"], fl["N"]
N["lihtcYLinked"] = c(y["linked"]); N["lihtcYNot"] = c(y["not_linked"]); N["lihtcNLinked"] = c(nn_["linked"]); N["lihtcNNot"] = c(nn_["not_linked"])
N["lihtcSens"] = f1(100 * y["linked"] / (y["linked"] + y["not_linked"])); N["lihtcFalse"] = f1(100 * nn_["linked"] / (nn_["linked"] + nn_["not_linked"]))
N["lihtcPPV"] = f1(100 * y["linked"] / (y["linked"] + nn_["linked"])); N["lihtcRows"] = c(LC["lihtc_rows"])
N["lihtcMulti"] = c((prop.lihtc_n_projects.astype(int) > 1).sum())
N["legacyTotal"] = c(LC["legacy_projects"]); N["legacyAny"] = c(LC["legacy_with_any_candidate"]); N["legacyUnique"] = c(LC["legacy_with_unique_candidate"])
N["legacyAnyPct"] = f1(100 * LC["legacy_with_any_candidate"] / LC["legacy_projects"])
N["mfAssistedRows"] = c(LC["mf_assisted_rows"]); N["mfInsuredRows"] = c(LC["mf_insured_rows"]); N["phDevRows"] = c(LC["ph_dev_rows"]); N["placesTractsAll"] = c(LC["places_tracts"]); N["placesCT"] = c(LC["places_ct_rekeyed"])
rows = []
link = [("Census tract (2020)", prop.tract_geoid_2020.notna(), cur.tract_geoid_2020.notna()),
        ("HUD subsidy record", prop.hud_layer != "not_in_current_hud_layers", cur.hud_layer != "not_in_current_hud_layers"),
        ("LIHTC project", prop.lihtc_match_type != "none", cur.lihtc_match_type != "none"),
        ("PLACES tract estimates", prop.places_tract_matched == "1", cur.places_tract_matched == "1")]
for name, a, b in link: rows.append([name, c(a.sum()), f1(100 * a.mean()), c(b.sum()), f1(100 * b.mean())])
table("linkage", "Linkage & All properties & \\% & In 2026 vintage & \\%", rows, "lrrrr")

# ---- subsidy categories among current properties ---------------------------------------------------------------------------------
cur = cur.copy(); cur["score"] = cur.last_inspection_score.astype(float); cur["units"] = pd.to_numeric(cur.total_units, errors="coerce")
cat = cur.subsidy_category.fillna("Not in current HUD layers")
rows = []
for k, g in cur.groupby(cat):
    if len(g) < 100: continue
    rows.append((len(g), [k.replace("&", "\\&"), c(len(g)), f1(g.units.median()) if g.units.notna().any() else "--", f1(g.score.mean()), f1(g.score.median()), f1(100 * (g.score < 60).mean()), f1(100 * (g.last_protocol == "NSPIRE").mean())]))
rows = [r for _, r in sorted(rows, key=lambda t: -t[0])]
table("subsidy", "Subsidy category & Properties & Median units & Mean score & Median & $<$60 (\\%) & NSPIRE (\\%)", rows, "lrrrrrr")
N["curFailPct"] = f1(100 * (cur.score < 60).mean()); N["curFailN"] = c((cur.score < 60).sum()); N["curNspirePct"] = f1(100 * (cur.last_protocol == "NSPIRE").mean())
N["curUnits"] = c(cur.units.sum()); N["curUnitsKnownPct"] = f1(100 * cur.units.notna().mean())

# ---- illustrative tract-context tabulation ---------------------------------------------------------------------------------
m = cur.merge(th[["tract_geoid_places", "places_housinsecu", "places_casthma", "places_ghlth"]], on="tract_geoid_places", how="inner")
m = m[m.last_protocol == "NSPIRE"].dropna(subset=["places_housinsecu"])
m["q"] = pd.qcut(m.places_housinsecu, 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"])
rows = []
for q, g in m.groupby("q", observed=True):
    rows.append([q, c(len(g)), f"{g.places_housinsecu.min():.1f}--{g.places_housinsecu.max():.1f}", f1(g.places_casthma.mean()), f1(g.score.mean()), f1(100 * (g.score < 60).mean())])
table("context", "Tract housing-insecurity quartile & Properties & Range (\\%) & Asthma (\\%) & Mean score & $<$60 (\\%)", rows, "lrrrrr")
N["ctxN"] = c(len(m)); N["ctxSpearman"] = f2(m[["places_housinsecu", "score"]].corr(method="spearman").iloc[0, 1])
N["ctxFailLow"] = rows[0][-1]; N["ctxFailHigh"] = rows[-1][-1]

# ---- data records table ---------------------------------------------------------------------------------
desc = {"ahcp_inspections.csv.gz": "One row per inspection", "ahcp_properties.csv": "One row per property",
        "ahcp_snapshots.csv.gz": "One row per source row", "ahcp_tract_health.csv": "One row per tract",
        "ahcp_ph_legacy_crosswalk.csv": "Candidate links"}
rows = []
for f, d_ in desc.items():
    df = pd.read_csv(os.path.join(P, f), dtype=str, usecols=[0]); ncol = len(pd.read_csv(os.path.join(P, f), nrows=0).columns)
    rows.append(["\\texttt{" + f.replace("ahcp_", "").replace("_", "\\_") + "}", d_, c(len(df)), ncol, f1(os.path.getsize(os.path.join(P, f)) / 1e6)])
    N["rows" + "".join(w.capitalize() for w in f.split(".")[0].replace("ahcp_", "").split("_"))] = c(len(df))
table("records", "File & Unit & Rows & Cols. & MB", rows, "@{}llrrr@{}")

# ---- worked example: one property's listings across vintages ----------------------------------------------------
ex = snap[snap.ahcp_property_id == "MF:800006156"].sort_values(["inspection_date", "vintage"])
rows = [[r.vintage, r.source_row, r.inspection_id if isinstance(r.inspection_id, str) else "--", r.inspection_date.strftime("%Y-%m-%d"), f"{r.inspection_score:g}", r.protocol_hud if isinstance(r.protocol_hud, str) else "--"] for r in ex.itertuples()]
table("example_snap", "Vintage & Row & HUD insp. ID & Date & Score & Protocol", rows, "rrllrl")
exi = insp[insp.ahcp_property_id == "MF:800006156"].sort_values("inspection_date")
rows = [[r.inspection_seq, r.inspection_date.strftime("%Y-%m-%d"), f"{r.inspection_score:g}", r.protocol, r.protocol_source.replace("_", "\\_"), f"{r.first_vintage}--{r.last_vintage}", r.score_conflict, "" if pd.isna(r.days_since_prev) else int(r.days_since_prev)] for r in exi.itertuples()]
table("example_insp", "Seq. & Date & Score & Protocol & Source & Vintages & Conflict & Days since prev.", rows, "rlrlllrr")
N["exSnapRows"] = len(ex); N["exInspRows"] = len(exi)

# ---- headline numbers from stats.json ---------------------------------------------------------------------------------
for k, v in S.items():
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        key = "S" + "".join(w.capitalize() for w in re.sub(r"\d+", lambda m_: {"2010": "TwentyTen", "2012": "TwentyTwelve", "1": "One"}.get(m_.group(), ""), k).split("_"))
        N[key] = c(v) if isinstance(v, int) else (f"{v:g}")
N["rawFiles"] = 18; N["nVintages"] = len(L.VINTAGES)
json.dump(N, open(os.path.join(OUT, "paper_stats.json"), "w"), indent=1)
with open(os.path.join(OUT, "numbers.tex"), "w") as fh:
    for k, v in sorted(N.items()):
        assert re.fullmatch(r"[A-Za-z]+", k), k
        fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
print(len(N), "numbers;", len(os.listdir(TB)), "tables")
