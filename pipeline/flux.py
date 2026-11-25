"""Cloudflare FLUX.2 klein 4B. Multipart request, PNG bytes back."""

import base64
import json
import os
import subprocess
from pathlib import Path

from pipeline.env import load_env
from pipeline.http import post_multipart
from pipeline.images import HEIGHT, MODEL_ID, WIDTH

API = "https://api.cloudflare.com/client/v4/accounts/%s/ai/run/%s"


def generate(prompt, seed, reference_path=None, width=None, height=None):
    """Return (png_bytes, latency_ms). Raises if the call fails or has no image."""
    load_env()
    account = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token = os.environ["CLOUDFLARE_WORKERS_AI_API_TOKEN"]
    fields = [
        ("prompt", prompt),
        ("seed", int(seed)),
        ("width", width or WIDTH),
        ("height", height or HEIGHT),
    ]
    paths = reference_path
    if isinstance(paths, str):
        paths = [paths]
    files = []
    for index, path in enumerate(paths or []):
        if not path:
            continue
        scaled = _scale_reference(path)
        files.append(("input_image_%s" % index, "reference-%s.png" % index, scaled))
    url = API % (account, MODEL_ID)
    status, raw, content_type, latency_ms = post_multipart(
        url,
        fields,
        files,
        {"Authorization": "Bearer " + token},
    )
    if status >= 400:
        raise RuntimeError("FLUX HTTP %s" % status)
    image = _image_bytes(raw, content_type)
    return _as_png(image), latency_ms


def _image_bytes(raw, content_type):
    if content_type.startswith("image/"):
        return raw
    parsed = json.loads(raw.decode("utf-8"))
    encoded = _find_image(parsed)
    if not encoded:
        raise RuntimeError("FLUX response had no image")
    if "," in encoded[:80] and encoded.strip().startswith("data:"):
        encoded = encoded.split(",", 1)[1]
    return base64.b64decode(encoded)


def _find_image(value):
    if isinstance(value, dict):
        image = value.get("image")
        if isinstance(image, str) and len(image) > 80:
            return image
        for item in value.values():
            found = _find_image(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_image(item)
            if found:
                return found
    return None


def face_crop(path):
    """Head-and-shoulders crop so the reference face is large enough to follow."""
    source = Path(path)
    dest = source.with_name(source.stem + "-face.png")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vf",
        "crop=iw*0.7:ih*0.42:(iw-ow)/2:ih*0.18",
        "-frames:v",
        "1",
        str(dest),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[-500:])
    return dest


def _scale_reference(path):
    """Cloudflare accepts a reference only under 512 by 512."""
    source = Path(path)
    dest = source.with_name(source.stem + "-512.png")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vf",
        "scale=512:512:force_original_aspect_ratio=decrease",
        "-frames:v",
        "1",
        str(dest),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[-500:])
    data = dest.read_bytes()
    dest.unlink()
    return data


def _as_png(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return data
    import tempfile

    folder = Path(tempfile.mkdtemp())
    raw = folder / "flux.bin"
    png = folder / "flux.png"
    raw.write_bytes(data)
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(raw), str(png)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError("could not convert FLUX image to png")
    return png.read_bytes()
