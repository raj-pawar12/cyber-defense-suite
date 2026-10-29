import csv

import pytest

from module1_url_engine.predict import URLDetector
from module2_message_engine.generate_data import build_dataset
from module2_message_engine.link_extractor import extract_links
from module2_message_engine.preprocessing import clean_text
from module2_message_engine.predict import MessageDetector
from module2_message_engine.qr_decoder import decode_qr
from module2_message_engine.train import run_training

PHISH = "Dear Customer, your SBI account has been suspended. Verify your KYC within 24 hours: http://sbi-kyc-update.top/login"
OTP = "123456 is your OTP for HDFC Bank. It is valid for 10 minutes. Do not share it with anyone."
MEETING = "Hi Rahul, reminder: project review on Monday at 4 PM. Agenda in the invite."


@pytest.fixture(scope="module")
def detector():
    return MessageDetector()


def test_clean_text_masks_links_and_numbers():
    cleaned = clean_text("Visit https://evil.top/a now! OTP 123456, mail me@x.com")
    assert "urltoken" in cleaned and "numtoken" in cleaned and "emailtoken" in cleaned


def test_extract_links():
    links = extract_links("mail name@example.com or visit example.com/path, https://a.b/c). and bit.ly/xyz")
    assert "https://a.b/c" in links and "bit.ly/xyz" in links and "example.com/path" in links
    assert not any("name@" in l for l in links)
    assert extract_links("no links here") == []
    assert len(extract_links(" ".join("http://a%d.com" % i for i in range(30)), limit=5)) == 5


def test_phishing_text_is_flagged(detector):
    r = detector.analyze(PHISH, URLDetector())
    assert r["verdict"] == "phishing"
    assert r["links"] and r["reasons"] and r["influential_words"]
    assert r["phishing_probability"] >= max(r["text_probability"], r["worst_link_probability"]) - 1e-6


@pytest.mark.parametrize("text", [OTP, MEETING])
def test_legitimate_text(detector, text):
    assert detector.analyze(text, URLDetector())["verdict"] == "legitimate"


def test_works_without_url_detector(detector):
    r = detector.analyze(PHISH, None)
    assert r["links"][0]["analysis"] is None


def test_training_on_small_data(tmp_path):
    data = tmp_path / "m.csv"
    with open(data, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        writer.writerows(build_dataset(200, 1, 0.0))
    metrics = run_training(data, tmp_path / "msg.joblib", tmp_path / "reports", verbose=False)
    assert metrics["accuracy"] > 0.85
    assert MessageDetector(tmp_path / "msg.joblib").analyze(PHISH)["verdict"] != "legitimate"


def test_qr_decode_roundtrip():
    qrcode = pytest.importorskip("qrcode")
    pytest.importorskip("cv2")
    import io
    image = qrcode.make("https://example.com/hello")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    assert decode_qr(buffer.getvalue()) == ["https://example.com/hello"]


def test_qr_rejects_non_image():
    pytest.importorskip("cv2")
    with pytest.raises(ValueError):
        decode_qr(b"this is not an image")
