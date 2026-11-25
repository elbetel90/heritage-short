# Failures

## Gemini text smoke

`gemini-3.8-flash` and `gemini-3.7-flash` timed out on `generateContent` during the smoke call. `gemini-3.6-flash` answered. Each attempt is a line in `runs.jsonl`. The text model is only used to prove the key. Narration uses the TTS models, which answered.

## Narration fallback

The first Kore pass spoke shot `s09` with `gemini-3.8-flash-lite-tts`. The failed attempt was not logged. Failed attempts are logged now.

The first Schedar pass spoke `s04`, `s08`, `s10`, and `s11` with the lite model. The free tier allows 3 requests a minute on `gemini-3.8-flash-tts`, and a 429 was abandoned after a fraction of a second. That is why the voice changed weight at about 20 seconds. The retake waits out the rate limit and calls only `gemini-3.8-flash-tts`. Shot `s05` was rate-limited once, then spoken by that same model.
