#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point: monitor 용산아이파크몰 토이스토리5 일반관 2D (~11시) booking.

Examples
--------
    # 정각 기준 5분마다 감시 (이메일은 .env / 환경변수 설정 시 자동)
    python scripts/monitor_toystory5.py

    # 지금 상태만 1회 확인
    python scripts/monitor_toystory5.py --once

    # 특정 일요일 / 시간창 / 등급 조정
    python scripts/monitor_toystory5.py --date 20260628 --window 1030-1200
    python scripts/monitor_toystory5.py --grade all     # 전체 포맷 감시
"""

from __future__ import annotations

import argparse
import os
import sys

# allow running as a plain script (no install needed)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cgv_cinema import config                       # noqa: E402
from cgv_cinema.monitor import ToyStory5Monitor     # noqa: E402
from cgv_cinema.notify import build_default_notifier  # noqa: E402


def parse_window(s: str) -> tuple[str, str]:
    lo, hi = s.split("-")
    return lo.strip(), hi.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true", help="1회 확인 후 종료")
    ap.add_argument("--date", metavar="YYYYMMDD",
                    help="조회 날짜 (기본: 다가오는 일요일)")
    ap.add_argument("--site", default=config.YONGSAN_IPARK_SITE_NO,
                    help=f"극장 siteNo (기본 {config.YONGSAN_IPARK_SITE_NO}=용산아이파크몰)")
    ap.add_argument("--grade", default=config.GRADE_GENERAL_2D,
                    help="scnsGradCd (기본 0101=일반2D). 'all'=전체 포맷")
    ap.add_argument("--window", default="-".join(config.DEFAULT_TIME_WINDOW),
                    help="시간창 HHMM-HHMM (기본 1030-1200)")
    ap.add_argument("--interval", type=int, default=5,
                    help="갱신 간격(분), 정각 정렬 (기본 5)")
    args = ap.parse_args()

    # grade='all' → 시간창만 적용하고 등급 필터는 무력화
    grade = args.grade
    monitor = ToyStory5Monitor(
        site_no=args.site,
        grade_code=grade,
        time_window=parse_window(args.window),
        date=args.date,
        interval_min=args.interval,
        notifier=build_default_notifier(),
    )
    # grade='all' 처리: matching에서 등급 필터를 건너뛰도록 패치
    if grade.lower() == "all":
        import types
        from cgv_cinema import filters

        def matching(self, shows):
            s = filters.filter_movie(shows)
            s = filters.in_time_window(s, self.time_window)
            return filters.sort_by_start(s)
        monitor.matching = types.MethodType(matching, monitor)

    from cgv_cinema.config import email_enabled
    print(f"이메일 알림: {'활성(SMTP 설정 감지)' if email_enabled() else '비활성(콘솔만)'}")

    if args.once:
        monitor.poll_once()
        return 0
    monitor.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
