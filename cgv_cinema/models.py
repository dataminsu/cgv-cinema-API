# -*- coding: utf-8 -*-
"""Typed view over a single raw showtime record returned by the CGV API."""

from __future__ import annotations

from dataclasses import dataclass, asdict

from .config import GRADE_NAMES, GRADE_GENERAL_2D


def _to_int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def hhmm(t: str) -> str:
    """'0830' -> '08:30'."""
    t = (t or "").strip()
    return f"{t[:2]}:{t[2:]}" if len(t) == 4 else (t or "--:--")


@dataclass
class Showtime:
    site_no: str
    site_name: str
    movie: str            # movNm (KR)
    movie_en: str         # movEnm (EN)
    hall: str             # scnsNm
    screen_no: str        # scnsNo
    grade_code: str       # scnsGradCd
    format: str           # movkndDsplNm  (e.g. "2D", "IMAX LASER 2D")
    date: str             # scnYmd  (YYYYMMDD)
    seq: str              # scnSseq (회차)
    start: str            # scnsrtTm (HHMM)
    end: str              # scnendTm (HHMM)
    total_seats: int | None   # stcnt
    free_seats: int | None    # frSeatCnt

    # ── derived ──
    @property
    def grade_name(self) -> str:
        return GRADE_NAMES.get(self.grade_code, self.grade_code or "?")

    @property
    def is_general_2d(self) -> bool:
        return self.grade_code == GRADE_GENERAL_2D

    @property
    def sold_out(self) -> bool:
        return self.free_seats == 0

    @property
    def has_seats(self) -> bool:
        return (self.free_seats or 0) > 0

    @property
    def key(self) -> str:
        """Stable identity of a screening (for snapshot diffing)."""
        return f"{self.date}|{self.screen_no}|{self.seq}|{self.start}"

    @property
    def start_hhmm(self) -> str:
        return hhmm(self.start)

    @property
    def end_hhmm(self) -> str:
        return hhmm(self.end)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["grade_name"] = self.grade_name
        d["start_fmt"] = self.start_hhmm
        d["end_fmt"] = self.end_hhmm
        return d

    @classmethod
    def from_raw(cls, r: dict) -> "Showtime":
        return cls(
            site_no=r.get("siteNo", ""),
            site_name=(r.get("siteNm") or "").strip(),
            movie=(r.get("movNm") or "").strip(),
            movie_en=(r.get("movEnm") or "").strip(),
            hall=(r.get("scnsNm") or "").strip(),
            screen_no=r.get("scnsNo", ""),
            grade_code=r.get("scnsGradCd", ""),
            format=(r.get("movkndDsplNm") or "").strip(),
            date=r.get("scnYmd", ""),
            seq=r.get("scnSseq", ""),
            start=r.get("scnsrtTm", ""),
            end=r.get("scnendTm", ""),
            total_seats=_to_int(r.get("stcnt")),
            free_seats=_to_int(r.get("frSeatCnt")),
        )
