"""One 9:16 still per shot, conditioned on the golden reference."""

import hashlib
import sys
from pathlib import Path

from pipeline.cache import hash_payload, load, save
from pipeline.env import ROOT, secrets_from_env
from pipeline.images import HEIGHT, MODEL_ID, WIDTH, compose, golden_id
from pipeline.log import append
from pipeline.references import OUTPUT_DIR as REFERENCE_DIR
from pipeline.validate import STORYBOARD_PATH, load_json, validate_storyboard

OUTPUT_DIR = ROOT / "outputs" / "keyframes"
WIDE_DIR = ROOT / "outputs" / "keyframes-16x9"
MANIFEST_PATH = ROOT / "cache" / "manifest.json"
LOG_PATH = ROOT / "runs.jsonl"
WIDE_WIDTH = 1280
WIDE_HEIGHT = 720


class GoldenError(Exception):
    pass


def _client(prompt, seed, reference_path):
    from pipeline.flux import face_crop, generate

    face = face_crop(reference_path)
    locked = (
        "The face is image 0. The black hoodie is the reference. "
        "Same man, medium olive-brown skin, dark hair on the forehead, lips closed, resting, "
        "not smiling, not excited, not crying, not frowning. "
        "Dim room leaning dark, a little disordered, he stays inside the room. "
        "One weak lamp, no daylight. The room is image 1. "
    )
    references = [str(face), reference_path]
    try:
        png, latency_ms = generate(locked + prompt, seed, references)
    finally:
        if face.is_file():
            face.unlink()
    return png, latency_ms


def render(storyboard, output_dir=None, reference_dir=None, manifest_path=None, log_path=None, client=None):
    """Write one PNG per shot. Raises GoldenError when no golden frame is chosen."""
    chosen = golden_id(storyboard)
    if not chosen:
        raise GoldenError("golden_id is empty. Pick a reference still before generating shot stills.")
    reference_dir = Path(reference_dir) if reference_dir else REFERENCE_DIR
    golden = reference_dir / (chosen + ".png")
    if not golden.is_file():
        raise GoldenError("missing golden frame: %s" % golden)
    output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    manifest_path = Path(manifest_path) if manifest_path else MANIFEST_PATH
    log_path = Path(log_path) if log_path else LOG_PATH
    client = client or _client
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load(manifest_path)
    secrets = secrets_from_env()
    golden_hash = hashlib.sha256(golden.read_bytes()).hexdigest()
    written = []
    for shot in storyboard["shots"]:
        shot_id = shot["id"]
        dest = output_dir / (shot_id + ".png")
        prompt = compose(storyboard, shot["image"]["prompt"])
        payload = {
            "style_block": storyboard["style_block"],
            "description": storyboard["characters"][0]["description"],
            "golden": golden_hash,
            "prompt": shot["image"]["prompt"],
            "seed": shot["image"]["seed"],
            "model": MODEL_ID,
            "width": WIDTH,
            "height": HEIGHT,
        }
        digest = hash_payload(payload)
        key = "keyframes/" + shot_id
        cached = manifest.get(key) or {}
        if cached.get("input_hash") == digest and dest.is_file():
            written.append(dest)
            continue
        try:
            png, latency_ms = client(prompt, shot["image"]["seed"], str(golden))
            dest.write_bytes(png)
            status = "ok"
            error = None
        except Exception as exc:
            append(
                log_path,
                _record(shot_id, shot["image"]["seed"], digest, getattr(exc, "latency_ms", None), "error", None, str(exc)),
                secrets,
            )
            raise
        manifest[key] = {
            "input_hash": digest,
            "model": MODEL_ID,
            "seed": shot["image"]["seed"],
            "output_path": _relative(dest),
            "status": status,
        }
        save(manifest_path, manifest)
        append(
            log_path,
            _record(shot_id, shot["image"]["seed"], digest, latency_ms, status, manifest[key]["output_path"], error),
            secrets,
        )
        written.append(dest)
    return written


