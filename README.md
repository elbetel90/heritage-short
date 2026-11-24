# heritage-short

A 60–90 second short film built from one contract, `storyboard.json`. Each stage reads that file and writes its own output: narration, keyframes, moving shots, music, and the final edit. Changing one shot regenerates only that shot.

The film is for the audience named in `DESIGN.md`. This repository is the pipeline that makes it.

## Run

From a clean clone, the pipeline command will be:

```bash
make film
```

That command is not implemented yet. This commit is the project scaffold.

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
