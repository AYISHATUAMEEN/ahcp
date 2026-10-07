# Run from the repository root after installing the package:
#   Rscript r/ahcp/inst/check_against_python.R
# Compares the R rebuild with the counts the Python pipeline wrote to paper/stats.json.
library(ahcp)
s <- jsonlite::fromJSON("paper/stats.json")
x <- ahcp_rebuild("data/raw/hud_pis")
got <- c(snapshot_rows = nrow(x$snapshots), inspections = nrow(x$inspections), properties = nrow(x$properties),
         nspire = sum(x$inspections$protocol == "NSPIRE"), score_conflicts = sum(x$inspections$score_conflict),
         unknown_protocol = sum(x$inspections$protocol == "UNKNOWN"))
want <- c(snapshot_rows = s$snapshot_rows, inspections = s$inspections, properties = s$properties,
          nspire = s$nspire_hud_flag + s$nspire_inferred, score_conflicts = s$score_conflicts, unknown_protocol = 0)
print(data.frame(check = names(got), r = unname(got), python = unname(want), match = unname(got) == unname(want)))
p <- data.table::fread("data/processed/ahcp_inspections.csv.gz", colClasses = "character")
m <- merge(x$inspections[, .(ahcp_inspection_id, r_score = inspection_score, r_date = as.character(inspection_date))],
           p[, .(ahcp_inspection_id, py_score = as.numeric(inspection_score), py_date = inspection_date)], by = "ahcp_inspection_id", all = TRUE)
cat("inspection keys only in one build:", sum(is.na(m$r_score) | is.na(m$py_score)), "\n")
cat("scores that differ:", sum(abs(m$r_score - m$py_score) > 1e-9, na.rm = TRUE), " dates that differ:", sum(m$r_date != m$py_date, na.rm = TRUE), "\n")
if (!all(got == want)) quit(status = 1)
