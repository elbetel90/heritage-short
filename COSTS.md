# Costs

Every call in the run logs was made on a free tier. The `cost` field on those lines sums to 0.
That sum is the logged bill. It is not a list price.

| Stage | Model | Status | Calls |
| --- | --- | --- | --- |
| keyframes | @cf/black-forest-labs/flux-2-klein-4b | ok | 64 |
| keyframes-16x9 | @cf/black-forest-labs/flux-2-klein-4b | ok | 36 |
| motion | Wan2.2-TI2V-5B | ok | 1 |
| motion | stable-video-diffusion-img2vid-xt-1-1 | ok | 12 |
| motion-16x9 | stable-video-diffusion-img2vid-xt-1-1 | error | 2 |
| motion-16x9 | stable-video-diffusion-img2vid-xt-1-1 | ok | 8 |
| music | ACE-Step-1.5 | ok | 12 |
| narration | gemini-3.8-flash-lite-tts | ok | 5 |
| narration | gemini-3.8-flash-tts | error | 7 |
| narration | gemini-3.8-flash-tts | ok | 29 |
| narration | gemini-tts | error | 2 |
| references | @cf/black-forest-labs/flux-2-klein-4b | ok | 6 |
| smoke-cloudflare | @cf/meta/llama-3.1-8b-instruct | ok | 2 |
| smoke-gemini | gemini-2.5-flash | error | 1 |
| smoke-gemini | gemini-3.6-flash | ok | 1 |
| smoke-gemini | gemini-3.7-flash | error | 1 |
| smoke-gemini | gemini-3.8-flash | error | 1 |
| smoke-kaggle | kaggle-gpu-t4-x2 | ok | 2 |

## GPU minutes

These minutes are `latency_ms` on the motion logs. A shot that is not in those files is not counted.

| Log | Shot | Status | Minutes |
| --- | --- | --- | --- |
| runs-motion.jsonl | s10 | ok | 6.12 |
| runs-motion.jsonl | s11 | ok | 6.26 |
| runs-motion-16x9.jsonl | s02 | error | 0.67 |
| runs-motion-16x9.jsonl | s03 | error | 0.48 |
| runs-motion-16x9.jsonl | s02 | ok | 6.39 |
| runs-motion-16x9.jsonl | s02 | ok | 6.36 |
| runs-motion-16x9.jsonl | s03 | ok | 6.29 |
| runs-motion-16x9.jsonl | s04 | ok | 6.27 |
| runs-motion-16x9.jsonl | s05 | ok | 6.28 |
| runs-motion-16x9.jsonl | s06 | ok | 6.28 |
| runs-motion-16x9.jsonl | s07 | ok | 6.28 |
| runs-motion-16x9.jsonl | s08 | ok | 6.28 |

Logged GPU time is 63.96 minutes.

The list price is Google Cloud's published on-demand rate for one NVIDIA T4 GPU attachment: $0.35 per GPU-hour. The virtual machine is extra and is not in this rate. Source: https://cloud.google.com/compute/gpus-pricing. This is a published rate, not a measured bill. The film ran on free Colab and Kaggle quota and paid $0.

At that rate, 63.96 minutes is $0.37.
