import garth
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
from typing import List, Dict, Optional, Any


class GarminActivityDownloader:
    """Download and save Garmin Connect activities to JSON files."""
    
    def __init__(self, email: str, password: str, output_dir: str = "garmin_activities"):
        """
        Initialize the Garmin activity downloader.
        
        Args:
            email: Garmin Connect email
            password: Garmin Connect password
            output_dir: Directory to save activity files
        """
        self.email = email
        self.password = password
        self.session_file = Path.home() / ".garth"
        self.output_dir = Path(output_dir)
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True)
        print(f"Output directory: {self.output_dir.absolute()}")
        
    def authenticate(self) -> None:
        """Authenticate with Garmin Connect."""
        try:
            # Try to resume existing session
            garth.resume(str(self.session_file))
            print("Resumed existing session")
        except Exception:
            print("Logging in to Garmin Connect...")
            garth.login(self.email, self.password)
            garth.save(str(self.session_file))
            print("Login successful")
    
    def get_activities(self, weeks: int = 2, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get activities from the last N weeks.
        
        Args:
            weeks: Number of weeks to look back
            limit: Maximum number of activities to fetch
            
        Returns:
            List of activity dictionaries
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        print(f"Fetching activities from {start_str} to {end_str}")
        
        try:
            activities = garth.connectapi(
                "/activitylist-service/activities/search/activities",
                params={
                    "startDate": start_str,
                    "endDate": end_str,
                    "limit": limit
                }
            )
            return activities
        except Exception as e:
            print(f"Error fetching activities: {e}")
            return []
    
    def download_activity_data(self, activity_id: str) -> Optional[Dict[str, Any]]:
        """
        Download detailed data for a specific activity.
        
        Args:
            activity_id: The Garmin activity ID
            
        Returns:
            Dictionary containing activity summary and details, or None if error
        """
        try:
            # Get basic activity data
            summary = garth.connectapi(f"/activity-service/activity/{activity_id}")
            
            # Get detailed metrics
            details = garth.connectapi(f"/activity-service/activity/{activity_id}/details")
            
            return {
                'summary': summary,
                'details': details
            }
        except Exception as e:
            print(f"Error downloading activity {activity_id}: {e}")
            return None
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Remove invalid characters from filename.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for filesystem
        """
        # Replace invalid characters with underscore
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Trim underscores and spaces
        return sanitized.strip('_ ')
    
    def save_activity_to_file(self, activity_data: Dict[str, Any], activity_info: Dict[str, Any]) -> bool:
        """
        Save individual activity data to JSON file.
        
        Args:
            activity_data: Detailed activity data from Garmin
            activity_info: Basic activity information
            
        Returns:
            True if successful, False otherwise
        """
        # Create filename from activity info
        activity_id = activity_info['activityId']
        activity_name = activity_info['activityName']
        activity_type = activity_info['activityType']['typeKey']
        start_time = activity_info['startTimeLocal']
        
        # Parse date for filename
        date_obj = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        date_str = date_obj.strftime("%Y-%m-%d_%H-%M")
        
        # Create safe filename
        safe_name = self.sanitize_filename(activity_name)
        filename = f"{date_str}_{activity_type}_{safe_name}_{activity_id}.json"
        
        # Full path
        file_path = self.output_dir / filename
        
        # Prepare data to save
        complete_data = {
            'metadata': {
                'activity_id': activity_id,
                'name': activity_name,
                'type': activity_type,
                'start_time': start_time,
                'download_timestamp': datetime.now().isoformat(),
                'duration': activity_info.get('duration'),
                'distance': activity_info.get('distance'),
                'calories': activity_info.get('calories')
            },
            'garmin_data': activity_data
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(complete_data, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"  ✓ Saved: {filename}")
            return True
        except Exception as e:
            print(f"  ✗ Error saving {filename}: {e}")
            return False
    
    def create_summary_file(self, activities_summary: List[Dict[str, Any]]) -> None:
        """
        Create a summary file with all activities info.
        
        Args:
            activities_summary: List of activity summary dictionaries
        """
        summary_file = self.output_dir / "activities_summary.json"
        
        summary_data = {
            'download_info': {
                'total_activities': len(activities_summary),
                'download_timestamp': datetime.now().isoformat(),
                'date_range': {
                    'start': min(act['start_time'] for act in activities_summary) if activities_summary else None,
                    'end': max(act['start_time'] for act in activities_summary) if activities_summary else None
                }
            },
            'activities': activities_summary
        }
        
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, default=str, ensure_ascii=False)
            print(f"\n📋 Summary saved: {summary_file}")
        except Exception as e:
            print(f"Error saving summary: {e}")
    
    def download_activities(self, weeks: int = 2) -> Dict[str, Any]:
        """
        Main method to download all activities.
        
        Args:
            weeks: Number of weeks to look back
            
        Returns:
            Dictionary with download statistics
        """
        print("🏃 Starting Garmin activity download...")
        
        # Authenticate
        self.authenticate()
        
        # Get recent activities
        activities = self.get_activities(weeks=weeks)
        if not activities:
            print("No activities found")
            return {'success': False, 'total': 0, 'downloaded': 0}
        
        print(f"📊 Found {len(activities)} activities")
        
        # Download detailed data for each activity
        successful_downloads = 0
        activities_summary = []
        
        for i, activity in enumerate(activities, 1):
            activity_id = activity['activityId']
            name = activity['activityName']
            activity_type = activity['activityType']['typeKey']
            
            print(f"\n[{i}/{len(activities)}] {name} ({activity_type})")
            
            # Download detailed data
            detailed_data = self.download_activity_data(activity_id)
            if detailed_data:
                # Save to individual file
                if self.save_activity_to_file(detailed_data, activity):
                    successful_downloads += 1
                    
                    # Add to summary
                    activities_summary.append({
                        'activity_id': activity_id,
                        'name': name,
                        'type': activity_type,
                        'start_time': activity['startTimeLocal'],
                        'duration': activity.get('duration'),
                        'distance': activity.get('distance'),
                        'calories': activity.get('calories')
                    })
        
        # Create summary file
        self.create_summary_file(activities_summary)
        
        print(f"\n✅ Download complete!")
        print(f"   Successfully downloaded: {successful_downloads}/{len(activities)} activities")
        print(f"   Files saved to: {self.output_dir.absolute()}")
        
        return {
            'success': True,
            'total': len(activities),
            'downloaded': successful_downloads,
            'output_dir': str(self.output_dir.absolute())
        }
