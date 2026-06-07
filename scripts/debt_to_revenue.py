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
cycles in the window) and, per year, which states sit at the extremes.
"""

from collections import defaultdict

from _datasets import sadipem_rows, transferencias_rows


def main():
    sadipem_value = defaultdict(float)
    for row in sadipem_rows():
        if row["status"].startswith("Deferido"):
            sadipem_value[(row["uf"], row["year"])] += row["valor"]

    transfers_total = defaultdict(float)
    for row in transferencias_rows():
        transfers_total[(row["uf"], row["year"])] += row["total"]

    keys = sorted(set(sadipem_value) & set(transfers_total))
    years = sorted({year for _, year in keys})

    ratio = {k: sadipem_value[k] / transfers_total[k] for k in keys if transfers_total[k]}

    print("Debt-to-revenue ratio = SADIPEM approved credit value ÷ constitutional transfers received\n")
    print(f"{'Year':<6} {'States':>7} {'National avg ratio':>19} {'Highest (state: ratio)':>34} {'Lowest (state: ratio)':>30}")
    for year in years:
        year_keys = [k for k in keys if k[1] == year and k in ratio]
        if not year_keys:
            continue
        avg = sum(ratio[k] for k in year_keys) / len(year_keys)
        highest = max(year_keys, key=lambda k: ratio[k])
        lowest = min(year_keys, key=lambda k: ratio[k])
        print(
            f"{year:<6} {len(year_keys):>7} {avg:>19.4f} "
            f"{highest[0] + ': ' + format(ratio[highest], '.4f'):>34} "
            f"{lowest[0] + ': ' + format(ratio[lowest], '.4f'):>30}"
        )

    # Across the whole window, which states most consistently lean on credit
    # relative to their constitutional revenue (vs. those that barely do)?
    avg_ratio_by_uf = defaultdict(list)
    for (uf, year), r in ratio.items():
        avg_ratio_by_uf[uf].append(r)
    avg_ratio_by_uf = {uf: sum(rs) / len(rs) for uf, rs in avg_ratio_by_uf.items()}

    ranked = sorted(avg_ratio_by_uf.items(), key=lambda kv: -kv[1])
    print(f"\nAverage ratio across {years[0]}-{years[-1]}, highest to lowest:")
    for uf, avg in ranked:
        print(f"  {uf:<4} {avg:.4f}")


if __name__ == "__main__":
    main()
