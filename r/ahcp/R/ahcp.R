# ahcp: read and rebuild the Assisted Housing Condition Panel.
# Mirrors code/ahcp_load.py and code/02_build_panel.py. Linkages (tract, subsidy, LIHTC, health) are
# produced by the Python pipeline (code/03_link.py) and are read, not rebuilt, by this package.

utils::globalVariables(c(".", ".N", ".SD", ":=", "program", "vintage", "source_row", "property_id", "inspection_id",
  "inspection_date", "inspection_score", "protocol_hud", "ahcp_property_id", "ahcp_inspection_id", "legacy",
  "seq_in_day", "npid", "shared_inspection_id", "protocol", "protocol_source", "last_vintage", "score_conflict",
  "score_min_across_vintages", "score_max_across_vintages", "date_conflict_days", "date_earliest", "inspection_seq",
  "prev_inspection_date", "prev_inspection_score", "prev_protocol", "days_since_prev", "score_change",
  "protocol_change", "score_scale", "inspection_year", "id_scheme", "first_vintage", "n_vintages"))

#' Score-file vintages in AHCP v1.0 and the "as of" date HUD states for each.
#' @export
ahcp_vintages <- function() {
  c(`2011` = "2011-12-31", `2015` = "2015-07-01", `2016` = "2016-08-17", `2018` = "2018-03-31", `2019` = "2019-03-31",
    `2020` = "2020-06-30", `2021` = "2021-03-31", `2025` = "2025-08-25", `2026` = "2026-04-08")
}

.nspire_start <- c(PH = "2023-07-01", MF = "2023-10-01")

.clean <- function(x) {
  x <- trimws(as.character(x))
  x[x %in% c("", "NA", "nan", "None")] <- NA_character_
  x
}

# Dates arrive as Excel serials (date cells read as text), "m/d/Y [H:M]", "dd-MON-yy", or ISO strings.
.parse_date <- function(x) {
  x <- .clean(x)
  out <- as.Date(rep(NA_character_, length(x)))
  num <- !is.na(x) & grepl("^[0-9]+(\\.[0-9]+)?$", x)
  out[num] <- as.Date(floor(as.numeric(x[num])), origin = "1899-12-30")
  mdy <- !is.na(x) & grepl("^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}", x)
  out[mdy] <- as.Date(sub(" .*$", "", x[mdy]), format = "%m/%d/%Y")
  iso <- !is.na(x) & grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}", x)
  out[iso] <- as.Date(substr(x[iso], 1, 10))
  dmy <- !is.na(x) & grepl("^[0-9]{1,2}-[A-Za-z]{3}-[0-9]{2}$", x)
  if (any(dmy)) {
    p <- strsplit(toupper(x[dmy]), "-", fixed = TRUE)
    mon <- match(vapply(p, `[`, "", 2), toupper(month.abb))
    yy <- as.integer(vapply(p, `[`, "", 3))
    yyyy <- ifelse(yy <= 68, 2000L + yy, 1900L + yy)
    out[dmy] <- as.Date(sprintf("%04d-%02d-%02d", yyyy, mon, as.integer(vapply(p, `[`, "", 1))))
  }
  out
}

.read_vintage <- function(raw_dir, program, vintage) {
  base <- file.path(raw_dir, sprintf("ahcp_%s_%s", program, vintage))
  if (vintage == 2011) {
    d <- data.table::fread(paste0(base, ".txt"), colClasses = "character", encoding = "Latin-1", na.strings = "")
  } else {
    d <- data.table::as.data.table(readxl::read_excel(paste0(base, ".xlsx"), sheet = 1, col_types = "text",
                                                      .name_repair = "minimal"))
    keep <- !is.na(names(d)) & names(d) != ""
    d <- d[, which(keep), with = FALSE]
  }
  data.table::setnames(d, tolower(trimws(names(d))))
  ren <- c(devlopment_id = "property_id", development_id = "property_id", develpment_name = "property_name",
           development_name = "property_name", zipcode = "zip", inspection_protocol = "protocol_hud")
  hit <- intersect(names(ren), names(d))
  if (length(hit)) data.table::setnames(d, hit, unname(ren[hit]))
  # 2018 and 2019 label the columns STATE_CODE (abbreviation) / FIPS_STATE_CODE; the rest STATE_NAME / STATE_CODE
  if ("fips_state_code" %in% names(d)) {
    data.table::setnames(d, c("state_code", "fips_state_code"), c("state_abbr", "state_fips"))
  } else {
    data.table::setnames(d, c("state_name", "state_code"), c("state_abbr", "state_fips"))
  }
  cols <- c("inspection_id", "property_id", "property_name", "address", "city", "cbsa_name", "cbsa_code", "county_name",
            "county_code", "state_abbr", "state_fips", "zip", "latitude", "longitude", "location_quality", "pha_code",
            "pha_name", "inspection_score", "inspection_date", "protocol_hud")
  for (cc in setdiff(cols, names(d))) d[, (cc) := NA_character_]
  d <- d[, cols, with = FALSE]
  d <- d[rowSums(!is.na(d)) > 0]
  d[, `:=`(program = toupper(program), vintage = as.integer(vintage), source_row = seq_len(.N) + 1L)]
  d[]
}

