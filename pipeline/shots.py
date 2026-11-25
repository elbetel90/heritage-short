"""Ken Burns pans from accepted stills. No GPU and no model call."""

import hashlib
from pathlib import Path

from pipeline.cache import hash_payload, load, save
from pipeline.env import ROOT
from pipeline.images import HEIGHT, WIDTH
from pipeline.keyframes import OUTPUT_DIR as STILL_DIR
from pipeline.radio import _run

OUTPUT_DIR = ROOT / "outputs" / "shots"
MANIFEST_PATH = ROOT / "cache" / "manifest.json"
FPS = 24


class ShotError(Exception):
    pass


def pan(still_path, dest, duration, zoom_in=True, width=WIDTH, height=HEIGHT):
    """Write a silent pan that lasts duration seconds."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, int(round(float(duration) * FPS)))
    if zoom_in:
        zoom = "min(1+0.0012*on\\,1.10)"
    else:
        zoom = "max(1.10-0.0012*on\\,1.0)"
    video = (
        "scale=%d:%d,zoompan=z='%s':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=%d:s=%dx%d:fps=%d"
        % (width * 2, height * 2, zoom, frames, width, height, FPS)
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(still_path),
            "-vf",
            video,
            "-frames:v",
            str(frames),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(dest),
        ]
    )
    return dest


def render(storyboard, still_dir=None, output_dir=None, manifest_path=None, width=WIDTH, height=HEIGHT, cache_key="shots"):
    """Write one silent pan per shot. Raises ShotError when a still is missing."""
    still_dir = Path(still_dir) if still_dir else STILL_DIR
    output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    manifest_path = Path(manifest_path) if manifest_path else MANIFEST_PATH
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load(manifest_path)
    written = []
    for index, shot in enumerate(storyboard["shots"]):
        shot_id = shot["id"]
        still = still_dir / (shot_id + ".png")
        if not still.is_file():
            raise ShotError("missing still: %s" % still)
        dest = output_dir / (shot_id + ".mp4")
        zoom_in = index % 2 == 0
        payload = {
            "still": hashlib.sha256(still.read_bytes()).hexdigest(),
            "duration_sec": shot["duration_sec"],
            "zoom_in": zoom_in,
            "width": width,
            "height": height,
            "mode": "kenburns",
        }
        digest = hash_payload(payload)
        key = cache_key + "/" + shot_id
        cached = manifest.get(key) or {}
        if cached.get("input_hash") == digest and dest.is_file():
            written.append(dest)
            continue
        pan(still, dest, shot["duration_sec"], zoom_in=zoom_in, width=width, height=height)
        manifest[key] = {
            "input_hash": digest,
            "model": "kenburns",
            "seed": shot["motion"]["seed"],
            "output_path": _relative(dest),
            "status": "ok",
        }
        save(manifest_path, manifest)
        written.append(dest)
    for path in written:
        print(path)
    return written


def _relative(path):
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)
