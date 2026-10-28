"""Vercel entry point: Vercel looks for a WSGI object called `app`."""
from flyway import create_app

app = create_app()
