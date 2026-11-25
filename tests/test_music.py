import pathlib
import tempfile
import unittest

from pipeline.audio import write_silence
from pipeline.music import candidate_path, ingest, music_payload
from pipeline.validate import load_json
from tests.test_validate import STORYBOARD


class MusicTests(unittest.TestCase):
    def test_payload_uses_the_cue_and_seed(self):
        board = load_json(STORYBOARD)
        payload = music_payload(board, 11)
        self.assertTrue(payload["instrumental"])
        self.assertEqual(payload["seed"], 11)
        self.assertIn("no vocals", payload["caption"])
        self.assertEqual(len(board["music"]["candidate_seeds"]), 3)

    def test_ingest_copies_the_wav_and_logs_the_seed(self):
        board = load_json(STORYBOARD)
        directory = pathlib.Path(tempfile.mkdtemp())
        source = directory / "taken.wav"
        write_silence(source, 0.3)
        dest = ingest(
            board,
            11,
            source,
            latency_ms=10,
            log_path=directory / "runs.jsonl",
            manifest_path=directory / "manifest.json",
            output_dir=directory / "music",
        )
        self.assertEqual(dest, candidate_path(11, directory / "music"))
        self.assertTrue(dest.is_file())
        log = (directory / "runs.jsonl").read_text(encoding="utf-8")
        self.assertIn('"seed": 11', log)
        self.assertIn("ACE-Step-1.5", log)


if __name__ == "__main__":
    unittest.main()
