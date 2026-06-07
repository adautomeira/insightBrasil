#!/usr/bin/env python3
"""Track how national totals evolved year over year across the local window.

A single correlation coefficient collapses everything into one number; this
script keeps the time axis intact and reports the trajectory itself — national
totals per year for both datasets, plus year-over-year percent change — so
swings tied to elections, economic shocks, or policy changes (e.g. the 2020
pandemic — see pandemic_spotlight.py for a focused look at that one) are
visible directly rather than smoothed away into an aggregate statistic.

`compute()` returns the underlying numbers with no printing, so other tools
(e.g. generate_report.py) can render them their own way.
"""

import datetime
from collections import defaultdict

from _datasets import sadipem_rows, transferencias_rows

CURRENT_YEAR = str(datetime.date.today().year)
EXTRAORDINARY_SWING_PCT = 40


def pct_change(previous, current):
    if not previous:
        return float("nan")
    return 100 * (current - previous) / previous


def build_series(totals):
    """Turn a {year: total} dict into an ordered list of rows with YoY change and flags.

    Each series gets its own year range — the two datasets cover different
    spans locally (SADIPEM is a single file with the full 2002+ history, while
    transferências is a rolling 12-year window, see download_data.py), and
    padding the shorter one with "R$ 0.00" rows for years it has no data for
    would be misleading, not informative.
    """
    rows = []
    previous = None
    for year in sorted(totals):
        value = totals[year]
        is_partial = year == CURRENT_YEAR
        change = None if (previous is None or is_partial) else pct_change(previous, value)
        rows.append({
            "year": year,
            "value": value,
            "change_pct": change,
            "is_partial": is_partial,
            "is_extraordinary": change is not None and abs(change) > EXTRAORDINARY_SWING_PCT,
        })
        previous = value
    return rows


def compute():
    """Aggregate national totals per year for both datasets.

    Returns a dict: {"sadipem_value": [...rows...], "sadipem_count": [...],
    "transfers": [...]} — each row has year, value, change_pct (None for the
    first year and for the in-progress current year), is_partial, is_extraordinary.
    """
    sadipem_value = defaultdict(float)
    sadipem_count = defaultdict(int)
    for row in sadipem_rows():
        if row["status"].startswith("Deferido"):
            sadipem_value[row["year"]] += row["valor"]
            sadipem_count[row["year"]] += 1

    transfers_total = defaultdict(float)
    for row in transferencias_rows():
        transfers_total[row["year"]] += row["total"]

    return {
        "sadipem_value": build_series(sadipem_value),
        "sadipem_count": build_series(sadipem_count),
        "transfers": build_series(transfers_total),
    }


def print_series(title, rows, unit_label):
    print(f"\n{title}")
    print(f"{'Year':<6} {'Total':>20} {'YoY change':>12}")
    for row in rows:
        if row["is_partial"]:
            change_str, flag = "", "  ← year in progress, not comparable"
        elif row["change_pct"] is None:
            change_str, flag = "", ""
        else:
            change_str = f"{row['change_pct']:+.1f}%"
            flag = "  ← extraordinary swing" if row["is_extraordinary"] else ""
        print(f"{row['year']:<6} {row['value']:>20,.2f} {change_str:>12}{flag}")
    print(f"(values in {unit_label})")


def main():
    result = compute()
    print("National totals by year (each series spans whatever years it has locally — see note above)")
    print_series("=== SADIPEM approved (\"Deferido*\") credit value — full 2002+ history (single consolidated file) ===",
                 result["sadipem_value"], "R$")
    print_series("=== SADIPEM approved (\"Deferido*\") request count — full 2002+ history ===",
                 result["sadipem_count"], "requests")
    print_series("=== Constitutional transfers received — rolling 12-year window (2016+) ===",
                 result["transfers"], "R$")


if __name__ == "__main__":
    main()
