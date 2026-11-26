"""Write COSTS.md from the run logs. Logged cost stays 0 on the free tier."""

import json
import sys
from pathlib import Path

from pipeline.env import ROOT

LOGS = (
    ROOT / "runs.jsonl",
    ROOT / "runs-music.jsonl",
    ROOT / "runs-motion.jsonl",
    ROOT / "runs-motion-16x9.jsonl",
)
MOTION_LOGS = (ROOT / "runs-motion.jsonl", ROOT / "runs-motion-16x9.jsonl")
DEST = ROOT / "COSTS.md"
# Google Cloud published on-demand price for one NVIDIA T4 GPU attachment.
# The virtual machine is billed separately and is not included.
# https://cloud.google.com/compute/gpus-pricing
T4_USD_PER_GPU_HOUR = 0.35


def _rows(path):
    path = Path(path)
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def tally(paths):
    """Return ((stage, model, status) -> count, summed cost field)."""
    counts = {}
    spent = 0
    for path in paths:
        for row in _rows(path):
            key = (row.get("stage") or "", row.get("model") or "", row.get("status") or "")
            counts[key] = counts.get(key, 0) + 1
            spent += int(row.get("cost") or 0)
    return counts, spent


def gpu_calls(paths):
    """Return logged motion calls that have a latency. Missing shots are absent."""
    calls = []
    for path in paths:
        for row in _rows(path):
            if row.get("latency_ms") is None:
                continue
            calls.append(
                {
                    "file": Path(path).name,
                    "shot_id": row.get("shot_id") or "",
                    "status": row.get("status") or "",
                    "latency_ms": int(row["latency_ms"]),
                }
            )
    return calls


def _minutes(latency_ms):
    return latency_ms / 60000.0


def document(counts, spent, gpu=None):
    lines = [
        "# Costs",
        "",
        "Every call in the run logs was made on a free tier. The `cost` field on those lines sums to %d." % spent,
        "That sum is the logged bill. It is not a list price.",
        "",
        "| Stage | Model | Status | Calls |",
        "| --- | --- | --- | --- |",
    ]
    for stage, model, status in sorted(counts):
        lines.append("| %s | %s | %s | %d |" % (stage, model, status, counts[(stage, model, status)]))
    lines.extend(["", "## GPU minutes", ""])
    lines.append(
        "These minutes are `latency_ms` on the motion logs. A shot that is not in those files is not counted."
    )
    lines.append("")
    if not gpu:
        lines.append("No motion latency was logged.")
        lines.append("")
        return "\n".join(lines)
    lines.extend(
        [
            "| Log | Shot | Status | Minutes |",
            "| --- | --- | --- | --- |",
        ]
    )
    total_ms = 0
    for call in gpu:
        total_ms += call["latency_ms"]
        lines.append(
            "| %s | %s | %s | %.2f |"
            % (call["file"], call["shot_id"], call["status"], _minutes(call["latency_ms"]))
        )
    hours = total_ms / 3600000.0
    equivalent = hours * T4_USD_PER_GPU_HOUR
    lines.extend(
        [
            "",
            "Logged GPU time is %.2f minutes." % _minutes(total_ms),
            "",
            "The list price is Google Cloud's published on-demand rate for one NVIDIA T4 GPU attachment: $%.2f per GPU-hour. The virtual machine is extra and is not in this rate. Source: https://cloud.google.com/compute/gpus-pricing. This is a published rate, not a measured bill. The film ran on free Colab and Kaggle quota and paid $0."
            % T4_USD_PER_GPU_HOUR,
            "",
            "At that rate, %.2f minutes is $%.2f." % (_minutes(total_ms), equivalent),
            "",
        ]
    )
    return "\n".join(lines)


def write(paths=None, dest=None, motion_paths=None):
    paths = paths if paths is not None else LOGS
    dest = Path(dest) if dest else DEST
    motion_paths = motion_paths if motion_paths is not None else MOTION_LOGS
    counts, spent = tally(paths)
    text = document(counts, spent, gpu_calls(motion_paths))
    dest.write_text(text, encoding="utf-8")
    return dest


def main():
    print(write())
    return 0


if __name__ == "__main__":
    sys.exit(main())
