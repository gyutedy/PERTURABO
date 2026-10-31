"""
F00 — GET borné. Timeout court. 40x / réseau / ban = None (trou), jamais d'invention.
"""

import json
import os
import urllib.error
import urllib.request

TIMEOUT = int(os.environ.get("PARI_F00_TIMEOUT", "8"))
UA = "PERTURABO-PARI/F00"
MAX_FAILS = int(os.environ.get("PARI_F00_MAX_FAILS", "3"))
_FAILS = {}


def _host(url):
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc or "default"
    except Exception:
        return "default"


def _dead(url):
    return _FAILS.get(_host(url), 0) >= MAX_FAILS


def _mark_fail(url):
    h = _host(url)
    _FAILS[h] = _FAILS.get(h, 0) + 1


def get_json(url, headers=None, timeout=None):
    if _dead(url):
        return None
    timeout = TIMEOUT if timeout is None else timeout
    hdrs = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError):
        _mark_fail(url)
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        _mark_fail(url)
        return None


def get_text(url, headers=None, timeout=None):
    if _dead(url):
        return None
    timeout = TIMEOUT if timeout is None else timeout
    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError):
        _mark_fail(url)
        return None
