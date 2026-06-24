# -*- coding: utf-8 -*-
"""Polling monitor: detects when 일반관 2D 토이스토리5 (~11:00, Sunday) booking
opens and/or has remaining seats, and fires notifications.

Scheduling is wall-clock aligned: ticks land on :00, :05, :10 … (정각 기준).
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import time

from . import config, filters
from .client import CGVClient, CGVError
from .models import Showtime
from .notify import build_default_notifier, format_alert


class ToyStory5Monitor:
    def __init__(
        self,
        client: CGVClient | None = None,
        site_no: str = config.YONGSAN_IPARK_SITE_NO,
        site_name: str = config.YONGSAN_IPARK_SITE_NAME,
        grade_code: str = config.GRADE_GENERAL_2D,     # 일반관 2D
        time_window: tuple[str, str] = config.DEFAULT_TIME_WINDOW,
        date: str | None = None,        # YYYYMMDD; None → upcoming Sunday
        interval_min: int = 5,
        notifier=None,
        log_dir: str | None = None,
    ):
        self.client = client or CGVClient()
        self.site_no = site_no
        self.site_name = site_name
        self.grade_code = grade_code
        self.time_window = time_window
        self.fixed_date = date
        self.interval_min = interval_min
        self.notifier = notifier or build_default_notifier()
        self.log_dir = log_dir or os.path.join(os.getcwd(), "logs")
        # snapshot of previously seen target slots: {key: free_seats}
        self._prev: dict[str, int | None] = {}
        self._known_open: set[str] = set()

    # ── target selection ─────────────────────────────────────────────────
    def target_date(self) -> str:
        return self.fixed_date or filters.next_sunday().strftime("%Y%m%d")

    def matching(self, shows: list[Showtime]) -> list[Showtime]:
        """toystory5 ∩ given grade ∩ time window, sorted by start."""
        s = filters.filter_movie(shows)
        s = filters.filter_grade(s, self.grade_code)
        s = filters.in_time_window(s, self.time_window)
        return filters.sort_by_start(s)

    # ── one polling cycle ────────────────────────────────────────────────
    def poll_once(self) -> dict:
        """Fetch, evaluate, alert. Returns a status dict."""
        date = self.target_date()
        now = dt.datetime.now()
        try:
            shows = self.client.get_showtimes(self.site_no, date)
        except CGVError as e:
            print(f"[{now:%H:%M:%S}] 조회 실패: {e}", flush=True)
            return {"ok": False, "error": str(e), "date": date}

        all_toy = filters.filter_movie(shows)
        targets = self.matching(shows)
        self._report(now, date, all_toy, targets)

        # ── transition detection ──
        newly_opened, seats_back = [], []
        cur = {}
        for s in targets:
            cur[s.key] = s.free_seats
            if s.key not in self._known_open:
                self._known_open.add(s.key)
                if s.has_seats:
                    newly_opened.append(s)        # 예매가 새로 열림 + 좌석 있음
            else:
                prev_free = self._prev.get(s.key)
                if (prev_free == 0 or prev_free is None) and s.has_seats:
                    seats_back.append(s)          # 매진→좌석 발생
        self._prev = cur

        if newly_opened:
            subj, body = format_alert("예매 오픈 (좌석 있음)",
                                      newly_opened, date, self.site_name)
            self.notifier.send(subj, body)
        if seats_back:
            subj, body = format_alert("잔여좌석 발생",
                                      seats_back, date, self.site_name)
            self.notifier.send(subj, body)

        self._save(date, now, targets, all_toy)
        return {
            "ok": True, "date": date,
            "toystory5_total": len(all_toy),
            "target_count": len(targets),
            "open": bool(targets),
            "available": any(s.has_seats for s in targets),
            "newly_opened": [s.to_dict() for s in newly_opened],
            "seats_back": [s.to_dict() for s in seats_back],
            "targets": [s.to_dict() for s in targets],
        }

    # ── console status line ──────────────────────────────────────────────
    def _report(self, now, date, all_toy, targets):
        d = dt.datetime.strptime(date, "%Y%m%d").date()
        wd = "월화수목금토일"[d.weekday()]
        lo, hi = self.time_window
        grade = config.GRADE_NAMES.get(self.grade_code, self.grade_code)
        print(f"[{now:%H:%M:%S}] {self.site_name} · 토이스토리5 · {grade} · "
              f"{d:%m/%d}({wd}) {lo[:2]}:{lo[2:]}~{hi[:2]}:{hi[2:]}", flush=True)
        if not all_toy:
            print("   · 토이스토리5 자체가 아직 편성/미개봉 (예매 미오픈)", flush=True)
        if not targets:
            print("   · 매칭 회차 없음 → 일반관 2D 예매 아직 안 열림 (감시 계속)",
                  flush=True)
            return
        for s in targets:
            tag = "  [매진]" if s.sold_out else ""
            print(f"   ✔ {s.start_hhmm}~{s.end_hhmm} | {s.hall} | "
                  f"잔여 {s.free_seats}/{s.total_seats}석 | {s.seq}회{tag}",
                  flush=True)

    # ── persistence ──────────────────────────────────────────────────────
    def _save(self, date, now, targets, all_toy):
        snap = {
            "fetched_at": now.isoformat(timespec="seconds"),
            "site_no": self.site_no, "site_name": self.site_name,
            "date": date, "movie": "토이 스토리 5",
            "grade_code": self.grade_code,
            "time_window": list(self.time_window),
            "open": bool(targets),
            "available": any(s.has_seats for s in targets),
            "toystory5_total": len(all_toy),
            "targets": [s.to_dict() for s in targets],
        }
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            with open(os.path.join(self.log_dir, "latest.json"),
                      "w", encoding="utf-8") as f:
                json.dump(snap, f, ensure_ascii=False, indent=2)
            with open(os.path.join(self.log_dir, f"monitor_{date}.jsonl"),
                      "a", encoding="utf-8") as f:
                f.write(json.dumps(snap, ensure_ascii=False) + "\n")
        except OSError as e:
            print(f"   ⚠️  스냅샷 저장 실패: {e}", flush=True)

    # ── scheduling loop ──────────────────────────────────────────────────
    def _sleep_to_next_tick(self) -> None:
        now = dt.datetime.now()
        secs = now.minute * 60 + now.second + now.microsecond / 1e6
        period = self.interval_min * 60
        wait = (math.floor(secs / period) + 1) * period - secs
        nxt = now + dt.timedelta(seconds=wait)
        print(f"\n다음 갱신: {nxt:%H:%M:%S} ({wait:,.0f}초 후)\n", flush=True)
        time.sleep(wait)

    def run(self) -> None:
        print(f"모니터 시작 — 정각 기준 {self.interval_min}분 간격, Ctrl+C 종료\n",
              flush=True)
        self.poll_once()
        try:
            while True:
                self._sleep_to_next_tick()
                self.poll_once()
        except KeyboardInterrupt:
            print("\n종료합니다.", flush=True)
