# Verbal Identity Workshop Tool

Small internal CLI for first-pass verbal identity analysis. Paste brand copy + competitor copy as plain text files and generate workshop-ready findings.

## What it does
- Extracts repeated lexical patterns (bi-grams, tri-grams, and shared high-frequency terms).
- Flags bland category language using a built-in lexicon.
- Suggests strategic whitespace prompts to explore alternative voice territories.
- Exports findings as both JSON and Markdown for easy drop-in to strategy docs.

## Quick start
```bash
python verbal_identity_tool.py \
  --brand ./examples/brand.txt \
  --competitors ./examples/competitor_a.txt ./examples/competitor_b.txt \
  --outdir ./findings
```

Outputs:
- `findings/verbal_identity_findings.json`
- `findings/verbal_identity_findings.md`
