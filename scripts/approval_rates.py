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

`compute()` returns the underlying numbers with no printing, so other tools
(e.g. generate_report.py) can render them their own way.
"""

from collections import defaultdict

from _datasets import sadipem_rows

MIN_REQUESTS_FOR_UF_RATE = 30
ABOVE_BELOW_AVERAGE_PP = 5


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


def compute():
    """Aggregate SADIPEM request outcomes overall, per year and per state.

    Returns a dict:
      total, overall: grand total request count and {bucket: count} status mix
      national_rate: overall approval rate (%)
      by_year: [{"year", "requests", "rate", "vs_national"}, ...]
      by_uf:   [{"uf", "requests", "rate", "diff_pp"}, ...] (UFs with at least
               MIN_REQUESTS_FOR_UF_RATE requests, ranked by rate desc)
    """
    overall = defaultdict(int)
    by_year_counts = defaultdict(lambda: defaultdict(int))
    by_uf_counts = defaultdict(lambda: defaultdict(int))

    for row in sadipem_rows():
        bucket = status_bucket(row["status"])
        overall[bucket] += 1
        by_year_counts[row["year"]][bucket] += 1
        by_uf_counts[row["uf"]][bucket] += 1

    total = sum(overall.values())
    national_rate = approval_rate(overall)

    by_year = []
    for year in sorted(by_year_counts):
        counts = by_year_counts[year]
        rate = approval_rate(counts)
        by_year.append({
            "year": year,
            "requests": sum(counts.values()),
            "rate": rate,
            "vs_national": (
                "above" if rate > national_rate + ABOVE_BELOW_AVERAGE_PP else
                "below" if rate < national_rate - ABOVE_BELOW_AVERAGE_PP else
                "average"
            ),
        })

    by_uf = []
    for uf, counts in by_uf_counts.items():
        requests = sum(counts.values())
        if requests < MIN_REQUESTS_FOR_UF_RATE:
            continue
        rate = approval_rate(counts)
        by_uf.append({"uf": uf, "requests": requests, "rate": rate, "diff_pp": rate - national_rate})
    by_uf.sort(key=lambda row: -row["rate"])

    return {
        "total": total,
        "overall": dict(overall),
        "national_rate": national_rate,
        "by_year": by_year,
        "by_uf": by_uf,
    }


def main():
    result = compute()
    total = result["total"]

    print(f"Status mix across all {total} SADIPEM requests in the local data:")
    for bucket, count in sorted(result["overall"].items(), key=lambda kv: -kv[1]):
        print(f"  {bucket:<10} {count:>6}  ({100 * count / total:.1f}%)")
    print(f"\nOverall approval rate: {result['national_rate']:.1f}%")

    print(f"\n{'Year':<6} {'Requests':>9} {'Approval rate':>14}")
    for row in result["by_year"]:
        flag = (
            "  ↑ above average" if row["vs_national"] == "above" else
            "  ↓ below average" if row["vs_national"] == "below" else ""
        )
        print(f"{row['year']:<6} {row['requests']:>9} {row['rate']:>13.1f}%{flag}")

    print(f"\n{'UF':<4} {'Requests':>9} {'Approval rate':>14}  vs. national average ({result['national_rate']:.1f}%)")
    for row in result["by_uf"]:
        print(f"{row['uf']:<4} {row['requests']:>9} {row['rate']:>13.1f}%  {row['diff_pp']:+.1f} pp")


if __name__ == "__main__":
    main()
