import json
import sys
from pathlib import Path

import jsonschema

from pipeline.env import ROOT
from pipeline.timing import bookend_sec

SCHEMA_PATH = ROOT / "schema" / "storyboard.schema.json"
STORYBOARD_PATH = ROOT / "storyboard.json"
SUBTITLE_LINE_MAX = 42
DURATION_LOW = 60.0
DURATION_HIGH = 90.0


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def subtitle_errors(shot):
    text = shot["narration"]["text"]
    subtitle = shot["narration"]["subtitle_en"]
    shot_id = shot["id"]
    if not text.strip():
        if subtitle.strip():
            return ["%s: a silent shot must have an empty subtitle" % shot_id]
        return []
    lines = subtitle.split("\n")
    errors = []
    if len(lines) > 2:
        errors.append("%s: subtitle has %d lines" % (shot_id, len(lines)))
    for line in lines:
        if len(line) > SUBTITLE_LINE_MAX:
            errors.append("%s: subtitle line is %d characters" % (shot_id, len(line)))
    if not subtitle.strip():
        errors.append("%s: spoken shot is missing a subtitle" % shot_id)
    return errors


def semantic_errors(storyboard):
    errors = []
    ethics = storyboard["ethics"]
    if ethics["likeness"] == "real" and not ethics["real_people"]:
        errors.append("ethics.likeness is real but ethics.real_people is empty")
    ids = [shot["id"] for shot in storyboard["shots"]]
    if len(ids) != len(set(ids)):
        errors.append("shot ids are not unique")
    for shot in storyboard["shots"]:
        errors.extend(subtitle_errors(shot))
    total = sum(float(shot["duration_sec"]) for shot in storyboard["shots"])
    total += bookend_sec(storyboard)
    if not (DURATION_LOW <= total <= DURATION_HIGH):
        errors.append("total duration %.2fs is outside 60–90 seconds" % total)
    return errors


def validate_storyboard(storyboard, schema=None):
    if schema is None:
        schema = load_json(SCHEMA_PATH)
    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(storyboard), key=lambda item: list(item.path)):
        path = ".".join(str(part) for part in error.path) or "(root)"
        errors.append("%s: %s" % (path, error.message))
    if not errors:
        errors.extend(semantic_errors(storyboard))
    return errors


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    path = Path(argv[0]) if argv else STORYBOARD_PATH
    storyboard = load_json(path)
    errors = validate_storyboard(storyboard)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    total = sum(float(shot["duration_sec"]) for shot in storyboard["shots"])
    total += bookend_sec(storyboard)
    print("storyboard ok (%.2fs)" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
