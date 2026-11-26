"""Write COSTS.md from the run logs. Logged cost stays 0 on the free tier."""

import json
import sys
from pathlib import Path

from pipeline.env import ROOT

LOGS = (ROOT / "runs.jsonl", ROOT / "runs-music.jsonl")
DEST = ROOT / "COSTS.md"


def tally(paths):
    """Return ((stage, model, status) -> count, summed cost field)."""
    counts = {}
    spent = 0
    for path in paths:
        path = Path(path)
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = (row.get("stage") or "", row.get("model") or "", row.get("status") or "")
            counts[key] = counts.get(key, 0) + 1
            spent += int(row.get("cost") or 0)
    return counts, spent


def document(counts, spent):
    lines = [
        "# Costs",
        "",
        "Every call in the run logs was made on a free tier. The `cost` field on those lines sums to %d." % spent,
        "This file does not invent a list price. It counts the calls that were actually logged.",
        "",
        "| Stage | Model | Status | Calls |",
        "| --- | --- | --- | --- |",
    ]
    for stage, model, status in sorted(counts):
        lines.append("| %s | %s | %s | %d |" % (stage, model, status, counts[(stage, model, status)]))
    lines.append("")
    lines.append("Kaggle GPU time is quota, not a line in `runs.jsonl`. Stop the session from the Draft Session menu when a notebook finishes.")
    lines.append("")
    return "\n".join(lines)


def write(paths=None, dest=None):
    paths = paths if paths is not None else LOGS
    dest = Path(dest) if dest else DEST
    counts, spent = tally(paths)
    text = document(counts, spent)
    dest.write_text(text, encoding="utf-8")
    return dest


def main():
    print(write())
    return 0


if __name__ == "__main__":
    sys.exit(main())
