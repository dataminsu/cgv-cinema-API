# -*- coding: utf-8 -*-
"""Static configuration and environment loading for the CGV cinema client.

NOTE on the HMAC secret
-----------------------
``HMAC_SECRET`` is a *client* secret that CGV ships, in plaintext, inside the
public JavaScript bundle of https://cgv.co.kr (Next.js build ``f65364c5``).
It is therefore not confidential, but CGV may rotate it on a site redeploy. If
signed requests suddenly start returning HTTP 401, re-extract it from
``https://cdn.cgv.co.kr/cgvpomscontent/static/script/<build>/_next/static/chunks/1453-*.js``
(search the chunk for ``HmacSHA256(r,"...")``) and update this value.
"""

from __future__ import annotations

import os

# ── CGV internal JSON API ────────────────────────────────────────────────
API_BASE = "https://api.cgv.co.kr"
ENDPOINT_SHOWTIMES = "/cnm/atkt/searchMovScnInfo"          # 극장+날짜별 상영정보
ENDPOINT_REGION_SITE = "/cnm/site/searchAllRegionAndSite"  # 지역/극장 목록
ENDPOINT_SITE_DATES = "/cnm/atkt/searchSiteScnscYmdListBySite"  # 극장 상영일 목록

CO_CD = "A420"   # CGV 코리아 법인코드 (bundle 상수)

# Extracted from CGV's public JS bundle (see module docstring).
HMAC_SECRET = "ydqXY0ocnFLmJGHr_zNzFcpjwAsXq_8JcBNURAkRscg"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# ── Yongsan I'Park Mall ───────────────────────────────────────────────────
YONGSAN_IPARK_SITE_NO = "0013"          # 용산아이파크몰 (씨네드쉐프 용산 P013 아님)
YONGSAN_IPARK_SITE_NAME = "CGV 용산아이파크몰"

# ── Screen grade codes (scnsGradCd) ───────────────────────────────────────
GRADE_GENERAL_2D = "0101"               # 일반관 2D
GRADE_NAMES = {
    "0101": "일반 2D",
    "0105": "CINE de CHEF",
    "0106": "CINE de CHEF",
    "0112": "CGV아트하우스",
    "0201": "4DX",
    "0301": "IMAX",
    "0401": "SCREENX",
}

# ── Toy Story 5 monitor defaults ──────────────────────────────────────────
# Movie names are compared after stripping whitespace, so this matches both
# "토이 스토리 5" (as CGV returns it) and "토이스토리5".
TARGET_MOVIE_NORM = "토이스토리5"
TARGET_MOVIE_EN = "toystory5"
# "11시 부근" time window, inclusive, in HHMM strings.
DEFAULT_TIME_WINDOW = ("1030", "1200")

HTTP_TIMEOUT = 15


# ── SMTP / email alert config (from environment) ──────────────────────────
def email_config() -> dict:
    """Read SMTP settings from environment variables.

    Required for email alerts:
        SMTP_HOST, SMTP_USER, SMTP_PASSWORD, ALERT_TO
    Optional:
        SMTP_PORT (default 587), ALERT_FROM (default SMTP_USER),
        SMTP_USE_TLS (default "1" → STARTTLS)
    """
    to_raw = os.environ.get("ALERT_TO", "")
    return {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587") or "587"),
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from_addr": os.environ.get("ALERT_FROM") or os.environ.get("SMTP_USER", ""),
        "to_addrs": [a.strip() for a in to_raw.split(",") if a.strip()],
        "use_tls": os.environ.get("SMTP_USE_TLS", "1") not in ("0", "false", "False"),
        # implicit SSL (port 465). STARTTLS (587) is the default otherwise.
        "use_ssl": (os.environ.get("SMTP_USE_SSL", "").lower() in ("1", "true", "yes"))
        or os.environ.get("SMTP_PORT", "") == "465",
    }


def email_enabled() -> bool:
    c = email_config()
    return bool(c["host"] and c["user"] and c["password"] and c["to_addrs"])


def load_dotenv(path: str | None = None) -> None:
    """Minimal .env loader (no dependency). Loads KEY=VALUE lines into the
    environment WITHOUT overriding variables already set. Looks at the repo
    root (next to .env.example) by default. Quotes are stripped."""
    if path is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(repo_root, ".env")
    if not os.path.isfile(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except OSError:
        pass


# Auto-load a local .env on import so `python scripts/...` just works.
load_dotenv()
