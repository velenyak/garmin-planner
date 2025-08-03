"""
Tests for the GarminWorkoutUploader class.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import tempfile
import shutil

from garmin_planner.garmin_uploader import GarminWorkoutUploader


class TestGarminWorkoutUploader:
    """Test cases for GarminWorkoutUploader."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.uploader = GarminWorkoutUploader(
            email="test@example.com",
            password="testpass"
        )
    
    def test_init(self):
        """Test uploader initialization."""
        assert self.uploader.email == "test@example.com"
        assert self.uploader.password == "testpass"
    
    def test_parse_date_string(self):
        """Test date string parsing."""
        test_cases = [
            ("Monday, August 4th", datetime(datetime.now().year, 8, 4)),
            ("Tuesday, August 5th", datetime(datetime.now().year, 8, 5)),
            ("August 4", datetime(datetime.now().year, 8, 4)),
            ("Aug 4", datetime(datetime.now().year, 8, 4)),
        ]
        
        for date_str, expected in test_cases:
            result = self.uploader._parse_date_string(date_str)
            assert result is not None
            assert result.month == expected.month
            assert result.day == expected.day
    
    def test_determine_workout_type(self):
        """Test workout type determination."""
        test_cases = [
            ("4 x 5-minute intervals at Zone 4", "intervals"),
            ("Running with intervals", "intervals"),
            ("Tempo run in Zone 3", "tempo"),
            ("Easy Zone 2 run", "base"),
            ("Long endurance ride", "endurance"),
            ("Strength training session", "strength"),
            ("General workout", "general"),
        ]
        
        for description, expected in test_cases:
            result = self.uploader._determine_workout_type(description)
            assert result == expected
    
    def test_map_sport_type(self):
        """Test sport type mapping."""
        test_cases = [
            ("running", {"sportTypeId": 1, "sportTypeKey": "running"}),
            ("cycling", {"sportTypeId": 2, "sportTypeKey": "cycling"}),
            ("swimming", {"sportTypeId": 5, "sportTypeKey": "swimming"}),
            ("strength", {"sportTypeId": 13, "sportTypeKey": "strength_training"}),
            ("yoga", {"sportTypeId": 43, "sportTypeKey": "yoga"}),
        ]
        
        for sport_type, expected in test_cases:
            result = self.uploader._map_sport_type(sport_type)
            assert result == expected
    
    def test_create_structured_workout(self):
        """Test structured workout creation."""
        date = datetime(2025, 8, 4)
        sport_type = "running"
        duration = 60
        description = "Easy Zone 2 run for base building"
        
        workout = self.uploader._create_structured_workout(
            date, sport_type, duration, description
        )
        
        assert workout is not None
        assert workout['workoutName'] == "2025-08-04 Running base"
        assert workout['estimatedDurationInSecs'] == 3600
        assert workout['sport']['sportTypeKey'] == "running"
        assert len(workout['workoutSegments']) > 0
    
    def test_create_interval_segments(self):
        """Test interval segment creation."""
        segments = self.uploader._create_interval_segments(
            "running", 60, "4 x 5-minute intervals at Zone 4"
        )
        
        # Should have warm-up, intervals, recoveries, and cool-down
        assert len(segments) > 5  # At least warm-up + 4 intervals + 3 recoveries + cool-down
        
        # Check warm-up
        assert segments[0]['targetValueOne'] == 2  # Zone 2
        
        # Check first interval
        assert segments[1]['targetValueOne'] == 4  # Zone 4
    
    def test_extract_daily_sections(self):
        """Test daily section extraction."""
        plan_text = """
        **Monday, August 4th:**
        * Morning: Running (60 minutes)
        
        **Tuesday, August 5th:**
        * Morning: Cycling (90 minutes)
        """
        
        sections = self.uploader._extract_daily_sections(plan_text)
        
        assert len(sections) >= 2
        assert "Monday, August 4th" in sections or "Monday, August 4th:" in str(sections.keys())
    
    def test_parse_daily_section(self):
        """Test daily section parsing."""
        date_str = "Monday, August 4th"
        section = """
        * Morning: Running (60 minutes, Zone 2). Easy base run.
        * Afternoon: Strength Training (45 minutes). Full body workout.
        """
        
        workouts = self.uploader._parse_daily_section(date_str, section)
        
        # Should find at least the running workout
        assert len(workouts) >= 1
        
        # Check first workout
        running_workout = next((w for w in workouts if 'Running' in w['workoutName']), None)
        assert running_workout is not None
        assert "2025-08-04" in running_workout['workoutName']
