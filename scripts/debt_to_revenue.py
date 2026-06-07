#!/usr/bin/env python3
"""Compare states by how much credit they take on relative to constitutional revenue.

Correlation tells us whether two series move together; it doesn't tell us
whether any given state is borrowing a *lot* relative to its size. This script
computes a simple debt-to-revenue ratio per (UF, year):

    ratio = SADIPEM approved ("Deferido*") credit value / transfers received

A ratio near zero means a state's new credit operations are small next to its
constitutional revenue; a ratio above 1 means it took on more in new approved
credit that year than it received in transfers — a much more "fiscal exposure"
framing than a correlation coefficient gives you.

Reports the national average ratio per year (a trend across the political
cycles in the window) and, per year, which states sit at the extremes — plus
each state's average ratio across the whole window, ranked.

`compute()` returns the underlying numbers with no printing, so other tools
(e.g. generate_report.py) can render them their own way.
"""

from collections import defaultdict

from _datasets import sadipem_rows, transferencias_rows


def compute():
    """Aggregate both datasets by (UF, year) and derive the debt-to-revenue ratio.

    Returns a dict:
      years:       sorted list of years with at least one valid ratio
      by_year:     [{"year", "states", "national_avg",
                     "highest": (uf, ratio), "lowest": (uf, ratio)}, ...]
      by_uf:       [{"uf", "avg_ratio"}, ...] sorted highest to lowest
    """
    sadipem_value = defaultdict(float)
    for row in sadipem_rows():
        if row["status"].startswith("Deferido"):
            sadipem_value[(row["uf"], row["year"])] += row["valor"]

    transfers_total = defaultdict(float)
    for row in transferencias_rows():
        transfers_total[(row["uf"], row["year"])] += row["total"]

    keys = sorted(set(sadipem_value) & set(transfers_total))
    ratio = {k: sadipem_value[k] / transfers_total[k] for k in keys if transfers_total[k]}
    years = sorted({year for _, year in ratio})

    by_year = []
    for year in years:
        year_keys = [k for k in keys if k[1] == year and k in ratio]
        if not year_keys:
            continue
        avg = sum(ratio[k] for k in year_keys) / len(year_keys)
        highest = max(year_keys, key=lambda k: ratio[k])
        lowest = min(year_keys, key=lambda k: ratio[k])
        by_year.append({
            "year": year,
            "states": len(year_keys),
            "national_avg": avg,
            "highest": (highest[0], ratio[highest]),
            "lowest": (lowest[0], ratio[lowest]),
        })

    avg_ratio_by_uf = defaultdict(list)
    for (uf, year), r in ratio.items():
        avg_ratio_by_uf[uf].append(r)
    by_uf = [
        {"uf": uf, "avg_ratio": sum(rs) / len(rs)}
        for uf, rs in avg_ratio_by_uf.items()
    ]
    by_uf.sort(key=lambda row: -row["avg_ratio"])

    return {"years": years, "by_year": by_year, "by_uf": by_uf}


def main():
    result = compute()
    years = result["years"]

    print("Debt-to-revenue ratio = SADIPEM approved credit value ÷ constitutional transfers received\n")
    print(f"{'Year':<6} {'States':>7} {'National avg ratio':>19} {'Highest (state: ratio)':>34} {'Lowest (state: ratio)':>30}")
    for row in result["by_year"]:
        highest_uf, highest_ratio = row["highest"]
        lowest_uf, lowest_ratio = row["lowest"]
        print(
            f"{row['year']:<6} {row['states']:>7} {row['national_avg']:>19.4f} "
            f"{highest_uf + ': ' + format(highest_ratio, '.4f'):>34} "
            f"{lowest_uf + ': ' + format(lowest_ratio, '.4f'):>30}"
        )

    print(f"\nAverage ratio across {years[0]}-{years[-1]}, highest to lowest:")
    for row in result["by_uf"]:
        print(f"  {row['uf']:<4} {row['avg_ratio']:.4f}")


if __name__ == "__main__":
    main()
