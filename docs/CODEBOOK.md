# AHCP v1.0 codebook

Every column in every released table. All tables are UTF-8 CSV; `.gz` files are gzip-compressed CSV. Missing values are empty cells. Read identifier and FIPS columns as text to keep leading zeros.


## `ahcp_inspections.csv.gz`

| Column | Definition | Source and transformation |
|---|---|---|
| `ahcp_inspection_id` | AHCP key for one inspection. | `{program}:{HUD inspection ID}` when HUD gives an ID (2015 vintage on). 2011 file has no IDs: `{program}:L:{property_id}:{yyyymmdd}`, with `#2` for a second score on the same property-day. `@{property_id}` is appended when one HUD inspection ID is listed under two properties. |
| `ahcp_property_id` | AHCP key for the property. | `{program}:{property_id}`. |
| `program` | `MF` multifamily or `PH` public housing. | Which HUD file the row came from. |
| `property_id` | HUD identifier: REMS property ID (MF) or PIC development/project number (PH). | HUD PIS file: PROPERTY_ID, DEVELOPMENT_ID (misspelled DEVLOPMENT_ID in 2015). Upper-cased, trimmed. |
| `inspection_id` | HUD inspection ID. Blank for the 2011 file. | HUD PIS file: INSPECTION_ID. NSPIRE inspections carry an `INSP-` prefix. |
| `inspection_date` | Inspection date (YYYY-MM-DD). | Time of day dropped. Where vintages disagree, the most recent vintage's date. |
| `inspection_year` | Calendar year of `inspection_date`. | Derived. |
| `inspection_score` | Inspection score, 0-100, as published. | Where vintages disagree, the most recent vintage's score. Not rescaled across protocols. |
| `score_scale` | `decimal_0_100` (2011 file, two decimals) or `integer_0_100`. | Derived from the vintage supplying the score. |
| `protocol` | `UPCS` or `NSPIRE`. | HUD's INSPECTION_PROTOCOL where the inspection is listed in the 2025 or 2026 file; otherwise inferred, see `protocol_source`. |
| `protocol_source` | How `protocol` was determined. | `hud_flag`; `inferred_pre_nspire_date` (dated before 2023-07-01 for PH or 2023-10-01 for MF, so UPCS); `inferred_id_prefix` (`INSP-` ID, so NSPIRE); `not_determinable`. |
| `inspection_seq` | Order of this inspection within the property's known history (1 = earliest). | Derived. Counts only inspections present in AHCP. |
| `prev_inspection_date` | Date of the property's previous inspection in AHCP. | Derived. Not necessarily the previous inspection that occurred. |
| `prev_inspection_score` | Score of that previous inspection. | Derived. |
| `days_since_prev` | Days between this inspection and the previous one in AHCP. | Derived. |
| `score_change` | `inspection_score` minus `prev_inspection_score`. | Derived. Mixes protocols when `protocol_change` = 1. |
| `protocol_change` | 1 if the previous inspection used the other protocol. | Derived. |
| `first_vintage` | Earliest vintage listing this inspection. | Derived. |
| `last_vintage` | Latest vintage listing this inspection; supplies score and date. | Derived. |
| `n_vintages` | Number of vintages listing this inspection. | Derived. |
| `score_conflict` | 1 if vintages report different scores for this inspection. | Derived. |
| `score_min_across_vintages` | Lowest score any vintage reports for it. | Derived. |
| `score_max_across_vintages` | Highest score any vintage reports for it. | Derived. |
| `date_conflict_days` | Days between the kept date and the earliest date any vintage reports (0 = agree). | Derived. |
| `shared_inspection_id` | 1 if HUD lists this inspection ID under two properties. | Derived; each property keeps its own row. |

## `ahcp_properties.csv`

