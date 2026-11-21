"""Tiny stdlib HTTP helpers (no 'requests' dependency)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

TIMEOUT = 20
UA = "pi-dashboard/0.1"


def get(url: str, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def get_json(url: str, headers: dict[str, str] | None = None):
    return json.loads(get(url, headers))


def post_form_json(url: str, form: dict[str, str]):
    data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())
