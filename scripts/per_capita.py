#!/usr/bin/env python3
"""Rank states by transfers received and SADIPEM credit activity, per capita.

Raw totals are dominated by the biggest states simply because they have more
people, more municípios, and bigger budgets — São Paulo will always look like
the protagonist of any ranking by absolute value. Dividing by population (IBGE
2025 estimates, see download_population.py) reframes the comparison around
"how much per resident", which surfaces a very different — and arguably more
meaningful — picture of fiscal weight.

Sums every (UF, year) pair in the local data/ window (2016-2026) and ranks
states by:
  - constitutional transfers received per capita
  - SADIPEM approved ("Deferido*") credit value per capita
...then highlights states whose per-capita rank differs sharply from their
raw-total rank, since that gap is the whole point of normalizing.

`compute()` returns the underlying numbers with no printing, so other tools
(e.g. generate_report.py) can render them their own way.
"""

from collections import defaultdict

from _datasets import population_by_uf, sadipem_rows, transferencias_rows

RANK_SHIFT_THRESHOLD = 8


def rank_desc(by_uf):
    """Turn a {UF: value} mapping into a {UF: rank} one (rank 1 = highest value).

    Used twice per dataset — once on raw totals, once on per-capita figures —
    so each state ends up with two ranks that `build_ranking` below can then
    compare. The minus sign in the sort key just flips "smallest first"
    (Python's default) into "largest first" without a separate `reverse=True`.
    """
    ordered = sorted(by_uf, key=lambda uf: -by_uf[uf])
    return {uf: i + 1 for i, uf in enumerate(ordered)}


def build_ranking(raw_total, population):
    """Combine raw totals, per-capita figures and rank shift into one row list."""
    per_capita = {uf: raw_total[uf] / population[uf] for uf in raw_total}
    raw_rank = rank_desc(raw_total)
    pc_rank = rank_desc(per_capita)

    rows = []
    for uf in sorted(per_capita, key=lambda u: -per_capita[u]):
        rows.append({
            "uf": uf,
            "per_capita": per_capita[uf],
            "raw_total": raw_total[uf],
            "population": population[uf],
            "raw_rank": raw_rank[uf],
            "per_capita_rank": pc_rank[uf],
            "shift": raw_rank[uf] - pc_rank[uf],
        })
    return rows


def compute():
    """Aggregate both datasets per UF (summed across the whole local window) and rank per capita.

    Returns a dict: {"transfers": [...rows...], "sadipem": [...rows...]}
    where each row has uf, per_capita, raw_total, population, raw_rank,
    per_capita_rank, shift (positive = punches above its raw-total weight).
    """
    population = population_by_uf()

    transfers_total = defaultdict(float)
    for row in transferencias_rows():
        if row["uf"] in population:
            transfers_total[row["uf"]] += row["total"]

    sadipem_total = defaultdict(float)
    for row in sadipem_rows():
        if row["status"].startswith("Deferido") and row["uf"] in population:
            sadipem_total[row["uf"]] += row["valor"]

    return {
        "transfers": build_ranking(transfers_total, population),
        "sadipem": build_ranking(sadipem_total, population),
    }


def print_ranking(title, rows, unit_label):
    print(f"\n{title}")
    print(f"{'UF':<4} {'Per capita':>14} {'Raw total':>20} {'Population':>12} {'Raw rank':>9} {'Per-capita rank':>16}  Shift")
    for row in rows:
        marker = ""
        if row["shift"] >= RANK_SHIFT_THRESHOLD:
            marker = "  ↑↑ punches above its raw-total weight"
        elif row["shift"] <= -RANK_SHIFT_THRESHOLD:
            marker = "  ↓↓ raw total overstates it per resident"
        print(
            f"{row['uf']:<4} {row['per_capita']:>14,.2f} {row['raw_total']:>20,.2f} {row['population']:>12,d} "
            f"{row['raw_rank']:>9} {row['per_capita_rank']:>16}{marker}"
        )
    print(f"(values in {unit_label} per resident; raw totals in R$)")


def main():
    result = compute()
    print("Per-capita view of the local window (raw totals summed across all years, divided by 2025 population)")
    print_ranking("=== Constitutional transfers received per capita ===", result["transfers"], "R$")
    print_ranking("=== SADIPEM approved (\"Deferido*\") credit value per capita ===", result["sadipem"], "R$")


if __name__ == "__main__":
    main()
