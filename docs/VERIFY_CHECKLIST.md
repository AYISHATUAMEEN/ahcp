# Verification checklist (author completes before any release)

Initial and date each line in your own copy. Nothing is published until this is done.

## Reproduce
- [ ] `python code/01_fetch.py --log-only` reproduces the hashes in `data/raw/PROVENANCE.txt` from your own copy of the raw files
- [ ] Fresh download with `python code/01_fetch.py` in an empty `data/raw`; any hash that differs is explained (HUD replaced a file)
- [ ] Scripts 02 to 06 re-run; `data/processed/qa_report.txt` ends "ALL HARD CHECKS PASSED" and row counts match: 313,732 inspections, 65,337 properties
- [ ] R package: `ahcp_rebuild()` run on your machine; inspection and property counts equal the Python build (this has never been run)

## Source-level checks
- [ ] HUD PIS page re-read: the nine vintages are still the complete list; any newer vintage noted
- [ ] HUD data dictionaries (in `data/raw/hud_pis/ahcp_dd_*`) read; column meanings in the codebook agree, especially LOCATION_QUALITY codes
- [ ] Terms of each source re-read; nothing forbids redistribution of the derived tables

## Row-level spot checks
Open the source file and row given in section 8 of `qa_report.txt` for each:
- [ ] `MF:800006929` (easy case, many vintages)
- [ ] `PH:AK001000247` (public housing, both protocols)
- [ ] `MF:800006156` (score differs between vintages)
- [ ] `MF:800005037` (lowest NSPIRE score in 2026)
- [ ] `PH:AK001011` (pre-AMP project and its candidate development)
- [ ] `MF:800003255` (Hartford; check the tract on a Census map and the PLACES row)
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
