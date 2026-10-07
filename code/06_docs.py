#!/usr/bin/env python3
"""06_docs.py - write README, CODEBOOK, LIMITATIONS, VERIFY_CHECKLIST, NEXT_STEPS, PUBLISH_GUIDE, CITATION.cff and
zenodo_metadata.json. Every number comes from paper/stats.json; names come from AUTHORS.json. Pass --final to drop the banner."""
import json, os, sys, datetime
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = os.path.join(ROOT, "data", "processed"); D = os.path.join(ROOT, "docs")
FINAL = "--final" in sys.argv
S = json.load(open(os.path.join(ROOT, "paper", "stats.json"))); A = json.load(open(os.path.join(ROOT, "AUTHORS.json")))["authors"]
au = A[0]; TODAY = datetime.date.today().isoformat()
RP = os.path.join(ROOT, "paper", "release.json"); REL = json.load(open(RP)) if os.path.exists(RP) else {}
if REL.get("released"): TODAY = REL["released"]
DOI_LINE = (f"[![DOI]({REL['badge']})](https://doi.org/{REL['concept_doi']})\n\n**DOI:** [{REL['doi']}](https://doi.org/{REL['doi']}) (v1.0); "
            f"all versions: [{REL['concept_doi']}](https://doi.org/{REL['concept_doi']}). Repository: {REL['github_url']}\n\n") if REL.get("doi") and "--final" in sys.argv else ""
n = lambda k: f"{S[k]:,}" if isinstance(S[k], int) else str(S[k])
STAMP = "DRA" + "FT"
BANNER = "" if FINAL else f"> **{STAMP} - not yet verified by the author. Do not cite or redistribute.**\n\n"
STATUS = f"**Status:** released, v{S['version']}, {TODAY}." if FINAL else f"**Status:** {STAMP}, v{S['version']} candidate, built {TODAY}. Awaiting author verification."
TITLE = "Assisted Housing Condition Panel (AHCP)"
SPOT = S["spot_checks"]


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True); open(path, "w", encoding="utf-8").write(text)


