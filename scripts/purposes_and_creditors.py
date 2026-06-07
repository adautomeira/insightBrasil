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

`compute()` returns the underlying numbers with no printing, so other tools
(e.g. generate_report.py) can render them their own way.
"""

from collections import defaultdict

from _datasets import sadipem_rows

TOP_N = 12


def build_breakdown(value_by_key, count_by_key, total_value):
    ranked = sorted(value_by_key.items(), key=lambda kv: -kv[1])[:TOP_N]
    return [
        {
            "label": key,
            "value": value,
            "share_pct": 100 * value / total_value if total_value else 0.0,
            "operations": count_by_key[key],
        }
        for key, value in ranked
    ]


def compute():
    """Aggregate approved ("Deferido*") SADIPEM operations by purpose, creditor and creditor type.

    Returns a dict:
      total_value, total_count: grand totals across all approved operations
      finalidade, tipo_credor, credor: each a list of the TOP_N breakdown rows
        ({"label", "value", "share_pct", "operations"}), sorted by value desc.
    """
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

    return {
        "total_value": total_value,
        "total_count": total_count,
        "finalidade": build_breakdown(value_by_finalidade, count_by_finalidade, total_value),
        "tipo_credor": build_breakdown(value_by_tipo_credor, count_by_tipo_credor, total_value),
        "credor": build_breakdown(value_by_credor, count_by_credor, total_value),
    }


def print_breakdown(title, rows):
    print(f"\n{title}")
    print(f"{'#':>3}  {'Value (R$)':>20} {'Share':>7} {'Operations':>11}  Description")
    for i, row in enumerate(rows, start=1):
        print(f"{i:>3}  {row['value']:>20,.2f} {row['share_pct']:>6.1f}% {row['operations']:>11}  {row['label']}")


def main():
    result = compute()
    print(f"Approved (\"Deferido*\") SADIPEM operations, {result['total_count']} total, "
          f"R$ {result['total_value']:,.2f} combined\n")
    print(f"Top {TOP_N} by total approved value:")

    print_breakdown("=== Purpose (Finalidade) ===", result["finalidade"])
    print_breakdown("=== Creditor type (Tipo de credor) — fewer, broader categories ===", result["tipo_credor"])
    print_breakdown("=== Creditor (Credor) — specific institutions ===", result["credor"])


if __name__ == "__main__":
    main()
