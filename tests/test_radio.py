import pathlib
import tempfile
import unittest

from pipeline.audio import write_silence
from pipeline.radio import HEIGHT, WIDTH, assemble, probe


class RadioTests(unittest.TestCase):
    def test_assemble_is_vertical_and_matches_wavs(self):
        directory = pathlib.Path(tempfile.mkdtemp())
        shots = []
        wavs = {}
        for name in ("s01", "s02", "s03"):
            shots.append({"id": name, "duration_sec": 0.4})
            wavs[name] = directory / (name + ".wav")
            write_silence(wavs[name], 0.4)
        output = directory / "cut.mp4"
        duration = assemble(shots, wavs, output, directory / "work")
        info = probe(output)
        self.assertAlmostEqual(duration, 1.2, delta=0.5)
        video = [stream for stream in info["streams"] if stream["codec_type"] == "video"][0]
        audio = [stream for stream in info["streams"] if stream["codec_type"] == "audio"]
        self.assertEqual(video["width"], WIDTH)
        self.assertEqual(video["height"], HEIGHT)
        self.assertEqual(audio[0]["channels"], 2)


if __name__ == "__main__":
    unittest.main()
