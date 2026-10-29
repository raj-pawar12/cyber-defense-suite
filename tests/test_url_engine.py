import csv

import pytest

from module1_url_engine.features import FEATURE_NAMES, extract_features, normalize_url, split_url
from module1_url_engine.generate_data import build_dataset
from module1_url_engine.predict import URLDetector
from module1_url_engine.train import run_training


@pytest.fixture(scope="module")
def detector():
    return URLDetector()


def test_feature_vector_is_fixed_length():
    assert len(FEATURE_NAMES) == 31
    assert set(extract_features("https://example.com")) == set(FEATURE_NAMES)


def test_basic_features():
    assert extract_features("http://192.168.1.5/login")["has_ip_host"] == 1
    assert extract_features("https://www.google.com@evil.tk/")["has_at"] == 1
    assert extract_features("https://paypal.secure-update.xyz/")["brand_mismatch"] == 1
    assert extract_features("https://www.paypal.com/signin")["brand_mismatch"] == 0
    assert extract_features("https://www.google.com@evil.tk/")["brand_mismatch"] == 1


def test_normalize_and_split():
    assert normalize_url("example.com/x") == ("https://example.com/x", True)
    assert split_url("https://www.google.com@evil.tk/x")["domain"] == "evil.tk"
    assert split_url("https://news.bbc.co.uk/a")["domain"] == "bbc.co.uk"


@pytest.mark.parametrize("url", ["https://www.wikipedia.org/wiki/Phishing", "https://github.com/pallets/flask",
                                 "https://www.amazon.in/gp/cart", "https://accounts.google.com/signin"])
def test_legitimate_links(detector, url):
    assert detector.analyze(url)["verdict"] == "legitimate"


@pytest.mark.parametrize("url", ["http://paypa1-secure-login.xyz/verify/account.php?session=9f3a1c",
                                 "http://192.168.44.12:8080/amazon/signin.php",
                                 "https://netflix.verify-account-billing.top/login.php",
                                 "https://paypal.com.secure-update.xyz/webscr"])
def test_phishing_links(detector, url):
    result = detector.analyze(url)
    assert result["verdict"] == "phishing"
    assert result["reasons"]


def test_result_shape_and_contributions(detector):
    r = detector.analyze("https://www.google.com@login-update.tk/")
    assert {"url", "verdict", "phishing_probability", "parts", "reasons", "contributions", "model"} <= set(r)
    assert 0.0 <= r["phishing_probability"] <= 1.0
    for item in r["contributions"]:
        assert {"label", "effect", "direction"} <= set(item)
    assert "contributions" not in detector.analyze("https://example.com", explain=False)


def test_training_pipeline_on_small_data(tmp_path):
    data = tmp_path / "urls.csv"
    with open(data, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "label"])
        writer.writerows(build_dataset(250, 1))
    metrics = run_training(data, tmp_path / "m.joblib", tmp_path / "reports", verbose=False)
    assert metrics["accuracy"] > 0.85
    assert (tmp_path / "m.joblib").exists() and (tmp_path / "reports" / "metrics.json").exists()
    assert URLDetector(tmp_path / "m.joblib").analyze("http://192.168.1.1/login")["verdict"] != "legitimate"
