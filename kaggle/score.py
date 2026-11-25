"""Generate the three score candidates on a Kaggle GPU notebook.

Upload this repo (or storyboard.json beside this file) into the notebook.
Turn the GPU on. Run this file. Download outputs/music and runs-music.jsonl.
Then stop the session from the Draft Session menu. Closing the tab does not stop it.

Locally, for each wav:

    python3 -m pipeline.music ingest SEED path/to/seed-SEED.wav LATENCY_MS
"""

import json
import shutil
import sys
import time
from pathlib import Path

REPO = "https://github.com/ace-step/ACE-Step-1.5"
CLONE = Path("/kaggle/working/ACE-Step-1.5")
OUT = Path("/kaggle/working/music")
LOG = Path("/kaggle/working/runs-music.jsonl")
MODEL_ID = "ACE-Step-1.5"


def _storyboard():
    for path in (Path("storyboard.json"), Path("/kaggle/working/storyboard.json")):
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise SystemExit("Put storyboard.json next to this script.")


def _install():
    import subprocess

    if not CLONE.is_dir():
        subprocess.check_call(["git", "clone", "--depth", "1", REPO, str(CLONE)])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-e", str(CLONE)])


def _handlers():
    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler

    dit = AceStepHandler()
    llm = LLMHandler()
    dit_status = dit.initialize_service(
        project_root=str(CLONE),
        config_path="acestep-v15-turbo",
        device="cuda",
    )
    print(dit_status)
    checkpoint_dir = str(CLONE / "checkpoints")
    llm_status, ok = llm.initialize(
        checkpoint_dir=checkpoint_dir,
        lm_model_path="acestep-5Hz-lm-0.6B",
        backend="vllm",
        device="cuda",
        offload_to_cpu=True,
    )
    print(llm_status)
    if not ok:
        raise SystemExit("language model did not start")
    return dit, llm


def _one(dit, llm, music, seed):
    from acestep.inference import GenerationConfig, GenerationParams, generate_music

    params = GenerationParams(
        task_type="text2music",
        caption=music["caption"],
        lyrics="[Instrumental]",
        instrumental=True,
        bpm=int(music["bpm"]),
        keyscale=music["key"],
        duration=float(music["duration_sec"]),
        seed=int(seed),
        inference_steps=8,
        shift=3.0,
        infer_method="ode",
    )
    config = GenerationConfig(
        batch_size=1,
        audio_format="wav",
        use_random_seed=False,
        seeds=[int(seed)],
    )
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    result = generate_music(dit, llm, params, config, save_dir=str(OUT / ("raw-%s" % seed)))
    latency_ms = int((time.time() - started) * 1000)
    record = {
        "stage": "music",
        "shot_id": None,
        "model": MODEL_ID,
        "parameters": {
            "caption": music["caption"],
            "instrumental": True,
            "bpm": music["bpm"],
            "key": music["key"],
            "duration_sec": music["duration_sec"],
            "seed": int(seed),
            "model": MODEL_ID,
        },
        "seed": int(seed),
        "latency_ms": latency_ms,
        "cost": 0,
        "status": "ok" if result.success else "error",
        "output_path": None,
        "error": None if result.success else str(result.error),
    }
    if result.success and result.audios:
        src = Path(result.audios[0]["path"])
        dest = OUT / ("seed-%s.wav" % seed)
        shutil.copyfile(str(src), str(dest))
        record["output_path"] = dest.name
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps(record, sort_keys=True))
    if not result.success:
        raise SystemExit(result.error)


def main():
    board = _storyboard()
    music = board["music"]
    if not music.get("instrumental"):
        raise SystemExit("music.instrumental must be true")
    _install()
    sys.path.insert(0, str(CLONE))
    dit, llm = _handlers()
    for seed in music["candidate_seeds"]:
        _one(dit, llm, music, seed)
    print("Download %s and %s" % (OUT, LOG))
    print("Stop the Kaggle session from the Draft Session menu. Closing the tab leaves the GPU running.")


if __name__ == "__main__":
    main()
