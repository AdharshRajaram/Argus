"""ATS adapters for job fetching."""

from .base import CareerFetcher
from .detector import ATSDetector
from .greenhouse import GreenhouseFetcher
from .lever import LeverFetcher
from .ashby import AshbyFetcher
from .workday import WorkdayFetcher
from .generic import GenericFetcher
from .uber import UberFetcher
from .amazon import AmazonFetcher
from .meta import MetaFetcher
from .google import GoogleFetcher
from .tiktok import TikTokFetcher

__all__ = [
    "CareerFetcher",
    "ATSDetector",
    "GreenhouseFetcher",
    "LeverFetcher",
    "AshbyFetcher",
    "WorkdayFetcher",
    "GenericFetcher",
    "UberFetcher",
    "AmazonFetcher",
    "MetaFetcher",
    "GoogleFetcher",
    "TikTokFetcher",
]
