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

`make radio` validates `storyboard.json`, speaks the English lines, and writes `outputs/radio/radio-cut.mp4` (black picture, voice, quiet tone). `make film`, which adds pictures, moving shots, and the score, is not implemented yet.

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
