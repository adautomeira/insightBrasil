#!/usr/bin/env python3
"""Break down approved SADIPEM credit operations by what they're for and who's lending.

Knowing that states borrow more when transfers are higher says nothing about
*what the money is for* or *who's supplying it*. The "Finalidade" (purpose) and
"Credor" (creditor) columns answer that — turning "states borrow more" into
"states borrow more for X, mostly from Y". Reports the top entries by total
approved value (and how many operations make up that total) for both, plus a
breakdown of creditor *type* (national financial institution, multilateral
organism, foreign government, etc.) which is the cleaner high-level lens since
"Credor" itself has dozens of distinct institution names.
"""

from collections import defaultdict

from _datasets import sadipem_rows

TOP_N = 12


def print_breakdown(title, value_by_key, count_by_key, total_value):
    ranked = sorted(value_by_key.items(), key=lambda kv: -kv[1])[:TOP_N]
    print(f"\n{title}")
    print(f"{'#':>3}  {'Value (R$)':>20} {'Share':>7} {'Operations':>11}  Description")
    for i, (key, value) in enumerate(ranked, start=1):
        share = 100 * value / total_value if total_value else 0
        print(f"{i:>3}  {value:>20,.2f} {share:>6.1f}% {count_by_key[key]:>11}  {key}")


def main():
    value_by_finalidade = defaultdict(float)
    count_by_finalidade = defaultdict(int)
    value_by_credor = defaultdict(float)
    count_by_credor = defaultdict(int)
    value_by_tipo_credor = defaultdict(float)
    count_by_tipo_credor = defaultdict(int)
    total_value = 0.0
    total_count = 0

    for row in sadipem_rows():
        if not row["status"].startswith("Deferido"):
            continue
        v = row["valor"]
        value_by_finalidade[row["finalidade"]] += v
        count_by_finalidade[row["finalidade"]] += 1
        value_by_credor[row["credor"]] += v
        count_by_credor[row["credor"]] += 1
        value_by_tipo_credor[row["tipo_credor"]] += v
        count_by_tipo_credor[row["tipo_credor"]] += 1
        total_value += v
        total_count += 1

    print(f"Approved (\"Deferido*\") SADIPEM operations, {total_count} total, R$ {total_value:,.2f} combined\n")
    print(f"Top {TOP_N} by total approved value:")

    print_breakdown("=== Purpose (Finalidade) ===", value_by_finalidade, count_by_finalidade, total_value)
    print_breakdown("=== Creditor type (Tipo de credor) — fewer, broader categories ===",
                    value_by_tipo_credor, count_by_tipo_credor, total_value)
    print_breakdown("=== Creditor (Credor) — specific institutions ===",
                    value_by_credor, count_by_credor, total_value)


if __name__ == "__main__":
    main()
