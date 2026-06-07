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

`compute()` returns the underlying numbers with no printing, so other tools
(e.g. generate_report.py) can render them their own way.
"""

from collections import defaultdict

from _datasets import sadipem_rows, transferencias_rows

PANDEMIC_YEARS = ["2020", "2021"]
BASELINE_YEARS = ["2018", "2019", "2022", "2023"]
EXTRAORDINARY_DEVIATION_PCT = 25


def avg(values):
    values = list(values)
    return sum(values) / len(values) if values else float("nan")


def compute():
    """Compare pandemic-year (2020-2021) figures against a 2018-19/2022-23 baseline.

    Returns a dict:
      metrics: [{"label", "unit", "fmt", "baseline", "pandemic", "deviation_pct",
                 "is_extraordinary"}, ...] — one entry per comparison angle
      by_year: [{"year", "transfers", "sadipem_value", "rate", "ratio",
                 "is_pandemic"}, ...] for the full baseline+pandemic year range
    """
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

    def metric(label, series, unit, fmt):
        """Build one baseline-vs-pandemic comparison.

        `series` is a function that looks up this metric's value for a given
        year (e.g. `lambda y: transfers_by_year[y]`) — passing the lookup
        itself, rather than precomputed numbers, lets every metric below
        share this one averaging/deviation calculation regardless of which
        underlying dict (or derived computation, like `approval_rate`) it
        reads from.

        `deviation_pct` is how far the pandemic-years average sits from the
        baseline average, as a percentage of the baseline — e.g. +118 means
        "the pandemic average was 118% higher than the surrounding normal
        years' average". Anything beyond ±EXTRAORDINARY_DEVIATION_PCT is
        flagged as `is_extraordinary`, the headline finding of this script.
        """
        baseline = avg(series(y) for y in BASELINE_YEARS)
        pandemic = avg(series(y) for y in PANDEMIC_YEARS)
        deviation = 100 * (pandemic - baseline) / baseline if baseline else float("nan")
        return {
            "label": label,
            "unit": unit,
            "fmt": fmt,
            "baseline": baseline,
            "pandemic": pandemic,
            "deviation_pct": deviation,
            "is_extraordinary": abs(deviation) > EXTRAORDINARY_DEVIATION_PCT,
        }

    metrics = [
        metric("Constitutional transfers received", lambda y: transfers_by_year[y], "R$", "{:,.2f}"),
        metric("SADIPEM approved credit value", lambda y: sadipem_value_by_year[y], "R$", "{:,.2f}"),
        metric("SADIPEM approved request count", lambda y: sadipem_count_by_year[y], "requests", "{:,.1f}"),
        metric("SADIPEM approval rate", approval_rate, "%", "{:.1f}"),
        metric("Debt-to-revenue ratio", ratio, "ratio", "{:.4f}"),
    ]

    by_year = []
    for year in sorted(set(BASELINE_YEARS) | set(PANDEMIC_YEARS)):
        by_year.append({
            "year": year,
            "transfers": transfers_by_year[year],
            "sadipem_value": sadipem_value_by_year[year],
            "rate": approval_rate(year),
            "ratio": ratio(year),
            "is_pandemic": year in PANDEMIC_YEARS,
        })

    return {"metrics": metrics, "by_year": by_year}


def print_deviation(m):
    arrow = "▲" if m["deviation_pct"] > 0 else "▼"
    flag = "  ⚠ EXTRAORDINARY" if m["is_extraordinary"] else ""
    fmt = m["fmt"]
    print(
        f"  {m['label']:<32} baseline {fmt.format(m['baseline']):>18} {m['unit']:<10} "
        f"→ pandemic {fmt.format(m['pandemic']):>18} {m['unit']:<10} "
        f"  {arrow} {m['deviation_pct']:+.1f}%{flag}"
    )


def main():
    result = compute()

    print("=" * 78)
    print("  ⚠  PANDEMIC SPOTLIGHT — 2020-2021 vs. surrounding 'normal' years (2018-19, 2022-23)")
    print("=" * 78)
    print(
        "\nBrazil's COVID-19 public-health emergency hit in March 2020: GDP contracted,\n"
        "tax collection dropped, the federal government rolled out emergency aid and\n"
        "ad-hoc transfer supplements, and states scrambled for credit to cover the gap.\n"
        "None of that fits the normal year-to-year pattern — here's how far it strayed:\n"
    )

    for m in result["metrics"]:
        print_deviation(m)

    print(f"\n{'Year':<6} {'Transfers (R$)':>20} {'SADIPEM value (R$)':>22} {'Approval rate':>14} {'Debt/revenue':>13}")
    for row in result["by_year"]:
        marker = " ⚠ pandemic" if row["is_pandemic"] else ""
        print(
            f"{row['year']:<6} {row['transfers']:>20,.2f} {row['sadipem_value']:>22,.2f} "
            f"{row['rate']:>13.1f}% {row['ratio']:>13.4f}{marker}"
        )


if __name__ == "__main__":
    main()
