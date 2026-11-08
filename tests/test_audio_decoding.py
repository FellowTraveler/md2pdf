"""Regression test: faster-whisper must be able to decode audio with the installed PyAV.

faster-whisper 1.2.1 calls av.open(..., metadata_errors=...), which av 19 removed,
so every transcription failed. install.sh caps av<19; this catches a recurrence.
Run under the md2pdf venv (~/.md2pdf-venv/bin/python -m unittest discover -s tests).
"""
import tempfile
import unittest
import wave
from pathlib import Path

from faster_whisper import decode_audio

SAMPLE_RATE = 16000
DURATION_SECONDS = 1


class DecodeAudioTest(unittest.TestCase):
    def test_decodes_wav_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "silence.wav"
            with wave.open(str(wav_path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(SAMPLE_RATE)
                wav.writeframes(b"\x00\x00" * SAMPLE_RATE * DURATION_SECONDS)

            samples = decode_audio(str(wav_path), sampling_rate=SAMPLE_RATE)

        self.assertEqual(len(samples), SAMPLE_RATE * DURATION_SECONDS)


if __name__ == "__main__":
    unittest.main()
