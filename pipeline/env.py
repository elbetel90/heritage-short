import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def load_env(path=None):
    """Read KEY=VALUE lines. Does not override variables already set."""
    env_path = Path(path) if path else ENV_PATH
    if not env_path.is_file():
        return {}
    loaded = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        loaded[key] = value
        if key not in os.environ:
            os.environ[key] = value
    return loaded


def secrets_from_env():
    load_env()
    names = (
        "GEMINI_API_KEY",
        "CLOUDFLARE_WORKERS_AI_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
    )
    return [os.environ[name] for name in names if os.environ.get(name)]
