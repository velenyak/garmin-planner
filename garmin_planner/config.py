"""
Configuration management for Garmin Workout Planner.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Configuration class for Garmin activity downloader."""
    
    def __init__(self, env_file: str = '.env'):
        """
        Initialize configuration.
        
        Args:
            env_file: Path to .env file
        """
        self.env_file = env_file
        self._load_env()
    
    def _load_env(self) -> None:
        """Load environment variables from .env file if it exists."""
        env_path = Path(self.env_file)
        if env_path.exists():
            load_dotenv(env_path)
    
    @property
    def garmin_email(self) -> Optional[str]:
        """Get Garmin email from environment."""
        return os.getenv('GARMIN_EMAIL')
    
    @property
    def garmin_password(self) -> Optional[str]:
        """Get Garmin password from environment."""
        return os.getenv('GARMIN_PASSWORD')
    
    @property
    def default_output_dir(self) -> str:
        """Get default output directory."""
        return os.getenv('GARMIN_OUTPUT_DIR', 'garmin_activities')
    
    @property
    def default_weeks(self) -> int:
        """Get default number of weeks to look back."""
        try:
            return int(os.getenv('GARMIN_DEFAULT_WEEKS', '2'))
        except ValueError:
            return 2
    
    def validate_credentials(self) -> bool:
        """
        Validate that required credentials are available.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        return bool(self.garmin_email and self.garmin_password)
    
    def get_session_file(self) -> Path:
        """Get path to Garth session file."""
        return Path.home() / '.garth'
