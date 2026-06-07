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

Pearson vs. Spearman: pooling years of SADIPEM values mixes wildly different
scales — a single mega-operation (e.g. São Paulo's ~R$224 billion 2017 debt
renegotiation) can be 100x the size of a typical (state, year) pair, and such
an extreme leverage point can swing Pearson's r across hundreds of data points.
Spearman sidesteps that: it correlates the *ranks* of the values rather than
the values themselves, so one enormous outlier counts no more than "the
biggest one this year" — making it the more trustworthy aggregate measure when
years of differing scale are pooled together (Pearson stays useful per-year,
where all pairs share roughly the same scale).

`compute()` returns the underlying numbers with no printing, so other tools
(e.g. generate_report.py) can render them their own way.
"""

from collections import defaultdict

from _datasets import sadipem_rows, transferencias_rows


def pearson(xs, ys):
    """Pearson's r: how strongly two equal-length series move together, linearly.

    Standard textbook formula — r = covariance(x, y) / (stdev(x) * stdev(y)):
      - covariance: do x and y tend to be above/below their own averages
        *at the same time*? (positive when they do, negative when they move
        in opposite directions)
      - dividing by both spreads (stdev_x * stdev_y) rescales that into the
        familiar -1..+1 range, independent of the units each series is in
    Returns NaN if either series is constant (zero spread) — "how correlated
    is X with a value that never changes" has no meaningful answer.
    """
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
    """Convert values to their ranks (1 = smallest), the input Spearman needs.

    Spearman correlation is just Pearson's r computed on ranks instead of raw
    values (see `spearman` below) — this function does that conversion.

    Walks the values from smallest to largest. Equal values form a "tied"
    group that all share one rank: the *average* of the positions they
    occupy. E.g. values [10, 20, 20, 40] occupy positions 1, 2, 3, 4 — the
    two 20s tie for positions 2 and 3, so they both get rank (2+3)/2 = 2.5,
    and the 40 gets rank 4 (its position is unaffected by the tie below it).
    This is the standard way to rank data with ties; it keeps the total of
    all ranks the same as if there had been no ties at all.
    """
    # `order` lists each value's original index, sorted by that value —
    # i.e. order[0] is the index of the smallest value, and so on.
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        # Grow the group [i, j] to cover every following value equal to
        # values[order[i]] — that's one tied group sharing one rank.
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        # Positions are 1-based ranks; the group spans ranks i+1..j+1,
        # and ties share the midpoint of that span.
        average_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            result[order[k]] = average_rank
        i = j + 1
    return result


def spearman(xs, ys):
    """Pearson's r computed on ranks instead of raw values — robust to outliers."""
    return pearson(ranks(xs), ranks(ys))


def compute():
    """Aggregate both datasets by (UF, year) and correlate them, pooled and per year.

    Returns a dict:
      years:    sorted list of years present in both datasets
      pooled:   {"value": {"pearson": r, "spearman": rho}, "count": {...}}
      by_year:  [{"year", "pairs", "pearson_value", "spearman_value",
                  "pearson_count", "spearman_count"}, ...] (years with >= 3 pairs)
    """
    sadipem_value = defaultdict(float)
    sadipem_count = defaultdict(int)
    for row in sadipem_rows():
        if row["status"].startswith("Deferido"):
            key = (row["uf"], row["year"])
            sadipem_value[key] += row["valor"]
            sadipem_count[key] += 1

    transferencias_total = defaultdict(float)
    for row in transferencias_rows():
        transferencias_total[(row["uf"], row["year"])] += row["total"]

    # Only pairs present on both sides make a valid data point for correlation.
    keys = sorted(set(sadipem_value) & set(transferencias_total))
    years = sorted({year for _, year in keys})

    values = [sadipem_value[k] for k in keys]
    counts = [sadipem_count[k] for k in keys]
    transfers = [transferencias_total[k] for k in keys]

    pooled = {
        "value": {"pearson": pearson(values, transfers), "spearman": spearman(values, transfers)},
        "count": {"pearson": pearson(counts, transfers), "spearman": spearman(counts, transfers)},
    }

    by_year = []
    for year in years:
        year_keys = [k for k in keys if k[1] == year]
        if len(year_keys) < 3:
            continue
        yv = [sadipem_value[k] for k in year_keys]
        yc = [sadipem_count[k] for k in year_keys]
        yt = [transferencias_total[k] for k in year_keys]
        by_year.append({
            "year": year,
            "pairs": len(year_keys),
            "pearson_value": pearson(yv, yt),
            "spearman_value": spearman(yv, yt),
            "pearson_count": pearson(yc, yt),
            "spearman_count": spearman(yc, yt),
        })

    return {"years": years, "pooled": pooled, "by_year": by_year}


def main():
    result = compute()
    years = result["years"]
    pooled = result["pooled"]

    total_pairs = sum(row["pairs"] for row in result["by_year"])
    print(f"{total_pairs} (UF, year) pairs across {len(years)} years: {years[0]}-{years[-1]}\n")

    print("Pooled across all years (Pearson is skewed here by mega-outliers like SP 2017 — see Spearman):")
    print(f"  value  vs. transfers — Pearson r: {pooled['value']['pearson']:>8.4f}   Spearman ρ: {pooled['value']['spearman']:>8.4f}")
    print(f"  count  vs. transfers — Pearson r: {pooled['count']['pearson']:>8.4f}   Spearman ρ: {pooled['count']['spearman']:>8.4f}")

    # Break it down per year too — useful to see whether the relationship
    # holds steady or shifts across the political cycles in the window. Within
    # a single year all pairs share roughly the same scale, so Pearson and
    # Spearman tend to agree much more closely than they do pooled.
    print(f"\n{'Year':<6} {'Pairs':>5} {'Pearson (val)':>14} {'Spearman (val)':>15} {'Pearson (cnt)':>14} {'Spearman (cnt)':>15}")
    for row in result["by_year"]:
        print(
            f"{row['year']:<6} {row['pairs']:>5} "
            f"{row['pearson_value']:>14.4f} {row['spearman_value']:>15.4f} "
            f"{row['pearson_count']:>14.4f} {row['spearman_count']:>15.4f}"
        )


if __name__ == "__main__":
    main()
