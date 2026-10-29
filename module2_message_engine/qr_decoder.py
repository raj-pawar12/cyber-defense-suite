"""Decode a QR code from an uploaded image. Needs the optional opencv-python-headless package."""
from __future__ import annotations


class QRUnavailable(RuntimeError):
    """OpenCV is not installed."""


def decode_qr(image_bytes: bytes) -> list:
    """Return the text stored in the QR code (empty list if none was found)."""
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise QRUnavailable("QR scanning needs OpenCV. Run: pip install opencv-python-headless") from exc
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("That file is not a readable image.")
    detector = cv2.QRCodeDetector()
    data, _points, _ = detector.detectAndDecode(image)
    return [data] if data else []
