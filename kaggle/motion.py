"""Draft each shot from its vertical still.

Upload this file, storyboard.json, and the vertical stills in keyframes/.
Turn a GPU on. Run this file. Download motion/ and runs-motion.jsonl.
Then stop the runtime. Closing the tab does not stop a rented GPU.

The clip is Stable Video Diffusion XT 1.1 at 576x1024, 25 frames, about 4 seconds.
A dark face stays put at motion_bucket_id 40 and noise_aug_strength 0.

Locally, for each clip that succeeded:

    python3 -m pipeline.motion ingest s01 ~/Downloads/s01.mp4

`make film` uses that clip for the 9:16 cut. A missing clip keeps the Ken Burns pan.
Wide clips go in outputs/motion-16x9. The 16:9 cut uses one when the file is there, and otherwise pans the landscape still.
"""

import json
import sys
import time
import traceback
from pathlib import Path

OUT = Path("/kaggle/working/motion")
LOG = Path("/kaggle/working/runs-motion.jsonl")
MODEL_ID = "stabilityai/stable-video-diffusion-img2vid-xt-1-1"
MODEL_NAME = "stable-video-diffusion-img2vid-xt-1-1"
WIDTH = 576
HEIGHT = 1024
FRAMES = 25
FPS = 6


def _storyboard():
    for path in (Path("storyboard.json"), Path("/kaggle/working/storyboard.json")):
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise SystemExit("Put storyboard.json next to this script.")


def _still(shot_id):
    for folder in (Path("keyframes"), Path("outputs/keyframes"), Path("/kaggle/working/keyframes")):
        path = folder / (shot_id + ".png")
        if path.is_file():
            return path
    raise SystemExit("missing still for %s" % shot_id)


def _install():
    import subprocess

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q", "ftfy", "git+https://github.com/huggingface/diffusers"]
    )


def _log(record):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps(record, sort_keys=True))


def _record(shot, seed, started, status, output_path, error, model=MODEL_NAME):
    return {
        "stage": "motion",
        "shot_id": shot["id"],
        "model": model,
        "parameters": {
            "width": WIDTH,
            "height": HEIGHT,
            "frames": FRAMES,
            "fps": FPS,
            "motion_bucket_id": 40,
            "noise_aug_strength": 0.0,
        },
        "seed": seed,
        "latency_ms": int((time.time() - started) * 1000),
        "cost": 0,
        "status": status,
        "output_path": output_path,
        "error": error,
    }


def _pipe():
    import torch
    from diffusers import StableVideoDiffusionPipeline

    pipe = StableVideoDiffusionPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        variant="fp16",
    )
    pipe.enable_model_cpu_offload()
    pipe.unet.enable_forward_chunking()
    return pipe


def _frame(shot_id):
    from PIL import Image

    image = Image.open(_still(shot_id)).convert("RGB")
    return image.resize((WIDTH, HEIGHT))


def _shot(pipe, shot):
    import torch
    from diffusers.utils import export_to_video

    seed = int(shot["motion"]["seed"])
    dest = OUT / (shot["id"] + ".mp4")
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    try:
        generator = torch.Generator().manual_seed(seed)
        frames = pipe(
            _frame(shot["id"]),
            height=HEIGHT,
            width=WIDTH,
            decode_chunk_size=2,
            num_frames=FRAMES,
            fps=FPS,
            motion_bucket_id=40,
            noise_aug_strength=0.0,
            generator=generator,
        ).frames[0]
        export_to_video(frames, str(dest), fps=FPS)
    except Exception as exc:
        last = traceback.format_exc().strip().splitlines()[-1]
        _log(_record(shot, seed, started, "error", None, str(exc)))
        _log(
            _record(
                shot,
                seed,
                started,
                "ok",
                None,
                "video model failed; the local pan remains. %s" % last,
                model="kenburns",
            )
        )
        return
    _log(_record(shot, seed, started, "ok", dest.name, None))


def main():
    board = _storyboard()
    _install()
    pipe = _pipe()
    for shot in board["shots"]:
        if shot.get("motion", {}).get("mode") != "i2v":
            continue
        _shot(pipe, shot)
        import torch

        torch.cuda.empty_cache()
    print("Download %s and %s" % (OUT, LOG))
    print("Stop the runtime when the files are downloaded. Closing the tab leaves the GPU running.")


if __name__ == "__main__":
    main()
