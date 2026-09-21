import contextlib
import importlib.machinery
import importlib.util
import io
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

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


class ScanScreenTests(unittest.TestCase):
    """The interactive flow with every macOS side effect mocked out."""

    def setUp(self):
        self.capture_paths = []
        self.notify = self.patch("notify")
        self.copy_to_clipboard = self.patch("copy_to_clipboard")
        self.open_settings = self.patch("open_screen_recording_settings")
        self.patch("decoder_available", return_value=True)

    def patch(self, function_name, **kwargs):
        patcher = mock.patch.object(qr2clip, function_name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def fake_capture(self, fixture_name):
        """Stand-in for capture_selection: fixture_name=None simulates an empty capture."""
        def capture(capture_path):
            self.capture_paths.append(capture_path)
            if fixture_name is None:
                return False
            shutil.copyfile(FIXTURES_DIR / fixture_name, capture_path)
            return True
        return capture

    def assert_temp_file_removed(self):
        self.assertEqual(len(self.capture_paths), 1)
        self.assertFalse(os.path.exists(self.capture_paths[0]))

    def test_empty_capture_with_access_reports_cancelled(self):
        self.patch("capture_selection", side_effect=self.fake_capture(None))
        self.patch("has_screen_capture_access", return_value=True)
        self.assertEqual(qr2clip.scan_screen(), 1)
        self.notify.assert_called_once_with(qr2clip.MSG_CANCELLED)
        self.open_settings.assert_not_called()
        self.copy_to_clipboard.assert_not_called()
        self.assert_temp_file_removed()

    def test_empty_capture_without_access_reports_permission(self):
        self.patch("capture_selection", side_effect=self.fake_capture(None))
        self.patch("has_screen_capture_access", return_value=False)
        self.assertEqual(qr2clip.scan_screen(), 1)
        self.notify.assert_called_once_with(qr2clip.MSG_PERMISSION)
        self.open_settings.assert_called_once_with()
        self.copy_to_clipboard.assert_not_called()
        self.assert_temp_file_removed()

    def test_capture_without_qr_reports_not_found(self):
        self.patch("capture_selection", side_effect=self.fake_capture("no_qr.png"))
        self.assertEqual(qr2clip.scan_screen(), 1)
        self.notify.assert_called_once_with(qr2clip.MSG_NOT_FOUND)
        self.copy_to_clipboard.assert_not_called()
        self.assert_temp_file_removed()

    def test_successful_scan_copies_payload(self):
        self.patch("capture_selection", side_effect=self.fake_capture("qr_center_logo.jpg"))
        self.assertEqual(qr2clip.scan_screen(), 0)
        self.copy_to_clipboard.assert_called_once_with(CENTER_LOGO_QR_TEXT)
        self.notify.assert_called_once_with(
            qr2clip.MSG_COPIED.format(preview=CENTER_LOGO_QR_TEXT)
        )
        self.assert_temp_file_removed()

    def test_missing_decoder_reports_before_capturing(self):
        self.patch("decoder_available", return_value=False)
        capture = self.patch("capture_selection")
        self.assertEqual(qr2clip.scan_screen(), 1)
        self.notify.assert_called_once_with(qr2clip.MSG_MISSING_DECODER)
        capture.assert_not_called()

    def test_long_payload_preview_is_truncated(self):
        long_payload = "x" * (qr2clip.PREVIEW_LENGTH + 50)
        self.assertEqual(len(qr2clip.preview_of(long_payload)), qr2clip.PREVIEW_LENGTH + 1)
        self.assertTrue(qr2clip.preview_of(long_payload).endswith("…"))
        self.assertEqual(qr2clip.preview_of("short"), "short")


if __name__ == "__main__":
    unittest.main()
