import pathlib
import subprocess
import tempfile
import unittest

from pipeline.audio import write_silence
from pipeline.film import assemble
from pipeline.radio import probe
from pipeline.shots import ShotError, pan, render


def _png(directory, name):
    path = directory / name
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=gray:s=64x96",
            "-frames:v",
            "1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return path


class FilmTests(unittest.TestCase):
    def test_pan_matches_the_shot_length(self):
        directory = pathlib.Path(tempfile.mkdtemp())
        dest = directory / "pan.mp4"
        pan(_png(directory, "still.png"), dest, 0.5, zoom_in=True)
        info = probe(dest)
        video = [stream for stream in info["streams"] if stream["codec_type"] == "video"][0]
        self.assertEqual(video["width"], 720)
        self.assertEqual(video["height"], 1280)
        self.assertAlmostEqual(float(info["format"]["duration"]), 0.5, delta=0.15)

    def test_missing_still_stops_before_a_pan(self):
        directory = pathlib.Path(tempfile.mkdtemp())
        board = {"shots": [{"id": "s01", "duration_sec": 0.4, "motion": {"seed": 1}}]}
        with self.assertRaises(ShotError):
            render(board, still_dir=directory, output_dir=directory / "out", manifest_path=directory / "manifest.json")

    def test_picture_cut_burns_the_end_card_and_makes_a_wide_frame(self):
        directory = pathlib.Path(tempfile.mkdtemp())
        shots = []
        clips = {}
        wavs = {}
        for name in ("s01", "s02"):
            shots.append(
                {
                    "id": name,
                    "duration_sec": 0.4,
                    "narration": {"subtitle_en": "A line.\nThe next line."},
                }
            )
            clips[name] = directory / (name + ".mp4")
            pan(_png(directory, name + ".png"), clips[name], 0.4, zoom_in=True)
            wavs[name] = directory / (name + ".wav")
            write_silence(wavs[name], 0.4)
        vertical = directory / "film-9x16.mp4"
        wide = directory / "film-16x9.mp4"
        duration = assemble(
            shots,
            clips,
            wavs,
            vertical,
            wide,
            directory / "work",
            {"text": "Made with AI", "duration_sec": 0.4},
        )
        info = probe(vertical)
        wide_info = probe(wide)
        video = [stream for stream in info["streams"] if stream["codec_type"] == "video"][0]
        wide_video = [stream for stream in wide_info["streams"] if stream["codec_type"] == "video"][0]
        audio = [stream for stream in info["streams"] if stream["codec_type"] == "audio"][0]
        self.assertAlmostEqual(duration, 1.2, delta=0.5)
        self.assertEqual(video["width"], 720)
        self.assertEqual(video["height"], 1280)
        self.assertEqual(audio["channels"], 2)
        self.assertEqual(wide_video["width"], 1280)
        self.assertEqual(wide_video["height"], 720)
