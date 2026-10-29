"""Generate a labelled demo dataset of URLs (label 1 = phishing, 0 = legitimate).

IMPORTANT: this is *synthetic* data built from common real-world patterns so the
project runs end to end without downloads. For your final results, replace
module1_url_engine/data/urls.csv with a real dataset (PhishTank / OpenPhish / UCI / Kaggle) that has
the columns `url,label`, and re-run `python manage.py setup`.
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent

LEGIT_DOMAINS = [
    "google.com", "youtube.com", "wikipedia.org", "github.com", "stackoverflow.com",
    "amazon.in", "amazon.com", "microsoft.com", "apple.com", "linkedin.com",
    "facebook.com", "instagram.com", "twitter.com", "reddit.com", "netflix.com",
    "paypal.com", "dropbox.com", "medium.com", "bbc.co.uk", "nytimes.com",
    "theguardian.com", "cnn.com", "flipkart.com", "paytm.com", "irctc.co.in",
    "sbi.co.in", "hdfcbank.com", "icicibank.com", "zoom.us", "slack.com",
    "notion.so", "python.org", "djangoproject.com", "flask.palletsprojects.com",
    "scikit-learn.org", "kaggle.com", "coursera.org", "udemy.com", "nptel.ac.in",
    "mit.edu", "stanford.edu", "iitb.ac.in", "nasa.gov", "who.int",
    "timesofindia.indiatimes.com", "hotstar.com", "spotify.com", "adobe.com",
    "salesforce.com", "oracle.com", "ibm.com", "intel.com", "nvidia.com",
    "cloudflare.com", "aws.amazon.com", "azure.microsoft.com", "mozilla.org",
    "w3schools.com", "geeksforgeeks.org", "leetcode.com", "hackerrank.com",
    "naukri.com", "indeed.com", "glassdoor.com", "ted.com", "quora.com",
    "pinterest.com", "twitch.tv", "office.com", "outlook.com", "live.com",
    "yahoo.com", "bing.com", "duckduckgo.com", "imdb.com", "booking.com",
    "airbnb.com", "uber.com", "swiggy.com", "zomato.com", "myntra.com",
    "ebay.com", "walmart.com", "bestbuy.com", "espn.com", "weather.com",
]
LEGIT_SUBS = ["www", "www", "www", "m", "mail", "docs", "drive", "accounts", "login",
              "support", "help", "blog", "news", "shop", "api", "developer", "learn", ""]
LEGIT_PATH_WORDS = ["about", "contact", "products", "pricing", "docs", "blog", "careers",
                    "help", "news", "search", "watch", "wiki", "questions", "users",
                    "courses", "jobs", "store", "cart", "orders", "profile", "settings",
                    "signin", "login", "account", "support", "download", "features",
                    "privacy", "terms", "security", "payment", "billing"]
SLUG_WORDS = ["how", "to", "learn", "python", "in", "2026", "best", "guide", "for",
              "beginners", "data", "science", "machine", "learning", "career", "tips",
              "review", "top", "ten", "tools", "every", "developer", "should", "know",
              "interview", "questions", "project", "ideas", "cloud", "security"]

BRANDS = ["paypal", "google", "amazon", "microsoft", "apple", "facebook", "instagram",
          "netflix", "linkedin", "whatsapp", "dropbox", "flipkart", "paytm",
          "hdfcbank", "icicibank", "outlook"]
EVIL_WORDS = ["secure", "verify", "login", "account", "update", "support", "service",
              "online", "portal", "help", "center", "auth", "id", "alert", "billing",
              "access", "web", "mobile", "customer", "care", "confirm", "recovery"]
EVIL_TLDS = ["com", "net", "info", "online", "site", "xyz", "top", "tk", "ml", "click",
             "live", "co", "in", "cc", "ru", "work", "link", "icu", "cf", "ga"]
FREE_HOSTS = ["000webhostapp.com", "weebly.com", "blogspot.com", "wixsite.com",
              "github.io", "firebaseapp.com", "web.app", "netlify.app", "pages.dev",
              "glitch.me", "herokuapp.com"]
SHORTENERS = ["bit.ly", "tinyurl.com", "t.co", "ow.ly", "is.gd", "cutt.ly"]
PHISH_PATHS = ["/login.php", "/signin/verify", "/secure/update/account.php",
               "/wp-content/uploads/2024/05/index.html", "/confirm", "/account/recover",
               "/webscr", "/auth/session", "/verify-identity", "/login", "/update-billing.php",
               "/~user/signin.html", "/cgi-bin/login.pl", "/wp-includes/js/verify.php"]
CONSONANTS, VOWELS = "bcdfghklmnprstvz", "aeiou"
LEET_MAP = {"a": "4", "e": "3", "i": "1", "o": "0", "l": "1", "s": "5"}


def rnd_word(rng, syll=None) -> str:
    return "".join(rng.choice(CONSONANTS) + rng.choice(VOWELS) for _ in range(syll or rng.randint(2, 4)))


def rnd_token(rng, n) -> str:
    return "".join(rng.choice("abcdef0123456789") for _ in range(n))


def rnd_ip(rng) -> str:
    return ".".join(str(rng.randint(1, 254)) for _ in range(4))


def legit_url(rng) -> str:
    kind = rng.random()
    if kind < 0.18:  # unknown small site
        domain = f"{rnd_word(rng)}.{rng.choice(['com', 'org', 'in', 'net', 'io', 'co.in'])}"
        sub = rng.choice(["www", "www", ""])
    elif kind < 0.22:  # legit free-hosted portfolio
        domain = f"{rnd_word(rng)}-{rng.choice(['portfolio', 'blog', 'dev', 'notes'])}.{rng.choice(['github.io', 'netlify.app', 'pages.dev'])}"
        sub = ""
    elif kind < 0.26:
        return f"https://{rng.choice(SHORTENERS)}/{rnd_token(rng, rng.randint(6, 8))}"
    else:
        domain = rng.choice(LEGIT_DOMAINS)
        sub = rng.choice(LEGIT_SUBS)
        if domain.startswith("www.") or domain.count(".") >= 2 and sub == "www":
            sub = ""
    host = f"{sub}.{domain}" if sub else domain
    scheme = "http" if rng.random() < 0.10 else "https"
    r = rng.random()
    if r < 0.25:
        path = ""
    elif r < 0.55:
        path = "/" + "/".join(rng.choice(LEGIT_PATH_WORDS) for _ in range(rng.randint(1, 3)))
    elif r < 0.80:
        slug = "-".join(rng.choice(SLUG_WORDS) for _ in range(rng.randint(3, 8)))
        path = f"/{rng.randint(2019, 2026)}/{rng.randint(1, 12):02d}/{slug}" if rng.random() < 0.5 else f"/{slug}"
    else:
        path = f"/{rng.choice(LEGIT_PATH_WORDS)}/{rng.randint(1000, 99999999)}"
    q = rng.random()
    query = ""
    if q < 0.15:
        query = f"?q={rng.choice(SLUG_WORDS)}+{rng.choice(SLUG_WORDS)}"
    elif q < 0.25:
        query = f"?id={rng.randint(1, 99999)}&ref={rnd_word(rng, 2)}"
    elif q < 0.32:
        query = f"?v={rnd_token(rng, 11)}"
    elif q < 0.38:
        query = "?utm_source=newsletter&utm_medium=email&utm_campaign=" + rnd_word(rng, 3)
    return f"{scheme}://{host}{path}{query}"


def typosquat(rng, brand: str) -> str:
    choice = rng.random()
    chars = list(brand)
    idx = [i for i, ch in enumerate(chars) if ch in LEET_MAP]
    if choice < 0.6 and idx:
        i = rng.choice(idx)
        chars[i] = LEET_MAP[chars[i]]
    elif choice < 0.8 and len(chars) > 3:
        i = rng.randrange(1, len(chars) - 1)
        chars.insert(i, chars[i])  # doubled letter
    else:
        i = rng.randrange(1, len(chars) - 2)
        chars[i], chars[i + 1] = chars[i + 1], chars[i]  # swapped letters
    return "".join(chars)


def phishing_url(rng) -> str:
    brand = rng.choice(BRANDS)
    word = rng.choice(EVIL_WORDS)
    tld = rng.choice(EVIL_TLDS)
    path = rng.choice(PHISH_PATHS)
    kind = rng.choices(range(11), weights=[14, 14, 12, 10, 6, 9, 9, 10, 6, 5, 5])[0]
    if kind == 0:
        host = f"{brand}.{word}-{rng.choice(EVIL_WORDS)}.{tld}"
    elif kind == 1:
        host = rng.choice([f"{brand}-{word}.{tld}", f"{word}-{brand}.{tld}", f"{brand}{word}.{tld}"])
    elif kind == 2:
        host = f"{typosquat(rng, brand)}{rng.choice(['', '-' + word, '-support'])}.{rng.choice(['com', 'net', tld])}"
    elif kind == 3:
        host = rnd_ip(rng) + rng.choice(["", ":8080", ":8443", ":81"])
        path = rng.choice(["/" + brand + path, path, f"/{brand}/{word}" + path])
    elif kind == 4:
        legit = rng.choice(LEGIT_DOMAINS)
        host = f"www.{legit}@{rnd_word(rng)}-{word}.{tld}"
    elif kind == 5:
        host = f"{brand}-{word}.{rng.choice(FREE_HOSTS)}"
    elif kind == 6:
        host = "-".join(rng.sample(EVIL_WORDS, rng.randint(3, 5))) + f".{tld}"
    elif kind == 7:  # plain-looking, harder to catch
        host = f"{rnd_word(rng)}.{rng.choice(['com', 'net', 'org', 'info'])}"
        path = rng.choice(["/login", "/verify", "/account", "/signin", "/secure", path])
    elif kind == 8:  # brand hidden in the path
        host = f"{rnd_word(rng)}-{rnd_word(rng, 2)}.{tld}"
        path = f"/www.{brand}.com{rng.choice(['/signin', '/login', '/secure'])}"
    elif kind == 9:  # punycode / encoded path
        host = f"xn--{typosquat(rng, brand)}-{rnd_token(rng, 3)}.{rng.choice(['com', tld])}"
        path = "/" + "%2F".join(rng.sample(EVIL_WORDS, 2)) + "%3Fsession%3D" + rnd_token(rng, 8)
    else:  # shortener hiding the destination
        return f"{rng.choice(['http', 'https'])}://{rng.choice(SHORTENERS)}/{rnd_token(rng, rng.randint(6, 8))}"
    scheme = "https" if rng.random() < 0.55 else "http"
    query = rng.choice(["", "", "", f"?session={rnd_token(rng, 16)}", f"?email=user{rng.randint(1, 999)}%40mail.com",
                        f"?id={rng.randint(10000, 9999999)}&token={rnd_token(rng, 12)}"])
    return f"{scheme}://{host}{path}{query}"


def build_dataset(n_per_class: int, seed: int) -> list[tuple[str, int]]:
    rng = random.Random(seed)
    rows: set[tuple[str, int]] = set()
    while sum(1 for _, l in rows if l == 0) < n_per_class:
        rows.add((legit_url(rng), 0))
    while sum(1 for _, l in rows if l == 1) < n_per_class:
        rows.add((phishing_url(rng), 1))
    data = sorted(rows)
    rng.shuffle(data)
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=6000, help="URLs per class")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "urls.csv")
    args = ap.parse_args()
    data = build_dataset(args.n, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url", "label"])
        w.writerows(data)
    print(f"Wrote {len(data)} rows to {args.out}")


if __name__ == "__main__":
    main()
