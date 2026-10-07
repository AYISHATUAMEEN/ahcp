# ahcp (R package)

Reads the AHCP release tables and rebuilds the inspection panel from HUD's raw score files.

**This package has not been run.** It was written alongside the tested Python pipeline, in an environment without R.
Before relying on it, run the comparison script below; it must report every check as matching.

```r
install.packages(c("data.table", "readxl", "jsonlite"))
install.packages("r/ahcp", repos = NULL, type = "source")   # from the repository root

library(ahcp)
x <- ahcp_read("data/processed")              # released tables
ahcp_history(x, "MF:800006929")               # one property's inspections

ahcp_fetch("data/raw/hud_pis", "code/sources.json")   # download the HUD files
y <- ahcp_rebuild("data/raw/hud_pis")                 # snapshots, inspections, properties (core columns)
```

```
Rscript r/ahcp/inst/check_against_python.R
```

Scope in v1.0: `ahcp_rebuild()` reproduces the harmonization and history reconstruction (`code/02_build_panel.py`).
The tract, subsidy, LIHTC and health linkages are built only by the Python pipeline (`code/03_link.py`);
`ahcp_read()` loads them from the release.
