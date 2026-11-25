import wave
from pathlib import Path


def write_silence(path, duration_sec, rate=24000):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, int(round(duration_sec * rate)))
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames)
    return path


def _pad(path, duration_sec, before):
    path = Path(path)
    with wave.open(str(path), "r") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    pad = int(round(float(duration_sec) * rate))
    silence = b"\x00" * (pad * channels * width)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(rate)
        if before:
            handle.writeframes(silence + frames)
        else:
            handle.writeframes(frames + silence)
    return path


def prepend_silence(path, duration_sec):
    return _pad(path, duration_sec, True)


def append_silence(path, duration_sec):
    return _pad(path, duration_sec, False)


def wav_duration(path):
    with wave.open(str(path), "r") as handle:
        return handle.getnframes() / float(handle.getframerate())
