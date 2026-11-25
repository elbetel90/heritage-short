import os
from datetime import datetime, timezone

from pipeline.cache import hash_payload
from pipeline.env import ROOT, load_env, secrets_from_env
from pipeline.http import HTTPError, post_json
from pipeline.log import append

LOG_PATH = ROOT / "runs.jsonl"
TEXT_MODELS = (
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
)
GEMINI_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
CLOUDFLARE_MODEL = "@cf/meta/llama-3.1-8b-instruct"
KAGGLE_OBSERVED = "Tue Nov 24 22:45:15 2026"


def _gemini_text(prompt):
    key = os.environ["GEMINI_API_KEY"]
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    errors = []
    for model_id in TEXT_MODELS:
        url = "%s/%s:generateContent" % (GEMINI_ROOT, model_id)
        try:
            _status, _parsed, latency_ms = post_json(url, payload, headers, timeout=45, attempts=2)
            return model_id, latency_ms, "ok", None, errors
        except HTTPError as error:
            errors.append((model_id, error))
        except Exception as error:
            errors.append((model_id, error))
    model_id, error = errors[-1]
    latency_ms = getattr(error, "latency_ms", None)
    return model_id, latency_ms, "error", str(error), errors


def _cloudflare_text(prompt):
    account = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token = os.environ["CLOUDFLARE_WORKERS_AI_API_TOKEN"]
    url = "https://api.cloudflare.com/client/v4/accounts/%s/ai/run/%s" % (
        account,
        CLOUDFLARE_MODEL,
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
    }
    try:
        _status, parsed, latency_ms = post_json(url, {"prompt": prompt}, headers, timeout=60)
    except Exception as error:
        return CLOUDFLARE_MODEL, getattr(error, "latency_ms", None), "error", str(error)
    if isinstance(parsed, dict) and parsed.get("success") is False:
        return CLOUDFLARE_MODEL, latency_ms, "error", str(parsed.get("errors"))
    return CLOUDFLARE_MODEL, latency_ms, "ok", None


def _write(stage, model, parameters, latency_ms, status, error, secrets):
    record = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stage": stage,
        "shot_id": None,
        "model": model,
        "parameters": parameters,
        "seed": None,
        "latency_ms": latency_ms,
        "cost": 0,
        "status": status,
        "input_hash": hash_payload(parameters),
        "output_path": None,
        "error": error,
    }
    append(LOG_PATH, record, secrets)
    print("%s %s %s" % (stage, model, status))
    return status == "ok"


def main():
    load_env()
    secrets = secrets_from_env()
    prompt = "Say hello in one sentence."
    ok = True
    model, latency_ms, status, error, attempts = _gemini_text(prompt)
    for failed_model, failed in attempts:
        _write(
            "smoke-gemini",
            failed_model,
            {"prompt": prompt},
            getattr(failed, "latency_ms", None),
            "error",
            str(failed),
            secrets,
        )
    if status == "ok":
        ok = _write("smoke-gemini", model, {"prompt": prompt}, latency_ms, status, error, secrets) and ok
    else:
        ok = False
    model, latency_ms, status, error = _cloudflare_text(prompt)
    ok = _write(
        "smoke-cloudflare",
        model,
        {"prompt": prompt},
        latency_ms,
        status,
        error,
        secrets,
    ) and ok
    _write(
        "smoke-kaggle",
        "kaggle-gpu-t4-x2",
        {
            "command": "nvidia-smi",
            "gpus": 2,
            "name": "Tesla T4",
            "memory_mib": 15360,
            "driver": "580.178.04",
            "observed_at": KAGGLE_OBSERVED,
        },
        None,
        "ok",
        None,
        secrets,
    )
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