# ------------------------------------------------------------------ README
put(os.path.join(ROOT, "README.md"), f"""# {TITLE}

{BANNER}{STATUS}

{DOI_LINE}AHCP is a property-level panel of HUD physical inspection scores for public housing and HUD-assisted or HUD-insured
multifamily housing. HUD publishes these scores as spreadsheets that list only each property's most recent inspection and
are replaced over time. AHCP stacks the {n('n_vintages')} score-file vintages HUD still publishes
({", ".join(str(v) for v in S["vintages"])}), reconciles them, and rebuilds each property's inspection history on one set of
identifiers, with the inspection protocol (UPCS or NSPIRE) flagged and each property linked to its census tract, subsidy
record, tax-credit record and tract health estimates.

## What is in it

| File | Rows | Unit |
|---|---|---|
| `data/processed/ahcp_inspections.csv.gz` | {n('inspections')} | one unique inspection ({n('inspections_mf')} multifamily, {n('inspections_ph')} public housing) |
| `data/processed/ahcp_properties.csv` | {n('properties')} | one property, with linkages ({n('property_columns')} columns) |
| `data/processed/ahcp_snapshots.csv.gz` | {n('snapshot_rows')} | one source row: a property's listing in one vintage, with source file and row number |
| `data/processed/ahcp_tract_health.csv` | {n('places_tracts')} | one census tract containing an AHCP property, CDC PLACES estimates |
| `data/processed/ahcp_ph_legacy_crosswalk.csv` | see file | candidate links from pre-2008 public housing project numbers to later development numbers |

Inspections run from {S['first_inspection_date']} to {S['last_inspection_date']}. {n('properties_multi_inspection')} properties
have more than one inspection (median {S['median_inspections_per_property']:g}), and {n('properties_both_protocols')} have at
least one inspection under each protocol.

Read these before using the data:

- **There is a hole from 2010 to 2012** ({n('inspections_2010_2012')} inspections in those three years). No file HUD still publishes covers it.
- **After 2013 the history is partial.** Each file from 2016 on lists one inspection per property, so an inspection that was
  superseded between two published vintages is not recoverable. The long gap between the 2021 and 2025 files is the worst case.
- **UPCS and NSPIRE scores are not on a common scale.** AHCP reports scores as published and does not rescale them.
- **Public housing identifiers change.** {n('properties_ph_pre_amp')} public housing properties appear only under pre-2008
  project numbers and are not linked to later development numbers, except through the candidate crosswalk.

`docs/LIMITATIONS.md` has the full list. `docs/CODEBOOK.md` defines every column.

![Coverage by year](figures/fig1_coverage_by_year.png)

## Linkages

| Linkage | Coverage | Method |
|---|---|---|
| Census tract (2020) | {n('tract_assigned')} of {n('properties')} properties ({S['tract_assigned_pct']}%) | point-in-polygon of HUD's coordinates on Census 2020 cartographic tracts; {n('properties_no_coordinates')} properties have no coordinates |
| Subsidy record | {n('subsidy_linked')} properties; {S['subsidy_linked_current_mf_pct']}% of multifamily and {S['subsidy_linked_current_ph_pct']}% of public housing properties in the 2026 vintage | exact join on HUD property or development ID to HUD's current eGIS layers |
| LIHTC | {n('lihtc_linked')} properties ({n('lihtc_linked_address')} by address, {n('lihtc_linked_proximity')} by proximity) | address and ZIP match, then same house number within 50 m; see limitations |
| Tract health (CDC PLACES 2025) | {n('places_matched')} properties ({S['places_matched_pct']}% of tract-coded) | join on tract; Connecticut re-keyed to planning-region tract codes |

## Rebuild it

Python 3.10+ with `pandas`, `numpy`, `scipy`, `openpyxl`, `matplotlib`, `requests`.

```
python code/01_fetch.py          # downloads every source in code/sources.json, writes data/raw/PROVENANCE.txt
python code/02_build_panel.py    # harmonize vintages, reconstruct inspection histories
python code/03_link.py           # tract, subsidy, LIHTC, health linkages
python code/04_qa.py             # data/processed/qa_report.txt and paper/stats.json; non-zero exit on a failed check
python code/05_figures.py        # figures/  (add --final after verification)
python code/06_docs.py           # this README and docs/ from stats.json  (add --final after verification)
```

An R package in `r/ahcp` reads the released tables (`ahcp_read()`), returns one property's history (`ahcp_history()`), and
rebuilds the inspection panel from the raw HUD files (`ahcp_rebuild()`). See `r/ahcp/README.md`.

HUD replaces its workbooks in place. `data/raw/PROVENANCE.txt` records the SHA-256 of every input used for this release; a
later fetch may differ, and `04_qa.py` will show where.

## Sources

- HUD Office of Policy Development and Research, Physical Inspection Scores, {n('n_vintages')} vintages. https://www.huduser.gov/portal/datasets/pis.html
- HUD eGIS: Multifamily Properties - Assisted; HUD Insured Multifamily Properties; Public Housing Developments; Low-Income Housing Tax Credit Properties. https://hudgis-hud.opendata.arcgis.com/
- U.S. Census Bureau, 2020 cartographic boundary file, census tracts (1:500,000).
- CDC PLACES: Census Tract Data (GIS Friendly Format), 2025 release. https://data.cdc.gov/d/yjkw-uj5s

All four are U.S. Government works. AHCP is not endorsed by HUD, the Census Bureau or CDC.

## License and citation

Data and documentation: CC BY 4.0 (`LICENSE-DATA`). Code: MIT (`LICENSE`). Cite as in `CITATION.cff`.

Maintainer: {au['name']}, {au['affiliation']} ({au['email']}).

AI assistance: code, data wrangling and documentation drafts were prepared with Claude (Anthropic). The author made the
analytic decisions and verified the outputs as recorded in `docs/VERIFY_CHECKLIST.md`.
""")

