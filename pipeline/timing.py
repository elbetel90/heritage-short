"""Fit shot holds so speech plus silence plus the end card lands in 60–90 seconds."""

MIN_HOLD = 3.0
TARGET_TOTAL = 88.0
LOW = 60.0
HIGH = 90.0


class DurationError(Exception):
    pass


def _shot_map(storyboard):
    return {shot["id"]: shot for shot in storyboard["shots"]}


def apply_measured_speech(storyboard, wav_durations):
    """Set spoken-shot durations from wav length. Silent holds stay put."""
    for shot in storyboard["shots"]:
        if shot["narration"]["text"].strip() and shot["id"] in wav_durations:
            shot["duration_sec"] = round(float(wav_durations[shot["id"]]), 2)


def spoken_sum(storyboard):
    total = 0.0
    for shot in storyboard["shots"]:
        if shot["narration"]["text"].strip():
            total += float(shot["duration_sec"])
    return total


def hold_ids(storyboard):
    return [shot["id"] for shot in storyboard["shots"] if not shot["narration"]["text"].strip()]


def block_sec(storyboard, key):
    block = storyboard.get(key) or {}
    return float(block.get("duration_sec") or 0)


def bookend_sec(storyboard):
    """Black intro, black outro, and the end card."""
    return block_sec(storyboard, "intro") + block_sec(storyboard, "outro") + float(storyboard["end_card"]["duration_sec"])


def fit_holds(storyboard):
    """Lengthen the wordless shots so the film lands near 88s and inside 60–90s.

    Returns the hold length in seconds. Raises DurationError when no hold works.
    """
    end = bookend_sec(storyboard)
    speech = spoken_sum(storyboard)
    ids = hold_ids(storyboard)
    if not ids:
        raise DurationError("no wordless shots to hold")
    holds = _shot_map(storyboard)

    def total(hold):
        return speech + hold * len(ids) + end

    gap = TARGET_TOTAL - speech - end
    hold = gap / float(len(ids))
    if total(hold) < LOW:
        hold = (LOW - speech - end) / float(len(ids))
    if total(hold) > HIGH:
        hold = (HIGH - speech - end) / float(len(ids))
    if hold < MIN_HOLD and total(MIN_HOLD) <= HIGH:
        hold = MIN_HOLD
    if hold < MIN_HOLD or not (LOW <= total(hold) <= HIGH):
        raise DurationError(
            "cannot fit duration: speech %.2fs, end %.2fs, hold %.2fs, total %.2fs"
            % (speech, end, hold, total(hold))
        )
    hold = round(hold, 2)
    for shot_id in ids:
        holds[shot_id]["duration_sec"] = hold
    return hold
