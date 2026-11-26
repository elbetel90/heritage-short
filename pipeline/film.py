"""9:16 and 16:9 picture cut. Pans, voice, burned-in English, placeholder bed."""

import sys
from pathlib import Path

from pipeline.env import ROOT
from pipeline.radio import (
    HEIGHT,
    WIDTH,
    _bed_filter,
    _placeholder_filter,
    _run,
    probe,
)
from pipeline.music import candidate_path
from pipeline.keyframes import WIDE_DIR, GoldenError, render_wide
from pipeline.motion import MOTION_DIR, WIDE_MOTION_DIR
from pipeline.shots import OUTPUT_DIR as SHOT_DIR
from pipeline.shots import ShotError, render as render_shots
from pipeline.timing import DurationError, block_sec
from pipeline.validate import STORYBOARD_PATH, load_json, validate_storyboard

FINAL_DIR = ROOT / "outputs" / "final"
NARRATION_DIR = ROOT / "outputs" / "narration"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
VERTICAL_PATH = FINAL_DIR / "film-9x16.mp4"
WIDE_PATH = FINAL_DIR / "film-16x9.mp4"


def _escape(text):
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\u2019")
        .replace("%", "\\%")
        .replace(",", "\\,")
    )


def _drawtext(text, fontsize, y):
    return (
        "drawtext=fontfile='%s':text='%s':fontsize=%s:fontcolor=white:"
        "borderw=2:bordercolor=black:x=(w-text_w)/2:y=%s"
        % (FONT, _escape(text), fontsize, y)
    )


def _video_filter(subtitle, end_card_text, wide=False):
    if end_card_text:
        return _drawtext(end_card_text, 42 if wide else 48, "(h-text_h)/2")
    lines = [line.strip() for line in (subtitle or "").split("\n") if line.strip()]
    if not lines:
        return None
    size = 32 if wide else 28
    base = 118 if wide else 170
    step = 42 if wide else 46
    filters = []
    for index, line in enumerate(lines):
        filters.append(_drawtext(line, size, "h-%d" % (base - index * step)))
    return ",".join(filters)


def _lead_trim(picture, duration):
    """Drop the first half second of a clip that is longer than the shot."""
    try:
        length = float(probe(picture)["format"]["duration"])
    except (OSError, KeyError, ValueError):
        return False
    return length > float(duration) + 1.0


def _stamp(seconds):
    total = int(round(float(seconds) * 1000))
    if total < 0:
        total = 0
    hours, total = divmod(total, 3600000)
    minutes, total = divmod(total, 60000)
    secs, millis = divmod(total, 1000)
    return "%02d:%02d:%02d,%03d" % (hours, minutes, secs, millis)


def write_srt(shots, dest, intro_sec=0, outro_sec=0, end_card=None):
    """Write one subtitle file. Silent shots get no cue. Timing matches both masters."""
    cues = []
    cursor = float(intro_sec or 0)
    for shot in shots:
        duration = float(shot["duration_sec"])
        text = ((shot.get("narration") or {}).get("subtitle_en") or "").strip()
        if text:
            cues.append((cursor, cursor + duration, text))
        cursor += duration
    cursor += float(outro_sec or 0)
    card = ((end_card or {}).get("text") or "").strip()
    if card:
        cues.append((cursor, cursor + float(end_card["duration_sec"]), card))
    lines = []
    for index, (start, end, text) in enumerate(cues, start=1):
        lines.append(str(index))
        lines.append("%s --> %s" % (_stamp(start), _stamp(end)))
        lines.append(text)
        lines.append("")
    Path(dest).write_text("\n".join(lines), encoding="utf-8")
    return Path(dest)


def _encode(segment, picture, duration, voice_path, subtitle, bed_path, bed_offset, duck, voice, end_card_text=None, black=False):
    if end_card_text or black:
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=%dx%d:r=24:d=%s" % (WIDTH, HEIGHT, duration),
        ]
    else:
        command = ["ffmpeg", "-y"]
        if _lead_trim(picture, duration):
            command.extend(["-ss", "0.5"])
        command.extend(["-i", str(picture)])
    if voice:
        command.extend(["-i", str(voice_path)])
    if bed_path:
        command.extend(["-i", str(bed_path)])
        audio = _bed_filter(duration, bed_offset, duck, voice)
    else:
        command.extend(
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=110:sample_rate=48000:duration=%s" % duration,
            ]
        )
        audio = _placeholder_filter(duration, voice)
    video = _video_filter(subtitle, end_card_text)
    if end_card_text or black:
        if video:
            graph = "[0:v]%s[v];%s" % (video, audio)
            video_map = "[v]"
        else:
            graph = audio
            video_map = "0:v"
    else:
        fit = (
            "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
            "tpad=stop_mode=clone:stop_duration=60"
            % (WIDTH, HEIGHT, WIDTH, HEIGHT)
        )
        chain = fit if not video else "%s,%s" % (fit, video)
        graph = "[0:v]%s[v];%s" % (chain, audio)
        video_map = "[v]"
    command.extend(
        [
            "-filter_complex",
            graph,
            "-map",
            video_map,
            "-map",
            "[a]",
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(segment),
        ]
    )
    _run(command)


