# -*- coding: utf-8 -*-
"""Low-level client for CGV's (unofficial) internal JSON API.

Every request to ``api.cgv.co.kr`` must carry an HMAC signature, or the server
returns ``HTTP 401 {"statusCode":"401","statusMessage":"401 Unauthorized1"}``.

Signature scheme (extracted verbatim from the site's JS request interceptor)::

    X-TIMESTAMP = str(int(time.time()))                      # epoch seconds
    X-SIGNATURE = base64( HMAC_SHA256( "<ts>|<pathname>|<body>", SECRET ) )

where ``pathname`` is the URL path only (no query string) and ``body`` is the
empty string for GET requests.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import config
from .models import Showtime


class CGVError(RuntimeError):
    """Raised on transport, HTTP, or API-level (statusCode != 0) failures."""


class CGVClient:
    """Thin, dependency-free client (uses only the Python standard library)."""

    def __init__(
        self,
        secret: str = config.HMAC_SECRET,
        user_agent: str = config.USER_AGENT,
        timeout: int = config.HTTP_TIMEOUT,
        co_cd: str = config.CO_CD,
    ):
        self.secret = secret
        self.user_agent = user_agent
        self.timeout = timeout
        self.co_cd = co_cd

    # ── signing ──────────────────────────────────────────────────────────
    def _sign(self, pathname: str, body: str, ts: str) -> str:
        msg = f"{ts}|{pathname}|{body}"
        digest = hmac.new(
            self.secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256
        ).digest()
        return base64.b64encode(digest).decode("ascii")

    def _get(self, pathname: str, params: dict) -> dict:
        url = f"{config.API_BASE}{pathname}?{urlencode(params)}"
        ts = str(int(time.time()))
        headers = {
            "User-Agent": self.user_agent,
            "Origin": "https://cgv.co.kr",
            "Referer": "https://cgv.co.kr/",
            "Accept": "application/json",
            "Accept-Language": "ko-KR",
            "X-TIMESTAMP": ts,
            "X-SIGNATURE": self._sign(pathname, "", ts),   # GET -> empty body
        }
        req = Request(url, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code == 401:
                raise CGVError(
                    "401 Unauthorized — HMAC signature rejected. CGV may have "
                    "rotated the client secret; see cgv_cinema/config.py docstring. "
                    f"Body: {body}"
                )
            raise CGVError(f"HTTP {e.code}: {body}")
        except URLError as e:
            raise CGVError(f"Network error: {e.reason}")

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise CGVError(f"Invalid JSON response: {e}")

        if payload.get("statusCode") != 0:
            raise CGVError(
                f"API error statusCode={payload.get('statusCode')} "
                f"message={payload.get('statusMessage')}"
            )
        return payload

    # ── public methods ──────────────────────────────────────────────────
    def get_showtimes(self, site_no: str, date: str) -> list[Showtime]:
        """All screenings for a theater (`site_no`) on a date (`YYYYMMDD`)."""
        params = {
            "coCd": self.co_cd,
            "siteNo": site_no,
            "scnYmd": date,
            "scnsNo": "",
            "scnSseq": "",
            "rtctlScopCd": "08",
            "custNo": "",
        }
        data = self._get(config.ENDPOINT_SHOWTIMES, params).get("data") or []
        return [Showtime.from_raw(r) for r in data]

    def get_showtimes_raw(self, site_no: str, date: str) -> list[dict]:
        """Same as :meth:`get_showtimes` but returns raw API dicts."""
        params = {
            "coCd": self.co_cd, "siteNo": site_no, "scnYmd": date,
            "scnsNo": "", "scnSseq": "", "rtctlScopCd": "08", "custNo": "",
        }
        return self._get(config.ENDPOINT_SHOWTIMES, params).get("data") or []

    def get_sites(self) -> list[dict]:
        """All CGV theaters with ``siteNo`` / ``siteNm`` (region grouped)."""
        return self._get(
            config.ENDPOINT_REGION_SITE, {"coCd": self.co_cd}
        ).get("data") or []

    def get_screening_dates(self, site_no: str) -> list[dict]:
        """Dates that have screenings for a theater (``[{scnYmd, hldyYn}, ...]``)."""
        params = {"coCd": self.co_cd, "siteNo": site_no}
        return self._get(config.ENDPOINT_SITE_DATES, params).get("data") or []
