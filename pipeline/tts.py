import base64
import os
import re
import time

from pipeline.http import post_json

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
PRIMARY_MODEL = "gemini-3.8-flash-tts"
TTS_MODELS = (PRIMARY_MODEL, "gemini-3.8-flash-lite-tts")
RATE_WAITS = 4


def _find_audio(value):
    if isinstance(value, dict):
        mime = str(value.get("mime_type") or value.get("mimeType") or "")
        data = value.get("data")
        if data and ("audio" in mime or value.get("type") == "audio"):
            return data
        output_audio = value.get("output_audio")
        if isinstance(output_audio, dict) and output_audio.get("data"):
            return output_audio["data"]
        for item in value.values():
            found = _find_audio(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_audio(item)
            if found:
                return found
    return None


def _retry_after(error):
    if getattr(error, "status", None) != 429:
        return None
    match = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)", str(error), re.IGNORECASE)
    if match:
        return float(match.group(1)) + 1.0
    return 60.0


def synthesize(text, voice, style, model=None):
    """Return wav bytes, model id, latency, and failed attempts.

    The film uses one model. A rate limit waits and retries that same model.
    The lite model is not called.
    """
    key = os.environ["GEMINI_API_KEY"]
    model_id = model or PRIMARY_MODEL
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key,
    }
    payload = {
        "model": model_id,
        "input": [
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                        "annotations": [
                            {"type": "speech_metadata", "style": style}
                        ],
                    }
                ],
            }
        ],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice}]},
    }
    url = API_ROOT + "/interactions"
    failures = []
    for attempt in range(RATE_WAITS):
        try:
            _status, parsed, latency_ms = post_json(url, payload, headers, timeout=120, attempts=1)
        except Exception as error:
            failures.append(
                {
                    "model": model_id,
                    "latency_ms": getattr(error, "latency_ms", None),
                    "error": str(error),
                }
            )
            wait = _retry_after(error)
            if wait is not None and attempt < RATE_WAITS - 1:
                time.sleep(min(wait, 90.0))
                continue
            break
        encoded = _find_audio(parsed)
        if not encoded:
            failures.append(
                {"model": model_id, "latency_ms": latency_ms, "error": "response had no audio"}
            )
            break
        return base64.b64decode(encoded), model_id, latency_ms, failures
    raise RuntimeError("; ".join("%s: %s" % (item["model"], item["error"]) for item in failures))