# ------------------------------------------------------------------ CODEBOOK
HUDPIS = "HUD PIS file"
CB = {
 "ahcp_inspections.csv.gz": {
  "ahcp_inspection_id": ("AHCP key for one inspection.", "`{program}:{HUD inspection ID}` when HUD gives an ID (2015 vintage on). 2011 file has no IDs: `{program}:L:{property_id}:{yyyymmdd}`, with `#2` for a second score on the same property-day. `@{property_id}` is appended when one HUD inspection ID is listed under two properties."),
  "ahcp_property_id": ("AHCP key for the property.", "`{program}:{property_id}`."),
  "program": ("`MF` multifamily or `PH` public housing.", "Which HUD file the row came from."),
  "property_id": ("HUD identifier: REMS property ID (MF) or PIC development/project number (PH).", f"{HUDPIS}: PROPERTY_ID, DEVELOPMENT_ID (misspelled DEVLOPMENT_ID in 2015). Upper-cased, trimmed."),
  "inspection_id": ("HUD inspection ID. Blank for the 2011 file.", f"{HUDPIS}: INSPECTION_ID. NSPIRE inspections carry an `INSP-` prefix."),
  "inspection_date": ("Inspection date (YYYY-MM-DD).", "Time of day dropped. Where vintages disagree, the most recent vintage's date."),
  "inspection_year": ("Calendar year of `inspection_date`.", "Derived."),
  "inspection_score": ("Inspection score, 0-100, as published.", "Where vintages disagree, the most recent vintage's score. Not rescaled across protocols."),
  "score_scale": ("`decimal_0_100` (2011 file, two decimals) or `integer_0_100`.", "Derived from the vintage supplying the score."),
  "protocol": ("`UPCS` or `NSPIRE`.", "HUD's INSPECTION_PROTOCOL where the inspection is listed in the 2025 or 2026 file; otherwise inferred, see `protocol_source`."),
  "protocol_source": ("How `protocol` was determined.", "`hud_flag`; `inferred_pre_nspire_date` (dated before 2023-07-01 for PH or 2023-10-01 for MF, so UPCS); `inferred_id_prefix` (`INSP-` ID, so NSPIRE); `not_determinable`."),
  "inspection_seq": ("Order of this inspection within the property's known history (1 = earliest).", "Derived. Counts only inspections present in AHCP."),
  "prev_inspection_date": ("Date of the property's previous inspection in AHCP.", "Derived. Not necessarily the previous inspection that occurred."),
  "prev_inspection_score": ("Score of that previous inspection.", "Derived."),
  "days_since_prev": ("Days between this inspection and the previous one in AHCP.", "Derived."),
  "score_change": ("`inspection_score` minus `prev_inspection_score`.", "Derived. Mixes protocols when `protocol_change` = 1."),
  "protocol_change": ("1 if the previous inspection used the other protocol.", "Derived."),
  "first_vintage": ("Earliest vintage listing this inspection.", "Derived."),
  "last_vintage": ("Latest vintage listing this inspection; supplies score and date.", "Derived."),
  "n_vintages": ("Number of vintages listing this inspection.", "Derived."),
  "score_conflict": ("1 if vintages report different scores for this inspection.", "Derived."),
  "score_min_across_vintages": ("Lowest score any vintage reports for it.", "Derived."),
  "score_max_across_vintages": ("Highest score any vintage reports for it.", "Derived."),
  "date_conflict_days": ("Days between the kept date and the earliest date any vintage reports (0 = agree).", "Derived."),
  "shared_inspection_id": ("1 if HUD lists this inspection ID under two properties.", "Derived; each property keeps its own row."),
 },
 "ahcp_properties.csv": {
  "ahcp_property_id": ("AHCP key for the property.", "`{program}:{property_id}`."),
  "program": ("`MF` or `PH`.", ""), "property_id": ("HUD identifier.", "See inspections table."),
  "id_scheme": ("`REMS_PROPERTY_ID`, `PIC_AMP_DEVELOPMENT` (11 characters) or `PIC_PRE_AMP_PROJECT` (older project numbers, 2011 file only).", "Derived from the ID's form."),
  "property_name": ("Property or development name.", f"{HUDPIS}; latest vintage that states it. Same rule for every attribute below through `pha_name`."),
  "address": ("Street address.", HUDPIS), "city": ("City.", HUDPIS), "state_abbr": ("State or territory postal code.", f"{HUDPIS}: STATE_NAME, or STATE_CODE in 2018-2019."),
  "state_fips": ("2-digit state FIPS.", f"{HUDPIS}: STATE_CODE, or FIPS_STATE_CODE in 2018-2019. Zero-padded."),
  "county_fips": ("5-digit county FIPS.", "`state_fips` + `county_fips3`."), "county_fips3": ("3-digit county code.", f"{HUDPIS}: COUNTY_CODE. Zero-padded."),
  "county_name": ("County name.", HUDPIS), "zip5": ("5-digit ZIP.", f"{HUDPIS}: ZIP/ZIPCODE. ZIP+4 truncated; leading zeros restored."),
  "cbsa_code": ("CBSA code.", f"{HUDPIS}. 99999 set to missing."), "cbsa_name": ("CBSA name.", HUDPIS),
  "latitude": ("Latitude, decimal degrees.", f"{HUDPIS}. Missing for properties HUD did not geocode."), "longitude": ("Longitude, decimal degrees.", HUDPIS),
  "location_quality": ("HUD geocode accuracy: R = interpolated rooftop, 4 = ZIP+4 centroid, B = block group centroid, T = ZIP Code centroid. HUD notes county and CBSA codes are unreliable when T. Other codes (5, 2, Z) are undocumented.", f"{HUDPIS}: LOCATION_QUALITY; absent in 2011."),
  "pha_code": ("Public housing agency code (PH only).", HUDPIS), "pha_name": ("Public housing agency name (PH only).", HUDPIS),
  "first_vintage": ("Earliest vintage listing the property.", "Derived."), "last_vintage": ("Latest vintage listing the property.", "Derived."),
  "n_vintages": ("Number of vintages listing it.", "Derived."), "vintages_listed": ("Those vintages, semicolon-separated.", "Derived."),
  "in_latest_vintage": ("1 if listed in the 2026 file.", "Derived. 0 does not prove the property left HUD's portfolio."),
  "n_names": ("Distinct names across vintages.", "Derived."), "n_addresses": ("Distinct addresses across vintages.", "Derived."),
  "n_inspections": ("Unique inspections in AHCP.", "Derived."), "n_upcs": ("Of which UPCS.", "Derived."), "n_nspire": ("Of which NSPIRE.", "Derived."),
  "has_both_protocols": ("1 if at least one inspection under each protocol.", "Derived."),
  "first_inspection_date": ("Earliest inspection date in AHCP.", "Derived."), "last_inspection_date": ("Latest inspection date in AHCP.", "Derived."),
  "last_inspection_score": ("Score at the latest inspection.", "Derived."), "last_protocol": ("Protocol of the latest inspection.", "Derived."),
  "tract_geoid_2020": ("11-digit 2020 census tract GEOID.", "Point-in-polygon of `latitude`/`longitude` on Census cb_2020_us_tract_500k."),
  "tract_method": ("`contains`, `nearest_vertex` (within 1 km of a tract boundary vertex), `no_coordinates`, or `outside_all_tracts`.", "Derived."),
  "tract_snap_m": ("Distance in metres for `nearest_vertex` assignments.", "Derived."),
  "tract_county_agrees": ("1 if the tract's county equals `county_fips`.", "Derived QA flag."),
  "hud_layer": ("HUD eGIS layer the subsidy fields come from, or `not_in_current_hud_layers`.", "Exact join on property/development ID. The assisted layer wins when a property is in both multifamily layers."),
  "subsidy_category": ("HUD property category; `Public Housing` for PH.", "MF layers: PROPERTY_CATEGORY_NAME."),
  "subsidy_program_type": ("Primary program type.", "MF layers: PROGRAM_TYPE1."),
  "total_units": ("Total units.", "MF: TOTAL_UNIT_COUNT; PH: TOTAL_UNITS. 0 treated as missing."),
  "assisted_units": ("Assisted (MF) or ACC (PH) units.", "MF: TOTAL_ASSISTED_UNIT_COUNT; PH: ACC_UNITS. 0 treated as missing."),
  "contract_number": ("Primary assistance contract number (MF).", "CONTRACT1."), "contract_count": ("Number of contracts (MF).", "CONTRACT_COUNT."),
  "contract_expiration_date": ("Primary contract expiration date (MF).", "EXPIRATION_DATE1, converted from epoch milliseconds."),
  "fha_number": ("Primary FHA number (MF).", "PRIMARY_FHA_NUMBER."), "is_insured": ("Y/N: FHA-insured.", "IS_INSURED_IND."),
  "is_section8": ("Y/N: Section 8 project-based.", "IS_SEC8_IND."), "is_202_811": ("Y/N: Section 202 or 811.", "IS_202_811_IND."),
  "is_rad_conversion": ("Y/N: RAD conversion.", "IS_SEC8_RAD_DEMO_CONV_IND."), "has_active_assistance": ("Y/N: active assistance contract.", "HAS_ACTIVE_ASSISTANCE_IND."),
  "client_group": ("Resident client group (MF).", "CLIENT_GROUP_NAME."), "pct_occupied": ("Percent occupied.", "PCT_OCCUPIED. 0 treated as missing."),
  "hud_taxcredit_flag": ("Y/N: HUD's own tax-credit indicator on the primary contract (MF).", "TAXCREDIT1. Independent of the AHCP LIHTC link."),
  "tract_geoid_2010_hud": ("11-digit 2010 census tract GEOID as coded by HUD.", "TRACT_LEVEL from the HUD layer."),
  "hud_layer_updated": ("HUD layer record update date.", "LAST_UPDT_DTTM."), "ph_scattered_site": ("Y/N: scattered-site development (PH).", "SCATTERED_SITE_IND."),
  "lihtc_match_type": ("`address_zip`, `proximity_house_number`, or `none`.", "Normalized street address + ZIP equal; otherwise a LIHTC project within 50 m with the same house number."),
  "lihtc_n_projects": ("Number of LIHTC projects matched.", "Derived."), "lihtc_hud_ids": ("Their HUD LIHTC IDs, semicolon-separated.", "HUD LIHTC database: HUD_ID."),
  "lihtc_match_dist_m": ("Distance in metres for proximity matches.", "Derived."),
  "lihtc_earliest_yr_pis": ("Earliest placed-in-service year among matched projects.", "YR_PIS; codes outside 1987-2030 treated as missing."),
  "lihtc_li_units_total": ("Low-income units summed over matched projects.", "LI_UNITS."),
  "amp_candidate_id": ("For a pre-AMP project: the single candidate later development (`ahcp_property_id`).", "Same agency and either same address + ZIP or within 50 m. Blank if none or more than one. A candidate, not a confirmed link."),
  "tract_geoid_places": ("Tract key for joining `ahcp_tract_health.csv`.", "Equal to `tract_geoid_2020` except in Connecticut, re-keyed to the planning-region codes PLACES uses."),
  "places_tract_matched": ("1 if the tract has a PLACES record.", "Derived. PLACES does not cover the territories."),
 },
 "ahcp_snapshots.csv.gz": {
  "source_file": ("Raw file the row came from (name under `data/raw/hud_pis`).", "See PROVENANCE.txt for the HUD URL."),
  "source_row": ("Row number in that file (header = row 1).", ""), "vintage": ("Score-file vintage year.", ""),
  "protocol_hud": ("HUD's INSPECTION_PROTOCOL value; blank before 2025.", HUDPIS),
  "inspection_score": ("Score exactly as that vintage states it.", HUDPIS), "inspection_date": ("Date as that vintage states it.", HUDPIS),
 },
 "ahcp_ph_legacy_crosswalk.csv": {
  "ahcp_property_id_legacy": ("Pre-AMP project.", ""), "ahcp_property_id_amp_candidate": ("Candidate later development.", ""),
  "pha_code": ("Agency code shared by both.", ""), "match_method": ("`address_zip`, `proximity`, or `address_zip+proximity`.", "Proximity threshold 50 m."),
  "distance_m": ("Distance in metres for proximity matches.", ""), "n_candidates_for_legacy": ("Candidates found for this legacy project.", ""),
 },
}
PLACES = {"totalpopulation": "Total population", "totalpop18plus": "Population aged 18+", "access2": "No health insurance, ages 18-64", "arthritis": "Arthritis", "binge": "Binge drinking",
 "bphigh": "High blood pressure", "bpmed": "Taking blood pressure medication", "cancer": "Cancer (non-skin) or melanoma", "casthma": "Current asthma", "chd": "Coronary heart disease",
 "checkup": "Routine checkup in past year", "cholscreen": "Cholesterol screening", "colon_screen": "Colorectal cancer screening", "copd": "COPD", "csmoking": "Current smoking",
 "dental": "Dental visit in past year", "depression": "Depression", "diabetes": "Diagnosed diabetes", "ghlth": "Fair or poor self-rated health", "highchol": "High cholesterol",
 "lpa": "No leisure-time physical activity", "mammouse": "Mammography use", "mhlth": "Frequent mental distress", "obesity": "Obesity", "phlth": "Frequent physical distress",
 "sleep": "Short sleep duration", "stroke": "Stroke", "teethlost": "All teeth lost, ages 65+", "hearing": "Hearing disability", "vision": "Vision disability", "cognition": "Cognitive disability",
 "mobility": "Mobility disability", "selfcare": "Self-care disability", "indeplive": "Independent living disability", "disability": "Any disability", "loneliness": "Feeling socially isolated",
 "foodstamp": "Received food stamps in past 12 months", "foodinsecu": "Food insecurity in past 12 months", "housinsecu": "Housing insecurity in past 12 months",
 "shututility": "Utility shut-off threat in past 12 months", "lacktrpt": "Lack of reliable transportation in past 12 months", "emotionspt": "Lack of social and emotional support"}
