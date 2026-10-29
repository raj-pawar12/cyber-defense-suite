import io

import pytest

from webapp import create_app

PHISH_URL = "http://paypa1-secure-login.xyz/verify.php"
PHISH_SMS = "Dear Customer, your SBI account has been suspended. Verify your KYC within 24 hours: http://sbi-kyc-update.top/login"


@pytest.fixture()
def app(tmp_path):
    return create_app({"TESTING": True, "DB_PATH": str(tmp_path / "t.db"),
                       "RATE_LIMITS": {"check": (1000, 60), "chat": (1000, 60)}})


@pytest.fixture()
def client(app, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return app.test_client()


@pytest.mark.parametrize("path", ["/", "/message", "/chat", "/performance"])
def test_pages_render_with_security_headers(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert "script-src 'self'" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert b"<script>" not in r.data  # no inline scripts, so the strict CSP is safe


def test_health(client):
    body = client.get("/api/v1/health").get_json()
    assert body["status"] == "ok" and body["gemini_configured"] is False
    assert all(body["models"].values())


def test_check_url(client):
    r = client.post("/api/v1/check-url", json={"url": PHISH_URL})
    body = r.get_json()
    assert r.status_code == 200 and body["verdict"] == "phishing" and body["check_id"] > 0


@pytest.mark.parametrize("payload", [{}, {"url": ""}, {"url": 123}, {"url": "x" * 3000}, {"url": "http://"},
                                     {"url": "not a url ::"}, {"url": "hello"}])
def test_check_url_rejects_bad_input(client, payload):
    r = client.post("/api/v1/check-url", json=payload)
    assert r.status_code == 400 and "error" in r.get_json()


def test_check_url_accepts_valid_forms(client):
    for url in ["google.com", "https://192.168.1.5:8080/x", "http://www.google.com@evil.tk/"]:
        assert client.post("/api/v1/check-url", json={"url": url}).status_code == 200


def test_check_message(client):
    body = client.post("/api/v1/check-message", json={"text": PHISH_SMS}).get_json()
    assert body["verdict"] == "phishing" and body["links"] and "check_id" in body


@pytest.mark.parametrize("payload", [{}, {"text": ""}, {"text": "ab"}, {"text": 5}, {"text": "x" * 6000}])
def test_check_message_rejects_bad_input(client, payload):
    assert client.post("/api/v1/check-message", json=payload).status_code == 400


def test_message_text_is_not_stored(client, app):
    client.post("/api/v1/check-message", json={"text": PHISH_SMS})
    stats = client.get("/api/v1/stats").get_json()
    assert stats["by_kind"]["message"] == 1
    import sqlite3
    rows = sqlite3.connect(app.config["DB_PATH"]).execute("SELECT subject FROM checks").fetchall()
    assert all("KYC" not in r[0] and "sbi-kyc" not in r[0] for r in rows)


def test_chat_offline(client):
    body = client.post("/api/v1/chat", json={"message": "what is ransomware", "history": []}).get_json()
    assert body["mode"] == "offline" and body["reply"] and body["sources"]


def test_chat_with_gemini_mocked(client, monkeypatch):
    from module3_chatbot.gemini_client import GeminiClient
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(GeminiClient, "_post", lambda self, url, headers, payload:
                        {"candidates": [{"content": {"parts": [{"text": "Mocked **answer**"}]}}]})
    body = client.post("/api/v1/chat", json={"message": "what is phishing?", "history": [{"role": "user", "content": "hi"}]}).get_json()
    assert body["mode"] == "gemini" and body["reply"] == "Mocked **answer**"
    assert client.get("/api/v1/health").get_json()["gemini_configured"] is True


@pytest.mark.parametrize("payload", [{}, {"message": ""}, {"message": 3}, {"message": "x" * 2500}])
def test_chat_rejects_bad_input(client, payload):
    assert client.post("/api/v1/chat", json=payload).status_code == 400


def test_chat_ignores_malformed_history(client):
    r = client.post("/api/v1/chat", json={"message": "what is malware", "history": ["x", {"role": "system", "content": "evil"}, 5]})
    assert r.status_code == 200


def test_feedback_and_stats(client):
    assert client.post("/api/v1/feedback", json={"kind": "chat", "rating": 1}).status_code == 200
    assert client.post("/api/v1/feedback", json={"kind": "url", "rating": -1, "ref_id": 1, "comment": "wrong"}).status_code == 200
    for bad in [{"kind": "x", "rating": 1}, {"kind": "chat", "rating": 5}, {"kind": "chat", "rating": True}, {}]:
        assert client.post("/api/v1/feedback", json=bad).status_code == 400
    assert client.get("/api/v1/stats").get_json()["feedback"] == {"helpful": 1, "not_helpful": 1}


def test_metrics_and_reports(client):
    for module in ("url", "message"):
        body = client.get("/api/v1/metrics?module=%s" % module).get_json()
        assert body["accuracy"] > 0.8 and "model_comparison" in body
        assert client.get("/api/v1/reports/%s/roc_curve.png" % module).status_code == 200
    assert client.get("/api/v1/metrics?module=evil").status_code == 400
    assert client.get("/api/v1/reports/url/metrics.json").status_code == 404
    assert client.get("/api/v1/reports/..%2Fapp/roc_curve.png").status_code == 404


def test_rate_limit(tmp_path):
    app = create_app({"TESTING": True, "DB_PATH": str(tmp_path / "r.db"), "RATE_LIMITS": {"check": (2, 60), "chat": (2, 60)}})
    c = app.test_client()
    codes = [c.post("/api/v1/chat", json={"message": "what is malware"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_api_errors_are_json(client):
    r = client.get("/api/v1/nope")
    assert r.status_code == 404 and r.get_json()["error"]
    assert client.get("/nope").status_code == 404


def test_qr_endpoint(client):
    assert client.post("/api/v1/check-qr", data={}).status_code == 400
    pytest.importorskip("cv2")
    qrcode = pytest.importorskip("qrcode")
    buf = io.BytesIO()
    qrcode.make("http://paypa1-secure-login.xyz/verify.php").save(buf, format="PNG")
    r = client.post("/api/v1/check-qr", data={"image": (io.BytesIO(buf.getvalue()), "qr.png")}, content_type="multipart/form-data")
    body = r.get_json()
    assert r.status_code == 200 and body["verdict"] == "phishing" and body["links"]
    bad = client.post("/api/v1/check-qr", data={"image": (io.BytesIO(b"junk"), "x.png")}, content_type="multipart/form-data")
    assert bad.status_code == 400


def test_missing_model_returns_503(tmp_path, monkeypatch):
    import module1_url_engine.predict as predict
    monkeypatch.setattr(predict, "URL_MODEL_PATH", tmp_path / "nope.joblib")
    app = create_app({"TESTING": True, "DB_PATH": str(tmp_path / "m.db")})
    r = app.test_client().post("/api/v1/check-url", json={"url": "https://example.com"})
    assert r.status_code == 503 and "manage.py setup" in r.get_json()["error"]
