import os
from pathlib import Path

from pipeline.audio import prepend_silence, wav_duration, write_silence
from pipeline.cache import hash_payload, load, narration_payload, save, shot_style
from pipeline.env import ROOT, secrets_from_env
from pipeline.log import append

MANIFEST_PATH = ROOT / "cache" / "manifest.json"
LOG_PATH = ROOT / "runs.jsonl"
OUTPUT_DIR = ROOT / "outputs" / "narration"


def _client(text, voice, style):
    from pipeline.tts import synthesize

    return synthesize(text, voice["name"], style)


def render(storyboard, output_dir=None, manifest_path=None, log_path=None, client=None):
    """Write one wav per shot. Returns {shot_id: duration_sec}."""
    output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    manifest_path = Path(manifest_path) if manifest_path else MANIFEST_PATH
    log_path = Path(log_path) if log_path else LOG_PATH
    client = client or _client
    voice = storyboard["voice"]
    manifest = load(manifest_path)
    secrets = secrets_from_env()
    durations = {}
    output_dir.mkdir(parents=True, exist_ok=True)

    for shot in storyboard["shots"]:
        shot_id = shot["id"]
        dest = output_dir / (shot_id + ".wav")
        payload = narration_payload(shot, voice)
        digest = hash_payload(payload)
        key = "narration/" + shot_id
        cached = manifest.get(key) or {}
        if cached.get("input_hash") == digest and dest.is_file():
            durations[shot_id] = wav_duration(dest)
            continue

        text = shot["narration"]["text"].strip()
        style = shot_style(shot, voice)
        if not text:
            write_silence(dest, float(shot["duration_sec"]))
            model_id = "silence"
            latency_ms = 0
            status = "ok"
            error = None
        else:
            try:
                result = client(text, voice, style)
                failures = []
                if len(result) == 4:
                    audio, model_id, latency_ms, failures = result
                else:
                    audio, model_id, latency_ms = result
                for failure in failures:
                    append(
                        log_path,
                        _record(
                            shot_id,
                            failure["model"],
                            voice,
                            style,
                            digest,
                            failure.get("latency_ms"),
                            "error",
                            None,
                            failure.get("error"),
                        ),
                        secrets,
                    )
                dest.write_bytes(audio)
                lead_in = float(shot["narration"].get("lead_in_sec") or 0)
                if lead_in > 0:
                    prepend_silence(dest, lead_in)
                status = "ok"
                error = None
            except Exception as exc:
                model_id = "gemini-tts"
                latency_ms = getattr(exc, "latency_ms", None)
                status = "error"
                error = str(exc)
                append(
                    log_path,
                    _record(shot_id, model_id, voice, style, digest, latency_ms, status, None, error),
                    secrets,
                )
                raise

        durations[shot_id] = wav_duration(dest)
        manifest[key] = {
            "input_hash": digest,
            "model": model_id,
            "seed": None,
            "output_path": str(dest.relative_to(ROOT)) if _is_relative_to(dest, ROOT) else str(dest),
            "status": status,
        }
        if model_id != "silence":
            append(
                log_path,
                _record(shot_id, model_id, voice, style, digest, latency_ms, status, manifest[key]["output_path"], None),
                secrets,
            )
        save(manifest_path, manifest)
    return durations


def _is_relative_to(path, root):
    try:
        Path(path).relative_to(root)
        return True
    except ValueError:
        return False


def _record(shot_id, model_id, voice, style, digest, latency_ms, status, output_path, error):
    return {
        "stage": "narration",
        "shot_id": shot_id,
        "model": model_id,
        "parameters": {"voice": voice["name"], "style": style},
        "seed": None,
        "latency_ms": latency_ms,
        "cost": 0,
        "status": status,
        "input_hash": digest,
        "output_path": output_path,
        "error": error,
    }


def main():
    from pipeline.validate import STORYBOARD_PATH, load_json, validate_storyboard

    storyboard = load_json(STORYBOARD_PATH)
    errors = validate_storyboard(storyboard)
    if errors:
        raise SystemExit("\n".join(errors))
    os.chdir(str(ROOT))
    durations = render(storyboard)
    for shot_id in sorted(durations):
        print("%s %.2fs" % (shot_id, durations[shot_id]))


if __name__ == "__main__":
    main()