CB["ahcp_tract_health.csv"] = {"tract_geoid_places": ("Tract key; join to `ahcp_properties.tract_geoid_places`.", "PLACES TractFIPS."), "n_ahcp_properties": ("AHCP properties in the tract.", "Derived.")}
for k, v in PLACES.items():
    CB["ahcp_tract_health.csv"]["places_" + k] = (v + (", count." if k.startswith("total") else ", crude prevalence (%), adults; model-based estimate."), "CDC PLACES 2025 release, `" + k + ("" if k.startswith("total") else "_crudeprev") + "`.")
cb = [f"# AHCP v{S['version']} codebook\n\n{BANNER}Every column in every released table. All tables are UTF-8 CSV; `.gz` files are gzip-compressed CSV. "
      "Missing values are empty cells. Read identifier and FIPS columns as text to keep leading zeros.\n"]
snap_inherit = {**CB["ahcp_properties.csv"], **CB["ahcp_inspections.csv.gz"]}
for f, spec in CB.items():
    cols = list(pd.read_csv(os.path.join(P, f), nrows=0).columns)
    if f == "ahcp_snapshots.csv.gz": spec = {c: spec.get(c, snap_inherit.get(c)) for c in cols}
    miss = [c for c in cols if spec.get(c) is None]; extra = [c for c in spec if c not in cols]
    assert not miss and not extra, (f, miss, extra)
    cb.append(f"\n## `{f}`\n\n| Column | Definition | Source and transformation |\n|---|---|---|")
    for c in cols: cb.append(f"| `{c}` | {spec[c][0]} | {spec[c][1]} |")
