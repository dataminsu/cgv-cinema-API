# -*- coding: utf-8 -*-
"""FastAPI wrapper exposing the CGV showtime client as an HTTP/JSON API.

Run:
    uvicorn api.server:app --reload --port 8000
Then open http://localhost:8000/docs for interactive Swagger UI.
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from cgv_cinema import CGVClient, CGVError, config, filters

app = FastAPI(
    title="CGV Cinema API (unofficial)",
    version="1.0.0",
    description=(
        "Unofficial HTTP wrapper over CGV's private internal showtime API "
        "(api.cgv.co.kr). Defaults target 용산아이파크몰 (siteNo=0013) and "
        "토이 스토리 5. Not affiliated with or endorsed by CJ CGV."
    ),
)

client = CGVClient()


def _err(e: CGVError):
    raise HTTPException(status_code=502, detail=f"CGV upstream error: {e}")


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": app.version}


@app.get("/sites", tags=["theaters"])
def sites(q: Optional[str] = Query(None, description="이름 부분일치 필터(예: 용산)")):
    """All CGV theaters (siteNo / siteNm)."""
    try:
        data = client.get_sites()
    except CGVError as e:
        _err(e)
    if q:
        data = [s for s in data if q in (s.get("siteNm") or "")]
    return {"count": len(data), "sites": data}


@app.get("/showtimes", tags=["showtimes"])
def showtimes(
    site_no: str = Query(config.YONGSAN_IPARK_SITE_NO, description="극장 코드"),
    date: Optional[str] = Query(None, description="YYYYMMDD (기본: 다가오는 일요일)"),
):
    """All screenings for a theater on a date."""
    date = date or filters.next_sunday().strftime("%Y%m%d")
    try:
        shows = client.get_showtimes(site_no, date)
    except CGVError as e:
        _err(e)
    return {
        "site_no": site_no, "date": date, "count": len(shows),
        "showtimes": [s.to_dict() for s in shows],
    }


@app.get("/toystory5", tags=["showtimes"])
def toystory5(
    site_no: str = Query(config.YONGSAN_IPARK_SITE_NO),
    date: Optional[str] = Query(None, description="YYYYMMDD (기본: 다가오는 일요일)"),
    grade: str = Query(config.GRADE_GENERAL_2D,
                       description="scnsGradCd (0101=일반2D). 'all'=전체 포맷"),
    window: Optional[str] = Query(
        None, description="시간창 HHMM-HHMM (예: 1030-1200). 생략 시 전체"),
):
    """토이 스토리 5 회차(영화/등급/시간창 필터)."""
    date = date or filters.next_sunday().strftime("%Y%m%d")
    try:
        shows = client.get_showtimes(site_no, date)
    except CGVError as e:
        _err(e)
    sel = filters.filter_movie(shows)
    if grade and grade.lower() != "all":
        sel = filters.filter_grade(sel, grade)
    if window:
        try:
            lo, hi = window.split("-")
            sel = filters.in_time_window(sel, (lo, hi))
        except ValueError:
            raise HTTPException(400, "window 형식은 'HHMM-HHMM' 입니다.")
    sel = filters.sort_by_start(sel)
    return {
        "site_no": site_no, "date": date,
        "grade": grade, "window": window,
        "open": bool(sel),
        "available": any(s.has_seats for s in sel),
        "count": len(sel),
        "showtimes": [s.to_dict() for s in sel],
    }


@app.get("/monitor/status", tags=["monitor"])
def monitor_status(
    site_no: str = Query(config.YONGSAN_IPARK_SITE_NO),
    date: Optional[str] = Query(None),
):
    """현재 '일반관 2D · 11시 부근' 토이스토리5 예매가 열렸는지 / 좌석 있는지."""
    date = date or filters.next_sunday().strftime("%Y%m%d")
    try:
        shows = client.get_showtimes(site_no, date)
    except CGVError as e:
        _err(e)
    sel = filters.sort_by_start(
        filters.in_time_window(
            filters.general_2d(filters.filter_movie(shows))))
    return {
        "site_no": site_no, "date": date,
        "target": "토이 스토리 5 · 일반관 2D · 11시 부근",
        "booking_open": bool(sel),
        "seats_available": any(s.has_seats for s in sel),
        "count": len(sel),
        "showtimes": [s.to_dict() for s in sel],
    }
