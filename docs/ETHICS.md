# Ethics

## Consent

No real person is interviewed, shown, or voiced. Every character is fictional. No face, likeness, or voice in the film belongs to a living person, so there is no consent form and no name to record.

`storyboard.json` carries the same rule: `ethics.likeness` is `fictional` and `ethics.real_people` is empty. The pipeline stops if a prompt names a real person, or if likeness is set to `real` while that list is empty.

Gemini TTS uses a named stock voice and a style instruction. It does not clone anyone.

## Private data

The free Gemini tier may use prompts to improve Google's products. Family details and other private facts stay out of provider prompts. The story's personal meaning can live in this file and in `docs/DESIGN.md`. It does not need to be sent to a model.

Style prompts describe qualities of light, palette, and medium. They do not name a living artist.

## Licences

| Model or tool | Terms used here |
| --- | --- |
| Gemini API and Gemini TTS | Free tier. Used for the storyboard draft, translation, and narration. |
| FLUX.2 klein 4B (`@cf/black-forest-labs/flux-2-klein-4b`) on Cloudflare Workers AI | Apache 2.0. This is the keyframe model. |
| FLUX.2 klein 9B | Non-commercial. Not used. |
| Wan 2.2 | Apache 2.0. Tried for the moving shots. It did not fit in the GPU memory, so it is not in the film. |
| HunyuanVideo 1.5 | The checkpoint returned 401 and did not download. Not used. |
| Stable Video Diffusion XT 1.1 (`stabilityai/stable-video-diffusion-img2vid-xt-1-1`) | Stability AI Community License, last updated 5 July 2024. Research, non-commercial, and commercial use are free under USD $1,000,000 annual revenue. Above that, the licence ends and an enterprise licence is required. This film is a non-commercial student short. The weights are gated: the Hugging Face agreement was accepted before download. https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt-1-1/blob/main/LICENSE.md |
| ACE-Step 1.5 | MIT. Outputs may be used commercially. The score is instrumental. |
| FFmpeg | Local assembly only. The licence is the one that ships with the build on this machine. |

## Labelling

The film ends with a visible card that says it was made with AI. The public post uses the platform's AI disclosure. SynthID and C2PA metadata are left in the file when a model writes them. Subtitles and titles are added in FFmpeg, not painted into generated images.