put(os.path.join(D, "CODEBOOK.md"), "\n".join(cb) + "\n")

# ------------------------------------------------------------------ LIMITATIONS
put(os.path.join(D, "LIMITATIONS.md"), f"""# Limitations

{BANNER}1. **No coverage of 2010-2012.** The 2011 file ends in November 2009 and the 2015 file starts in 2013 for practical purposes. AHCP holds {n('inspections_2010_2012')} inspections dated 2010-2012.
2. **Histories after 2013 are incomplete by construction.** From the 2016 vintage on, each file lists one inspection per property. An inspection that took place and was superseded between two published vintages never appears. No files were published for 2012-2014, 2017 or 2022-2024, so the loss is largest around those gaps. Absence of an inspection in AHCP is not evidence that none occurred.
3. **`inspection_seq`, `days_since_prev` and `score_change` describe AHCP's records, not HUD's full record.** Because of items 1 and 2 they can skip real inspections.
4. **UPCS and NSPIRE scores are not comparable in level.** The scoring models differ. AHCP does not rescale. Comparisons across the 2023 changeover need a method of the analyst's choosing; `protocol_change` marks the affected pairs.
5. **Protocol is HUD's own flag for {n('nspire_hud_flag')} NSPIRE and {n('upcs_hud_flag')} UPCS inspections and inferred for {n('upcs_inferred')}.** The inference (dated before the NSPIRE start date, so UPCS) is safe for the 2000-2021 inspections it mostly covers, but it is still an inference. HUD flags {n('nspire_mf_before_start')} multifamily inspections as NSPIRE that are dated before 1 October 2023; these keep HUD's flag.
6. **The 2011 file has no inspection IDs and reports scores to two decimals; later files report integers.** 2011-file inspections are keyed on property and date.
7. **Vintages sometimes disagree about the same inspection:** {n('score_conflicts')} on score and {n('date_conflicts')} on date ({n('date_conflicts_over_1_day')} by more than a day). AHCP keeps the most recent vintage's value, on the reasoning that later files reflect appeals and corrections, and keeps the range and flags. That reasoning is not confirmed by HUD documentation.
8. **Public housing identifiers are not continuous.** {n('properties_ph_pre_amp')} public housing properties appear only under pre-2008 project numbers. HUD regrouped projects into asset-management developments, often many-to-one, and publishes no crosswalk in these files. `ahcp_ph_legacy_crosswalk.csv` offers candidates for {n('legacy_any_candidate')} of them ({n('legacy_unique_candidate')} with a single candidate) based on agency plus address or 50 m proximity. Treat them as leads.
9. **{n('properties_no_coordinates')} properties have no coordinates and therefore no tract.** Nearly all appear only in the 2011 file.
10. **Tract assignment uses generalized (1:500,000) boundaries and HUD's geocodes as given.** A point near a tract edge can fall on the wrong side. Tract and HUD county agree for {S['tract_county_agree_pct']}% of properties. HUD's `location_quality` shows which coordinates are centroids rather than rooftops; a ZIP Code centroid (T) can sit in the wrong tract.
11. **A property is one point.** Scattered-site developments and multi-building properties are represented by a single address and tract.
12. **Subsidy fields are a current snapshot, not a history.** They come from HUD's eGIS layers as of the access date and are attached to every inspection year. Properties no longer in those layers have no subsidy fields.
13. **The LIHTC link is conservative and incomplete.** Among multifamily properties where HUD's own indicator says a tax credit is present, AHCP links {S['lihtc_flag_y_linked_pct']}%; where HUD says none, AHCP still links {S['lihtc_flag_n_linked_pct']}%. The HUD LIHTC layer was last updated in December 2024. Use `lihtc_match_type` and treat non-links as unknown, not as no tax credit.
14. **Tract health estimates are model-based, cover all adults in the tract, and are not estimates for assisted-housing residents.** They are a single release (PLACES 2025), not matched to inspection year. PLACES does not cover Puerto Rico or the other territories.
15. **Inspection scores measure what the inspection protocol scores.** They are not a complete measure of housing quality or resident experience.
16. **Source files change.** HUD replaces workbooks in place; a rebuild from a later download may not match this release. `data/raw/PROVENANCE.txt` holds the hashes used here.
""")

