import json
import subprocess
import sys
from pathlib import Path

from pipeline.audio import wav_duration
from pipeline.env import ROOT
from pipeline.narration import OUTPUT_DIR, render
from pipeline.timing import DurationError, apply_measured_speech, block_sec, fit_holds
from pipeline.validate import STORYBOARD_PATH, load_json, validate_storyboard

RADIO_PATH = ROOT / "outputs" / "radio" / "radio-cut.mp4"
WIDTH = 720
HEIGHT = 1280


def _run(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[-2000:])
    return result


def probe(path):
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-show_entries",
            "stream=codec_type,width,height,channels",
            "-of",
            "json",
            str(path),
        ]
    )
    return json.loads(result.stdout.decode("utf-8"))


def _encode_segment(segment, duration, voice_path, bed_path, bed_offset, duck, voice):
    color = "color=c=black:s=%dx%d:r=24:d=%s" % (WIDTH, HEIGHT, duration)
    command = ["ffmpeg", "-y", "-f", "lavfi", "-i", color]
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
    command.extend(
        [
            "-filter_complex",
            audio,
            "-map",
            "0:v",
            "-map",
            "[a]",
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
            "-t",
            str(duration),
            str(segment),
        ]
    )
    _run(command)


def _placeholder_filter(duration, voice):
    if not voice:
        return "[1:a]aresample=48000,volume=0.03[a]"
    return (
        "[1:a]aresample=48000,apad=whole_dur=%s,atrim=0:%s[voice];"
        "[2:a]aresample=48000,volume=0.03[bed];"
        "[voice][bed]amix=inputs=2:duration=first:dropout_transition=0[a]"
        % (duration, duration)
    )


def _bed_filter(duration, bed_offset, duck, voice):
    duck = duck or {}
    start = float(bed_offset)
    end = start + float(duration)
    if not voice:
        return (
            "[1:a]atrim=%s:%s,asetpts=PTS-STARTPTS,aresample=48000,apad=whole_dur=%s[a]"
            % (start, end, duration)
        )
    return (
        "[2:a]atrim=%s:%s,asetpts=PTS-STARTPTS,aresample=48000,apad=whole_dur=%s[bed];"
        "[1:a]aresample=48000,apad=whole_dur=%s,atrim=0:%s,asplit=2[voice][sc];"
        "[bed][sc]sidechaincompress=threshold=%s:ratio=%s:attack=%s:release=%s[ducked];"
        "[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0[a]"
        % (
            start,
            end,
            duration,
            duration,
            duration,
            duck.get("threshold", 0.02),
            duck.get("ratio", 6),
            duck.get("attack_ms", 300),
            duck.get("release_ms", 1500),
        )
    )


def assemble(shots, wav_paths, output_path, work_dir, end_card_sec=None, bed_path=None, duck=None, intro_sec=0, outro_sec=0):
    """Build a black 9:16 MP4 from per-shot wavs. Returns the probed duration."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    segments = []
    offset = 0.0
    if intro_sec:
        segment = work_dir / "intro.mp4"
        _encode_segment(segment, float(intro_sec), None, bed_path, offset, duck, voice=False)
        segments.append(segment)
        offset += float(intro_sec)
    for shot in shots:
        shot_id = shot["id"]
        duration = float(shot["duration_sec"])
        segment = work_dir / (shot_id + ".mp4")
        _encode_segment(
            segment,
            duration,
            wav_paths[shot_id],
            bed_path,
            offset,
            duck,
            voice=True,
        )
        segments.append(segment)
        offset += duration
    if outro_sec:
        segment = work_dir / "outro.mp4"
        _encode_segment(segment, float(outro_sec), None, bed_path, offset, duck, voice=False)
        segments.append(segment)
        offset += float(outro_sec)
    if end_card_sec:
        segment = work_dir / "endcard.mp4"
        _encode_segment(segment, float(end_card_sec), None, bed_path, offset, duck, voice=False)
        segments.append(segment)
    listing = work_dir / "concat.txt"
    listing.write_text(
        "".join("file '%s'\n" % segment.resolve().as_posix() for segment in segments),
        encoding="utf-8",
    )
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
            str(output_path),
        ]
    )
    info = probe(output_path)
    return float(info["format"]["duration"])


def build(storyboard, output_dir=None, radio_path=None, work_dir=None, client=None):
    output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    radio_path = Path(radio_path) if radio_path else RADIO_PATH
    work_dir = Path(work_dir) if work_dir else radio_path.parent / "work"
    errors = validate_storyboard(storyboard)
    if errors:
        raise DurationError("\n".join(errors))
    render(storyboard, output_dir=output_dir, client=client)
    measured = {}
    for shot in storyboard["shots"]:
        if shot["narration"]["text"].strip():
            measured[shot["id"]] = wav_duration(output_dir / (shot["id"] + ".wav"))
    apply_measured_speech(storyboard, measured)
    fit_holds(storyboard)
    errors = validate_storyboard(storyboard)
    if errors:
        raise DurationError("\n".join(errors))
    render(storyboard, output_dir=output_dir, client=client)
    wav_paths = {shot["id"]: output_dir / (shot["id"] + ".wav") for shot in storyboard["shots"]}
    duration = assemble(
        storyboard["shots"],
        wav_paths,
        radio_path,
        work_dir,
        end_card_sec=storyboard["end_card"]["duration_sec"],
        intro_sec=block_sec(storyboard, "intro"),
        outro_sec=block_sec(storyboard, "outro"),
    )
    return duration


def main():
    storyboard = load_json(STORYBOARD_PATH)
    try:
        duration = build(storyboard)
    except DurationError as error:
        print(str(error), file=sys.stderr)
        return 1
    STORYBOARD_PATH.write_text(json.dumps(storyboard, indent=2) + "\n", encoding="utf-8")
    print("radio cut %.2fs %s" % (duration, RADIO_PATH))
    if not (60.0 <= duration <= 90.0):
        print("probed duration is outside 60–90 seconds", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
