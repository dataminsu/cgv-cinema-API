# -*- coding: utf-8 -*-
"""cgv_cinema — a small, dependency-free client for CGV's internal showtime API,
plus a Toy Story 5 (용산아이파크몰, 일반관 2D) booking-open / seat monitor.

NOTE: unofficial. CGV has no public API; this calls the private JSON API used by
cgv.co.kr's own web app. Use responsibly and at a modest request rate.
"""

from .client import CGVClient, CGVError
from .models import Showtime
from .monitor import ToyStory5Monitor
from . import config, filters, notify

__version__ = "1.0.0"
__all__ = [
    "CGVClient", "CGVError", "Showtime", "ToyStory5Monitor",
    "config", "filters", "notify",
]
