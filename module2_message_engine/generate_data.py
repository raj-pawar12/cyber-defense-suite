"""Generate a synthetic labelled dataset of e-mails and SMS (label 1 = phishing, 0 = legitimate).

The data is synthetic so the project runs without downloads. For final results replace
module2_message_engine/data/messages.csv with a real dataset (columns: text,label) and retrain.
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = ["Rahul", "Priya", "Amit", "Sneha", "Vikram", "Anjali", "Rohan", "Neha", "Karan", "Pooja"]
BRANDS = ["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Paytm", "PhonePe", "Amazon", "Flipkart", "Netflix",
          "Microsoft", "PayPal", "Google"]
WORDS = ["secure", "verify", "login", "update", "account", "kyc", "support", "alert", "rewards", "care"]
TLDS = ["xyz", "top", "tk", "ml", "click", "online", "site", "info", "live", "cc", "icu"]
GOOD_LINKS = ["https://www.amazon.in/gp/your-orders", "https://github.com/notifications", "https://meet.google.com/abc-defg-hij",
              "https://www.irctc.co.in", "https://www.flipkart.com/account/orders", "https://docs.google.com/document/d/1",
              "https://www.sbi.co.in", "https://www.hdfcbank.com", "https://zoom.us/j/123456789", "https://www.linkedin.com/jobs"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MONTHS = ["January", "March", "June", "August", "October", "December"]
TEAMS = ["project review", "placement briefing", "lab session", "team stand-up", "viva rehearsal", "design discussion"]

PHISH = [
    "Dear Customer, your {brand} account has been suspended. Verify your KYC within {hours} hours to avoid permanent closure: {link}",
    "URGENT: Unusual login detected on your {brand} account. Confirm your identity now: {link}",
    "Congratulations {name}! You have won Rs {amount} in the {brand} lucky draw. Claim your prize here: {link}",
    "Your {brand} package could not be delivered. Pay a small fee of Rs {small} to reschedule: {link}",
    "Your {brand} card ending {last4} is blocked. Update your PAN and card details immediately: {link}",
    "Income tax refund of Rs {amount} is pending for you. Submit your bank details to receive it: {link}",
    "Hello {name}, we noticed a new sign-in to your {brand} account. If this was not you, review activity: {link}",
    "Your password expires today. Click here to keep your {brand} password and avoid losing access: {link}",
    "Final notice: your {brand} service will be terminated. Share the OTP sent to your phone to continue.",
    "Dear user, a payment of Rs {amount} is pending. Send your UPI PIN to receive the refund.",
    "Job offer from {brand}: work from home and earn Rs {amount} daily. Pay Rs {small} registration fee: {link}",
    "{brand} security alert: your account will be deactivated. Log in and verify your details here {link}",
    "Invoice #{last4} attached. Open the attached file and enable content to view the payment details.",
    "You have received Rs {amount} cashback. Accept now before it expires: {link}",
    "Dear customer, your electricity will be disconnected tonight. Call this number and pay the pending bill: {link}",
    "Hi {name}, your {brand} subscription payment failed. Update your payment method to avoid cancellation: {link}",
    "Official notice from {brand}: confirm your account within {hours} hours or it will be frozen. {link}",
    "We have detected a virus on your device. Download the security tool now: {link}",
    "Your SIM will be blocked in 24 hours. Complete re-verification with your Aadhaar and OTP: {link}",
    "Hi {name}, I am in urgent need of gift cards. Please buy them and send the codes. I will refund you later.",
    "Exclusive offer! Claim your free {brand} gift voucher worth Rs {amount}. Limited time: {link}",
    "Action required: your {brand} wallet KYC is incomplete. Complete it now to avoid restrictions {link}",
    "Hi {name}, the document you requested is ready. View it here: {link}",
    "{brand}: a new message is waiting for you. Open: {link}",
    "Hello {name}, please see the updated schedule for {day}: {link}",
    "Your {brand} order #{last4} has been placed. If this was not you, cancel it here: {link}",
    "Hi {name}, you have been tagged in a photo. See it here: {link}",
    "Reminder: your {brand} password was used on a new device. Review and secure it: {link}",
]
LEGIT = [
    "Hi {name}, reminder: {team} on {day} at {hour} PM. Agenda is attached in the calendar invite.",
    "Your {brand} order #{last4} has shipped and will arrive on {day}. Track it here: {goodlink}",
    "{otp} is your OTP for {brand}. It is valid for 10 minutes. Do not share it with anyone.",
    "Rs {amount} debited from A/c XX{last4} on {day}. If you did not make this transaction please call the number on the back of your card.",
    "Hello {name}, your statement for {month} is ready. You can view it by logging in to the official {brand} app.",
    "Thanks for your payment of Rs {amount}. Your receipt number is {last4}. No further action is needed.",
    "Hi {name}, can you share the notes from today's lecture? I missed the last part.",
    "Urgent: please submit the assignment before 5 PM today. Late submissions will not be accepted.",
    "Your interview for the software engineer role is scheduled for {day} at {hour} AM. Join here: {goodlink}",
    "Team update: the build is green and the demo is ready. See you at the {team} on {day}.",
    "Weekly newsletter: five new articles on Python and machine learning. Unsubscribe anytime from your settings.",
    "Your support ticket #{last4} has been resolved. Reply to this email if you need more help.",
    "Hey {name}, dinner at 8 tonight? Let me know and I will book a table.",
    "Your library book is due on {day}. Please return or renew it online: {goodlink}",
    "Security tip from {brand}: never share your PIN or password with anyone, including our staff.",
    "Hi {name}, the {team} has moved to {day}. Please update your calendar.",
    "Your {brand} subscription renews on {day} for Rs {amount}. Manage your plan in the app settings.",
    "College notice: exams begin on {day}. Hall tickets are available on the official portal {goodlink}",
    "Your cab is arriving in {hour} minutes. Driver details are in the app.",
    "Dear customer, your {brand} account statement for {month} is attached for your records. Regards, Customer Care.",
    "Congratulations {name}! You have been shortlisted for the next round. Please bring your ID card on {day}.",
    "Reminder: your electricity bill of Rs {amount} is due on {day}. Pay through your official provider app.",
    "Hi {name}, here are the minutes of the {team}. Please review the action items before {day}.",
    "Your parcel has been delivered to the reception. Collect it with your ID.",
    "Alert: your library account is suspended until you return the overdue books. Visit the library desk.",
    "Your {brand} account has been created. Verify your email address using the code {otp} in the app.",
    "URGENT: server maintenance tonight at {hour} PM. Please save your work before then.",
    "Congratulations {name}, you won the quiz competition! Collect your certificate from the office on {day}.",
    "Final notice: the semester fee is due on {day}. Pay through the official college portal {goodlink}",
    "Dear customer, your cheque book request has been processed. It will reach your registered address in 5 days.",
    "Your password was changed successfully. If this was not you, contact support through the official {brand} app.",
    "Hi {name}, I will send the files by {day}. Let me know if the link {goodlink} does not open.",
    "Reminder from {brand}: update your app to the latest version for new features.",
]
GREETINGS = ["", "", "Hi,\n", "Hello,\n", "Dear {name},\n"]
CLOSERS = ["", "", "\nRegards,\n{name}", "\nThanks", "\nSent from my iPhone", "\nPlease do not reply to this message."]


def bad_link(rng: random.Random, brand: str) -> str:
    slug = brand.lower().replace(" ", "")
    w1, w2, tld = rng.choice(WORDS), rng.choice(WORDS), rng.choice(TLDS)
    r = rng.random()
    if r < 0.30:
        return "http://%s-%s.%s/%s" % (slug, w1, tld, w2)
    if r < 0.50:
        return "https://%s-%s.%s/login.php?id=%d" % (w1, slug, tld, rng.randint(1000, 99999))
    if r < 0.65:
        return "http://%s/%s/verify" % (".".join(str(rng.randint(1, 254)) for _ in range(4)), slug)
    if r < 0.80:
        return "https://bit.ly/%s" % "".join(rng.choice("abcdef0123456789") for _ in range(7))
    return "https://%s.%s-%s.%s" % (slug, w1, w2, tld)


def make_message(rng: random.Random, phishing: bool) -> str:
    brand = rng.choice(BRANDS)
    values = {
        "brand": brand, "name": rng.choice(NAMES), "hours": rng.choice([2, 6, 12, 24, 48]),
        "amount": rng.choice([500, 1250, 4999, 25000, 100000]), "small": rng.choice([10, 49, 99, 199]),
        "last4": rng.randint(1000, 9999), "otp": rng.randint(100000, 999999), "day": rng.choice(DAYS),
        "month": rng.choice(MONTHS), "hour": rng.randint(1, 11), "team": rng.choice(TEAMS),
        "link": bad_link(rng, brand), "goodlink": rng.choice(GOOD_LINKS),
    }
    body = rng.choice(PHISH if phishing else LEGIT).format(**values)
    text = rng.choice(GREETINGS).format(**values) + body + rng.choice(CLOSERS).format(**values)
    if rng.random() < 0.5:  # word dropout makes messages less uniform
        words = text.split(" ")
        text = " ".join(w for w in words if rng.random() < 0.88) or text
    if rng.random() < 0.08:
        text = text.upper()
    if rng.random() < 0.10 and len(text) > 20:  # small typo noise
        i = rng.randrange(5, len(text) - 5)
        text = text[:i] + text[i + 1] + text[i] + text[i + 2:]
    return text


def build_dataset(n_per_class: int, seed: int, noise: float = 0.03) -> list:
    rng = random.Random(seed)
    rows = set()
    for label in (0, 1):
        count = 0
        while count < n_per_class:
            msg = make_message(rng, bool(label))
            if (msg, label) not in rows:
                rows.add((msg, label))
                count += 1
    data = sorted(rows)
    rng.shuffle(data)
    # annotation noise: a few labels are wrong, as in real data
    return [(t, 1 - l if rng.random() < noise else l) for t, l in data]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=3000, help="messages per class")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--noise", type=float, default=0.03, help="share of labels to flip")
    ap.add_argument("--out", type=Path, default=HERE / "data" / "messages.csv")
    args = ap.parse_args()
    data = build_dataset(args.n, args.seed, args.noise)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        writer.writerows(data)
    print("Wrote %d messages to %s" % (len(data), args.out))


if __name__ == "__main__":
    main()
