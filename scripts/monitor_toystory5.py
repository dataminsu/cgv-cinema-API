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


def smoke_test() -> int:
    """Send ONE sample '예매 오픈' alert to validate the SMTP/notifier setup."""
    from cgv_cinema import filters
    from cgv_cinema.config import email_enabled
    from cgv_cinema.models import Showtime
    from cgv_cinema.notify import ConsoleNotifier, EmailNotifier, format_alert

    date = filters.next_sunday().strftime("%Y%m%d")
    sample = Showtime(
        site_no=config.YONGSAN_IPARK_SITE_NO,
        site_name=config.YONGSAN_IPARK_SITE_NAME,
        movie="토이 스토리 5", movie_en="Toy Story 5",
        hall="1관 (Laser)", screen_no="001",
        grade_code=config.GRADE_GENERAL_2D, format="2D",
        date=date, seq="3", start="1100", end="1252",
        total_seats=204, free_seats=187,
    )
    enabled = email_enabled()
    print(f"이메일 알림: {'활성 (SMTP 설정 감지)' if enabled else '비활성 (SMTP 미설정 → 콘솔만)'}")
    subj, body = format_alert("[SMOKE TEST] 예매 오픈 — 좌석 있음 (샘플)",
                              [sample], date, config.YONGSAN_IPARK_SITE_NAME)
    ConsoleNotifier().send(subj, body)
    if not enabled:
        print("\n⚠️  SMTP 환경변수가 없어 실제 메일은 보내지 않았습니다(콘솔 출력만).")
        print("   .env 를 채우거나 환경변수를 설정한 뒤 다시 --test-email 하세요.")
        return 1
    ok = EmailNotifier().send(subj, body)
    if ok:
        print("\n✅ 스모크 테스트 메일 발송 성공 — 받은편지함을 확인하세요.")
        return 0
    print("\n❌ 메일 발송 실패(위 오류 참조). 자격증명/포트/앱비밀번호를 확인하세요.")
    return 1


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
    ap.add_argument("--max-alerts", type=int, default=12,
                    help="예매 오픈 후 보낼 최대 알림 수 (기본 12 = 5분×12 = 1시간)")
    ap.add_argument("--test-email", action="store_true",
                    help="샘플 알림 1통 전송 스모크 테스트(SMTP 검증) 후 종료")
    args = ap.parse_args()

    if args.test_email:
        return smoke_test()

    # grade='all' → 시간창만 적용하고 등급 필터는 무력화
    grade = args.grade
    monitor = ToyStory5Monitor(
        site_no=args.site,
        grade_code=grade,
        time_window=parse_window(args.window),
        date=args.date,
        interval_min=args.interval,
        max_alerts=args.max_alerts,
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
