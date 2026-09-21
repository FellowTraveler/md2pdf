"""Regenerates the synthetic test fixtures. Run with ~/.md2pdf-venv/bin/python3.

qr_center_logo.jpg is NOT generated — it is a real-world branded QR poster.
"""
from pathlib import Path

import zxingcpp
from PIL import Image

FIXTURES_DIR = Path(__file__).parent
PLAIN_QR_TEXT = "https://example.com/qr2clip-plain-fixture"
PLAIN_QR_SCALE = 8
BLANK_SIZE = (400, 400)


def make_plain_qr():
    barcode = zxingcpp.create_barcode(PLAIN_QR_TEXT, zxingcpp.BarcodeFormat.QRCode)
    pixels = memoryview(zxingcpp.write_barcode_to_image(barcode, scale=PLAIN_QR_SCALE))
    height, width = pixels.shape
    Image.frombuffer("L", (width, height), pixels.tobytes()).save(FIXTURES_DIR / "qr_plain.png")


def make_blank():
    Image.new("RGB", BLANK_SIZE, "white").save(FIXTURES_DIR / "no_qr.png")


if __name__ == "__main__":
    make_plain_qr()
    make_blank()
