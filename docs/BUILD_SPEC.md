# AHCP v1.0 build spec

```
PROJECT:        Assisted Housing Condition Panel (AHCP) v1.0. Archetype: open dataset, with a rebuild tool (R package).
QUESTION:       What is each HUD-assisted property's physical inspection history, on one consistent set of
                identifiers, once HUD's overwritten "latest inspection" spreadsheets are stacked back together?
SOURCES:        1. HUD PD&R Physical Inspection Scores, 9 vintages x 2 programs (2011, 2015, 2016, 2018, 2019,
                   2020, 2021, 2025, 2026). https://www.huduser.gov/portal/datasets/pis.html  Public domain
                   (U.S. Government work). Accessed 2026-10-06.
                2. HUD eGIS layers: Multifamily Properties - Assisted; HUD Insured Multifamily Properties;
                   Public Housing Developments; Low-Income Housing Tax Credit Properties.
                   https://hudgis-hud.opendata.arcgis.com/  Public domain. Accessed 2026-10-06.
                3. Census Bureau 2020 cartographic boundary tracts (cb_2020_us_tract_500k). Public domain.
                4. CDC PLACES census-tract estimates (2020 tract geography). Public domain.
UNIT:           Inspection (one row per unique inspection) and property (one row per property).
                Property = REMS property ID (multifamily) or PIC development number (public housing).
MEASURES:       inspection_score      as published, 0-100; no rescaling across protocols
                protocol              HUD's flag where published (2025, 2026 files); otherwise inferred from
                                      inspection ID prefix and date; source of each value recorded
                history fields        sequence number, previous score/date, days since previous, score change
                reconciliation flags  score, date and property disagreements for one inspection across vintages
                tract_geoid_2020      point-in-polygon of HUD coordinates on Census 2020 tracts
                subsidy fields        program type, units, contract and insurance indicators from HUD layers
                lihtc link            HUD LIHTC project matched by address, then by proximity; match type kept
                health fields         CDC PLACES tract estimates joined on tract_geoid_2020
OUTPUTS:        data/processed/ahcp_inspections.csv.gz, ahcp_properties.csv, ahcp_snapshots.csv.gz,
                ahcp_tract_health.csv, ahcp_ph_legacy_crosswalk.csv, qa_report.txt, stats.json
                docs/CODEBOOK.md, LIMITATIONS.md, VERIFY_CHECKLIST.md, PUBLISH_GUIDE.md, NEXT_STEPS.md
                data/raw/PROVENANCE.txt; figures/; r/ahcp (R package)
VENUES:         GitHub repository, then Zenodo deposit for the DOI; data descriptor paper later.
VERIFY POINTS:  (1) protocol inference rule and NSPIRE start dates; (2) which value wins when vintages
                disagree on a score or date; (3) LIHTC match rule and distance threshold; (4) pre-2008 public
                housing project numbers are not linked to later development numbers; (5) five named
                spot checks against the HUD files; (6) R package run on the author's machine.
LICENSE:        Data and documents CC BY 4.0; code MIT.
ASSUMPTIONS:    Python pipeline is the tested build; the R package mirrors
                it and is untested until the author runs it. The panel covers the 9 vintages HUD still
                publishes; inspections superseded between vintages are not recoverable from these files.
```
