import math
import pathlib
import struct
import subprocess
import tempfile
import unittest
import wave

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

    def test_bed_is_ducked_under_silence_and_stays_audible(self):
        directory = pathlib.Path(tempfile.mkdtemp())
        shots = []
        wavs = {}
        for name in ("s01", "s02", "s03"):
            shots.append({"id": name, "duration_sec": 0.4})
            wavs[name] = directory / (name + ".wav")
            write_silence(wavs[name], 0.4)
        bed = directory / "bed.wav"
        _write_tone(bed, 2.0)
        output = directory / "cut.mp4"
        assemble(
            shots,
            wavs,
            output,
            directory / "work",
            bed_path=bed,
            duck={"threshold": 0.02, "ratio": 6, "attack_ms": 300, "release_ms": 1500},
        )
        self.assertGreater(_max_volume_db(output), -20.0)


def _write_tone(path, duration, rate=48000, freq=220):
    frames = int(duration * rate)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        samples = []
        for index in range(frames):
            value = int(0.8 * 32767 * math.sin(2 * math.pi * freq * index / rate))
            samples.append(struct.pack("<h", value))
        handle.writeframes(b"".join(samples))


def _max_volume_db(path):
    result = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    text = result.stderr.decode("utf-8", errors="replace")
    for line in text.splitlines():
        if "max_volume:" in line:
            return float(line.split("max_volume:")[1].split("dB")[0].strip())
    raise AssertionError(text[-500:])


if __name__ == "__main__":
    unittest.main()