#' Download the HUD score files listed in the AHCP source manifest.
#' @param raw_dir Folder to hold the files (the pipeline uses data/raw/hud_pis).
#' @param manifest Path to code/sources.json from the AHCP repository.
#' @export
ahcp_fetch <- function(raw_dir, manifest) {
  if (!requireNamespace("jsonlite", quietly = TRUE)) stop("install.packages('jsonlite') to use ahcp_fetch()")
  src <- jsonlite::fromJSON(manifest, simplifyDataFrame = TRUE)$sources
  src <- src[grepl("^hud_pis/ahcp_(ph|mf)_", src$local), ]
  dir.create(raw_dir, recursive = TRUE, showWarnings = FALSE)
  for (i in seq_len(nrow(src))) {
    dest <- file.path(raw_dir, basename(src$local[i]))
    if (!file.exists(dest)) utils::download.file(src$url[i], dest, mode = "wb", quiet = TRUE)
  }
  invisible(list.files(raw_dir))
}

#' Rebuild the AHCP inspection panel from the raw HUD files.
#' @param raw_dir Folder holding ahcp_{ph,mf}_{vintage}.xlsx (and .txt for 2011).
#' @return A list with data.tables `snapshots`, `inspections` and `properties` (core columns, no linkages).
#' @export
ahcp_rebuild <- function(raw_dir) {
  v <- as.integer(names(ahcp_vintages()))
  d <- data.table::rbindlist(lapply(c("ph", "mf"), function(p) data.table::rbindlist(lapply(v, function(y) .read_vintage(raw_dir, p, y)))))
  chr <- c("inspection_id", "property_id", "property_name", "address", "city", "pha_code", "protocol_hud")
  d[, (chr) := lapply(.SD, .clean), .SDcols = chr]
  d[, inspection_id := sub("\\.0$", "", inspection_id)]
  d[, property_id := toupper(sub("\\.0$", "", property_id))]
  d[, protocol_hud := toupper(protocol_hud)]
  d[, inspection_score := as.numeric(inspection_score)]
  d[, inspection_date := .parse_date(inspection_date)]
  d <- d[!is.na(property_id) & !is.na(inspection_date) & !is.na(inspection_score)]

  d[, ahcp_property_id := paste0(program, ":", property_id)]
  d[, id_scheme := ifelse(program == "MF", "REMS_PROPERTY_ID",
                          ifelse(grepl("^[A-Z]{2}[0-9]{9}$", property_id), "PIC_AMP_DEVELOPMENT", "PIC_PRE_AMP_PROJECT"))]
  data.table::setorder(d, program, vintage, source_row)
  d[, seq_in_day := seq_len(.N), by = .(program, vintage, property_id, inspection_date)]
  d[, legacy := paste0(program, ":L:", property_id, ":", format(inspection_date, "%Y%m%d"), ifelse(seq_in_day > 1, paste0("#", seq_in_day), ""))]
  d[, ahcp_inspection_id := ifelse(is.na(inspection_id), legacy, paste0(program, ":", inspection_id))]
  d[, npid := data.table::uniqueN(property_id), by = ahcp_inspection_id]
  d[, shared_inspection_id := as.integer(npid > 1)]
  d[npid > 1, ahcp_inspection_id := paste0(ahcp_inspection_id, "@", property_id)]
  d[, c("legacy", "seq_in_day", "npid") := NULL]

  data.table::setorder(d, ahcp_inspection_id, vintage, source_row)
  last_nonmissing <- function(x) { x <- x[!is.na(x)]; if (length(x)) x[length(x)] else NA_character_ }
  insp <- d[, .(ahcp_property_id = ahcp_property_id[.N], program = program[.N], property_id = property_id[.N],
                inspection_id = inspection_id[.N], inspection_date = inspection_date[.N], inspection_score = inspection_score[.N],
                protocol_hud = last_nonmissing(protocol_hud), first_vintage = min(vintage), last_vintage = max(vintage),
                n_vintages = data.table::uniqueN(vintage), score_min_across_vintages = min(inspection_score),
                score_max_across_vintages = max(inspection_score), date_earliest = min(inspection_date),
                shared_inspection_id = max(shared_inspection_id)), by = ahcp_inspection_id]
  insp[, score_conflict := as.integer(score_min_across_vintages != score_max_across_vintages)]
  insp[, date_conflict_days := as.integer(inspection_date - date_earliest)]
  insp[, date_earliest := NULL]
  insp[, protocol := protocol_hud]
  insp[, protocol_source := ifelse(is.na(protocol_hud), NA_character_, "hud_flag")]
  insp[is.na(protocol) & !is.na(inspection_id) & startsWith(inspection_id, "INSP-"), `:=`(protocol = "NSPIRE", protocol_source = "inferred_id_prefix")]
  insp[is.na(protocol) & inspection_date < as.Date(.nspire_start[program]), `:=`(protocol = "UPCS", protocol_source = "inferred_pre_nspire_date")]
  insp[is.na(protocol), `:=`(protocol = "UNKNOWN", protocol_source = "not_determinable")]
  insp[, score_scale := ifelse(last_vintage == 2011L, "decimal_0_100", "integer_0_100")]
  insp[, inspection_year := as.integer(format(inspection_date, "%Y"))]
  data.table::setorder(insp, program, property_id, inspection_date, ahcp_inspection_id)
  insp[, inspection_seq := seq_len(.N), by = ahcp_property_id]
  insp[, `:=`(prev_inspection_date = data.table::shift(inspection_date), prev_inspection_score = data.table::shift(inspection_score),
              prev_protocol = data.table::shift(protocol)), by = ahcp_property_id]
  insp[, days_since_prev := as.integer(inspection_date - prev_inspection_date)]
  insp[, score_change := inspection_score - prev_inspection_score]
  insp[, protocol_change := as.integer(!is.na(prev_protocol) & prev_protocol != protocol)]
  insp[, c("prev_protocol", "protocol_hud") := NULL]

  props <- insp[, .(program = program[1], property_id = property_id[1], n_inspections = .N,
                    n_upcs = sum(protocol == "UPCS"), n_nspire = sum(protocol == "NSPIRE"),
                    first_inspection_date = min(inspection_date), last_inspection_date = max(inspection_date),
                    last_inspection_score = inspection_score[which.max(inspection_date)]), by = ahcp_property_id]
  pv <- d[, .(first_vintage = min(vintage), last_vintage = max(vintage), n_vintages = data.table::uniqueN(vintage),
              id_scheme = id_scheme[1]), by = ahcp_property_id]
  props <- merge(props, pv, by = "ahcp_property_id")
  list(snapshots = d[], inspections = insp[], properties = props[])
}

