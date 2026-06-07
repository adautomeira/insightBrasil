#!/usr/bin/env python3
"""Track how national totals evolved year over year across the 2016-2026 window.

A single correlation coefficient collapses everything into one number; this
script keeps the time axis intact and reports the trajectory itself — national
totals per year for both datasets, plus year-over-year percent change — so
swings tied to elections, economic shocks, or policy changes (e.g. the 2020
pandemic — see pandemic_spotlight.py for a focused look at that one) are
visible directly rather than smoothed away into an aggregate statistic.
"""

import datetime
from collections import defaultdict

from _datasets import sadipem_rows, transferencias_rows

CURRENT_YEAR = str(datetime.date.today().year)


def pct_change(previous, current):
    if not previous:
        return float("nan")
    return 100 * (current - previous) / previous


def print_series(title, totals, unit_label):
    """Print one year-by-year series, using only the years that series actually has data for.

    The two datasets cover different spans locally — SADIPEM is a single file
    with the full 2002+ history, while transferências is a rolling 12-year
    window (see download_data.py) — so each series gets its own year range
    rather than a shared one, which would otherwise pad the shorter series
    with misleading "R$ 0.00" rows for years it simply has no data for.
    """
    years = sorted(totals)
    print(f"\n{title}")
    print(f"{'Year':<6} {'Total':>20} {'YoY change':>12}")
    previous = None
    for year in years:
        value = totals[year]
        is_partial = year == CURRENT_YEAR
        if previous is None or is_partial:
            change = ""
        else:
            change = f"{pct_change(previous, value):+.1f}%"
        if is_partial:
            flag = "  ← year in progress, not comparable"
        elif previous and abs(pct_change(previous, value)) > 40:
            flag = "  ← extraordinary swing"
        else:
            flag = ""
        print(f"{year:<6} {value:>20,.2f} {change:>12}{flag}")
        previous = value
    print(f"(values in {unit_label})")


def main():
    sadipem_value = defaultdict(float)
    sadipem_count = defaultdict(int)
    for row in sadipem_rows():
        if row["status"].startswith("Deferido"):
            sadipem_value[row["year"]] += row["valor"]
            sadipem_count[row["year"]] += 1

    transfers_total = defaultdict(float)
    for row in transferencias_rows():
        transfers_total[row["year"]] += row["total"]

    print("National totals by year (each series spans whatever years it has locally — see note above)")
    print_series("=== SADIPEM approved (\"Deferido*\") credit value — full 2002+ history (single consolidated file) ===",
                 sadipem_value, "R$")
    print_series("=== SADIPEM approved (\"Deferido*\") request count — full 2002+ history ===",
                 sadipem_count, "requests")
    print_series("=== Constitutional transfers received — rolling 12-year window (2016+) ===",
                 transfers_total, "R$")


if __name__ == "__main__":
    main()
