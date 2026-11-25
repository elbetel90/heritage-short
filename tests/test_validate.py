import copy
import pathlib
import unittest

from pipeline.validate import load_json, validate_storyboard

ROOT = pathlib.Path(__file__).resolve().parents[1]
STORYBOARD = ROOT / "storyboard.json"
VALIDATE_SOURCE = ROOT / "pipeline" / "validate.py"


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.board = load_json(STORYBOARD)

    def test_real_storyboard_passes(self):
        self.assertEqual(validate_storyboard(self.board), [])

    def test_validate_module_does_not_call_providers(self):
        text = VALIDATE_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("urlopen", text)
        self.assertNotIn("generativelanguage", text)

    def test_missing_reason(self):
        board = copy.deepcopy(self.board)
        del board["shots"][0]["reason"]
        self.assertTrue(validate_storyboard(board))

    def test_seven_shots(self):
        board = copy.deepcopy(self.board)
        board["shots"] = board["shots"][:7]
        self.assertTrue(validate_storyboard(board))

    def test_thirteen_shots(self):
        board = copy.deepcopy(self.board)
        board["shots"] = board["shots"][:10]
        for number in (11, 12, 13):
            extra = copy.deepcopy(board["shots"][0])
            extra["id"] = "s%02d" % number
            board["shots"].append(extra)
        self.assertEqual(len(board["shots"]), 13)
        self.assertTrue(validate_storyboard(board))

    def test_unknown_beat(self):
        board = copy.deepcopy(self.board)
        board["shots"][0]["beat"] = "climax"
        self.assertTrue(validate_storyboard(board))

    def test_subtitle_too_long(self):
        board = copy.deepcopy(self.board)
        board["shots"][0]["narration"]["subtitle_en"] = "one\ntwo\nthree"
        self.assertTrue(validate_storyboard(board))

    def test_real_likeness_without_consent(self):
        board = copy.deepcopy(self.board)
        board["ethics"]["likeness"] = "real"
        board["ethics"]["real_people"] = []
        errors = validate_storyboard(board)
        self.assertTrue(any("real_people" in error for error in errors))

    def test_duration_outside_window(self):
        board = copy.deepcopy(self.board)
        for shot in board["shots"]:
            shot["duration_sec"] = 1
        self.assertTrue(validate_storyboard(board))


if __name__ == "__main__":
    unittest.main()
