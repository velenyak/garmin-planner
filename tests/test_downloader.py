"""
Tests for the GarminActivityDownloader class.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import shutil

from garmin_planner.downloader import GarminActivityDownloader


class TestGarminActivityDownloader:
    """Test cases for GarminActivityDownloader."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.downloader = GarminActivityDownloader(
            email="test@example.com",
            password="testpass",
            output_dir=self.temp_dir
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test downloader initialization."""
        assert self.downloader.email == "test@example.com"
        assert self.downloader.password == "testpass"
        assert self.downloader.output_dir == Path(self.temp_dir)
        assert self.downloader.output_dir.exists()
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        test_cases = [
            ("Normal Name", "Normal Name"),
            ("Name/with\\invalid:chars", "Name_with_invalid_chars"),
            ("Multiple___underscores", "Multiple_underscores"),
            ("  Spaces  ", "Spaces"),
            ("Name<>:\"/\\|?*", "Name_"),
        ]
        
        for input_name, expected in test_cases:
            result = self.downloader.sanitize_filename(input_name)
            assert result == expected
    
    @patch('garmin_planner.downloader.garth')
    def test_authenticate_resume_session(self, mock_garth):
        """Test authentication with existing session."""
        mock_garth.resume.return_value = None
        
        self.downloader.authenticate()
        
        mock_garth.resume.assert_called_once()
        mock_garth.login.assert_not_called()
    
    @patch('garmin_planner.downloader.garth')
    def test_authenticate_new_session(self, mock_garth):
        """Test authentication with new session."""
        mock_garth.resume.side_effect = Exception("No session")
        mock_garth.login.return_value = None
        mock_garth.save.return_value = None
        
        self.downloader.authenticate()
        
        mock_garth.resume.assert_called_once()
        mock_garth.login.assert_called_once_with("test@example.com", "testpass")
        mock_garth.save.assert_called_once()
    
    def test_save_activity_to_file(self):
        """Test saving activity data to file."""
        activity_data = {
            'summary': {'test': 'data'},
            'details': {'more': 'data'}
        }
        
        activity_info = {
            'activityId': '12345',
            'activityName': 'Test Run',
            'activityType': {'typeKey': 'running'},
            'startTimeLocal': '2024-01-15T08:30:00',
            'duration': 1800,
            'distance': 5000,
            'calories': 350
        }
        
        result = self.downloader.save_activity_to_file(activity_data, activity_info)
        
        assert result is True
        
        # Check that file was created
        json_files = list(Path(self.temp_dir).glob("*.json"))
        assert len(json_files) == 1
        
        # Check filename format
        filename = json_files[0].name
        assert filename.startswith("2024-01-15_08-30_running_Test Run_12345")
        assert filename.endswith(".json")
