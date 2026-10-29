"""Simple, transparent safety checks run before any question reaches the model."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .prompts import REFUSAL_REPLY

_BUILD = r"(?:write|create|build|make|generate|code|develop|program)"
_THING = (r"(?:ransomware|malware|virus|trojan|keylogger|spyware|botnet|rootkit|worm|stealer|"
          r"ddos\s+(?:tool|script|bot)|exploit\s+kit|phishing\s+(?:kit|page|site|website|template)|"
          r"fake\s+(?:login|bank)\s+(?:page|site))")
_INTENT = r"(?:how\s+(?:can|do|to)\s+i|help\s+me|teach\s+me|i\s+want\s+to|i\s+need\s+to|show\s+me\s+how\s+to|tell\s+me\s+how\s+to)"
_TARGET = r"(?:account|instagram|facebook|whatsapp|gmail|email|phone|wi-?fi|password|snapchat)"

BLOCK_PATTERNS = [
    re.compile(r"\b%s\b.{0,40}\b%s\b" % (_BUILD, _THING), re.I | re.S),
    re.compile(r"\b%s\b.{0,25}\b(?:hack|break\s+into|spy\s+on|track|crack|get\s+into)\b.{0,40}\b%s\b" % (_INTENT, _TARGET), re.I | re.S),
    re.compile(r"\b(?:steal|harvest|grab|dump)\b.{0,25}\b(?:passwords?|credentials|cookies|otps?|cards?)\b", re.I | re.S),
    re.compile(r"\b%s\b.{0,25}\b(?:bypass|defeat)\b.{0,25}\b(?:otp|2fa|mfa|two[- ]factor)\b" % _INTENT, re.I | re.S),
]
_EDUCATIONAL = re.compile(r"\b(report|essay|summary|summari[sz]e|notes|article|awareness|assignment|presentation|ppt|abstract|"
                          r"definition|what\s+is|explain|how\s+does)\b", re.I)
_CODE = re.compile(r"\b(code|script|source|payload|program|python|java|c\+\+|powershell|step[- ]by[- ]step|working)\b", re.I)

CYBER_WORDS = {
    "phishing", "password", "passwords", "malware", "ransomware", "virus", "hack", "hacker", "hacked", "security", "cyber",
    "cybersecurity", "firewall", "vpn", "encryption", "encrypt", "mfa", "2fa", "otp", "scam", "fraud", "privacy", "breach",
    "attack", "attacks", "vulnerability", "exploit", "injection", "xss", "sql", "owasp", "network", "wifi", "wi-fi", "router",
    "https", "ssl", "tls", "certificate", "antivirus", "backup", "backups", "spyware", "trojan", "botnet", "ddos", "spam",
    "upi", "kyc", "link", "url", "email", "sms", "qr", "threat", "risk", "incident", "forensics", "authentication", "hash",
    "cryptography", "social", "engineering", "deepfake", "secure", "safe", "safety", "pentest", "ctf", "cert", "certification",
}


@dataclass
class GuardResult:
    allowed: bool
    refusal: str = ""


def check_message(text: str) -> GuardResult:
    """Block requests to build attack tools or break into other people's accounts."""
    text = text or ""
    for pattern in BLOCK_PATTERNS:
        if pattern.search(text):
            if _EDUCATIONAL.search(text) and not _CODE.search(text):
                continue
            return GuardResult(False, REFUSAL_REPLY)
    return GuardResult(True)


def looks_cyber_related(text: str) -> bool:
    words = set(re.findall(r"[a-z0-9+-]+", (text or "").lower()))
    return bool(words & CYBER_WORDS)
