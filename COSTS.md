# Costs

Every call in the run logs was made on a free tier. The `cost` field on those lines sums to 0.
This file does not invent a list price. It counts the calls that were actually logged.

| Stage | Model | Status | Calls |
| --- | --- | --- | --- |
| keyframes | @cf/black-forest-labs/flux-2-klein-4b | ok | 64 |
| keyframes-16x9 | @cf/black-forest-labs/flux-2-klein-4b | ok | 36 |
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

Kaggle GPU time is quota, not a line in `runs.jsonl`. Stop the session from the Draft Session menu when a notebook finishes.