def _loudnorm(source, dest):
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-af",
            "loudnorm=I=-14:TP=-1:LRA=11",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(dest),
        ]
    )


WIDE_WIDTH = 1280
WIDE_HEIGHT = 720
WIDE_SHOT_DIR = ROOT / "outputs" / "shots-16x9"
# Scale a 16:9 clip to the master and hold the last frame when it is short.
WIDE_FIT = (
    "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
    "tpad=stop_mode=clone:stop_duration=60"
) % (WIDE_WIDTH, WIDE_HEIGHT, WIDE_WIDTH, WIDE_HEIGHT)


def _reframe(picture, audio_source, dest, duration, subtitle):
    video = _video_filter(subtitle, None, wide=True)
    chain = WIDE_FIT if not video else "%s,%s" % (WIDE_FIT, video)
    command = ["ffmpeg", "-y"]
    if _lead_trim(picture, duration):
        command.extend(["-ss", "0.5"])
    command.extend(
        [
            "-i",
            str(picture),
            "-i",
            str(audio_source),
            "-filter_complex",
            "[0:v]%s[v]" % chain,
            "-map",
            "[v]",
            "-map",
            "1:a",
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            str(dest),
        ]
    )
    _run(command)


def _wide_hold(audio_source, dest, duration, text=None):
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=%dx%d:r=24:d=%s" % (WIDE_WIDTH, WIDE_HEIGHT, duration),
        "-i",
        str(audio_source),
    ]
    if text:
        command.extend(
            [
                "-filter_complex",
                "[0:v]%s[v]" % _video_filter(None, text, wide=True),
                "-map",
                "[v]",
            ]
        )
    else:
        command.extend(["-map", "0:v"])
    command.extend(
        [
            "-map",
            "1:a",
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            str(dest),
        ]
    )
    _run(command)


def _write_wide(shots, clip_paths, segments, card_source, wide_path, work_dir, end_card, intro_source=None, outro_source=None, intro_sec=0, outro_sec=0, wide_clips=None):
    """Write a 16:9 master. Picture comes from a wide clip or a landscape pan. Audio comes from the vertical mix."""
    wide_dir = Path(work_dir) / "wide"
    wide_dir.mkdir(parents=True, exist_ok=True)
    wide_segments = []
    if intro_source:
        dest = wide_dir / "intro.mp4"
        _wide_hold(intro_source, dest, float(intro_sec))
        wide_segments.append(dest)
    for shot, source in zip(shots, segments):
        dest = wide_dir / (shot["id"] + ".mp4")
        picture = source
        if wide_clips:
            picture = wide_clips[shot["id"]]
        _reframe(
            picture,
            source,
            dest,
            float(shot["duration_sec"]),
            shot["narration"]["subtitle_en"],
        )
        wide_segments.append(dest)
    if outro_source:
        dest = wide_dir / "outro.mp4"
        _wide_hold(outro_source, dest, float(outro_sec))
        wide_segments.append(dest)
    card = wide_dir / "endcard.mp4"
    _wide_hold(card_source, card, float(end_card["duration_sec"]), end_card["text"])
    wide_segments.append(card)
    listing = wide_dir / "concat.txt"
    listing.write_text(
        "".join("file '%s'\n" % segment.resolve().as_posix() for segment in wide_segments),
        encoding="utf-8",
    )
    joined = wide_dir / "joined.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c",
            "copy",
            str(joined),
        ]
    )
    _loudnorm(joined, wide_path)


