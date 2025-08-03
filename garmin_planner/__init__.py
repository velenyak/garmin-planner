"""
Garmin Workout Planner - Download and analyze Garmin activities
"""

__version__ = "0.1.0"
__author__ = "Janos Velenyak"

from .downloader import GarminActivityDownloader
from .gemini_client import GeminiWorkoutPlanner

__all__ = ["GarminActivityDownloader", "GeminiWorkoutPlanner"]