def _record(shot_id, seed, digest, latency_ms, status, output_path, error):
    return {
        "stage": "keyframes",
        "shot_id": shot_id,
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


def _wide_client(prompt, seed, reference_path, still_path):
    from pipeline.flux import face_crop, generate

    face = face_crop(reference_path)
    locked = (
        "The face is image 0. Image 1 is the same moment, used for the face, the black hoodie, and the room. "
        "Do not copy its tall framing. "
        "Recompose that moment as a landscape 16:9 photograph that fills the frame edge to edge. "
        "The camera is farther back. The dim room continues to the left edge and the right edge. "
        "The same man stands inside the room, whole head in frame, space above the hair, lips closed, resting. "
        "No black bars, no pillarbox, no vertical strip of picture. "
    )
    references = [str(face), still_path]
    try:
        png, latency_ms = generate(locked + prompt, seed, references, width=WIDE_WIDTH, height=WIDE_HEIGHT)
    finally:
        if face.is_file():
            face.unlink()
    return png, latency_ms


def render_wide(storyboard, output_dir=None, still_dir=None, reference_dir=None, manifest_path=None, log_path=None, client=None):
    """Write one 16:9 still per shot, recomposed from the vertical keyframe."""
    chosen = golden_id(storyboard)
    if not chosen:
        raise GoldenError("golden_id is empty. Pick a reference still before generating shot stills.")
    reference_dir = Path(reference_dir) if reference_dir else REFERENCE_DIR
    golden = reference_dir / (chosen + ".png")
    if not golden.is_file():
        raise GoldenError("missing golden frame: %s" % golden)
    still_dir = Path(still_dir) if still_dir else OUTPUT_DIR
    output_dir = Path(output_dir) if output_dir else WIDE_DIR
    manifest_path = Path(manifest_path) if manifest_path else MANIFEST_PATH
    log_path = Path(log_path) if log_path else LOG_PATH
    client = client or _wide_client
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load(manifest_path)
    secrets = secrets_from_env()
    golden_hash = hashlib.sha256(golden.read_bytes()).hexdigest()
    written = []
    for shot in storyboard["shots"]:
        shot_id = shot["id"]
        source = still_dir / (shot_id + ".png")
        if not source.is_file():
            raise GoldenError("missing vertical still: %s" % source)
        dest = output_dir / (shot_id + ".png")
        prompt = (
            "Landscape 16:9 photograph. The dim room fills the frame from the left edge to the right edge. "
            "Whole head in frame, space above the hair. No black bars. "
            + compose(storyboard, shot["image"]["prompt"])
        )
        payload = {
            "style_block": storyboard["style_block"],
            "description": storyboard["characters"][0]["description"],
            "golden": golden_hash,
            "still": hashlib.sha256(source.read_bytes()).hexdigest(),
            "prompt": shot["image"]["prompt"],
            "seed": shot["image"]["seed"],
            "model": MODEL_ID,
            "width": WIDE_WIDTH,
            "height": WIDE_HEIGHT,
            "frame": "16:9",
        }
        digest = hash_payload(payload)
        key = "keyframes-16x9/" + shot_id
        cached = manifest.get(key) or {}
        if cached.get("input_hash") == digest and dest.is_file():
            written.append(dest)
            continue
        try:
            png, latency_ms = client(prompt, shot["image"]["seed"], str(golden), str(source))
            dest.write_bytes(png)
            status = "ok"
            error = None
        except Exception as exc:
            append(
                log_path,
                _wide_record(shot_id, shot["image"]["seed"], digest, getattr(exc, "latency_ms", None), "error", None, str(exc)),
                secrets,
            )
            raise
        manifest[key] = {
            "input_hash": digest,
            "model": MODEL_ID,
            "seed": shot["image"]["seed"],
            "output_path": _relative(dest),
            "status": status,
        }
        save(manifest_path, manifest)
        append(
            log_path,
            _wide_record(shot_id, shot["image"]["seed"], digest, latency_ms, status, manifest[key]["output_path"], error),
            secrets,
        )
        written.append(dest)
    return written


def _wide_record(shot_id, seed, digest, latency_ms, status, output_path, error):
    return {
        "stage": "keyframes-16x9",
        "shot_id": shot_id,
        "model": MODEL_ID,
        "parameters": {"seed": seed, "width": WIDE_WIDTH, "height": WIDE_HEIGHT},
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
    try:
        paths = render(storyboard)
    except GoldenError as error:
        print(str(error), file=sys.stderr)
        return 1
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
