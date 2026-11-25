import json
from datetime import datetime, timezone

SECRET_PARTS = ("key", "token", "secret", "authorization", "password")


def redact(value, secrets):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if any(part in key.lower() for part in SECRET_PARTS):
                cleaned[key] = "[redacted]"
            else:
                cleaned[key] = redact(item, secrets)
        return cleaned
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, str):
        cleaned = value
        for secret in secrets:
            if secret and secret in cleaned:
                cleaned = cleaned.replace(secret, "[redacted]")
        return cleaned
    return value


def append(path, record, secrets=None):
    secrets = list(secrets or [])
    row = redact(record, secrets)
    row.setdefault("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    path = _as_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def _as_path(path):
    from pathlib import Path
    return Path(path)
