#!/usr/bin/env python3
"""Verbal identity first-pass analyzer for brand/competitor copy.

Usage:
  python verbal_identity_tool.py --brand brand.txt --competitors comp1.txt comp2.txt --outdir findings
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "you", "our", "are", "not", "can", "all",
    "about", "more", "than", "have", "has", "will", "what", "when", "where", "how", "why", "who", "their", "they",
    "them", "its", "it's", "was", "were", "been", "being", "while", "over", "under", "across", "through", "between",
}

BLAND_CATEGORY_LANGUAGE = {
    "innovative", "innovation", "solutions", "solution", "leading", "leader", "best", "quality", "world-class", "trusted",
    "customer-centric", "value", "values", "seamless", "powerful", "cutting-edge", "efficient", "scalable", "robust",
    "holistic", "end-to-end", "future-proof", "optimize", "optimization", "platform", "service", "services", "experience",
    "transform", "transformation", "impact", "results", "excellence", "reliable", "mission", "vision",
}

WHITESPACE_PROMPTS = [
    "Name what your category avoids talking about (taboo truths, tradeoffs, constraints).",
    "Write 3 claims without any industry nouns (e.g., platform, solution, service).",
    "Swap every abstract adjective for concrete sensory evidence.",
    "Describe your offer as a ritual, not a feature list.",
    "Draft a one-sentence anti-position: what you refuse to promise.",
    "Borrow a voice from outside your category (coach, comedian, scientist) and rewrite a headline.",
    "Write the same message for skeptics first, advocates second.",
]

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z\-']+")


@dataclass
class AnalysisReport:
    repeated_patterns: list[dict]
    bland_language_flags: list[dict]
    whitespace_suggestions: list[str]
    summary: dict


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def ngrams(tokens: list[str], n: int) -> Iterable[tuple[str, ...]]:
    for i in range(len(tokens) - n + 1):
        ng = tuple(tokens[i : i + n])
        if any(t in STOPWORDS for t in ng):
            continue
        yield ng


def top_ngrams(tokens: list[str], n: int, top_k: int = 15, min_count: int = 2) -> list[tuple[str, int]]:
    counts = Counter(ngrams(tokens, n))
    filtered = [(" ".join(k), v) for k, v in counts.items() if v >= min_count]
    return sorted(filtered, key=lambda x: x[1], reverse=True)[:top_k]


def bland_flags(tokens: list[str]) -> list[dict]:
    counts = Counter(tokens)
    flags = []
    for term in sorted(BLAND_CATEGORY_LANGUAGE):
        c = counts[term]
        if c:
            flags.append({"term": term, "count": c, "severity": "high" if c >= 3 else "medium"})
    return sorted(flags, key=lambda x: x["count"], reverse=True)


def analyze(brand_text: str, competitor_texts: list[str]) -> AnalysisReport:
    brand_tokens = tokenize(brand_text)
    comp_tokens = tokenize("\n".join(competitor_texts))

    brand_uni = Counter(t for t in brand_tokens if t not in STOPWORDS)
    comp_uni = Counter(t for t in comp_tokens if t not in STOPWORDS)

    repeated_patterns = []
    for n in (2, 3):
        for phrase, count in top_ngrams(brand_tokens + comp_tokens, n=n):
            repeated_patterns.append({"pattern": phrase, "count": count, "n": n})

    overlap = []
    for term, bcount in brand_uni.items():
        ccount = comp_uni.get(term, 0)
        if bcount >= 2 and ccount >= 2:
            overlap.append({"term": term, "brand_count": bcount, "competitor_count": ccount})
    overlap = sorted(overlap, key=lambda x: (x["brand_count"] + x["competitor_count"]), reverse=True)[:20]

    bland = bland_flags(brand_tokens + comp_tokens)

    summary = {
        "brand_token_count": len(brand_tokens),
        "competitor_token_count": len(comp_tokens),
        "shared_terms": len(overlap),
        "repeated_patterns": len(repeated_patterns),
        "bland_flags": len(bland),
    }

    repeated_patterns.extend(
        {"pattern": item["term"], "count": item["brand_count"] + item["competitor_count"], "n": 1, "type": "overlap"}
        for item in overlap
    )

    return AnalysisReport(
        repeated_patterns=repeated_patterns,
        bland_language_flags=bland,
        whitespace_suggestions=WHITESPACE_PROMPTS,
        summary=summary,
    )


def export_report(report: AnalysisReport, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    json_path = outdir / "verbal_identity_findings.json"
    md_path = outdir / "verbal_identity_findings.md"

    json_path.write_text(json.dumps(report.__dict__, indent=2), encoding="utf-8")

    md = [
        "# Verbal Identity Findings",
        "",
        "## Summary",
        *(f"- **{k.replace('_', ' ').title()}**: {v}" for k, v in report.summary.items()),
        "",
        "## Repeated Lexical Patterns",
    ]
    for item in report.repeated_patterns[:30]:
        kind = item.get("type", f"{item['n']}-gram")
        md.append(f"- `{item['pattern']}` — count: {item['count']} ({kind})")

    md.extend(["", "## Bland Category Language Flags"])
    if report.bland_language_flags:
        for item in report.bland_language_flags:
            md.append(f"- `{item['term']}` — {item['count']} mentions ({item['severity']})")
    else:
        md.append("- None detected from default bland lexicon.")

    md.extend(["", "## Whitespace to Explore"])
    md.extend(f"- {prompt}" for prompt in report.whitespace_suggestions)

    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze brand and competitor copy for lexical patterns.")
    parser.add_argument("--brand", required=True, type=Path, help="Path to brand copy text file.")
    parser.add_argument("--competitors", required=True, nargs="+", type=Path, help="One or more competitor text files.")
    parser.add_argument("--outdir", default=Path("findings"), type=Path, help="Output directory for exported findings.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    brand_text = read_text(args.brand)
    competitor_texts = [read_text(p) for p in args.competitors]
    report = analyze(brand_text, competitor_texts)
    export_report(report, args.outdir)
    print(f"Findings exported to: {args.outdir}")


if __name__ == "__main__":
    main()
