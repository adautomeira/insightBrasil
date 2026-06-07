#!/usr/bin/env python3
"""Spotlight 2020-2021 — the pandemic years — as the extraordinary outliers they were.

Every other script in this folder treats all years in the window evenly. This
one deliberately doesn't: 2020-2021 saw a public-health emergency, a sudden
economic contraction, emergency federal aid (e.g. the "Auxílio Emergencial" and
ad-hoc FPM/FPE supplementation), and a wave of states rushing to secure credit
to cover the shortfall — none of which fit the normal year-to-year pattern.

Compares 2020-2021 against the two years immediately before and after (a
"baseline" of 2018-2019 and 2022-2023) across every angle the other scripts
look at — transfer totals, approved credit value, approval rates, and the debt-
to-revenue ratio — and reports each as a percent deviation from that baseline,
making the size of the disruption explicit rather than something you'd have to
notice yourself by eyeballing trends.py's output.
"""

from collections import defaultdict

from _datasets import sadipem_rows, transferencias_rows

PANDEMIC_YEARS = ["2020", "2021"]
BASELINE_YEARS = ["2018", "2019", "2022", "2023"]


def avg(values):
    values = list(values)
    return sum(values) / len(values) if values else float("nan")


def deviation_line(label, pandemic_avg, baseline_avg, unit_label, fmt="{:,.2f}"):
    deviation = 100 * (pandemic_avg - baseline_avg) / baseline_avg if baseline_avg else float("nan")
    arrow = "▲" if deviation > 0 else "▼"
    flag = "  ⚠ EXTRAORDINARY" if abs(deviation) > 25 else ""
    print(
        f"  {label:<32} baseline {fmt.format(baseline_avg):>18} {unit_label:<10} "
        f"→ pandemic {fmt.format(pandemic_avg):>18} {unit_label:<10} "
        f"  {arrow} {deviation:+.1f}%{flag}"
    )


def main():
    transfers_by_year = defaultdict(float)
    for row in transferencias_rows():
        transfers_by_year[row["year"]] += row["total"]

    sadipem_value_by_year = defaultdict(float)
    sadipem_count_by_year = defaultdict(int)
    status_by_year = defaultdict(lambda: defaultdict(int))
    for row in sadipem_rows():
        status_by_year[row["year"]][row["status"]] += 1
        if row["status"].startswith("Deferido"):
            sadipem_value_by_year[row["year"]] += row["valor"]
            sadipem_count_by_year[row["year"]] += 1

    def approval_rate(year):
        counts = status_by_year[year]
        total = sum(counts.values())
        approved = sum(c for s, c in counts.items() if s.startswith("Deferido"))
        return 100 * approved / total if total else float("nan")

    def ratio(year):
        return sadipem_value_by_year[year] / transfers_by_year[year] if transfers_by_year[year] else float("nan")

    print("=" * 78)
    print("  ⚠  PANDEMIC SPOTLIGHT — 2020-2021 vs. surrounding 'normal' years (2018-19, 2022-23)")
    print("=" * 78)
    print(
        "\nBrazil's COVID-19 public-health emergency hit in March 2020: GDP contracted,\n"
        "tax collection dropped, the federal government rolled out emergency aid and\n"
        "ad-hoc transfer supplements, and states scrambled for credit to cover the gap.\n"
        "None of that fits the normal year-to-year pattern — here's how far it strayed:\n"
    )

    deviation_line(
        "Constitutional transfers received",
        avg(transfers_by_year[y] for y in PANDEMIC_YEARS),
        avg(transfers_by_year[y] for y in BASELINE_YEARS),
        "R$",
    )
    deviation_line(
        "SADIPEM approved credit value",
        avg(sadipem_value_by_year[y] for y in PANDEMIC_YEARS),
        avg(sadipem_value_by_year[y] for y in BASELINE_YEARS),
        "R$",
    )
    deviation_line(
        "SADIPEM approved request count",
        avg(sadipem_count_by_year[y] for y in PANDEMIC_YEARS),
        avg(sadipem_count_by_year[y] for y in BASELINE_YEARS),
        "requests",
        fmt="{:,.1f}",
    )
    deviation_line(
        "SADIPEM approval rate",
        avg(approval_rate(y) for y in PANDEMIC_YEARS),
        avg(approval_rate(y) for y in BASELINE_YEARS),
        "%",
        fmt="{:.1f}",
    )
    deviation_line(
        "Debt-to-revenue ratio",
        avg(ratio(y) for y in PANDEMIC_YEARS),
        avg(ratio(y) for y in BASELINE_YEARS),
        "ratio",
        fmt="{:.4f}",
    )

    print(f"\n{'Year':<6} {'Transfers (R$)':>20} {'SADIPEM value (R$)':>22} {'Approval rate':>14} {'Debt/revenue':>13}")
    for year in sorted(set(BASELINE_YEARS) | set(PANDEMIC_YEARS)):
        marker = " ⚠ pandemic" if year in PANDEMIC_YEARS else ""
        print(
            f"{year:<6} {transfers_by_year[year]:>20,.2f} {sadipem_value_by_year[year]:>22,.2f} "
            f"{approval_rate(year):>13.1f}% {ratio(year):>13.4f}{marker}"
        )


if __name__ == "__main__":
    main()
