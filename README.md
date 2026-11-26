# heritage-short

A 60–90 second short film built from one contract, `storyboard.json`. Each stage reads that file and writes its own output: narration, keyframes, moving shots, music, and the final edit. Changing one shot regenerates only that shot.

The film is for the audience named in `docs/DESIGN.md`. Consent and licences are in `docs/ETHICS.md`. The stage contracts are in `docs/ARCHITECTURE.md`. This repository is the pipeline that makes the film.

## Run

From a clean clone, after `.env` is filled in:

```bash
make test
make validate
make smoke
make radio
```

`make radio` validates `storyboard.json`, speaks the English lines, and writes `outputs/radio/radio-cut.mp4` (black picture, voice, quiet tone). The score is generated on Kaggle with `kaggle/score.py`, then ingested and mixed locally:

```bash
python3 -m pipeline.music ingest 11 ~/Downloads/seed-11.wav
python3 -m pipeline.music mix
```

`mix` reads `music.chosen_id` and writes `outputs/radio/radio-score.mp4`.

Stills are Cloudflare calls from this machine, not a Kaggle session:

```bash
make references
```

That writes three PNGs in `outputs/references/`. Look at them, set `characters[0].golden_id` to the id you accept (`tarek-view`, `tarek-expression`, or `tarek-frame`), then:

```bash
make keyframes
```

That writes `outputs/keyframes/s01.png` through `s11.png`, each conditioned on the golden frame. `make keyframes` stops if `golden_id` is empty.

```bash
make film
```

`make film` pans each accepted still for its shot length, lays the spoken wavs on top, burns the English subtitles, and writes `outputs/final/film-9x16.mp4`, `film-16x9.mp4`, and `film.srt`. When `music.chosen_id` names a file in `outputs/music`, that bed is ducked under the voice. Otherwise the bed is the quiet placeholder. Run `make radio` first so the wavs exist.

Moving shots are drafted with `kaggle/motion.py` on a GPU notebook. Stable Video Diffusion XT 1.1 makes a 576×1024 clip of about 4 seconds from each vertical still. Download a clip that succeeded and register it:

```bash
python3 -m pipeline.motion ingest s01 ~/Downloads/s01.mp4
```

The next `make film` uses that clip for the 9:16 cut and a matching file in `outputs/motion-16x9/` for the wide cut. Both hold the last frame when the clip is shorter than the shot. A shot with no clip keeps its pan.

```bash
python3 -m pipeline.costs
```

That rewrites `COSTS.md` from `runs.jsonl` and `runs-music.jsonl`.

## Setup

```bash
cp .env.example .env
```

Fill in `.env` on your machine. Do not commit it.

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Story help, translation, and narration |
| `CLOUDFLARE_WORKERS_AI_API_TOKEN` | Keyframe images through Workers AI |
| `CLOUDFLARE_ACCOUNT_ID` | Account used by that token |

Video and music run on a phone-verified Kaggle account. Those stages are not part of this commit.

## Cost

API calls use the Gemini and Cloudflare free tiers. GPU time uses Kaggle’s weekly quota. Every model call will be appended to `runs.jsonl` with the model, parameters, seed, latency, and a list-price equivalent. Measured totals will be written in `COSTS.md`.
