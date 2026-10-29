"""Command line helper.

    python manage.py setup        generate data, train both models, build the chatbot index
    python manage.py train-url    retrain Module 1 only      (--data file.csv for real data)
    python manage.py train-message
    python manage.py build-kb     rebuild the chatbot knowledge-base index
    python manage.py check        verify that everything is ready
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_setup(_args) -> int:
    from module1_url_engine import generate_data as g1
    from module2_message_engine import generate_data as g2
    from module1_url_engine.train import DEFAULT_DATA as d1, run_training as t1
    from module2_message_engine.train import DEFAULT_DATA as d2, run_training as t2
    from module3_chatbot.ingest import build_index
    import csv

    for path, header, rows in ((d1, ["url", "label"], g1.build_dataset(6000, 42)), (d2, ["text", "label"], g2.build_dataset(3000, 42))):
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(rows)
            print("Created", path)
    t1(d1)
    t2(d2)
    print("[chatbot]", build_index())
    print("\nAll set. Start the app with: python run.py")
    return 0


def cmd_train_url(args) -> int:
    from module1_url_engine.train import run_training
    run_training(args.data)
    return 0


def cmd_train_message(args) -> int:
    from module2_message_engine.train import run_training
    run_training(args.data)
    return 0


def cmd_build_kb(_args) -> int:
    from module3_chatbot.ingest import build_index
    print(build_index())
    return 0


def cmd_check(_args) -> int:
    from config import gemini_api_key, load_dotenv_file
    from webapp.services import Services
    load_dotenv_file()
    status = Services().status()
    for name, ok in status.items():
        print("%-16s %s" % (name, "ready" if ok else "MISSING - run: python manage.py setup"))
    print("%-16s %s" % ("gemini", "key found" if gemini_api_key() else "no key (chatbot runs in offline mode)"))
    return 0 if all(status.values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("setup").set_defaults(func=cmd_setup)
    for name, func in (("train-url", cmd_train_url), ("train-message", cmd_train_message)):
        p = sub.add_parser(name)
        p.add_argument("--data", type=Path, default=None)
        p.set_defaults(func=func)
    sub.add_parser("build-kb").set_defaults(func=cmd_build_kb)
    sub.add_parser("check").set_defaults(func=cmd_check)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
