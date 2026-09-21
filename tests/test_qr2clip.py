import contextlib
import importlib.machinery
import importlib.util
import io
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
PLAIN_QR_TEXT = "https://example.com/qr2clip-plain-fixture"
CENTER_LOGO_QR_TEXT = "https://drodom.substack.com/p/the-truth-about-women-not-losing"


def load_qr2clip():
    """qr2clip has no .py extension, so it is loaded with an explicit source loader."""
    sys.dont_write_bytecode = True
    loader = importlib.machinery.SourceFileLoader("qr2clip", str(REPO_ROOT / "qr2clip"))
    spec = importlib.util.spec_from_loader("qr2clip", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


qr2clip = load_qr2clip()


class DecodeQrTests(unittest.TestCase):
    def test_plain_qr_decodes(self):
        self.assertEqual(qr2clip.decode_qr(str(FIXTURES_DIR / "qr_plain.png")), PLAIN_QR_TEXT)

    def test_center_logo_qr_decodes(self):
        self.assertEqual(
            qr2clip.decode_qr(str(FIXTURES_DIR / "qr_center_logo.jpg")), CENTER_LOGO_QR_TEXT
        )

    def test_image_without_qr_returns_none(self):
        self.assertIsNone(qr2clip.decode_qr(str(FIXTURES_DIR / "no_qr.png")))


class DecodeFileTests(unittest.TestCase):
    def run_decode_file(self, image_path):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = qr2clip.decode_file(str(image_path))
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_prints_payload_and_exits_zero(self):
        exit_code, stdout, _ = self.run_decode_file(FIXTURES_DIR / "qr_plain.png")
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.strip(), PLAIN_QR_TEXT)

    def test_no_qr_exits_one(self):
        exit_code, stdout, stderr = self.run_decode_file(FIXTURES_DIR / "no_qr.png")
        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("No QR code found", stderr)

    def test_missing_file_exits_one(self):
        exit_code, _, stderr = self.run_decode_file(FIXTURES_DIR / "does_not_exist.png")
        self.assertEqual(exit_code, 1)
        self.assertIn("no such file", stderr)

    def test_unreadable_image_exits_one(self):
        exit_code, _, stderr = self.run_decode_file(FIXTURES_DIR / "make_fixtures.py")
        self.assertEqual(exit_code, 1)
        self.assertIn("cannot read image", stderr)


if __name__ == "__main__":
    unittest.main()
