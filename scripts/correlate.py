#!/usr/bin/env python3
"""Correlate SADIPEM credit operations with constitutional transfers, by state and year.

Idea: states that receive more in constitutional transfers (FPM, FPE, FUNDEB,
ICMS, IPVA, ITR, CIDE-Combustíveis...) might also be the ones that take out more
credit operations through SADIPEM — both being rough proxies for the size of a
state's public finances. This script checks that hunch with Pearson's r, using
every (state, year) pair found in the locally downloaded data/ files, so the
result reflects the full rolling window the download script maintains rather
than a single snapshot year.

For each (UF, year) pair present in both datasets, it sums:
  - SADIPEM:        the value (and count) of "Deferido*" (approved) requests
  - Transferências: the three "decêndio" instalments across all monthly files

...then reports both Pearson's r and Spearman's rank correlation across all
those pairs — once for total value, and once using the request count instead.

Pearson vs. Spearman: pooling 11 years of SADIPEM values mixes wildly different
scales — a single mega-operation (e.g. São Paulo's ~R$224 billion 2017 debt
renegotiation) can be 100x the size of a typical (state, year) pair, and such
an extreme leverage point can swing Pearson's r across hundreds of data points.
Spearman sidesteps that: it correlates the *ranks* of the values rather than
the values themselves, so one enormous outlier counts no more than "the
biggest one this year" — making it the more trustworthy aggregate measure when
years of differing scale are pooled together (Pearson stays useful per-year,
where all pairs share roughly the same scale).
"""

import csv
import glob
import os
import re
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def to_float(value):
    """Parse a Brazilian-formatted number ("1.234.567,89") into a float."""
    value = value.strip()
    if not value:
        return 0.0
    value = value.replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return 0.0


def pearson(xs, ys):
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    spread_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
    spread_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
    if not spread_x or not spread_y:
        return float("nan")
    return covariance / (spread_x * spread_y)


def ranks(values):
    """Rank each value (1 = smallest), giving tied values their average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            result[order[k]] = average_rank
        i = j + 1
    return result


def spearman(xs, ys):
    """Pearson's r computed on ranks instead of raw values — robust to outliers."""
    return pearson(ranks(xs), ranks(ys))


def load_sadipem():
    """Sum of approved ("Deferido*") request values and counts, keyed by (UF, year)."""
    value_by_uf_year = defaultdict(float)
    count_by_uf_year = defaultdict(int)

    paths = glob.glob(os.path.join(DATA_DIR, "sadipemconsultapublicageral*.csv"))
    for path in paths:
        with open(path, encoding="cp1252") as f:
            for row in csv.DictReader(f, delimiter=";"):
                if not row["Status"].startswith("Deferido"):
                    continue
                m = re.match(r"\d{2}/\d{2}/(\d{4})", row["Data"].strip())
                if not m:
                    continue
                key = (row["UF"].strip(), m.group(1))
                value_by_uf_year[key] += to_float(row["Valor"])
                count_by_uf_year[key] += 1

    return value_by_uf_year, count_by_uf_year


def load_transferencias():
    """Sum of the three decêndio instalments, keyed by (UF, year)."""
    total_by_uf_year = defaultdict(float)

    paths = glob.glob(os.path.join(DATA_DIR, "transferenciamensalmunicipios*.csv*"))
    for path in paths:
        with open(path, encoding="cp1252") as f:
            for row in csv.DictReader(f, delimiter=";"):
                year = row.get("ANO", "").strip()
                if not year:
                    continue
                key = (row["UF"].strip(), year)
                total_by_uf_year[key] += (
                    to_float(row["1º Decêndio"])
                    + to_float(row["2º Decêndio"])
                    + to_float(row["3º Decêndio"])
                )

    return total_by_uf_year


def main():
    sadipem_value, sadipem_count = load_sadipem()
    transferencias_total = load_transferencias()

    # Only pairs present on both sides make a valid data point for correlation.
    keys = sorted(set(sadipem_value) & set(transferencias_total))
    years = sorted({year for _, year in keys})
    print(f"{len(keys)} (UF, year) pairs across {len(years)} years: {years[0]}-{years[-1]}\n")

    values = [sadipem_value[k] for k in keys]
    counts = [sadipem_count[k] for k in keys]
    transfers = [transferencias_total[k] for k in keys]

    print("Pooled across all years (Pearson is skewed here by mega-outliers like SP 2017 — see Spearman):")
    print(f"  value  vs. transfers — Pearson r: {pearson(values, transfers):>8.4f}   Spearman ρ: {spearman(values, transfers):>8.4f}")
    print(f"  count  vs. transfers — Pearson r: {pearson(counts, transfers):>8.4f}   Spearman ρ: {spearman(counts, transfers):>8.4f}")

    # Break it down per year too — useful to see whether the relationship
    # holds steady or shifts across the political cycles in the window. Within
    # a single year all pairs share roughly the same scale, so Pearson and
    # Spearman tend to agree much more closely than they do pooled.
    print(f"\n{'Year':<6} {'Pairs':>5} {'Pearson (val)':>14} {'Spearman (val)':>15} {'Pearson (cnt)':>14} {'Spearman (cnt)':>15}")
    for year in years:
        year_keys = [k for k in keys if k[1] == year]
        if len(year_keys) < 3:
            continue
        yv = [sadipem_value[k] for k in year_keys]
        yc = [sadipem_count[k] for k in year_keys]
        yt = [transferencias_total[k] for k in year_keys]
        print(
            f"{year:<6} {len(year_keys):>5} "
            f"{pearson(yv, yt):>14.4f} {spearman(yv, yt):>15.4f} "
            f"{pearson(yc, yt):>14.4f} {spearman(yc, yt):>15.4f}"
        )


if __name__ == "__main__":
    main()
