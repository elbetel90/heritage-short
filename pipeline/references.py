"""Three character stills. Stops so a person can pick the golden frame."""

import sys
from pathlib import Path

from pipeline.cache import hash_payload, load, save
from pipeline.env import ROOT, secrets_from_env
from pipeline.images import HEIGHT, MODEL_ID, WIDTH, compose
from pipeline.log import append
from pipeline.validate import STORYBOARD_PATH, load_json, validate_storyboard

OUTPUT_DIR = ROOT / "outputs" / "references"
MANIFEST_PATH = ROOT / "cache" / "manifest.json"
LOG_PATH = ROOT / "runs.jsonl"


def _client(prompt, seed, reference_path):
    from pipeline.flux import generate

    png, latency_ms = generate(prompt, seed, reference_path)
    return png, latency_ms


def render(storyboard, output_dir=None, manifest_path=None, log_path=None, client=None):
    """Write one PNG per reference. Returns the list of paths."""
    output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    manifest_path = Path(manifest_path) if manifest_path else MANIFEST_PATH
    log_path = Path(log_path) if log_path else LOG_PATH
    client = client or _client
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load(manifest_path)
    secrets = secrets_from_env()
    written = []
    for item in storyboard["references"]:
        ref_id = item["id"]
        dest = output_dir / (ref_id + ".png")
        prompt = compose(storyboard, item["prompt"])
        payload = {
            "style_block": storyboard["style_block"],
            "description": storyboard["characters"][0]["description"],
            "prompt": item["prompt"],
            "seed": item["seed"],
            "model": MODEL_ID,
            "width": WIDTH,
            "height": HEIGHT,
        }
        digest = hash_payload(payload)
        key = "references/" + ref_id
        cached = manifest.get(key) or {}
        if cached.get("input_hash") == digest and dest.is_file():
            written.append(dest)
            continue
        try:
            png, latency_ms = client(prompt, item["seed"], None)
            dest.write_bytes(png)
            status = "ok"
            error = None
        except Exception as exc:
            append(
                log_path,
                _record(ref_id, item["seed"], digest, getattr(exc, "latency_ms", None), "error", None, str(exc)),
                secrets,
            )
            raise
        manifest[key] = {
            "input_hash": digest,
            "model": MODEL_ID,
            "seed": item["seed"],
            "output_path": _relative(dest),
            "status": status,
        }
        save(manifest_path, manifest)
        append(log_path, _record(ref_id, item["seed"], digest, latency_ms, status, manifest[key]["output_path"], error), secrets)
        written.append(dest)
    return written


def _record(ref_id, seed, digest, latency_ms, status, output_path, error):
    return {
        "stage": "references",
        "shot_id": ref_id,
        "model": MODEL_ID,
        "parameters": {"seed": seed, "width": WIDTH, "height": HEIGHT},
        "seed": seed,
        "latency_ms": latency_ms,
        "cost": 0,
        "status": status,
        "input_hash": digest,
        "output_path": output_path,
        "error": error,
    }


def _relative(path):
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


def main():
    storyboard = load_json(STORYBOARD_PATH)
    errors = validate_storyboard(storyboard)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    paths = render(storyboard)
    for path in paths:
        print(path)
    print("Look at the three stills. Set characters[0].golden_id to the id you accept, then run make keyframes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
