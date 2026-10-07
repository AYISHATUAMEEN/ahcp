#!/usr/bin/env python3
"""01_fetch.py - download every raw input listed in code/sources.json and log provenance.

  python code/01_fetch.py            download anything missing, then (re)write data/raw/PROVENANCE.txt
  python code/01_fetch.py --log-only never touch the network; hash what is on disk and write the log

Files already present are never re-downloaded, so a hand-placed file is respected. Each source is one of:
  type=file    a single URL saved as-is
  type=arcgis  a HUD ArcGIS feature layer, paged 2,000 records at a time and written as CSV with the listed fields
HUD replaces the inspection workbooks in place: if a URL 404s, find the current link on the landing page
recorded in sources.json, update the URL there, and note the change in the provenance log.
"""
import csv, hashlib, json, os, sys, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(os.path.dirname(HERE), "data", "raw")
UA = {"User-Agent": "ahcp-fetch/1.0 (research; see repository README)"}


def get(url, **kw):
    import requests
    for attempt in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=180, **kw)
            if r.status_code == 200: return r
        except Exception as e:  # noqa
            err = e
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"could not fetch {url}")


def fetch_arcgis(src, path):
    fields = src["fields"].split(","); off = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n"); w.writerow(fields)
        while True:
            j = get(src["url"], params={"where": "1=1", "outFields": src["fields"], "returnGeometry": "false", "orderByFields": "OBJECTID",
                                        "resultOffset": off, "resultRecordCount": 2000, "f": "json"}).json()
            feats = j.get("features", [])
            for f in feats: w.writerow(["" if f["attributes"].get(k) is None else f["attributes"][k] for k in fields])
            off += len(feats)
            if not feats or not j.get("exceededTransferLimit"): break


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def main():
    log_only = "--log-only" in sys.argv
    man = json.load(open(os.path.join(HERE, "sources.json")))
    today = datetime.date.today().isoformat(); lines = []; missing = []
    for s in man["sources"]:
        path = os.path.join(RAW, s["local"]); os.makedirs(os.path.dirname(path), exist_ok=True)
        fetched = man["accessed"]
        if not os.path.exists(path):
            if log_only: missing.append(s["local"]); continue
            print("fetching", s["local"])
            if s["type"] == "arcgis": fetch_arcgis(s, path)
            else: open(path, "wb").write(get(s["url"]).content)
            fetched = today
        lines.append("\t".join([s["local"], str(os.path.getsize(path)), sha256(path), fetched, s["source"], s["url"]]))
    with open(os.path.join(RAW, "PROVENANCE.txt"), "w", encoding="utf-8") as fh:
        fh.write("# AHCP raw-input provenance. One line per file: path under data/raw, bytes, SHA-256, access date, source, URL\n")
        fh.write("# Access dates equal to %s are the original v1.0 retrieval (downloaded through a web browser and saved under the\n" % man["accessed"])
        fh.write("# local names shown; ArcGIS layers were paged through the query endpoint with the field list in code/sources.json).\n")
        fh.write("\n".join(lines) + "\n")
    print(f"{len(lines)} files logged; missing: {missing or 'none'}")


if __name__ == "__main__":
    main()
