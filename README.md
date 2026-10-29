# Cyber Defense Suite

A final-year cybersecurity project in Python with three modules and one web app:

| Module | What it does | Main techniques |
|---|---|---|
| **1. URL engine** | Scores a link as safe, suspicious or phishing, and explains why | 31 lexical features, Random Forest vs 3 other models + a character n-gram model, occlusion-based explanations |
| **2. Message engine** | Scores an email or SMS, scores every link inside it with Module 1, and reads QR codes | TF-IDF + Logistic Regression / Naive Bayes / calibrated SVM, link extraction, OpenCV QR decoding |
| **3. Cyber assistant** | A chatbot that answers cybersecurity questions using a local knowledge base and **Google Gemini** | Retrieval-augmented generation (TF-IDF retrieval), guardrails, tool calls into Modules 1 and 2, offline fallback |

Everything is analysed from **text only**: no link is ever opened or fetched, so checking a malicious address is safe.

## Quick start

```bash
# 1. create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate            # Windows PowerShell:  .venv\Scripts\Activate.ps1
# source .venv/bin/activate       # macOS / Linux

# 2. install
pip install -r requirements.txt
pip install -r requirements-optional.txt     # optional: QR code scanning

# 3. train the models and build the chatbot index (about a minute)
python manage.py setup

# 4. run
python run.py                     # open http://127.0.0.1:5000
```

If the models are missing or were built with a different scikit-learn version, `run.py` rebuilds them automatically.
`python manage.py check` tells you what is ready.

## Turn on the Gemini chatbot

The chatbot works without a key in **offline mode** (it answers from the local knowledge base). To use Gemini:

1. Create a free API key in Google AI Studio: https://aistudio.google.com/apikey
2. Copy `.env.example` to `.env` and paste the key: `GEMINI_API_KEY=your_key`
3. Restart `python run.py`. The chat page shows "Gemini connected".

Notes:
- The default model is `gemini-2.5-flash`. If Google renames or retires it you will see an "unavailable" notice in the chat; set `GEMINI_MODEL` in `.env` to a current model name.
- The key is read from the environment and sent in a request header. It is never put in a URL, logged or returned to the browser.
- When a key is set, chat questions are sent to Google's service. The page warns users not to type secrets.
- If Gemini fails (no network, quota, bad key) the chatbot falls back to offline mode instead of crashing.

## Run the tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

87 tests cover the three modules, the Gemini client (with mocked HTTP), guardrails, the REST API, validation, rate limiting and security headers.

## Project structure

```
cyber-defense-suite/
├── run.py                      development server
├── wsgi.py                     production entry point (gunicorn wsgi:app)
├── manage.py                   setup / train / check commands
├── bootstrap.py                auto-builds missing or outdated models
├── config.py  errors.py        settings and shared exceptions
├── module1_url_engine/         features, data generator, training, prediction, explanations
├── module2_message_engine/     text cleaning, link extractor, QR decoder, training, prediction
├── module3_chatbot/
│   ├── knowledge_base/         22 cybersecurity articles (Markdown)
│   ├── ingest.py  retriever.py build and search the TF-IDF index
│   ├── guardrails.py           blocks requests to build attacks
│   ├── gemini_client.py        Gemini REST client (standard library only)
│   ├── tools.py                lets the chatbot call Modules 1 and 2
│   └── chat_service.py         one chatbot turn, end to end
├── webapp/                     Flask app: API, pages, database, rate limiting
│   ├── templates/  static/     HTML, CSS, JavaScript (no inline scripts)
│   └── routes_api.py           REST API
├── models_store/               trained models (created by setup)
├── reports/                    metrics and charts (created by setup)
├── tests/                      pytest suite
└── docs/                       ARCHITECTURE.md, VIVA_NOTES.md
```

## REST API

| Method and path | Purpose |
|---|---|
| `POST /api/v1/check-url` | `{"url": "..."}` returns verdict, probability, reasons, explanation |
| `POST /api/v1/check-message` | `{"text": "..."}` returns verdict, per-link results, reasons, influential words |
| `POST /api/v1/check-qr` | multipart upload `image` returns the decoded QR content and its verdict |
| `POST /api/v1/chat` | `{"message": "...", "history": [...]}` returns reply, sources, tool cards |
| `POST /api/v1/feedback` | `{"kind": "chat", "rating": 1}` thumbs up or down |
| `GET /api/v1/stats` `/metrics` `/health` | usage statistics, model metrics, status |

## Use real data (do this before you submit)

The included datasets are **synthetic** so the project runs with no downloads, and their scores are not a measure of real-world accuracy. For final results:

```bash
# URLs: CSV with columns  url,label   (1 = phishing, 0 = legitimate)
python manage.py train-url --data path/to/real_urls.csv
# Messages: CSV with columns  text,label
python manage.py train-message --data path/to/real_messages.csv
```

Good sources: PhishTank or OpenPhish (phishing URLs), Tranco top sites (legitimate URLs), and public SMS/email spam or phishing datasets on Kaggle or the UCI repository. Report the new metrics and discuss why they are lower than the synthetic ones.

## Put it on GitHub and deploy it

```bash
git init
git add .
git commit -m "Cyber Defense Suite"
git branch -M main
git remote add origin https://github.com/<your-username>/cyber-defense-suite.git
git push -u origin main
```
`.gitignore` already keeps `.env` (your API key) out of the repository. **Never remove that line.**

On Render (New > Web Service > your repo):

| Setting | Value |
|---|---|
| Build command | `pip install -r requirements.txt && python manage.py setup` |
| Start command | `gunicorn wsgi:app` |
| Environment variables | `GEMINI_API_KEY` = your key, `TRUST_PROXY` = `1` |

Free instances sleep when idle, so open the site a couple of minutes before a demo. QR scanning needs `opencv-python-headless`; add it to `requirements.txt` if you want it online.

## Security and privacy design

- Links and messages are analysed as text and never fetched.
- Message text is **not stored**; the database keeps only a short hash, the verdict and the score.
- The web pages use a strict Content Security Policy, build all dynamic content with `textContent` (no HTML injection), and the server validates and size-limits every input.
- Per-visitor rate limits protect the Gemini quota.
- Guardrails refuse requests to build malware, phishing kits or break into other people's accounts, while still explaining how attacks work and how to defend.

## Limitations

- Detectors judge how a link or message looks, not the page behind it, so a clean-looking phishing link can slip through.
- Demo models are trained on synthetic data; accuracy on real traffic will be lower.
- Link shorteners are flagged because the destination is hidden, so some legitimate shortened links are marked risky.
- The chatbot's knowledge base is 22 short articles; Gemini fills the gaps, and Gemini can be wrong.

## Future scope

WHOIS and TLS features, a character-level neural network, a DistilBERT message model, a browser extension, embedding-based retrieval, streaming chat answers and a retraining job that learns from user feedback.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Model not found` or a 503 error | Run `python manage.py setup` |
| Chat says "Offline mode" | Add `GEMINI_API_KEY` to `.env` and restart |
| Chat says "AI model is unavailable (404...)" | Set `GEMINI_MODEL` in `.env` to a current model name |
| "QR scanning needs OpenCV" | `pip install opencv-python-headless` |
| "Address already in use" | Another copy is running; stop it with Ctrl+C or set `PORT=5001` |
