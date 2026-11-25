import pathlib
import tempfile
import unittest

from pipeline.images import compose
from pipeline.keyframes import GoldenError, render as render_keyframes, render_wide
from pipeline.references import render as render_references
from pipeline.validate import load_json
from tests.test_validate import STORYBOARD

REFERENCES_SOURCE = pathlib.Path(__file__).resolve().parents[1] / "pipeline" / "references.py"
KEYFRAMES_SOURCE = pathlib.Path(__file__).resolve().parents[1] / "pipeline" / "keyframes.py"
PNG = b"\x89PNG\r\n\x1a\nfake"


class StillTests(unittest.TestCase):
    def test_prompt_starts_with_the_style_block(self):
        board = load_json(STORYBOARD)
        prompt = compose(board, board["shots"][0]["image"]["prompt"])
        self.assertTrue(prompt.startswith(board["style_block"]))
        self.assertIn(board["shots"][0]["image"]["prompt"], prompt)
        self.assertGreater(prompt.index(board["style_block"]), -1)
        self.assertLess(prompt.index(board["style_block"]), prompt.index(board["shots"][0]["image"]["prompt"]))

    def test_reference_cache_skips_the_second_run(self):
        board = load_json(STORYBOARD)
        directory = pathlib.Path(tempfile.mkdtemp())
        calls = []

        def client(prompt, seed, reference_path):
            calls.append(seed)
            return PNG, 5

        kwargs = {
            "output_dir": directory / "refs",
            "manifest_path": directory / "manifest.json",
            "log_path": directory / "runs.jsonl",
            "client": client,
        }
        render_references(board, **kwargs)
        render_references(board, **kwargs)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len((directory / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()), 3)

    def test_keyframes_wait_for_a_golden_frame(self):
        board = load_json(STORYBOARD)
        board["characters"][0]["golden_id"] = None
        calls = []

        def client(prompt, seed, reference_path):
            calls.append(seed)
            return PNG, 5

        with self.assertRaises(GoldenError):
            render_keyframes(board, client=client)
        self.assertEqual(calls, [])

    def test_keyframe_cache_skips_the_second_run(self):
        board = load_json(STORYBOARD)
        directory = pathlib.Path(tempfile.mkdtemp())
        chosen = board["references"][0]["id"]
        board["characters"][0]["golden_id"] = chosen
        golden = directory / "refs" / (chosen + ".png")
        golden.parent.mkdir(parents=True)
        golden.write_bytes(PNG)
        calls = []

        def client(prompt, seed, reference_path):
            calls.append(reference_path)
            self.assertIn(board["style_block"], prompt)
            return PNG, 5

        kwargs = {
            "output_dir": directory / "frames",
            "reference_dir": directory / "refs",
            "manifest_path": directory / "manifest.json",
            "log_path": directory / "runs.jsonl",
            "client": client,
        }
        render_keyframes(board, **kwargs)
        first = len(calls)
        render_keyframes(board, **kwargs)
        self.assertEqual(first, len(board["shots"]))
        self.assertEqual(len(calls), first)

    def test_wide_cache_skips_the_second_run(self):
        board = load_json(STORYBOARD)
        directory = pathlib.Path(tempfile.mkdtemp())
        chosen = board["references"][0]["id"]
        board["characters"][0]["golden_id"] = chosen
        golden = directory / "refs" / (chosen + ".png")
        golden.parent.mkdir(parents=True)
        golden.write_bytes(PNG)
        stills = directory / "vertical"
        stills.mkdir()
        for shot in board["shots"]:
            (stills / (shot["id"] + ".png")).write_bytes(PNG)
        calls = []

        def client(prompt, seed, reference_path, still_path):
            calls.append(still_path)
            self.assertIn("16:9", prompt)
            return PNG, 5

        kwargs = {
            "output_dir": directory / "wide",
            "still_dir": stills,
            "reference_dir": directory / "refs",
            "manifest_path": directory / "manifest.json",
            "log_path": directory / "runs.jsonl",
            "client": client,
        }
        render_wide(board, **kwargs)
        first = len(calls)
        render_wide(board, **kwargs)
        self.assertEqual(first, len(board["shots"]))
        self.assertEqual(len(calls), first)

    def test_stage_modules_do_not_open_the_network(self):
        for path in (REFERENCES_SOURCE, KEYFRAMES_SOURCE):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("urlopen", text)


if __name__ == "__main__":
    unittest.main()
