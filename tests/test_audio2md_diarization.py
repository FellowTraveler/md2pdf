"""audio2md must hand pyannote preloaded audio, not a file path.

pyannote's own decoder returns short chunks for compressed formats like .m4a
("resulted in 477888 samples instead of the expected 480000"), so speaker
detection always failed. Run under the md2pdf venv.
"""
import importlib.machinery
import importlib.util
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
DURATION_SECONDS = 1


def load_audio2md():
    """audio2md has no .py extension, so it is loaded with an explicit source loader."""
    sys.dont_write_bytecode = True
    loader = importlib.machinery.SourceFileLoader("audio2md", str(REPO_ROOT / "audio2md"))
    spec = importlib.util.spec_from_loader("audio2md", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


audio2md = load_audio2md()


class RunPyannoteTest(unittest.TestCase):
    def test_passes_preloaded_mono_waveform(self):
        rate = audio2md.PYANNOTE_SAMPLE_RATE
        pipeline = mock.Mock(return_value="diarization")
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "silence.wav"
            with wave.open(str(wav_path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(rate)
                wav.writeframes(b"\x00\x00" * rate * DURATION_SECONDS)

            with mock.patch("pyannote.audio.Pipeline.from_pretrained", return_value=pipeline):
                result = audio2md._run_pyannote(wav_path, "hf-token")

        self.assertEqual(result, "diarization")
        (audio_input,), _ = pipeline.call_args
        self.assertEqual(audio_input["sample_rate"], rate)
        self.assertEqual(tuple(audio_input["waveform"].shape), (1, rate * DURATION_SECONDS))


if __name__ == "__main__":
    unittest.main()