def assemble(shots, clip_paths, wav_paths, output_path, wide_path, work_dir, end_card, bed_path=None, duck=None, intro_sec=0, outro_sec=0, wide_clips=None):
    """Burn subtitles, mix the bed, and write the vertical and wide masters."""
    if not Path(FONT).is_file():
        raise ShotError("missing subtitle font: %s" % FONT)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    segments = []
    shot_segments = []
    offset = 0.0
    intro = None
    if intro_sec:
        intro = work_dir / "intro.mp4"
        _encode(intro, None, float(intro_sec), None, None, bed_path, offset, duck, voice=False, black=True)
        segments.append(intro)
        offset += float(intro_sec)
    for shot in shots:
        shot_id = shot["id"]
        duration = float(shot["duration_sec"])
        segment = work_dir / (shot_id + ".mp4")
        _encode(
            segment,
            clip_paths[shot_id],
            duration,
            wav_paths[shot_id],
            shot["narration"]["subtitle_en"],
            bed_path,
            offset,
            duck,
            voice=True,
        )
        segments.append(segment)
        shot_segments.append(segment)
        offset += duration
    outro = None
    if outro_sec:
        outro = work_dir / "outro.mp4"
        _encode(outro, None, float(outro_sec), None, None, bed_path, offset, duck, voice=False, black=True)
        segments.append(outro)
        offset += float(outro_sec)
    card = work_dir / "endcard.mp4"
    _encode(
        card,
        None,
        float(end_card["duration_sec"]),
        None,
        None,
        bed_path,
        offset,
        duck,
        voice=False,
        end_card_text=end_card["text"],
    )
    segments.append(card)
    listing = work_dir / "concat.txt"
    listing.write_text(
        "".join("file '%s'\n" % segment.resolve().as_posix() for segment in segments),
        encoding="utf-8",
    )
    joined = work_dir / "joined.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c",
            "copy",
            str(joined),
        ]
    )
    _loudnorm(joined, output_path)
    write_srt(
        shots,
        Path(output_path).with_name("film.srt"),
        intro_sec=intro_sec,
        outro_sec=outro_sec,
        end_card=end_card,
    )
    _write_wide(
        shots,
        clip_paths,
        shot_segments,
        card,
        wide_path,
        work_dir,
        end_card,
        intro_source=intro,
        outro_source=outro,
        intro_sec=intro_sec,
        outro_sec=outro_sec,
        wide_clips=wide_clips,
    )
    info = probe(output_path)
    return float(info["format"]["duration"])


def build(storyboard, narration_dir=None, shot_dir=None, final_dir=None):
    errors = validate_storyboard(storyboard)
    if errors:
        raise DurationError("\n".join(errors))
    narration_dir = Path(narration_dir) if narration_dir else NARRATION_DIR
    shot_dir = Path(shot_dir) if shot_dir else SHOT_DIR
    final_dir = Path(final_dir) if final_dir else FINAL_DIR
    render_shots(storyboard, output_dir=shot_dir)
    render_wide(storyboard)
    wide_shot_dir = WIDE_SHOT_DIR
    render_shots(
        storyboard,
        still_dir=WIDE_DIR,
        output_dir=wide_shot_dir,
        width=WIDE_WIDTH,
        height=WIDE_HEIGHT,
        cache_key="shots-16x9",
    )
    wav_paths = {}
    clip_paths = {}
    wide_clips = {}
    for shot in storyboard["shots"]:
        wav_paths[shot["id"]] = narration_dir / (shot["id"] + ".wav")
        motion = MOTION_DIR / (shot["id"] + ".mp4")
        clip_paths[shot["id"]] = motion if motion.is_file() else shot_dir / (shot["id"] + ".mp4")
        wide_motion = WIDE_MOTION_DIR / (shot["id"] + ".mp4")
        wide_clips[shot["id"]] = wide_motion if wide_motion.is_file() else wide_shot_dir / (shot["id"] + ".mp4")
        if not wav_paths[shot["id"]].is_file():
            raise ShotError("missing narration: %s" % wav_paths[shot["id"]])
    vertical = final_dir / "film-9x16.mp4"
    wide = final_dir / "film-16x9.mp4"
    return assemble(
        storyboard["shots"],
        clip_paths,
        wav_paths,
        vertical,
        wide,
        final_dir / "work",
        storyboard["end_card"],
        bed_path=_chosen_bed(storyboard),
        duck=storyboard["mix"]["duck"],
        intro_sec=block_sec(storyboard, "intro"),
        outro_sec=block_sec(storyboard, "outro"),
        wide_clips=wide_clips,
    )


def _chosen_bed(storyboard):
    chosen = (storyboard.get("music") or {}).get("chosen_id")
    if not chosen:
        return None
    bed = candidate_path(str(chosen).replace("seed-", ""))
    if not bed.is_file():
        raise ShotError("missing score: %s" % bed)
    return bed


def main():
    storyboard = load_json(STORYBOARD_PATH)
    try:
        duration = build(storyboard)
    except (DurationError, ShotError, GoldenError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print("picture cut %.2fs %s" % (duration, VERTICAL_PATH))
    if not (60.0 <= duration <= 90.0):
        print("probed duration is outside 60–90 seconds", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
