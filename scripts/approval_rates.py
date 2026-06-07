#!/usr/bin/env python3
"""How often do SADIPEM credit requests actually get approved — and does it shift over time?

The "Status" column records what happened to each request: Deferido (approved),
Indeferido (denied), Arquivado (archived/withdrawn), and a few rarer outcomes.
Looking only at approved operations (as the other scripts do) hides the other
side of the story — how selective the process is, and whether that selectivity
changes with the political and economic climate (e.g. tightening in election
years, or loosening during a crisis when states urgently need credit).

Reports the overall status mix, the approval rate per year, and per state —
highlighting the states furthest from the national average.
"""

from collections import defaultdict

from _datasets import sadipem_rows


def status_bucket(status):
    """Group the many exact status strings into their broad outcome category."""
    if status.startswith("Deferido"):
        return "Deferido"
    if status.startswith("Indeferido"):
        return "Indeferido"
    if status.startswith("Arquivado"):
        return "Arquivado"
    return "Outro"


def approval_rate(counts):
    total = sum(counts.values())
    return 100 * counts.get("Deferido", 0) / total if total else float("nan")


def main():
    overall = defaultdict(int)
    by_year = defaultdict(lambda: defaultdict(int))
    by_uf = defaultdict(lambda: defaultdict(int))

    for row in sadipem_rows():
        bucket = status_bucket(row["status"])
        overall[bucket] += 1
        by_year[row["year"]][bucket] += 1
        by_uf[row["uf"]][bucket] += 1

    total = sum(overall.values())
    print(f"Status mix across all {total} SADIPEM requests in the local data:")
    for bucket, count in sorted(overall.items(), key=lambda kv: -kv[1]):
        print(f"  {bucket:<10} {count:>6}  ({100 * count / total:.1f}%)")
    print(f"\nOverall approval rate: {approval_rate(overall):.1f}%")

    print(f"\n{'Year':<6} {'Requests':>9} {'Approval rate':>14}")
    national_rate = approval_rate(overall)
    for year in sorted(by_year):
        counts = by_year[year]
        rate = approval_rate(counts)
        flag = "  ↑ above average" if rate > national_rate + 5 else "  ↓ below average" if rate < national_rate - 5 else ""
        print(f"{year:<6} {sum(counts.values()):>9} {rate:>13.1f}%{flag}")

    print(f"\n{'UF':<4} {'Requests':>9} {'Approval rate':>14}  vs. national average ({national_rate:.1f}%)")
    for uf in sorted(by_uf, key=lambda u: -approval_rate(by_uf[u])):
        counts = by_uf[uf]
        if sum(counts.values()) < 30:
            continue  # too few requests for the rate to mean much
        rate = approval_rate(counts)
        diff = rate - national_rate
        print(f"{uf:<4} {sum(counts.values()):>9} {rate:>13.1f}%  {diff:+.1f} pp")


if __name__ == "__main__":
    main()
