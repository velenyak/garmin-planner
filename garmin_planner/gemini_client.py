"""
Google Gemini client for generating workout plans.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from .downloader import GarminActivityDownloader


class GeminiWorkoutPlanner:
    """Generate workout plans using Google Gemini AI based on Garmin activities."""
    
    def __init__(self, api_key: str):
        """
        Initialize the Gemini workout planner.
        
        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def load_training_context(self, context_file: str = "training_context.txt") -> str:
        """
        Load training context from a text file.
        
        Args:
            context_file: Path to the training context file
            
        Returns:
            Training context as string, or default context if file doesn't exist
        """
        context_path = Path(context_file)
        
        if context_path.exists():
            try:
                with open(context_path, 'r', encoding='utf-8') as f:
                    context = f.read().strip()
                print(f"📖 Loaded training context from {context_file}")
                return context
            except Exception as e:
                print(f"⚠️  Error reading context file: {e}")
        else:
            print(f"📝 Context file {context_file} not found, using default context")
        
        # Default context if file doesn't exist
        return """
        Training Goals:
        - Maintain general fitness
        - Improve endurance
        - Balance between cardio and strength training
        
        Current Focus:
        - Building aerobic base
        - Injury prevention
        - Consistent training routine
        
        Preferences:
        - Mix of running, cycling, and swimming
        - 2-3 strength training sessions per week
        - 1-2 rest/recovery days per week
        """
    
    def load_recent_activities(self, activities_dir: str = "garmin_activities") -> List[Dict[str, Any]]:
        """
        Load recent activities from the summary file.
        
        Args:
            activities_dir: Directory containing Garmin activities
            
        Returns:
            List of recent activities
        """
        summary_file = Path(activities_dir) / "activities_summary.json"
        
        if not summary_file.exists():
            print(f"⚠️  No activities summary found at {summary_file}")
            return []
        
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            activities = data.get('activities', [])
            print(f"📊 Loaded {len(activities)} recent activities")
            return activities
            
        except Exception as e:
            print(f"❌ Error loading activities: {e}")
            return []
    
    def format_activities_for_prompt(self, activities: List[Dict[str, Any]]) -> str:
        """
        Format activities data for the Gemini prompt.
        
        Args:
            activities: List of activity dictionaries
            
        Returns:
            Formatted string of activities
        """
        if not activities:
            return "No recent activities available."
        
        formatted_activities = []
        
        for activity in activities:
            activity_str = f"""
Activity: {activity.get('name', 'Unknown')}
Type: {activity.get('type', 'Unknown')}
Date: {activity.get('start_time', 'Unknown')[:10]}
Duration: {self._format_duration(activity.get('duration'))}
Distance: {self._format_distance(activity.get('distance'))}
Calories: {activity.get('calories', 'N/A')}
"""
            formatted_activities.append(activity_str.strip())
        
        return "\n\n".join(formatted_activities)
    
    def _format_duration(self, duration_seconds: Optional[int]) -> str:
        """Format duration from seconds to human readable format."""
        if not duration_seconds:
            return "N/A"
        
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def _format_distance(self, distance_meters: Optional[float]) -> str:
        """Format distance from meters to kilometers."""
        if not distance_meters:
            return "N/A"
        
        distance_km = distance_meters / 1000
        return f"{distance_km:.2f} km"
    
    def generate_workout_plan(
        self, 
        context_file: str = "training_context.txt",
        activities_dir: str = "garmin_activities",
        weeks: int = 1
    ) -> str:
        """
        Generate a workout plan using Gemini AI.
        
        Args:
            context_file: Path to training context file
            activities_dir: Directory containing Garmin activities
            weeks: Number of weeks to plan for
            
        Returns:
            Generated workout plan as string
        """
        print("🤖 Generating workout plan with Google Gemini...")
        
        # Load training context and recent activities
        training_context = self.load_training_context(context_file)
        recent_activities = self.load_recent_activities(activities_dir)
        formatted_activities = self.format_activities_for_prompt(recent_activities)
        
        # Calculate start date (tomorrow)
        start_date = datetime.now() + timedelta(days=1)
        
        # Create the prompt
        prompt = f"""
You are an expert fitness coach and workout planner. Based on the training context and recent activities provided below, create a detailed workout plan for the next {weeks} week(s).

TRAINING CONTEXT:
{training_context}

RECENT ACTIVITIES (last 2-3 weeks):
{formatted_activities}

Please create a comprehensive workout plan that includes:

1. **Weekly Overview**: Brief summary of the training focus for each week

2. **Daily Workouts**: Detailed day-by-day plan with EXACT formatting as shown below:

For each day, use this EXACT format:
**Monday, August 5th:**
* **Morning (07:00):** [Activity Type] ([Duration] minutes, [Intensity/Zone]). [Detailed description with specific intervals, sets, reps, or zones]
* **Evening (18:00):** [Activity Type] ([Duration] minutes). [Detailed description]
* **Recovery:** [Recovery activities]

IMPORTANT FORMATTING RULES:
- Use day names with dates starting from {start_date.strftime('%A, %B %d')}
- Always include specific times in 24-hour format: "Morning (07:00)", "Evening (18:00)", "Afternoon (12:00)"
- Always include duration in minutes: "Running (75 minutes, Zone 2)"
- For intervals, specify clearly: "4 x 5-minute intervals at Zone 4"
- For strength training, include sets and reps: "3 sets of 8-12 reps"
- Use consistent activity names: Running, Cycling, Swimming, Open Water Swim, Pool Swim, Indoor Cycling, Strength Training, Yoga

3. **Training Principles**: 
   - Consider the athlete's recent training load and patterns
   - Ensure proper progression and recovery
   - Balance different training modalities
   - Account for any gaps or imbalances in recent training

4. **Key Recommendations**:
   - Focus areas based on recent activity analysis
   - Injury prevention tips
   - Nutrition or recovery suggestions

Format the response in clear, structured Markdown that can be easily parsed for workout upload and scheduling to Garmin Connect.

Current date: {datetime.now().strftime('%Y-%m-%d')}
Plan start date: {start_date.strftime('%Y-%m-%d')}

EXAMPLE FORMAT:
**Monday, August 5th:**
* **Morning (07:00):** Running (60 minutes, Zone 2). Easy base run focusing on aerobic development.
* **Evening (18:00):** Strength Training (45 minutes). Full body workout: 3 sets of squats, deadlifts, push-ups.

**Tuesday, August 6th:**
* **Morning (06:30):** Swimming (45 minutes, Zone 2-3). Pool swim with technique focus.
* **Recovery:** Light stretching and hydration.
"""

        try:
            # Generate the workout plan
            response = self.model.generate_content(prompt)
            
            if response.text:
                print("✅ Workout plan generated successfully!")
                return response.text
            else:
                return "❌ Failed to generate workout plan - empty response from Gemini"
                
        except Exception as e:
            error_msg = f"❌ Error generating workout plan: {e}"
            print(error_msg)
            return error_msg
    
    def save_workout_plan(self, plan: str, output_file: str = None) -> str:
        """
        Save the generated workout plan to a file.
        
        Args:
            plan: The workout plan text
            output_file: Output file path (optional)
            
        Returns:
            Path to the saved file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            output_file = f"workout_plan_{timestamp}.md"
        
        output_path = Path(output_file)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(plan)
            
            print(f"💾 Workout plan saved to: {output_path.absolute()}")
            return str(output_path.absolute())
            
        except Exception as e:
            error_msg = f"❌ Error saving workout plan: {e}"
            print(error_msg)
            return error_msg
