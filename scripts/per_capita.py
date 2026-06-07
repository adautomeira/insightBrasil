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
"""

from collections import defaultdict

from _datasets import population_by_uf, sadipem_rows, transferencias_rows


def rank_desc(by_uf):
    """UF -> rank (1 = highest value), for highlighting rank-shift later."""
    ordered = sorted(by_uf, key=lambda uf: -by_uf[uf])
    return {uf: i + 1 for i, uf in enumerate(ordered)}


def print_ranking(title, raw_total, per_capita, population, unit_label):
    raw_rank = rank_desc(raw_total)
    pc_rank = rank_desc(per_capita)

    print(f"\n{title}")
    print(f"{'UF':<4} {'Per capita':>14} {'Raw total':>20} {'Population':>12} {'Raw rank':>9} {'Per-capita rank':>16}  Shift")
    for uf in sorted(per_capita, key=lambda u: -per_capita[u]):
        shift = raw_rank[uf] - pc_rank[uf]
        marker = ""
        if shift >= 8:
            marker = "  ↑↑ punches above its raw-total weight"
        elif shift <= -8:
            marker = "  ↓↓ raw total overstates it per resident"
        print(
            f"{uf:<4} {per_capita[uf]:>14,.2f} {raw_total[uf]:>20,.2f} {population[uf]:>12,d} "
            f"{raw_rank[uf]:>9} {pc_rank[uf]:>16}{marker}"
        )
    print(f"(values in {unit_label} per resident; raw totals in R$)")


def main():
    population = population_by_uf()

    transfers_total = defaultdict(float)
    for row in transferencias_rows():
        if row["uf"] in population:
            transfers_total[row["uf"]] += row["total"]

    sadipem_total = defaultdict(float)
    for row in sadipem_rows():
        if row["status"].startswith("Deferido") and row["uf"] in population:
            sadipem_total[row["uf"]] += row["valor"]

    transfers_per_capita = {uf: transfers_total[uf] / population[uf] for uf in transfers_total}
    sadipem_per_capita = {uf: sadipem_total[uf] / population[uf] for uf in sadipem_total}

    print("Per-capita view of the 2016-2026 window (raw totals summed across all years, divided by 2025 population)")

    print_ranking(
        "=== Constitutional transfers received per capita ===",
        transfers_total, transfers_per_capita, population, "R$",
    )
    print_ranking(
        "=== SADIPEM approved (\"Deferido*\") credit value per capita ===",
        sadipem_total, sadipem_per_capita, population, "R$",
    )


if __name__ == "__main__":
    main()
