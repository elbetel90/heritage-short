import io
import pathlib
import tempfile
import unittest
import wave

from pipeline.narration import render
from pipeline.validate import load_json
from tests.test_validate import STORYBOARD


def _wav_bytes(duration=0.2, rate=24000):
    buffer = io.BytesIO()
    frames = int(duration * rate)
    with wave.open(buffer, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames)
    return buffer.getvalue()


class NarrationTests(unittest.TestCase):
    def test_cache_skips_second_run_and_silence_is_local(self):
        board = load_json(STORYBOARD)
        directory = pathlib.Path(tempfile.mkdtemp())
        calls = []

        def client(text, voice, style):
            calls.append(text)
            return _wav_bytes(), "fake-tts", 5

        kwargs = {
            "output_dir": directory / "wavs",
            "manifest_path": directory / "manifest.json",
            "log_path": directory / "runs.jsonl",
            "client": client,
        }
        spoken = [shot for shot in board["shots"] if shot["narration"]["text"].strip()]
        render(board, **kwargs)
        self.assertEqual(len(calls), len(spoken))
        render(board, **kwargs)
        self.assertEqual(len(calls), len(spoken))
        log_lines = (directory / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(log_lines), len(spoken))
        for shot in board["shots"]:
            if shot["narration"]["text"].strip():
                continue
            shot_id = shot["id"]
            path = directory / "wavs" / (shot_id + ".wav")
            self.assertTrue(path.is_file())
            with wave.open(str(path), "r") as handle:
                duration = handle.getnframes() / float(handle.getframerate())
            self.assertGreater(duration, 1.0)


if __name__ == "__main__":
    unittest.main()
