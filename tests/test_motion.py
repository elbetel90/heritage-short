import pathlib
import tempfile
import unittest

from pipeline.costs import document, tally
from pipeline.motion import clip_path, ingest


class MotionTests(unittest.TestCase):
    def test_ingest_copies_the_clip(self):
        directory = pathlib.Path(tempfile.mkdtemp())
        source = directory / "taken.mp4"
        source.write_bytes(b"clip")
        dest = ingest(
            "s01",
            source,
            latency_ms=12,
            log_path=directory / "runs.jsonl",
            output_dir=directory / "motion",
        )
        self.assertEqual(dest, clip_path("s01", directory / "motion"))
        self.assertEqual(dest.read_bytes(), b"clip")
        log = (directory / "runs.jsonl").read_text(encoding="utf-8")
        self.assertIn('"shot_id": "s01"', log)
        self.assertIn("stable-video-diffusion-img2vid-xt-1-1", log)

    def test_costs_count_logged_calls_and_do_not_invent_a_price(self):
        directory = pathlib.Path(tempfile.mkdtemp())
        log = directory / "runs.jsonl"
        log.write_text(
            '{"stage": "keyframes", "model": "flux", "status": "ok", "cost": 0}\n'
            '{"stage": "keyframes", "model": "flux", "status": "error", "cost": 0}\n',
            encoding="utf-8",
        )
        counts, spent = tally([log])
        text = document(
            counts,
            spent,
            gpu=[{"file": "runs-motion.jsonl", "shot_id": "s10", "status": "ok", "latency_ms": 60000}],
        )
        self.assertEqual(spent, 0)
        self.assertIn("| keyframes | flux | ok | 1 |", text)
        self.assertIn("published rate, not a measured bill", text)
        self.assertIn("| runs-motion.jsonl | s10 | ok | 1.00 |", text)


if __name__ == "__main__":
    unittest.main()
