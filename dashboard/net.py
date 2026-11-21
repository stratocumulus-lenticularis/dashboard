"""Tiny stdlib HTTP helpers (no 'requests' dependency)."""

from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request

TIMEOUT = 20
UA = "pi-dashboard/0.1"


def _context(verify: bool) -> ssl.SSLContext | None:
    """verify=False only for devices on the home LAN with a self-signed certificate."""
    if verify:
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def get(url: str, headers: dict[str, str] | None = None, verify: bool = True) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_context(verify)) as resp:
        return resp.read()


def get_json(url: str, headers: dict[str, str] | None = None, verify: bool = True):
    return json.loads(get(url, headers, verify))


def post_form_json(url: str, form: dict[str, str]):
    data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())
