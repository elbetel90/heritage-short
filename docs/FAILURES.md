# Failures

## Gemini text smoke

`gemini-3.8-flash` and `gemini-3.7-flash` timed out on `generateContent` during the smoke call. `gemini-3.6-flash` answered. Each attempt is a line in `runs.jsonl`. The text model is only used to prove the key. Narration uses the TTS models, which answered.

## Narration fallback

The first Kore pass spoke shot `s09` with `gemini-3.8-flash-lite-tts`. The failed attempt was not logged. Failed attempts are logged now.

The first Schedar pass spoke `s04`, `s08`, `s10`, and `s11` with the lite model. The free tier allows 3 requests a minute on `gemini-3.8-flash-tts`, and a 429 was abandoned after a fraction of a second. That is why the voice changed weight at about 20 seconds. The retake waits out the rate limit and calls only `gemini-3.8-flash-tts`. Shot `s05` was rate-limited once, then spoken by that same model.

## Wan 2.2 on a T4

Wan 2.2 TI2V-5B was the first video model. On a Kaggle T4 (14.56 GiB) the weights filled about 14.4 GiB. A first call failed because `ftfy` was not installed. After `pip install ftfy`, the same card ran out of GPU memory at 81 frames and again at 17 frames, with model CPU offload and VAE tiling already on. Sequential CPU offload was the next try. The machine ran out of system RAM before that finished. Wan is not the path in `kaggle/motion.py`.

## HunyuanVideo did not download

`hunyuanvideo-community/HunyuanVideo-1.5-480p_i2v` returned 401. The notebook loaded that pipeline before the shot loop, so shot 01 never started. The pipeline was set to `None`, and the script no longer calls Hunyuan. The licence was never reached because the checkpoint did not download.

## Colab ran out of RAM on Wan

The same Wan weights were tried on a Colab T4 (15360 MiB). The card is the same size. A normal Colab machine has about 12 GB of system RAM, and the weight files are 31.4 GB. The session died during "Loading weights". That confirmed the blocker was system RAM, not a missing CUDA step. The notebook moved to a smaller image-to-video model.

## The face dissolved

The first Stable Video Diffusion test was a 1024×576 clip cropped from a tall still, with `motion_bucket_id` 127. The face left the frame and dissolved. A 576×1024 clip, 25 frames at 6 fps, `motion_bucket_id` 40, and `noise_aug_strength` 0.0 kept the face through the test. Those are the settings in `kaggle/motion.py`. The near-final showing on 26 November still found the face broken in some shots. That note is in `docs/DESIGN.md`. Those shots are not replaced yet.

## The wide clip ran out of memory

The 16:9 batch uses the same model at 1024×576. After one shot, the next call on shot 03 asked for 844 MiB and found about 92 MiB free, with about 1.7 GiB reserved and unallocated. The kernel was restarted. `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` was set before `import torch`, `decode_chunk_size` was set to 1, the cache was emptied after each shot, and a shot that already had an mp4 was skipped. The eleven wide clips then finished. They are in `outputs/motion-16x9/`. The attempt is in `runs-motion-16x9.jsonl`.