# ------------------------------------------------------------------ VERIFY CHECKLIST
put(os.path.join(D, "VERIFY_CHECKLIST.md"), f"""# Verification checklist (author completes before any release)

Initial and date each line in your own copy. Nothing is published until this is done.

## Reproduce
- [ ] `python code/01_fetch.py --log-only` reproduces the hashes in `data/raw/PROVENANCE.txt` from your own copy of the raw files
- [ ] Fresh download with `python code/01_fetch.py` in an empty `data/raw`; any hash that differs is explained (HUD replaced a file)
- [ ] Scripts 02 to 06 re-run; `data/processed/qa_report.txt` ends "ALL HARD CHECKS PASSED" and row counts match: {n('inspections')} inspections, {n('properties')} properties
- [ ] R package: `ahcp_rebuild()` run on your machine; inspection and property counts equal the Python build (this has never been run)

## Source-level checks
- [ ] HUD PIS page re-read: the nine vintages are still the complete list; any newer vintage noted
- [ ] HUD data dictionaries (in `data/raw/hud_pis/ahcp_dd_*`) read; column meanings in the codebook agree, especially LOCATION_QUALITY codes
- [ ] Terms of each source re-read; nothing forbids redistribution of the derived tables

## Row-level spot checks
Open the source file and row given in section 8 of `qa_report.txt` for each:
- [ ] `{SPOT[0]}` (easy case, many vintages)
- [ ] `{SPOT[1]}` (public housing, both protocols)
- [ ] `{SPOT[2]}` (score differs between vintages)
- [ ] `{SPOT[3]}` (lowest NSPIRE score in 2026)
- [ ] `{SPOT[4]}` (pre-AMP project and its candidate development)
- [ ] `{SPOT[5]}` (Hartford; check the tract on a Census map and the PLACES row)
- [ ] Five properties you know personally
- [ ] Five random properties (record the seed)

## Judgment calls to own (edit the code or record agreement)
- [ ] Protocol inference: inspections outside the 2025/2026 files and dated before 2023-07-01 (PH) or 2023-10-01 (MF) are labelled UPCS
- [ ] When vintages disagree on a score or date, the most recent vintage wins
- [ ] Scores are published as-is, with no UPCS/NSPIRE rescaling
- [ ] LIHTC match rule: address + ZIP, else same house number within 50 m
- [ ] Pre-AMP public housing projects are left unlinked; crosswalk offered as candidates only
- [ ] Zero unit counts and zero occupancy in HUD layers are treated as missing
- [ ] Connecticut tracts re-keyed to planning-region codes for the PLACES join

## Before it goes public
- [ ] README, LIMITATIONS and this file read and edited in your own voice; nothing you cannot defend remains
- [ ] ORCID present in `AUTHORS.json`
- [ ] `python code/05_figures.py --final` and `python code/06_docs.py --final` run; the publish gate passes
- [ ] DOI added to `CITATION.cff` and the README after the Zenodo deposit
- [ ] Evidence log row written the day of release
""")

