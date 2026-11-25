import hashlib
import json
from pathlib import Path


def hash_payload(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load(path):
    path = Path(path)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, manifest):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def shot_style(shot, voice):
    return shot["narration"].get("delivery") or voice["style"]


def narration_payload(shot, voice):
    from pipeline.tts import PRIMARY_MODEL

    text = shot["narration"]["text"]
    payload = {
        "text": text,
        "lang": shot["narration"]["lang"],
        "voice": voice["name"],
        "style": shot_style(shot, voice),
        "model": PRIMARY_MODEL,
        "lead_in_sec": float(shot["narration"].get("lead_in_sec") or 0),
    }
    if not text.strip():
        payload["duration_sec"] = shot["duration_sec"]
    return payload
