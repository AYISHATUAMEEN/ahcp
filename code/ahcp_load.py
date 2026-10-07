"""Shared loader: reads every HUD PIS vintage into one long, uniformly named table (no cleaning beyond types)."""
import os, re, warnings
import pandas as pd
warnings.filterwarnings("ignore", category=UserWarning)

RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "hud_pis")

# vintage -> (label of the "as of" date HUD states on the page, ISO date used for ordering)
VINTAGES = {
    2011: "2011-12-31", 2015: "2015-07-01", 2016: "2016-08-17", 2018: "2018-03-31",
    2019: "2019-03-31", 2020: "2020-06-30", 2021: "2021-03-31", 2025: "2025-08-25", 2026: "2026-04-08",
}
RENAME = {
    "devlopment_id": "property_id", "development_id": "property_id",
    "develpment_name": "property_name", "development_name": "property_name",
    "zipcode": "zip", "inspection_protocol": "protocol_hud",
}
COLS = ["inspection_id", "property_id", "property_name", "address", "city", "cbsa_name", "cbsa_code",
        "county_name", "county_code", "state_abbr", "state_fips", "zip", "latitude", "longitude",
        "location_quality", "pha_code", "pha_name", "inspection_score", "inspection_date", "protocol_hud"]


def _fix_state(df, vintage):
    # 2018 and 2019 files label the columns STATE_CODE (abbr) / FIPS_STATE_CODE; all others STATE_NAME (abbr) / STATE_CODE (fips)
    if "fips_state_code" in df.columns:
        df = df.rename(columns={"state_code": "state_abbr", "fips_state_code": "state_fips"})
    else:
        df = df.rename(columns={"state_name": "state_abbr", "state_code": "state_fips"})
    return df


def read_vintage(program, vintage):
    """program: 'ph' or 'mf'. Returns raw rows as strings with uniform column names."""
    base = os.path.join(RAW, f"ahcp_{program}_{vintage}")
    if vintage == 2011:
        df = pd.read_csv(base + ".txt", dtype=str, encoding="latin-1", keep_default_na=False, na_values=[""])
    else:
        df = pd.read_excel(base + ".xlsx", sheet_name=0, dtype=object)
        df = df.loc[:, [c for c in df.columns if isinstance(c, str) and not c.startswith("Unnamed")]]
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns=RENAME)
    df = _fix_state(df, vintage)
    df = df.dropna(how="all")
    for c in COLS:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[COLS].copy()
    df.insert(0, "program", "PH" if program == "ph" else "MF")
    df.insert(1, "vintage", vintage)
    df.insert(2, "source_row", range(2, len(df) + 2))
    return df


def read_all():
    return pd.concat([read_vintage(p, v) for p in ("ph", "mf") for v in VINTAGES], ignore_index=True)