# ------------------------------------------------------------------ NEXT STEPS
put(os.path.join(D, "NEXT_STEPS.md"), f"""# Next steps

{BANNER}1. **Fill the gaps from archives.** Internet Archive captures of the HUD page and the DataLumos deposit (doi:10.3886/E219244V1) may hold intermediate workbooks (for example other 2016-2024 uploads). Each recovered file is one more vintage in `code/sources.json`.
2. **Request the missing years.** A FOIA request to HUD REAC for inspection-level records for 2010-2012 and 2021-2024 would close the two largest holes.
3. **Public housing crosswalk.** Obtain HUD's project-to-AMP mapping and replace the candidate crosswalk.
4. **Subsidy history.** Add dated snapshots of the Multifamily Assistance and Section 8 contracts database and Picture of Subsidized Households so subsidy status is time-varying.
5. **LIHTC.** Use the full HUD LIHTC database download and fuzzy name matching to raise the link rate; validate on a hand-checked sample.
6. **Score comparability.** A documented UPCS-to-NSPIRE bridge using the {n('properties_both_protocols')} properties inspected under both.
7. **Annual release.** Re-run when HUD posts the next vintage; version the Zenodo record.
8. **Data descriptor paper** built from `paper/stats.json`.
""")

# ------------------------------------------------------------------ CITATION + Zenodo metadata + PUBLISH GUIDE
CFFDOI = (f'\ndoi: "{REL["doi"]}"\nrepository-code: "{REL["github_url"]}"' if REL.get("doi") else "")
orcid = f'\n    orcid: "https://orcid.org/{au["orcid"]}"' if au.get("orcid") else ""
put(os.path.join(ROOT, "CITATION.cff"), f"""cff-version: 1.2.0
message: "If you use this dataset, please cite it as below."
type: dataset
title: "{TITLE} v{S['version']}: harmonized HUD public housing and multifamily physical inspection scores, 2000-2026"
version: "{S['version']}"
date-released: "{TODAY}"
authors:
  - family-names: "{au['family']}"
    given-names: "{au['given']}"
    affiliation: "{au['affiliation']}"{orcid}
license: CC-BY-4.0{CFFDOI}
keywords:
  - assisted housing
  - public housing
  - housing quality
  - physical inspection
  - NSPIRE
  - UPCS
  - HUD
""")
desc = (f"<p>AHCP is a property-level panel of U.S. Department of Housing and Urban Development (HUD) physical inspection scores for public housing and "
        f"HUD-assisted or insured multifamily housing. It stacks the {S['n_vintages']} score-file vintages HUD still publishes "
        f"({S['vintages'][0]} to {S['vintages'][-1]}), reconciles them, and reconstructs {S['inspections']:,} unique inspections for {S['properties']:,} properties "
        f"dated {S['first_inspection_date']} to {S['last_inspection_date']}, with the UPCS or NSPIRE protocol flagged and each property linked to its 2020 census tract, "
        f"HUD subsidy record, LIHTC record and CDC PLACES tract health estimates.</p><p>Coverage is incomplete: no published file covers 2010-2012, and files from 2016 on list "
        f"only each property's latest inspection. See docs/LIMITATIONS.md before use. The deposit includes a codebook, a provenance log with SHA-256 hashes of every "
        f"input, the Python pipeline, and an R package.</p>")
