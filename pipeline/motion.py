"""Register a moving-shot clip downloaded from the GPU notebook."""

import shutil
import sys
from pathlib import Path

from pipeline.env import ROOT
from pipeline.log import append

LOG_PATH = ROOT / "runs.jsonl"
MOTION_DIR = ROOT / "outputs" / "motion"
WIDE_MOTION_DIR = ROOT / "outputs" / "motion-16x9"


def clip_path(shot_id, directory=None):
    directory = Path(directory) if directory else MOTION_DIR
    return directory / (str(shot_id) + ".mp4")


def ingest(shot_id, source, latency_ms=None, model="stable-video-diffusion-img2vid-xt-1-1", log_path=None, output_dir=None):
    """Copy one generated clip into outputs/motion and append a run line."""
    source = Path(source)
    if not source.is_file():
        raise SystemExit("missing clip: %s" % source)
    dest = clip_path(shot_id, output_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(source), str(dest))
    try:
        output = str(dest.relative_to(ROOT))
    except ValueError:
        output = str(dest)
    append(
        Path(log_path) if log_path else LOG_PATH,
        {
            "stage": "motion",
            "shot_id": str(shot_id),
            "model": model,
            "parameters": {"width": 576, "height": 1024, "frames": 25, "fps": 6},
            "seed": None,
            "latency_ms": latency_ms,
            "cost": 0,
            "status": "ok",
            "input_hash": None,
            "output_path": output,
            "error": None,
        },
    )
    return dest


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 3 or argv[0] != "ingest":
        print("usage: python3 -m pipeline.motion ingest SHOT_ID path/to/shot.mp4 [LATENCY_MS]", file=sys.stderr)
        return 1
    latency = int(argv[3]) if len(argv) > 3 else None
    print(ingest(argv[1], argv[2], latency_ms=latency))
    return 0


if __name__ == "__main__":
    sys.exit(main())