| Column | Definition | Source and transformation |
|---|---|---|
| `ahcp_property_id` | AHCP key for the property. | `{program}:{property_id}`. |
| `program` | `MF` or `PH`. |  |
| `property_id` | HUD identifier. | See inspections table. |
| `id_scheme` | `REMS_PROPERTY_ID`, `PIC_AMP_DEVELOPMENT` (11 characters) or `PIC_PRE_AMP_PROJECT` (older project numbers, 2011 file only). | Derived from the ID's form. |
| `property_name` | Property or development name. | HUD PIS file; latest vintage that states it. Same rule for every attribute below through `pha_name`. |
| `address` | Street address. | HUD PIS file |
| `city` | City. | HUD PIS file |
| `state_abbr` | State or territory postal code. | HUD PIS file: STATE_NAME, or STATE_CODE in 2018-2019. |
| `state_fips` | 2-digit state FIPS. | HUD PIS file: STATE_CODE, or FIPS_STATE_CODE in 2018-2019. Zero-padded. |
| `county_fips` | 5-digit county FIPS. | `state_fips` + `county_fips3`. |
| `county_fips3` | 3-digit county code. | HUD PIS file: COUNTY_CODE. Zero-padded. |
| `county_name` | County name. | HUD PIS file |
| `zip5` | 5-digit ZIP. | HUD PIS file: ZIP/ZIPCODE. ZIP+4 truncated; leading zeros restored. |
| `cbsa_code` | CBSA code. | HUD PIS file. 99999 set to missing. |
| `cbsa_name` | CBSA name. | HUD PIS file |
| `latitude` | Latitude, decimal degrees. | HUD PIS file. Missing for properties HUD did not geocode. |
| `longitude` | Longitude, decimal degrees. | HUD PIS file |
| `location_quality` | HUD geocode accuracy: R = interpolated rooftop, 4 = ZIP+4 centroid, B = block group centroid, T = ZIP Code centroid. HUD notes county and CBSA codes are unreliable when T. Other codes (5, 2, Z) are undocumented. | HUD PIS file: LOCATION_QUALITY; absent in 2011. |
| `pha_code` | Public housing agency code (PH only). | HUD PIS file |
| `pha_name` | Public housing agency name (PH only). | HUD PIS file |
| `first_vintage` | Earliest vintage listing the property. | Derived. |
| `last_vintage` | Latest vintage listing the property. | Derived. |
| `n_vintages` | Number of vintages listing it. | Derived. |
| `vintages_listed` | Those vintages, semicolon-separated. | Derived. |
| `in_latest_vintage` | 1 if listed in the 2026 file. | Derived. 0 does not prove the property left HUD's portfolio. |
| `n_names` | Distinct names across vintages. | Derived. |
| `n_addresses` | Distinct addresses across vintages. | Derived. |
| `n_inspections` | Unique inspections in AHCP. | Derived. |
| `n_upcs` | Of which UPCS. | Derived. |
| `n_nspire` | Of which NSPIRE. | Derived. |
| `has_both_protocols` | 1 if at least one inspection under each protocol. | Derived. |
| `first_inspection_date` | Earliest inspection date in AHCP. | Derived. |
| `last_inspection_date` | Latest inspection date in AHCP. | Derived. |
| `last_inspection_score` | Score at the latest inspection. | Derived. |
| `last_protocol` | Protocol of the latest inspection. | Derived. |
| `tract_geoid_2020` | 11-digit 2020 census tract GEOID. | Point-in-polygon of `latitude`/`longitude` on Census cb_2020_us_tract_500k. |
| `tract_method` | `contains`, `nearest_vertex` (within 1 km of a tract boundary vertex), `no_coordinates`, or `outside_all_tracts`. | Derived. |
| `tract_snap_m` | Distance in metres for `nearest_vertex` assignments. | Derived. |
| `tract_county_agrees` | 1 if the tract's county equals `county_fips`. | Derived QA flag. |
| `hud_layer` | HUD eGIS layer the subsidy fields come from, or `not_in_current_hud_layers`. | Exact join on property/development ID. The assisted layer wins when a property is in both multifamily layers. |
| `subsidy_category` | HUD property category; `Public Housing` for PH. | MF layers: PROPERTY_CATEGORY_NAME. |
| `subsidy_program_type` | Primary program type. | MF layers: PROGRAM_TYPE1. |
| `total_units` | Total units. | MF: TOTAL_UNIT_COUNT; PH: TOTAL_UNITS. 0 treated as missing. |
| `assisted_units` | Assisted (MF) or ACC (PH) units. | MF: TOTAL_ASSISTED_UNIT_COUNT; PH: ACC_UNITS. 0 treated as missing. |
| `contract_number` | Primary assistance contract number (MF). | CONTRACT1. |
| `contract_count` | Number of contracts (MF). | CONTRACT_COUNT. |
| `contract_expiration_date` | Primary contract expiration date (MF). | EXPIRATION_DATE1, converted from epoch milliseconds. |
| `fha_number` | Primary FHA number (MF). | PRIMARY_FHA_NUMBER. |
| `is_insured` | Y/N: FHA-insured. | IS_INSURED_IND. |
| `is_section8` | Y/N: Section 8 project-based. | IS_SEC8_IND. |
| `is_202_811` | Y/N: Section 202 or 811. | IS_202_811_IND. |
| `is_rad_conversion` | Y/N: RAD conversion. | IS_SEC8_RAD_DEMO_CONV_IND. |
| `has_active_assistance` | Y/N: active assistance contract. | HAS_ACTIVE_ASSISTANCE_IND. |
| `client_group` | Resident client group (MF). | CLIENT_GROUP_NAME. |
| `pct_occupied` | Percent occupied. | PCT_OCCUPIED. 0 treated as missing. |
| `hud_taxcredit_flag` | Y/N: HUD's own tax-credit indicator on the primary contract (MF). | TAXCREDIT1. Independent of the AHCP LIHTC link. |
| `tract_geoid_2010_hud` | 11-digit 2010 census tract GEOID as coded by HUD. | TRACT_LEVEL from the HUD layer. |
| `hud_layer_updated` | HUD layer record update date. | LAST_UPDT_DTTM. |
| `ph_scattered_site` | Y/N: scattered-site development (PH). | SCATTERED_SITE_IND. |
| `lihtc_match_type` | `address_zip`, `proximity_house_number`, or `none`. | Normalized street address + ZIP equal; otherwise a LIHTC project within 50 m with the same house number. |
| `lihtc_n_projects` | Number of LIHTC projects matched. | Derived. |
| `lihtc_hud_ids` | Their HUD LIHTC IDs, semicolon-separated. | HUD LIHTC database: HUD_ID. |
| `lihtc_match_dist_m` | Distance in metres for proximity matches. | Derived. |
| `lihtc_earliest_yr_pis` | Earliest placed-in-service year among matched projects. | YR_PIS; codes outside 1987-2030 treated as missing. |
| `lihtc_li_units_total` | Low-income units summed over matched projects. | LI_UNITS. |
| `amp_candidate_id` | For a pre-AMP project: the single candidate later development (`ahcp_property_id`). | Same agency and either same address + ZIP or within 50 m. Blank if none or more than one. A candidate, not a confirmed link. |
| `tract_geoid_places` | Tract key for joining `ahcp_tract_health.csv`. | Equal to `tract_geoid_2020` except in Connecticut, re-keyed to the planning-region codes PLACES uses. |
| `places_tract_matched` | 1 if the tract has a PLACES record. | Derived. PLACES does not cover the territories. |