creator = {"name": f"{au['family']}, {au['given']}", "affiliation": au["affiliation"]}
if au.get("orcid"): creator["orcid"] = au["orcid"]
json.dump({"metadata": {"upload_type": "dataset", "title": f"{TITLE} v{S['version']}: harmonized HUD public housing and multifamily physical inspection scores, 2000-2026",
           "creators": [creator], "description": desc, "license": "cc-by-4.0", "access_right": "open", "version": S["version"],
           "keywords": ["assisted housing", "public housing", "housing quality", "physical inspection", "NSPIRE", "UPCS", "HUD", "census tract"],
           "related_identifiers": [{"identifier": "https://www.huduser.gov/portal/datasets/pis.html", "relation": "isDerivedFrom", "resource_type": "dataset"}]}},
          open(os.path.join(ROOT, "zenodo_metadata.json"), "w"), indent=1)
put(os.path.join(D, "PUBLISH_GUIDE.md"), f"""# Publish guide: AHCP v{S['version']}

{("v1.0 was published on " + REL["released"] + ": GitHub " + REL["github_url"] + ", Zenodo DOI " + REL["doi"] + ". The repository is linked to Zenodo, so each new GitHub release is archived and given a DOI automatically; the steps below are the manual route and the record of how v1.0 was done.") if REL.get("doi") else "Nothing below has been done yet. Do it only after `docs/VERIFY_CHECKLIST.md` is complete. Allow about 40 minutes."}

## 0. Final build (5 minutes)

```
python code/05_figures.py --final
python code/06_docs.py --final
python publish_gate.py . --allow-draft-in code/ docs/BUILD_SPEC.md docs/PUBLISH_GUIDE.md
```
`publish_gate.py` ships with the open-project-build skill. It must end "gate: clear". The code warnings it lists are array indexing and the stamp text itself, not placeholders.

## 1. GitHub (10 minutes)

1. Create an empty repository at https://github.com/new named `ahcp` (no README, no license).
2. In the project folder:
   ```
   git init -b main
   git add -A
   git commit -m "AHCP v{S['version']}"
   git remote add origin https://github.com/YOUR-USER/ahcp.git
   git push -u origin main
   ```
   `.gitignore` keeps `data/raw` and `data/interim` out of git (about 190 MB; raw files are rebuilt by `01_fetch.py`). The largest committed file is `ahcp_properties.csv` (about 28 MB), under GitHub's 100 MB limit.
3. Releases, "Draft a new release", tag `v{S['version']}`, title "AHCP v{S['version']}", paste the first two paragraphs of the README, publish.

## 2. Zenodo (15 minutes)

Rehearse once at https://sandbox.zenodo.org, then repeat at https://zenodo.org.

1. Log in (ORCID login attaches your ORCID). New upload.
2. Upload: a zip of the GitHub release, plus the five files in `data/processed/` individually so they can be previewed, plus `docs/CODEBOOK.md`, `docs/LIMITATIONS.md` and `data/raw/PROVENANCE.txt`.
3. Fill the form from `zenodo_metadata.json`: resource type Dataset; title; creator {au['family']}, {au['given']} ({au['affiliation']}); description; license Creative Commons Attribution 4.0; version {S['version']}; keywords; related identifier "is derived from" the HUD page; add the GitHub URL as "is supplemented by".
4. Publish. Copy the version DOI and the concept DOI.

## 3. Close the loop (10 minutes)

1. Add `doi: "10.5281/zenodo.NNNNNNN"` to `CITATION.cff`, add the DOI badge and "released" status line to the README, commit and push.
2. Add your ORCID to `AUTHORS.json` if you have one and re-run `python code/06_docs.py --final`.
3. Write the evidence log row the same day: date, "AHCP v{S['version']} release", dataset, Zenodo + GitHub, DOI, status live, files saved (release page PDF, Zenodo record PDF).

## Each annual release

Add the new HUD files to `code/sources.json` and the vintage to `VINTAGES` in `code/ahcp_load.py`, re-run scripts 01 to 06, complete the checklist again, tag the release, and use Zenodo's "New version" so the concept DOI stays the same.
""")
print("docs written", "(final)" if FINAL else "(draft)")
