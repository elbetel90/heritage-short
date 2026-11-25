import unittest

from pipeline.timing import DurationError, apply_measured_speech, fit_holds
from pipeline.validate import load_json, validate_storyboard
from tests.test_validate import STORYBOARD


class TimingTests(unittest.TestCase):
    def test_short_speech_lands_inside_window(self):
        board = load_json(STORYBOARD)
        measured = {}
        for shot in board["shots"]:
            if shot["narration"]["text"].strip():
                measured[shot["id"]] = 4.0
        apply_measured_speech(board, measured)
        fit_holds(board)
        self.assertEqual(validate_storyboard(board), [])

    def test_long_speech_still_fits(self):
        board = load_json(STORYBOARD)
        measured = {}
        for shot in board["shots"]:
            if shot["narration"]["text"].strip():
                measured[shot["id"]] = 9.0
        apply_measured_speech(board, measured)
        fit_holds(board)
        self.assertEqual(validate_storyboard(board), [])

    def test_impossible_duration_raises(self):
        board = load_json(STORYBOARD)
        for shot in board["shots"]:
            if shot["narration"]["text"].strip():
                shot["duration_sec"] = 12
        with self.assertRaises(DurationError):
            fit_holds(board)


if __name__ == "__main__":
    unittest.main()