## `ahcp_snapshots.csv.gz`

| Column | Definition | Source and transformation |
|---|---|---|
| `ahcp_property_id` | AHCP key for the property. | `{program}:{property_id}`. |
| `ahcp_inspection_id` | AHCP key for one inspection. | `{program}:{HUD inspection ID}` when HUD gives an ID (2015 vintage on). 2011 file has no IDs: `{program}:L:{property_id}:{yyyymmdd}`, with `#2` for a second score on the same property-day. `@{property_id}` is appended when one HUD inspection ID is listed under two properties. |
| `program` | `MF` multifamily or `PH` public housing. | Which HUD file the row came from. |
| `vintage` | Score-file vintage year. |  |
| `source_file` | Raw file the row came from (name under `data/raw/hud_pis`). | See PROVENANCE.txt for the HUD URL. |
| `source_row` | Row number in that file (header = row 1). |  |
| `property_id` | HUD identifier: REMS property ID (MF) or PIC development/project number (PH). | HUD PIS file: PROPERTY_ID, DEVELOPMENT_ID (misspelled DEVLOPMENT_ID in 2015). Upper-cased, trimmed. |
| `id_scheme` | `REMS_PROPERTY_ID`, `PIC_AMP_DEVELOPMENT` (11 characters) or `PIC_PRE_AMP_PROJECT` (older project numbers, 2011 file only). | Derived from the ID's form. |
| `inspection_id` | HUD inspection ID. Blank for the 2011 file. | HUD PIS file: INSPECTION_ID. NSPIRE inspections carry an `INSP-` prefix. |
| `inspection_date` | Date as that vintage states it. | HUD PIS file |
| `inspection_score` | Score exactly as that vintage states it. | HUD PIS file |
| `protocol_hud` | HUD's INSPECTION_PROTOCOL value; blank before 2025. | HUD PIS file |
| `property_name` | Property or development name. | HUD PIS file; latest vintage that states it. Same rule for every attribute below through `pha_name`. |
| `address` | Street address. | HUD PIS file |
| `city` | City. | HUD PIS file |
| `state_abbr` | State or territory postal code. | HUD PIS file: STATE_NAME, or STATE_CODE in 2018-2019. |
| `state_fips` | 2-digit state FIPS. | HUD PIS file: STATE_CODE, or FIPS_STATE_CODE in 2018-2019. Zero-padded. |
| `county_fips3` | 3-digit county code. | HUD PIS file: COUNTY_CODE. Zero-padded. |
| `county_name` | County name. | HUD PIS file |
| `zip5` | 5-digit ZIP. | HUD PIS file: ZIP/ZIPCODE. ZIP+4 truncated; leading zeros restored. |
| `cbsa_code` | CBSA code. | HUD PIS file. 99999 set to missing. |
| `cbsa_name` | CBSA name. | HUD PIS file |
| `latitude` | Latitude, decimal degrees. | HUD PIS file. Missing for properties HUD did not geocode. |
| `longitude` | Longitude, decimal degrees. | HUD PIS file |
| `location_quality` | HUD geocode accuracy: R = interpolated rooftop, 4 = ZIP+4 centroid, B = block group centroid, T = ZIP Code centroid. HUD notes county and CBSA codes are unreliable when T. Other codes (5, 2, Z) are undocumented. | HUD PIS file: LOCATION_QUALITY; absent in 2011. |
| `pha_code` | Public housing agency code (PH only). | HUD PIS file |
| `pha_name` | Public housing agency name (PH only). | HUD PIS file |

