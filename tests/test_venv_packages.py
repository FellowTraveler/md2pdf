"""Tests for venv_packages.sh: which optional pip packages install.sh puts in the venv."""
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "venv_packages.sh"
BASE_PACKAGES = ["pymupdf4llm", "pytesseract", "Pillow", "faster-whisper", "av<19"]


class VenvPackagesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.env_file = Path(self._tmp.name) / ".env"
        self.env_file.write_text("")

    def tearDown(self):
        self._tmp.cleanup()

    def _packages(self, **need_flags):
        flags = "".join(f"_need_{name}=true; " for name in need_flags)
        result = subprocess.run(
            ["/bin/bash", "-c", f'source "{SCRIPT}"; {flags}venv_packages "$1"', "_", str(self.env_file)],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.split()

    def test_keys_saved_by_earlier_install_still_install_packages(self):
        self.env_file.write_text("HUGGINGFACE_TOKEN=hf_abc\nELEVENLABS_API_KEY=el_abc\n")
        packages = self._packages(huggingface=True, elevenlabs=True)
        self.assertIn("pyannote.audio", packages)
        self.assertIn("elevenlabs", packages)

    def test_saved_key_without_selected_feature_adds_nothing(self):
        self.env_file.write_text("HUGGINGFACE_TOKEN=hf_abc\nANTHROPIC_API_KEY=sk_abc\n")
        self.assertEqual(self._packages(), BASE_PACKAGES)

    def test_selected_feature_without_key_adds_nothing(self):
        self.env_file.write_text("HUGGINGFACE_TOKEN=\n")
        self.assertEqual(self._packages(huggingface=True, elevenlabs=True, llm=True), BASE_PACKAGES)

    def test_qr_feature_adds_zxing_without_any_key(self):
        self.assertEqual(self._packages(qr=True), BASE_PACKAGES + ["zxing-cpp"])

    def test_llm_packages_follow_saved_keys(self):
        self.env_file.write_text("ANTHROPIC_API_KEY=sk_abc\nOPENAI_API_KEY=sk_def\n")
        packages = self._packages(llm=True)
        self.assertIn("anthropic", packages)
        self.assertIn("openai", packages)


if __name__ == "__main__":
    unittest.main()
