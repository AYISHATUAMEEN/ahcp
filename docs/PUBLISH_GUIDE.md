# Publish guide: AHCP v1.0

v1.0 was published on 2026-10-06: GitHub https://github.com/AYISHATUAMEEN/ahcp, Zenodo DOI 10.5281/zenodo.23200319. The repository is linked to Zenodo, so each new GitHub release is archived and given a DOI automatically; the steps below are the manual route and the record of how v1.0 was done.

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
   git commit -m "AHCP v1.0"
   git remote add origin https://github.com/YOUR-USER/ahcp.git
   git push -u origin main
   ```
   `.gitignore` keeps `data/raw` and `data/interim` out of git (about 190 MB; raw files are rebuilt by `01_fetch.py`). The largest committed file is `ahcp_properties.csv` (about 28 MB), under GitHub's 100 MB limit.
3. Releases, "Draft a new release", tag `v1.0`, title "AHCP v1.0", paste the first two paragraphs of the README, publish.

## 2. Zenodo (15 minutes)

Rehearse once at https://sandbox.zenodo.org, then repeat at https://zenodo.org.

1. Log in (ORCID login attaches your ORCID). New upload.
2. Upload: a zip of the GitHub release, plus the five files in `data/processed/` individually so they can be previewed, plus `docs/CODEBOOK.md`, `docs/LIMITATIONS.md` and `data/raw/PROVENANCE.txt`.
3. Fill the form from `zenodo_metadata.json`: resource type Dataset; title; creator Ameen, Ayishatu (Independent Researcher, Hartford, Connecticut, USA); description; license Creative Commons Attribution 4.0; version 1.0; keywords; related identifier "is derived from" the HUD page; add the GitHub URL as "is supplemented by".
4. Publish. Copy the version DOI and the concept DOI.

## 3. Close the loop (10 minutes)

1. Add `doi: "10.5281/zenodo.NNNNNNN"` to `CITATION.cff`, add the DOI badge and "released" status line to the README, commit and push.
2. Add your ORCID to `AUTHORS.json` if you have one and re-run `python code/06_docs.py --final`.
3. Write the evidence log row the same day: date, "AHCP v1.0 release", dataset, Zenodo + GitHub, DOI, status live, files saved (release page PDF, Zenodo record PDF).

## Each annual release

Add the new HUD files to `code/sources.json` and the vintage to `VINTAGES` in `code/ahcp_load.py`, re-run scripts 01 to 06, complete the checklist again, tag the release, and use Zenodo's "New version" so the concept DOI stays the same.