## `ahcp_ph_legacy_crosswalk.csv`

| Column | Definition | Source and transformation |
|---|---|---|
| `ahcp_property_id_legacy` | Pre-AMP project. |  |
| `ahcp_property_id_amp_candidate` | Candidate later development. |  |
| `pha_code` | Agency code shared by both. |  |
| `match_method` | `address_zip`, `proximity`, or `address_zip+proximity`. | Proximity threshold 50 m. |
| `distance_m` | Distance in metres for proximity matches. |  |
| `n_candidates_for_legacy` | Candidates found for this legacy project. |  |

## `ahcp_tract_health.csv`

| Column | Definition | Source and transformation |
|---|---|---|
| `tract_geoid_places` | Tract key; join to `ahcp_properties.tract_geoid_places`. | PLACES TractFIPS. |
| `places_totalpopulation` | Total population, count. | CDC PLACES 2025 release, `totalpopulation`. |
| `places_totalpop18plus` | Population aged 18+, count. | CDC PLACES 2025 release, `totalpop18plus`. |
| `places_access2` | No health insurance, ages 18-64, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `access2_crudeprev`. |
| `places_arthritis` | Arthritis, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `arthritis_crudeprev`. |
| `places_binge` | Binge drinking, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `binge_crudeprev`. |
| `places_bphigh` | High blood pressure, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `bphigh_crudeprev`. |
| `places_bpmed` | Taking blood pressure medication, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `bpmed_crudeprev`. |
| `places_cancer` | Cancer (non-skin) or melanoma, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `cancer_crudeprev`. |
| `places_casthma` | Current asthma, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `casthma_crudeprev`. |
| `places_chd` | Coronary heart disease, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `chd_crudeprev`. |
| `places_checkup` | Routine checkup in past year, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `checkup_crudeprev`. |
| `places_cholscreen` | Cholesterol screening, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `cholscreen_crudeprev`. |
| `places_colon_screen` | Colorectal cancer screening, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `colon_screen_crudeprev`. |
| `places_copd` | COPD, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `copd_crudeprev`. |
| `places_csmoking` | Current smoking, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `csmoking_crudeprev`. |
| `places_dental` | Dental visit in past year, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `dental_crudeprev`. |
| `places_depression` | Depression, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `depression_crudeprev`. |
| `places_diabetes` | Diagnosed diabetes, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `diabetes_crudeprev`. |
| `places_ghlth` | Fair or poor self-rated health, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `ghlth_crudeprev`. |
| `places_highchol` | High cholesterol, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `highchol_crudeprev`. |
| `places_lpa` | No leisure-time physical activity, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `lpa_crudeprev`. |
| `places_mammouse` | Mammography use, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `mammouse_crudeprev`. |
| `places_mhlth` | Frequent mental distress, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `mhlth_crudeprev`. |
| `places_obesity` | Obesity, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `obesity_crudeprev`. |
| `places_phlth` | Frequent physical distress, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `phlth_crudeprev`. |
| `places_sleep` | Short sleep duration, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `sleep_crudeprev`. |
| `places_stroke` | Stroke, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `stroke_crudeprev`. |
| `places_teethlost` | All teeth lost, ages 65+, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `teethlost_crudeprev`. |
| `places_hearing` | Hearing disability, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `hearing_crudeprev`. |
| `places_vision` | Vision disability, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `vision_crudeprev`. |
| `places_cognition` | Cognitive disability, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `cognition_crudeprev`. |
| `places_mobility` | Mobility disability, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `mobility_crudeprev`. |
| `places_selfcare` | Self-care disability, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `selfcare_crudeprev`. |
| `places_indeplive` | Independent living disability, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `indeplive_crudeprev`. |
| `places_disability` | Any disability, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `disability_crudeprev`. |
| `places_loneliness` | Feeling socially isolated, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `loneliness_crudeprev`. |
| `places_foodstamp` | Received food stamps in past 12 months, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `foodstamp_crudeprev`. |
| `places_foodinsecu` | Food insecurity in past 12 months, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `foodinsecu_crudeprev`. |
| `places_housinsecu` | Housing insecurity in past 12 months, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `housinsecu_crudeprev`. |
| `places_shututility` | Utility shut-off threat in past 12 months, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `shututility_crudeprev`. |
| `places_lacktrpt` | Lack of reliable transportation in past 12 months, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `lacktrpt_crudeprev`. |
| `places_emotionspt` | Lack of social and emotional support, crude prevalence (%), adults; model-based estimate. | CDC PLACES 2025 release, `emotionspt_crudeprev`. |
| `n_ahcp_properties` | AHCP properties in the tract. | Derived. |
