#!/usr/bin/env python3
"""Download recent CSV resources for the insightBrasil datasets from Tesouro Transparente (CKAN).

Each dataset is identified by its CKAN package id (taken from the dados.gov.br
pages linked in the README). Resources are matched against the filename pattern
of the CSVs already in data/ — e.g. files starting with "sadipemconsultapublicageral"
or "transferenciamensalmunicipios" — so metadata PDFs, API links, etc. are skipped.

Both datasets host CSVs going back decades, so instead of syncing everything,
each resource is kept only if the year embedded in its filename falls within the
last YEARS_BACK years (a rolling window — three Brazilian presidential terms,
enough to compare data across political cycles). Local files that age out of
that window are removed, so re-running the script keeps data/ in sync with the
window instead of only ever growing.
"""

import datetime
import json
import os
import re
import urllib.request

CKAN_API = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show?id={package_id}"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
HEADERS = {"User-Agent": "Mozilla/5.0"}

# How far back to keep data, as a number of calendar years counting backwards
# from today (inclusive). 12 years spans three Brazilian presidential terms
# (4 years each), enough to compare data across political cycles.
YEARS_BACK = 12
CUTOFF_YEAR = datetime.date.today().year - YEARS_BACK + 1

# Resource filenames encode the period they cover, either as a bare year
# (…2025.csv) or a YYYYMM month stamp (…202501.csv, …batch04062026.csv).
# This regex grabs that run of 4-6 digits starting with "20" — its first
# 4 characters are always the year, regardless of which form is used.
PERIOD_RE = re.compile(r"(20\d{2,6})")

DATASETS = [
    {
        "name": "Operações COPEM (SADIPEM)",
        "package_id": "25a770df-920e-4519-a172-65b84b14e643",
        "filename_pattern": re.compile(r"^sadipemconsultapublicageral", re.IGNORECASE),
    },
    {
        "name": "Transferências Constitucionais para Municípios",
        "package_id": "af4e7c47-2132-4d9a-bd7c-34e28a210b03",
        "filename_pattern": re.compile(r"^transferenciamensalmunicipios", re.IGNORECASE),
    },
]


def fetch_json(url):
    """GET a CKAN API URL and parse the JSON body (e.g. a package_show response)."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def filename_from_url(url):
    """The bare filename a resource will be saved as, taken from the end of its download URL."""
    return url.rsplit("/", 1)[-1]


def period_year(filename):
    """The year a resource covers, read from the period stamp in its filename.

    Returns None if the filename has no recognizable period (PERIOD_RE doesn't
    match), so such resources can be skipped rather than mis-sorted.
    """
    m = PERIOD_RE.search(filename)
    return int(m.group(1)[:4]) if m else None


def download(url, dest_path):
    """Stream a resource's CSV from its CKAN URL straight to disk at dest_path."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out:
        out.write(resp.read())


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Keeping resources from {CUTOFF_YEAR} onward ({YEARS_BACK}-year window).")

    for dataset in DATASETS:
        print(f"\n=== {dataset['name']} ===")
        # CKAN's package_show returns the dataset's full metadata, including a
        # "resources" list — every file attached to it (CSVs, PDFs, API docs, …).
        pkg = fetch_json(CKAN_API.format(package_id=dataset["package_id"]))["result"]

        # Decide which resources we want to end up with locally: only CSVs,
        # only the ones whose filename matches this dataset (the package also
        # lists unrelated companion files), and only those within the
        # YEARS_BACK window. `keep` maps filename -> download URL, and doubles
        # as the "expected final contents" set used for pruning below.
        keep = {}
        for resource in pkg["resources"]:
            if resource.get("format", "").upper() != "CSV":
                continue
            url = resource["url"]
            filename = filename_from_url(url)
            if not dataset["filename_pattern"].match(filename):
                continue
            year = period_year(filename)
            if year is None or year < CUTOFF_YEAR:
                continue
            keep[filename] = url

        # Fetch anything in `keep` that isn't on disk yet. Files already
        # present (from a previous run) are left untouched — CSVs for a given
        # period never change after publication, so no need to re-download.
        for filename, url in sorted(keep.items()):
            dest_path = os.path.join(DATA_DIR, filename)
            if os.path.exists(dest_path):
                print(f"  skip (already exists): {filename}")
                continue
            print(f"  downloading: {filename}")
            download(url, dest_path)

        # Remove local files for this dataset that fell outside the window
        # (e.g. last year's oldest month, now that a new month pushed the
        # cutoff forward). This is what keeps data/ a rolling window of a
        # fixed size instead of growing every time the script runs.
        for entry in os.listdir(DATA_DIR):
            if dataset["filename_pattern"].match(entry) and entry not in keep:
                print(f"  removing (aged out): {entry}")
                os.remove(os.path.join(DATA_DIR, entry))

    print("\nDone.")


if __name__ == "__main__":
    main()
