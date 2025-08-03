"""
Tests for the GeminiWorkoutPlanner class.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import tempfile
import shutil
import json

from garmin_planner.gemini_client import GeminiWorkoutPlanner


class TestGeminiWorkoutPlanner:
    """Test cases for GeminiWorkoutPlanner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test_api_key"
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('garmin_planner.gemini_client.genai')
    def test_init(self, mock_genai):
        """Test planner initialization."""
        planner = GeminiWorkoutPlanner(self.api_key)
        
        assert planner.api_key == self.api_key
        mock_genai.configure.assert_called_once_with(api_key=self.api_key)
        mock_genai.GenerativeModel.assert_called_once_with('gemini-pro')
    
    def test_load_training_context_existing_file(self):
        """Test loading training context from existing file."""
        context_content = "Test training context"
        context_file = Path(self.temp_dir) / "test_context.txt"
        
        with open(context_file, 'w') as f:
            f.write(context_content)
        
        planner = GeminiWorkoutPlanner(self.api_key)
        result = planner.load_training_context(str(context_file))
        
        assert result == context_content
    
    def test_load_training_context_missing_file(self):
        """Test loading training context when file doesn't exist."""
        planner = GeminiWorkoutPlanner(self.api_key)
        result = planner.load_training_context("nonexistent.txt")
        
        # Should return default context
        assert "Training Goals:" in result
        assert "general fitness" in result
    
    def test_load_recent_activities_existing_file(self):
        """Test loading activities from existing summary file."""
        activities_data = {
            "activities": [
                {
                    "activity_id": "123",
                    "name": "Test Run",
                    "type": "running",
                    "start_time": "2024-01-15T08:30:00",
                    "duration": 1800,
                    "distance": 5000,
                    "calories": 350
                }
            ]
        }
        
        activities_dir = Path(self.temp_dir) / "activities"
        activities_dir.mkdir()
        summary_file = activities_dir / "activities_summary.json"
        
        with open(summary_file, 'w') as f:
            json.dump(activities_data, f)
        
        planner = GeminiWorkoutPlanner(self.api_key)
        result = planner.load_recent_activities(str(activities_dir))
        
        assert len(result) == 1
        assert result[0]["name"] == "Test Run"
    
    def test_load_recent_activities_missing_file(self):
        """Test loading activities when summary file doesn't exist."""
        planner = GeminiWorkoutPlanner(self.api_key)
        result = planner.load_recent_activities("nonexistent_dir")
        
        assert result == []
    
    def test_format_activities_for_prompt(self):
        """Test formatting activities for the prompt."""
        activities = [
            {
                "name": "Morning Run",
                "type": "running",
                "start_time": "2024-01-15T08:30:00",
                "duration": 1800,
                "distance": 5000,
                "calories": 350
            }
        ]
        
        planner = GeminiWorkoutPlanner(self.api_key)
        result = planner.format_activities_for_prompt(activities)
        
        assert "Morning Run" in result
        assert "running" in result
        assert "2024-01-15" in result
        assert "30m" in result
        assert "5.00 km" in result
        assert "350" in result
    
    def test_format_activities_for_prompt_empty(self):
        """Test formatting empty activities list."""
        planner = GeminiWorkoutPlanner(self.api_key)
        result = planner.format_activities_for_prompt([])
        
        assert result == "No recent activities available."
    
    def test_format_duration(self):
        """Test duration formatting."""
        planner = GeminiWorkoutPlanner(self.api_key)
        
        assert planner._format_duration(3600) == "1h 0m"
        assert planner._format_duration(1800) == "30m"
        assert planner._format_duration(3900) == "1h 5m"
        assert planner._format_duration(None) == "N/A"
    
    def test_format_distance(self):
        """Test distance formatting."""
        planner = GeminiWorkoutPlanner(self.api_key)
        
        assert planner._format_distance(5000) == "5.00 km"
        assert planner._format_distance(1500) == "1.50 km"
        assert planner._format_distance(None) == "N/A"
    
    def test_save_workout_plan(self):
        """Test saving workout plan to file."""
        plan_content = "# Test Workout Plan\n\nThis is a test plan."
        output_file = Path(self.temp_dir) / "test_plan.md"
        
        planner = GeminiWorkoutPlanner(self.api_key)
        result = planner.save_workout_plan(plan_content, str(output_file))
        
        assert output_file.exists()
        assert result == str(output_file.absolute())
        
        with open(output_file, 'r') as f:
            saved_content = f.read()
        
        assert saved_content == plan_content
