#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal example: fetch Toy Story 5 일반관 2D showtimes at 용산아이파크몰."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cgv_cinema import CGVClient, config, filters

client = CGVClient()
date = filters.next_sunday().strftime("%Y%m%d")   # 다가오는 일요일

shows = client.get_showtimes(config.YONGSAN_IPARK_SITE_NO, date)
toy_2d = filters.sort_by_start(filters.general_2d(filters.filter_movie(shows)))

print(f"{config.YONGSAN_IPARK_SITE_NAME} · {date} · 토이스토리5 일반관 2D")
if not toy_2d:
    print("  → 아직 예매가 열리지 않았습니다.")
for s in toy_2d:
    print(f"  {s.start_hhmm}~{s.end_hhmm} | {s.hall} | "
          f"잔여 {s.free_seats}/{s.total_seats}석")
