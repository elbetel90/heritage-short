"""Shared prompt text for reference stills and shot stills."""

WIDTH = 720
HEIGHT = 1280
MODEL_ID = "@cf/black-forest-labs/flux-2-klein-4b"


def character(storyboard):
    return storyboard["characters"][0]


def compose(storyboard, text):
    """Style block, then the person, then the shot or reference line."""
    person = character(storyboard)
    parts = [storyboard["style_block"].strip(), person["description"].strip(), text.strip()]
    return " ".join(part for part in parts if part)


def golden_id(storyboard):
    value = character(storyboard).get("golden_id")
    if value is None or not str(value).strip():
        return None
    return str(value)
