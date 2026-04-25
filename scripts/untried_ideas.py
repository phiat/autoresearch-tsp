"""
Enumerate ideas in <subproject>/ideas.md that have NOT been tried yet
(no matching id in any results.tsv description). Bucketed by class +
provenance.

Usage (from a subproject dir):
    python ../scripts/untried_ideas.py
or with explicit paths:
    python scripts/untried_ideas.py --ideas tsp_heuristic/ideas.md \
        --results tsp_heuristic/results.tsv

Backs the `untried-ideas` skill in both .claude/skills/ pools.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Idea-id pattern: a class-prefix letter + 1-3 digits, like L10, X13, C14, M7.
ID_RE = re.compile(r"^- ([A-Z])(\d{1,3})\.")


def parse_ideas(ideas_md: Path) -> list[dict]:
    """Return list of {id, class, num, provenance, line} for every idea bullet."""
    if not ideas_md.exists():
        return []
    ideas: list[dict] = []
    current_section = "(unknown)"
    for raw in ideas_md.read_text().splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            current_section = line.removeprefix("## ").strip()
            continue
        m = ID_RE.match(line)
        if not m:
            continue
        cls, num = m.group(1), int(m.group(2))
        ideas.append({
            "id": f"{cls}{num}",
            "class": cls,
            "num": num,
            "provenance": _classify_provenance(current_section),
            "section": current_section,
            "line": line.strip(),
        })
    return ideas


def _classify_provenance(section: str) -> str:
    s = section.lower()
    if "permute" in s:
        return "permute"
    if "research" in s:
        if "domain" in s:
            return "research-domain"
        if "classical" in s:
            return "research-classical"
        if "modern-learned" in s or "modern" in s:
            return "research-modern"
        if "hybrid" in s:
            return "research-hybrid"
        if "manual" in s or "injection" in s:
            return "research-manual"
        return "research-other"
    if "appended (cycle" in s or "growth tick" in s or "self-generated" in s:
        return "growth-cycle"
    if "seed ideas" in s or section == "(unknown)":
        return "seed"
    return "other"


def parse_results_descriptions(results_tsv: Path) -> list[str]:
    """Return list of description strings (col 5) from results.tsv, skipping header."""
    if not results_tsv.exists():
        return []
    descs: list[str] = []
    for i, raw in enumerate(results_tsv.read_text().splitlines()):
        if i == 0:
            continue  # header
        cols = raw.split("\t")
        if len(cols) >= 5:
            descs.append(cols[4])
    return descs


def find_untried(ideas: list[dict], descs: list[str]) -> list[dict]:
    """An idea is "tried" if its id appears as a token in any description."""
    untried: list[dict] = []
    for idea in ideas:
        token_re = re.compile(r"\b" + re.escape(idea["id"]) + r"\b")
        tested = any(token_re.search(d) for d in descs)
        if not tested:
            untried.append(idea)
    return untried


def report(ideas: list[dict], untried: list[dict]) -> str:
    lines: list[str] = []
    lines.append(f"untried-ideas report:")
    lines.append(f"  total in pool: {len(ideas)}, untried: {len(untried)}, "
                 f"tested: {len(ideas) - len(untried)}")
    lines.append("")

    # By class
    by_class: dict[str, int] = {}
    for u in untried:
        by_class[u["class"]] = by_class.get(u["class"], 0) + 1
    if by_class:
        bits = "  ".join(f"{k}: {v}" for k, v in sorted(by_class.items()))
        lines.append(f"By class (untried count):  {bits}")

    # By provenance
    lines.append("")
    lines.append("By provenance:")
    by_prov: dict[str, int] = {}
    for u in untried:
        by_prov[u["provenance"]] = by_prov.get(u["provenance"], 0) + 1
    for prov, n in sorted(by_prov.items(), key=lambda kv: -kv[1]):
        ids = ", ".join(u["id"] for u in untried if u["provenance"] == prov)
        lines.append(f"  {prov:24s} {n:3d}  ({ids})")

    # Highlight research / manual injections
    high_novelty = [u for u in untried
                    if u["provenance"].startswith("research")
                    or u["provenance"] == "research-manual"]
    if high_novelty:
        lines.append("")
        lines.append("High-novelty untried (research-injected — strongest "
                     "candidates to break a plateau):")
        for u in high_novelty[:8]:
            preview = u["line"][:100] + ("…" if len(u["line"]) > 100 else "")
            lines.append(f"  {preview}")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ideas", default="ideas.md", help="path to ideas.md")
    ap.add_argument("--results", default="results.tsv", help="path to results.tsv")
    args = ap.parse_args()

    ideas_md = Path(args.ideas)
    results_tsv = Path(args.results)

    ideas = parse_ideas(ideas_md)
    if not ideas:
        print(f"no ideas parsed from {ideas_md}", file=sys.stderr)
        return 1
    descs = parse_results_descriptions(results_tsv)
    untried = find_untried(ideas, descs)

    print(report(ideas, untried))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
