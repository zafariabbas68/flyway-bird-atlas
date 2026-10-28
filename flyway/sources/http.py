"""Tiny HTTP helper (standard library only) with retries and a clear error."""
from __future__ import annotations

import ssl
import time
import urllib.error
import urllib.request

UA = "Flyway/1.0 (educational bird migration atlas; polite client)"


def _context():
    try:  # certifi fixes missing CA certificates on some Python installs
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        return ssl.create_default_context()


def http_get(url: str, timeout: float = 90, retries: int = 6, backoff: float = 1.8) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout, context=_context()) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (400, 401, 403, 404):  # retrying will not help
                raise RuntimeError(f"HTTP {exc.code} for {url[:160]}") from exc
            last = exc
            if exc.code == 429:  # rate limited: wait as long as the server asks, at least 5 s, growing each time
                try:
                    wait = float(exc.headers.get("Retry-After", 0))
                except (TypeError, ValueError):
                    wait = 0.0
                time.sleep(max(wait, 5.0 * (attempt + 1)))
                continue
        except Exception as exc:  # noqa: BLE001
            last = exc
        time.sleep(backoff ** attempt)
    raise RuntimeError(
        f"Could not reach {url[:120]} after {retries} tries ({last}). "
        "Check your internet connection. If you see a certificate error, run: pip install certifi"
    )
