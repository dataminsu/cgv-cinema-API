# -*- coding: utf-8 -*-
"""Pure helpers to select/sort :class:`Showtime` objects and find Sundays."""

from __future__ import annotations

import datetime as dt

from . import config
from .models import Showtime


def _norm(s: str) -> str:
    return "".join((s or "").split()).lower()


def is_target_movie(s: Showtime,
                    kr: str = config.TARGET_MOVIE_NORM,
                    en: str = config.TARGET_MOVIE_EN) -> bool:
    return kr in _norm(s.movie) or (bool(en) and en in _norm(s.movie_en))


def filter_movie(shows: list[Showtime], **kw) -> list[Showtime]:
    return [s for s in shows if is_target_movie(s, **kw)]


def filter_grade(shows: list[Showtime], grade_code: str) -> list[Showtime]:
    return [s for s in shows if s.grade_code == grade_code]


def general_2d(shows: list[Showtime]) -> list[Showtime]:
    """Only 일반관 2D (scnsGradCd == '0101')."""
    return [s for s in shows if s.is_general_2d]


def in_time_window(shows: list[Showtime],
                   window: tuple[str, str] = config.DEFAULT_TIME_WINDOW
                   ) -> list[Showtime]:
    lo, hi = window
    return [s for s in shows if lo <= (s.start or "") <= hi]


def sort_by_start(shows: list[Showtime]) -> list[Showtime]:
    return sorted(shows, key=lambda s: (s.start or "", s.hall or ""))


def next_sunday(today: dt.date | None = None) -> dt.date:
    """Upcoming Sunday (today if today is Sunday)."""
    today = today or dt.date.today()
    return today + dt.timedelta(days=(6 - today.weekday()) % 7)


def upcoming_sundays(n: int = 4, today: dt.date | None = None) -> list[dt.date]:
    first = next_sunday(today)
    return [first + dt.timedelta(days=7 * i) for i in range(n)]
