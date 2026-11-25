"""Register ACE-Step candidates and lay the chosen bed under the radio cut."""

import shutil
import sys
from pathlib import Path

from pipeline.audio import wav_duration
from pipeline.cache import hash_payload, load, save
from pipeline.env import ROOT
from pipeline.log import append
from pipeline.narration import OUTPUT_DIR
from pipeline.radio import RADIO_PATH, assemble
from pipeline.timing import block_sec
from pipeline.validate import STORYBOARD_PATH, load_json

MODEL_ID = "ACE-Step-1.5"
MUSIC_DIR = ROOT / "outputs" / "music"
MANIFEST_PATH = ROOT / "cache" / "manifest.json"
LOG_PATH = ROOT / "runs.jsonl"
SCORED_PATH = ROOT / "outputs" / "radio" / "radio-score.mp4"


def music_payload(storyboard, seed):
    music = storyboard["music"]
    return {
        "caption": music["caption"],
        "instrumental": bool(music["instrumental"]),
        "bpm": music["bpm"],
        "key": music["key"],
        "duration_sec": music["duration_sec"],
        "seed": int(seed),
        "model": MODEL_ID,
    }


def candidate_path(seed, directory=None):
    directory = Path(directory) if directory else MUSIC_DIR
    return directory / ("seed-%s.wav" % int(seed))


def ingest(storyboard, seed, source, latency_ms=None, log_path=None, manifest_path=None, output_dir=None):
    """Copy one generated wav into outputs/music and append a run line."""
    source = Path(source)
    if not source.is_file():
        raise SystemExit("missing candidate: %s" % source)
    dest = candidate_path(seed, output_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(source), str(dest))
    payload = music_payload(storyboard, seed)
    digest = hash_payload(payload)
    manifest_path = Path(manifest_path) if manifest_path else MANIFEST_PATH
    manifest = load(manifest_path)
    key = "music/seed-%s" % int(seed)
    manifest[key] = {
        "input_hash": digest,
        "model": MODEL_ID,
        "seed": int(seed),
        "output_path": str(dest.relative_to(ROOT)) if _is_relative_to(dest, ROOT) else str(dest),
        "status": "ok",
    }
    save(manifest_path, manifest)
    append(
        Path(log_path) if log_path else LOG_PATH,
        {
            "stage": "music",
            "shot_id": None,
            "model": MODEL_ID,
            "parameters": payload,
            "seed": int(seed),
            "latency_ms": latency_ms,
            "cost": 0,
            "status": "ok",
            "input_hash": digest,
            "output_path": manifest[key]["output_path"],
            "error": None,
        },
    )
    return dest


def mix(storyboard, bed_path, narration_dir=None, output_path=None, work_dir=None):
    """Rebuild the black cut with the chosen bed ducked under the voice."""
    narration_dir = Path(narration_dir) if narration_dir else OUTPUT_DIR
    output_path = Path(output_path) if output_path else SCORED_PATH
    work_dir = Path(work_dir) if work_dir else output_path.parent / "score-work"
    wav_paths = {}
    for shot in storyboard["shots"]:
        path = narration_dir / (shot["id"] + ".wav")
        if not path.is_file():
            raise SystemExit("missing narration %s" % path)
        wav_paths[shot["id"]] = path
    return assemble(
        storyboard["shots"],
        wav_paths,
        output_path,
        work_dir,
        end_card_sec=storyboard["end_card"]["duration_sec"],
        bed_path=bed_path,
        duck=storyboard["mix"]["duck"],
        intro_sec=block_sec(storyboard, "intro"),
        outro_sec=block_sec(storyboard, "outro"),
    )


def _is_relative_to(path, root):
    try:
        Path(path).relative_to(root)
        return True
    except ValueError:
        return False


def _print_candidates(storyboard):
    print("chosen_id is empty. Listen, then set music.chosen_id to one of:")
    for seed in storyboard["music"]["candidate_seeds"]:
        path = candidate_path(seed)
        mark = "ready" if path.is_file() else "missing"
        print("  seed-%s  %s  %s" % (seed, mark, path))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    storyboard = load_json(STORYBOARD_PATH)
    if not argv or argv[0] == "status":
        _print_candidates(storyboard)
        return 0
    if argv[0] == "ingest":
        if len(argv) < 3:
            print("usage: python3 -m pipeline.music ingest SEED WAV [LATENCY_MS]", file=sys.stderr)
            return 1
        latency = int(argv[3]) if len(argv) > 3 else None
        dest = ingest(storyboard, int(argv[1]), argv[2], latency)
        print("ingested %s (%.2fs)" % (dest, wav_duration(dest)))
        return 0
    if argv[0] == "mix":
        chosen = storyboard["music"].get("chosen_id")
        if not chosen:
            _print_candidates(storyboard)
            return 1
        seed = str(chosen).replace("seed-", "")
        bed = candidate_path(seed)
        if not bed.is_file():
            print("missing %s" % bed, file=sys.stderr)
            return 1
        duration = mix(storyboard, bed)
        print("scored radio %.2fs %s" % (duration, SCORED_PATH))
        return 0
    print("usage: python3 -m pipeline.music [status|ingest|mix]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