#' Read the released AHCP tables.
#' @param dir Folder holding the release files (data/processed).
#' @return A list of data.tables: inspections, properties, snapshots, tract_health, ph_legacy_crosswalk.
#' @export
ahcp_read <- function(dir) {
  rd <- function(f) data.table::as.data.table(utils::read.csv(file.path(dir, f), colClasses = "character", na.strings = "", check.names = FALSE))
  out <- list(inspections = rd("ahcp_inspections.csv.gz"), properties = rd("ahcp_properties.csv"), snapshots = rd("ahcp_snapshots.csv.gz"),
              tract_health = rd("ahcp_tract_health.csv"), ph_legacy_crosswalk = rd("ahcp_ph_legacy_crosswalk.csv"))
  num <- c("inspection_score", "prev_inspection_score", "score_change", "days_since_prev", "inspection_seq", "inspection_year")
  out$inspections[, (num) := lapply(.SD, as.numeric), .SDcols = num]
  out$inspections[, inspection_date := as.Date(inspection_date)]
  out
}

#' One property's inspection history.
#' @param x Result of ahcp_read() or ahcp_rebuild().
#' @param id An ahcp_property_id such as "MF:800006929", or a bare HUD property ID.
#' @export
ahcp_history <- function(x, id) {
  i <- x$inspections
  h <- i[ahcp_property_id == id | property_id == id]
  data.table::setorder(h, inspection_date)
  h[, .(ahcp_property_id, inspection_date, inspection_score, protocol, protocol_source, last_vintage, score_conflict)]
}
