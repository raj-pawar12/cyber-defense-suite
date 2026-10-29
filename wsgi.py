"""Production entry point:  gunicorn wsgi:app"""
from bootstrap import ensure_artifacts
from webapp import create_app

ensure_artifacts(verbose=False)
app = create_app()
