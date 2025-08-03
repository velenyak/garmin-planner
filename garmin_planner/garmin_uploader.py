"""
Garmin Connect workout uploader for structured workouts.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import garth
from .downloader import GarminActivityDownloader


class GarminWorkoutUploader:
    """Upload structured workouts to Garmin Connect."""
    
    def __init__(self, email: str, password: str):
        """
        Initialize the Garmin workout uploader.
        
        Args:
            email: Garmin Connect email
            password: Garmin Connect password
        """
        self.email = email
        self.password = password
        self.session_file = Path.home() / ".garth"
        
    def authenticate(self) -> None:
        """Authenticate with Garmin Connect."""
        try:
            # Try to resume existing session
            garth.resume(str(self.session_file))
            print("Resumed existing Garmin session")
        except Exception:
            print("Logging in to Garmin Connect...")
            garth.login(self.email, self.password)
            garth.save(str(self.session_file))
            print("Login successful")
    
    def parse_workout_plan(self, plan_text: str) -> List[Dict[str, Any]]:
        """
        Parse the Gemini-generated workout plan into structured workouts.
        
        Args:
            plan_text: The workout plan text from Gemini
            
        Returns:
            List of structured workout dictionaries
        """
        workouts = []
        
        # Split the plan into daily sections
        daily_sections = self._extract_daily_sections(plan_text)
        
        for date_str, section in daily_sections.items():
            daily_workouts = self._parse_daily_section(date_str, section)
            workouts.extend(daily_workouts)
        
        return workouts
    
    def _extract_daily_sections(self, plan_text: str) -> Dict[str, str]:
        """Extract daily workout sections from the plan text."""
        daily_sections = {}
        
        # Look for patterns like "**Monday, August 4th:**" or "Monday, August 4th:"
        # More specific pattern to match day names at the start
        date_pattern = r'^\*?\*?\s*([A-Za-z]+,\s+[A-Za-z]+\s+\d+(?:st|nd|rd|th)?)\s*[:\*]*\s*$'
        
        lines = plan_text.split('\n')
        current_date = None
        current_section = []
        
        for line in lines:
            # Check if this line contains a date pattern
            date_match = re.match(date_pattern, line.strip())
            if date_match:
                # Save previous section if we have one
                if current_date and current_section:
                    daily_sections[current_date] = '\n'.join(current_section)
                
                # Start new section
                current_date = date_match.group(1).strip()
                current_section = []
            elif current_date and line.strip():  # Only add non-empty lines
                # Add line to current section
                current_section.append(line)
        
        # Save last section
        if current_date and current_section:
            daily_sections[current_date] = '\n'.join(current_section)
        
        return daily_sections
    
    def _parse_daily_section(self, date_str: str, section: str) -> List[Dict[str, Any]]:
        """Parse a daily section into individual workouts."""
        workouts = []
        
        # Convert date string to datetime
        workout_date = self._parse_date_string(date_str)
        if not workout_date:
            return workouts
        
        # Look for workout patterns with time information
        workout_patterns = [
            (r'Running?\s*\((\d+)\s*minutes?.*?\)', 'running'),
            (r'Indoor Cycling?\s*\((\d+)\s*minutes?.*?\)', 'indoor_cycling'),  # Indoor cycling first
            (r'Cycling?\s*\((\d+)\s*minutes?.*?\)', 'cycling'),  # Outdoor cycling
            (r'Swimming?\s*\((\d+)\s*minutes?.*?\)', 'swimming'),
            (r'Open Water Swim\s*\((\d+)\s*minutes?.*?\)', 'swimming'),
            (r'Pool Swim\s*\((\d+)\s*minutes?.*?\)', 'swimming'),
            (r'Strength Training?\s*\((\d+)\s*minutes?.*?\)', 'strength'),
            (r'Yoga\s*\((\d+)\s*minutes?.*?\)', 'yoga'),
            (r'Bike.*?\s*\((\d+)\s*minutes?.*?\)', 'cycling'),  # Generic bike = outdoor
        ]
        
        for pattern, sport_type in workout_patterns:
            matches = re.finditer(pattern, section, re.IGNORECASE)
            for match in matches:
                duration = int(match.group(1))
                workout_text = self._extract_workout_context(section, match.start(), match.end())
                
                # Extract time information from the workout text
                workout_time = self._extract_workout_time(workout_text)
                
                workout = self._create_structured_workout(
                    date=workout_date,
                    sport_type=sport_type,
                    duration=duration,
                    description=workout_text,
                    scheduled_time=workout_time
                )
                
                if workout:
                    workouts.append(workout)
        
        return workouts
    
    def _extract_workout_time(self, workout_text: str) -> Optional[str]:
        """Extract workout time from the workout text."""
        # Look for time patterns like "Morning (07:00)", "Evening (18:00)", etc.
        time_patterns = [
            r'Morning\s*\((\d{2}:\d{2})\)',
            r'Evening\s*\((\d{2}:\d{2})\)',
            r'Afternoon\s*\((\d{2}:\d{2})\)',
            r'\*\*\s*(\d{2}:\d{2})\s*\*\*',  # **07:00**
            r'at\s+(\d{2}:\d{2})',  # at 07:00
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, workout_text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Default times based on workout context
        if 'morning' in workout_text.lower():
            return '07:00'
        elif 'evening' in workout_text.lower():
            return '18:00'
        elif 'afternoon' in workout_text.lower():
            return '12:00'
        
        return None
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        try:
            # Remove day of week and clean up
            date_clean = re.sub(r'^[A-Za-z]+,?\s*', '', date_str)
            date_clean = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_clean)
            
            # Try different date formats
            formats = [
                '%B %d',  # August 4
                '%b %d',  # Aug 4
            ]
            
            current_year = datetime.now().year
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_clean.strip(), fmt)
                    return parsed_date.replace(year=current_year)
                except ValueError:
                    continue
            
            return None
        except Exception:
            return None
    
    def _extract_workout_context(self, section: str, start: int, end: int) -> str:
        """Extract workout context around the matched pattern."""
        lines = section.split('\n')
        context_lines = []
        
        # Find the line containing the match
        char_count = 0
        target_line_idx = 0
        
        for i, line in enumerate(lines):
            if char_count <= start <= char_count + len(line):
                target_line_idx = i
                break
            char_count += len(line) + 1  # +1 for newline
        
        # Extract context (current line and next few lines)
        for i in range(target_line_idx, min(target_line_idx + 4, len(lines))):
            line = lines[i].strip()
            if line and not line.startswith('**') and not line.startswith('#'):
                context_lines.append(line)
        
        return ' '.join(context_lines)
    
    def _create_structured_workout(
        self, 
        date: datetime, 
        sport_type: str, 
        duration: int, 
        description: str,
        scheduled_time: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a structured workout for Garmin Connect."""
        
        # Determine workout type and structure based on description
        workout_type = self._determine_workout_type(description)
        
        # Create enhanced workout name with date and time
        if scheduled_time:
            workout_name = f"{date.strftime('%Y-%m-%d')} {scheduled_time} {sport_type.title()} {workout_type}"
        else:
            workout_name = f"{date.strftime('%Y-%m-%d')} {sport_type.title()} {workout_type}"
        
        # Create enhanced description with scheduling information
        enhanced_description = self._create_enhanced_description(description, date, scheduled_time)
        
        # Create scheduled datetime if time is provided
        scheduled_datetime = None
        if scheduled_time:
            try:
                time_parts = scheduled_time.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                scheduled_datetime = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            except (ValueError, IndexError):
                scheduled_datetime = None
        
        # Create basic workout structure matching Garmin's API
        workout = {
            'workoutName': workout_name,
            'description': enhanced_description,
            'sportType': self._map_sport_type(sport_type),
            'estimatedDurationInSecs': duration * 60,
            'workoutSegments': [{
                'segmentOrder': 1,
                'sportType': self._map_sport_type(sport_type),
                'workoutSteps': self._create_workout_steps(sport_type, workout_type, duration, description)
            }],
            # Add scheduling information for our tracking
            'scheduledDate': date.strftime('%Y-%m-%d'),
            'scheduledTime': scheduled_time,
            'scheduledDateTime': scheduled_datetime.isoformat() if scheduled_datetime else None
        }
        
        return workout
    
    def _create_enhanced_description(self, original_description: str, date: datetime, scheduled_time: Optional[str]) -> str:
        """Create enhanced description with scheduling information."""
        
        # Start with original description
        enhanced = original_description[:400] if original_description else ""  # Leave room for scheduling info
        
        # Add scheduling information
        scheduling_info = []
        
        # Add date information
        day_name = date.strftime('%A')
        date_str = date.strftime('%B %d, %Y')
        scheduling_info.append(f"📅 Scheduled: {day_name}, {date_str}")
        
        # Add time information
        if scheduled_time:
            # Convert 24-hour to 12-hour format for readability
            try:
                time_obj = datetime.strptime(scheduled_time, '%H:%M')
                time_12h = time_obj.strftime('%I:%M %p').lstrip('0')
                scheduling_info.append(f"⏰ Time: {time_12h}")
            except ValueError:
                scheduling_info.append(f"⏰ Time: {scheduled_time}")
        
        # Add helpful scheduling notes
        scheduling_info.append("📱 Tip: Add to your calendar or set a reminder!")
        
        # Combine original description with scheduling info
        if enhanced:
            enhanced += "\n\n" + "\n".join(scheduling_info)
        else:
            enhanced = "\n".join(scheduling_info)
        
        return enhanced[:500]  # Garmin's description limit
    
    def _determine_workout_type(self, description: str) -> str:
        """Determine workout type from description."""
        description_lower = description.lower()
        
        if any(word in description_lower for word in ['interval', 'intervals', 'zone 4', 'zone 5']):
            return 'intervals'
        elif any(word in description_lower for word in ['tempo', 'zone 3', 'threshold']):
            return 'tempo'
        elif any(word in description_lower for word in ['easy', 'zone 2', 'recovery', 'base']):
            return 'base'
        elif any(word in description_lower for word in ['long', 'endurance']):
            return 'endurance'
        elif any(word in description_lower for word in ['strength', 'weights', 'gym']):
            return 'strength'
        else:
            return 'general'
    
    def _map_sport_type(self, sport_type: str) -> Dict[str, Any]:
        """Map sport type to Garmin Connect sport structure."""
        sport_mapping = {
            'running': {'sportTypeId': 1, 'sportTypeKey': 'running'},
            'cycling': {'sportTypeId': 2, 'sportTypeKey': 'cycling'},
            'indoor_cycling': {'sportTypeId': 25, 'sportTypeKey': 'indoor_cycling'},  # Indoor cycling
            'swimming': {'sportTypeId': 4, 'sportTypeKey': 'swimming'},
            'strength': {'sportTypeId': 13, 'sportTypeKey': 'strength_training'},
            'yoga': {'sportTypeId': 43, 'sportTypeKey': 'yoga'},
        }
        
        return sport_mapping.get(sport_type, {'sportTypeId': 1, 'sportTypeKey': 'running'})
    
    def _create_workout_steps(
        self, 
        sport_type: str, 
        workout_type: str, 
        duration: int, 
        description: str
    ) -> List[Dict[str, Any]]:
        """Create workout steps based on type and description."""
        
        if workout_type == 'intervals':
            return self._create_interval_steps(sport_type, duration, description)
        elif workout_type == 'tempo':
            return self._create_tempo_steps(sport_type, duration)
        else:
            return self._create_basic_steps(sport_type, duration)
    
    def _create_basic_steps(self, sport_type: str, duration: int) -> List[Dict[str, Any]]:
        """Create basic workout steps for steady-state workouts."""
        
        # Determine equipment type based on sport
        equipment_type = self._get_equipment_type(sport_type)
        
        # Swimming workouts need special handling
        if sport_type == 'swimming':
            return [{
                'type': 'ExecutableStepDTO',
                'stepOrder': 1,
                'stepType': {
                    'stepTypeId': 8,  # 'main' step type for swimming
                    'stepTypeKey': 'main',
                    'displayOrder': 8
                },
                'endCondition': {
                    'conditionTypeId': 2,
                    'conditionTypeKey': 'time',
                    'displayOrder': 2,
                    'displayable': True
                },
                'endConditionValue': float(duration * 60),
                'endConditionCompare': '',
                'targetType': {
                    'workoutTargetTypeId': 4,
                    'workoutTargetTypeKey': 'heart.rate.zone',
                    'displayOrder': 4
                },
                'zoneNumber': 2,  # Zone 2 for base workouts
                'strokeType': {
                    'strokeTypeId': 6,  # 'free' stroke for freestyle
                    'strokeTypeKey': 'free',
                    'displayOrder': 6
                },
                'equipmentType': equipment_type,
                'weightValue': -1.0,
                'weightUnit': {
                    'unitId': 8,
                    'unitKey': 'kilogram',
                    'factor': 1000.0
                }
            }]
        
        # Non-swimming workouts
        return [{
            'type': 'ExecutableStepDTO',
            'stepOrder': 1,
            'stepType': {
                'stepTypeId': 5,
                'stepTypeKey': 'workout',
                'displayOrder': 5
            },
            'endCondition': {
                'conditionTypeId': 2,
                'conditionTypeKey': 'time',
                'displayOrder': 2,
                'displayable': True
            },
            'endConditionValue': float(duration * 60),
            'endConditionCompare': 'gt',
            'targetType': {
                'workoutTargetTypeId': 4,
                'workoutTargetTypeKey': 'heart.rate.zone',
                'displayOrder': 4
            },
            'zoneNumber': 2,  # Zone 2 for base workouts
            'strokeType': {
                'strokeTypeId': 0,
                'strokeTypeKey': None,
                'displayOrder': 0
            },
            'equipmentType': equipment_type,
            'weightValue': -1.0,
            'weightUnit': {
                'unitId': 8,
                'unitKey': 'kilogram',
                'factor': 1000.0
            }
        }]
    
    def _get_equipment_type(self, sport_type: str) -> Dict[str, Any]:
        """Get equipment type based on sport type."""
        equipment_mapping = {
            'indoor_cycling': {
                'equipmentTypeId': 1,  # Trainer/Indoor
                'equipmentTypeKey': 'trainer',
                'displayOrder': 1
            },
            'cycling': {
                'equipmentTypeId': 0,  # Default/Outdoor
                'equipmentTypeKey': None,
                'displayOrder': 0
            },
            # Default for all other sports
            'default': {
                'equipmentTypeId': 0,
                'equipmentTypeKey': None,
                'displayOrder': 0
            }
        }
        
        return equipment_mapping.get(sport_type, equipment_mapping['default'])
    
    def _create_tempo_steps(self, sport_type: str, duration: int) -> List[Dict[str, Any]]:
        """Create tempo workout steps."""
        steps = []
        
        # Determine stroke type for swimming
        stroke_type = {
            'strokeTypeId': 6 if sport_type == 'swimming' else 0,
            'strokeTypeKey': 'free' if sport_type == 'swimming' else None,
            'displayOrder': 6 if sport_type == 'swimming' else 0
        }
        equipment_type = self._get_equipment_type(sport_type)
        
        # Warm-up (15 minutes)
        steps.append({
            'type': 'ExecutableStepDTO',
            'stepOrder': 1,
            'stepType': {
                'stepTypeId': 1,
                'stepTypeKey': 'warmup',
                'displayOrder': 1
            },
            'endCondition': {
                'conditionTypeId': 2,
                'conditionTypeKey': 'time',
                'displayOrder': 2,
                'displayable': True
            },
            'endConditionValue': 900.0,  # 15 minutes
            'endConditionCompare': '' if sport_type == 'swimming' else 'gt',
            'targetType': {
                'workoutTargetTypeId': 4,
                'workoutTargetTypeKey': 'heart.rate.zone',
                'displayOrder': 4
            },
            'zoneNumber': 2,
            'strokeType': stroke_type,
            'equipmentType': {
                'equipmentTypeId': 0,
                'equipmentTypeKey': None,
                'displayOrder': 0
            },
            'weightValue': -1.0,
            'weightUnit': {
                'unitId': 8,
                'unitKey': 'kilogram',
                'factor': 1000.0
            }
        })
        
        # Tempo portion (main duration - 25 minutes for warm-up/cool-down)
        tempo_duration = max(20, duration - 25)
        steps.append({
            'type': 'ExecutableStepDTO',
            'stepOrder': 2,
            'stepType': {
                'stepTypeId': 8 if sport_type == 'swimming' else 5,
                'stepTypeKey': 'main' if sport_type == 'swimming' else 'workout',
                'displayOrder': 8 if sport_type == 'swimming' else 5
            },
            'endCondition': {
                'conditionTypeId': 2,
                'conditionTypeKey': 'time',
                'displayOrder': 2,
                'displayable': True
            },
            'endConditionValue': float(tempo_duration * 60),
            'endConditionCompare': '' if sport_type == 'swimming' else 'gt',
            'targetType': {
                'workoutTargetTypeId': 4,
                'workoutTargetTypeKey': 'heart.rate.zone',
                'displayOrder': 4
            },
            'zoneNumber': 3,  # Zone 3 for tempo
            'strokeType': stroke_type,
            'equipmentType': {
                'equipmentTypeId': 0,
                'equipmentTypeKey': None,
                'displayOrder': 0
            },
            'weightValue': -1.0,
            'weightUnit': {
                'unitId': 8,
                'unitKey': 'kilogram',
                'factor': 1000.0
            }
        })
        
        # Cool-down (10 minutes)
        steps.append({
            'type': 'ExecutableStepDTO',
            'stepOrder': 3,
            'stepType': {
                'stepTypeId': 2,
                'stepTypeKey': 'cooldown',
                'displayOrder': 2
            },
            'endCondition': {
                'conditionTypeId': 2,
                'conditionTypeKey': 'time',
                'displayOrder': 2,
                'displayable': True
            },
            'endConditionValue': 600.0,  # 10 minutes
            'endConditionCompare': '' if sport_type == 'swimming' else 'gt',
            'targetType': {
                'workoutTargetTypeId': 4,
                'workoutTargetTypeKey': 'heart.rate.zone',
                'displayOrder': 4
            },
            'zoneNumber': 1,  # Zone 1 for cool-down
            'strokeType': stroke_type,
            'equipmentType': {
                'equipmentTypeId': 0,
                'equipmentTypeKey': None,
                'displayOrder': 0
            },
            'weightValue': -1.0,
            'weightUnit': {
                'unitId': 8,
                'unitKey': 'kilogram',
                'factor': 1000.0
            }
        })
        
        return steps
    
    def _create_interval_steps(self, sport_type: str, duration: int, description: str) -> List[Dict[str, Any]]:
        """Create interval workout steps."""
        steps = []
        
        # Extract interval details from description
        interval_match = re.search(r'(\d+)\s*x\s*(\d+)[-\s]*(?:minute|min)', description, re.IGNORECASE)
        
        if interval_match:
            num_intervals = int(interval_match.group(1))
            interval_duration = int(interval_match.group(2))
        else:
            # Default intervals
            num_intervals = 4
            interval_duration = 5
        
        # Determine stroke type for swimming
        stroke_type = {
            'strokeTypeId': 6 if sport_type == 'swimming' else 0,
            'strokeTypeKey': 'free' if sport_type == 'swimming' else None,
            'displayOrder': 6 if sport_type == 'swimming' else 0
        }
        
        # Warm-up (15 minutes)
        steps.append({
            'type': 'ExecutableStepDTO',
            'stepOrder': 1,
            'stepType': {
                'stepTypeId': 1,
                'stepTypeKey': 'warmup',
                'displayOrder': 1
            },
            'endCondition': {
                'conditionTypeId': 2,
                'conditionTypeKey': 'time',
                'displayOrder': 2,
                'displayable': True
            },
            'endConditionValue': 900.0,  # 15 minutes
            'endConditionCompare': '' if sport_type == 'swimming' else 'gt',
            'targetType': {
                'workoutTargetTypeId': 4,
                'workoutTargetTypeKey': 'heart.rate.zone',
                'displayOrder': 4
            },
            'zoneNumber': 2,
            'strokeType': stroke_type,
            'equipmentType': {
                'equipmentTypeId': 0,
                'equipmentTypeKey': None,
                'displayOrder': 0
            },
            'weightValue': -1.0,
            'weightUnit': {
                'unitId': 8,
                'unitKey': 'kilogram',
                'factor': 1000.0
            }
        })
        
        # Create repeat group for intervals
        interval_steps = []
        
        # Work interval
        interval_steps.append({
            'type': 'ExecutableStepDTO',
            'stepOrder': 3,
            'stepType': {
                'stepTypeId': 8 if sport_type == 'swimming' else 3,
                'stepTypeKey': 'main' if sport_type == 'swimming' else 'interval',
                'displayOrder': 8 if sport_type == 'swimming' else 3
            },
            'childStepId': 1,
            'endCondition': {
                'conditionTypeId': 2,
                'conditionTypeKey': 'time',
                'displayOrder': 2,
                'displayable': True
            },
            'endConditionValue': float(interval_duration * 60),
            'endConditionCompare': '',
            'targetType': {
                'workoutTargetTypeId': 4,
                'workoutTargetTypeKey': 'heart.rate.zone',
                'displayOrder': 4
            },
            'zoneNumber': 4,  # Zone 4 for intervals
            'strokeType': stroke_type,
            'equipmentType': {
                'equipmentTypeId': 0,
                'equipmentTypeKey': None,
                'displayOrder': 0
            },
            'weightValue': -1.0,
            'weightUnit': {
                'unitId': 8,
                'unitKey': 'kilogram',
                'factor': 1000.0
            }
        })
        
        # Recovery interval
        interval_steps.append({
            'type': 'ExecutableStepDTO',
            'stepOrder': 4,
            'stepType': {
                'stepTypeId': 5 if sport_type == 'swimming' else 4,
                'stepTypeKey': 'rest' if sport_type == 'swimming' else 'recovery',
                'displayOrder': 5 if sport_type == 'swimming' else 4
            },
            'childStepId': 1,
            'endCondition': {
                'conditionTypeId': 2,
                'conditionTypeKey': 'time',
                'displayOrder': 2,
                'displayable': True
            },
            'endConditionValue': float(interval_duration * 60),  # Same duration for recovery
            'endConditionCompare': '',
            'targetType': {
                'workoutTargetTypeId': 4,
                'workoutTargetTypeKey': 'heart.rate.zone',
                'displayOrder': 4
            },
            'zoneNumber': 2,  # Zone 2 for recovery
            'strokeType': {
                'strokeTypeId': 0,
                'strokeTypeKey': None,
                'displayOrder': 0
            },
            'equipmentType': {
                'equipmentTypeId': 0,
                'equipmentTypeKey': None,
                'displayOrder': 0
            },
            'weightValue': -1.0,
            'weightUnit': {
                'unitId': 8,
                'unitKey': 'kilogram',
                'factor': 1000.0
            }
        })
        
        # Repeat group
        steps.append({
            'type': 'RepeatGroupDTO',
            'stepOrder': 2,
            'stepType': {
                'stepTypeId': 6,
                'stepTypeKey': 'repeat',
                'displayOrder': 6
            },
            'childStepId': 1,
            'numberOfIterations': num_intervals,
            'workoutSteps': interval_steps,
            'endConditionValue': float(num_intervals),
            'endCondition': {
                'conditionTypeId': 7,
                'conditionTypeKey': 'iterations',
                'displayOrder': 7,
                'displayable': False
            },
            'skipLastRestStep': True,
            'smartRepeat': False
        })
        
        # Cool-down
        steps.append({
            'type': 'ExecutableStepDTO',
            'stepOrder': 5,
            'stepType': {
                'stepTypeId': 2,
                'stepTypeKey': 'cooldown',
                'displayOrder': 2
            },
            'endCondition': {
                'conditionTypeId': 2,
                'conditionTypeKey': 'time',
                'displayOrder': 2,
                'displayable': True
            },
            'endConditionValue': 600.0,  # 10 minutes
            'endConditionCompare': '' if sport_type == 'swimming' else 'gt',
            'targetType': {
                'workoutTargetTypeId': 4,
                'workoutTargetTypeKey': 'heart.rate.zone',
                'displayOrder': 4
            },
            'zoneNumber': 1,  # Zone 1 for cool-down
            'strokeType': stroke_type,
            'equipmentType': {
                'equipmentTypeId': 0,
                'equipmentTypeKey': None,
                'displayOrder': 0
            },
            'weightValue': -1.0,
            'weightUnit': {
                'unitId': 8,
                'unitKey': 'kilogram',
                'factor': 1000.0
            }
        })
        
        return steps
    
    def upload_workout(self, workout: Dict[str, Any]) -> Optional[str]:
        """
        Upload a structured workout to Garmin Connect.
        
        Args:
            workout: Structured workout dictionary
            
        Returns:
            Workout ID if successful, None otherwise
        """
        try:
            self.authenticate()
            
            # Create a clean workout for upload (remove scheduling info for workout creation)
            upload_workout = {k: v for k, v in workout.items() 
                            if k not in ['scheduledDate', 'scheduledTime', 'scheduledDateTime']}
            
            # Upload workout to Garmin Connect
            response = garth.connectapi(
                "/workout-service/workout",
                method="POST",
                json=upload_workout
            )
            
            if response and 'workoutId' in response:
                workout_id = response['workoutId']
                
                # Enhanced success message with scheduling info
                if workout.get('scheduledTime'):
                    print(f"✅ Uploaded: {workout['workoutName']} (ID: {workout_id})")
                    print(f"   📅 Scheduled for: {workout['scheduledDate']} at {workout['scheduledTime']}")
                    print(f"   📱 Manual scheduling: Open Garmin Connect app → Workouts → Select workout → Schedule")
                else:
                    print(f"✅ Uploaded workout: {workout['workoutName']} (ID: {workout_id})")
                
                return str(workout_id)
            else:
                print(f"❌ Failed to upload workout: {workout['workoutName']}")
                return None
                
        except Exception as e:
            print(f"❌ Error uploading workout {workout['workoutName']}: {e}")
            return None
    
    def create_calendar_export(self, workouts: List[Dict[str, Any]], filename: str = "workout_schedule") -> str:
        """
        Create calendar export files for external calendar systems.
        
        Args:
            workouts: List of structured workout dictionaries
            filename: Base filename for export files
            
        Returns:
            Path to created calendar file
        """
        try:
            from datetime import datetime
            import csv
            
            # Create CSV export for easy import into calendar systems
            csv_filename = f"{filename}.csv"
            
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Subject', 'Start Date', 'Start Time', 'End Date', 'End Time',
                    'All Day Event', 'Description', 'Location', 'Categories'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for workout in workouts:
                    if workout.get('scheduledDate') and workout.get('scheduledTime'):
                        # Calculate end time
                        start_datetime = datetime.fromisoformat(workout['scheduledDateTime'])
                        duration_minutes = workout['estimatedDurationInSecs'] // 60
                        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
                        
                        # Create calendar entry
                        writer.writerow({
                            'Subject': workout['workoutName'],
                            'Start Date': workout['scheduledDate'],
                            'Start Time': workout['scheduledTime'],
                            'End Date': end_datetime.strftime('%Y-%m-%d'),
                            'End Time': end_datetime.strftime('%H:%M'),
                            'All Day Event': 'False',
                            'Description': workout.get('description', ''),
                            'Location': 'Garmin Connect Workout',
                            'Categories': 'Fitness,Training'
                        })
            
            print(f"📅 Calendar export created: {csv_filename}")
            print(f"   Import this file into Google Calendar, Outlook, or Apple Calendar")
            
            return csv_filename
            
        except Exception as e:
            print(f"❌ Error creating calendar export: {e}")
            return ""
    
    def create_scheduling_summary(self, workouts: List[Dict[str, Any]]) -> str:
        """
        Create a human-readable scheduling summary.
        
        Args:
            workouts: List of structured workout dictionaries
            
        Returns:
            Formatted scheduling summary
        """
        if not workouts:
            return "No workouts to schedule."
        
        summary_lines = [
            "📋 WORKOUT SCHEDULE SUMMARY",
            "=" * 50,
            ""
        ]
        
        # Group workouts by date
        from collections import defaultdict
        workouts_by_date = defaultdict(list)
        
        for workout in workouts:
            if workout.get('scheduledDate'):
                workouts_by_date[workout['scheduledDate']].append(workout)
        
        # Sort dates
        sorted_dates = sorted(workouts_by_date.keys())
        
        for date in sorted_dates:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_name = date_obj.strftime('%A')
            formatted_date = date_obj.strftime('%B %d, %Y')
            
            summary_lines.append(f"📅 {day_name}, {formatted_date}")
            summary_lines.append("-" * 30)
            
            # Sort workouts by time
            day_workouts = sorted(workouts_by_date[date], 
                                key=lambda w: w.get('scheduledTime', '00:00'))
            
            for workout in day_workouts:
                time_str = workout.get('scheduledTime', 'No time')
                if time_str != 'No time':
                    try:
                        time_obj = datetime.strptime(time_str, '%H:%M')
                        time_12h = time_obj.strftime('%I:%M %p').lstrip('0')
                    except ValueError:
                        time_12h = time_str
                else:
                    time_12h = 'No time'
                
                duration_min = workout['estimatedDurationInSecs'] // 60
                sport_type = workout['sportType']['sportTypeKey'].replace('_', ' ').title()
                
                summary_lines.append(f"  ⏰ {time_12h} - {workout['workoutName']}")
                summary_lines.append(f"     🏃 {sport_type} • {duration_min} minutes")
                summary_lines.append("")
            
            summary_lines.append("")
        
        summary_lines.extend([
            "📱 SCHEDULING INSTRUCTIONS:",
            "1. Open Garmin Connect app or website",
            "2. Go to Training → Workouts",
            "3. Find your uploaded workout",
            "4. Tap/click 'Schedule' or 'Add to Calendar'",
            "5. Set the date and time as shown above",
            "",
            "💡 TIP: You can also import the CSV file into your calendar app!"
        ])
        
        return "\n".join(summary_lines)
    
    def _schedule_workout(self, workout_id: str, workout: Dict[str, Any]) -> bool:
        """
        Schedule a workout in Garmin Connect calendar.
        
        Args:
            workout_id: The ID of the uploaded workout
            workout: Workout dictionary with scheduling information
            
        Returns:
            True if scheduling was successful, False otherwise
        """
        try:
            scheduled_datetime = workout.get('scheduledDateTime')
            if not scheduled_datetime:
                return False
            
            # Parse the scheduled datetime
            from datetime import datetime
            dt = datetime.fromisoformat(scheduled_datetime.replace('Z', '+00:00'))
            
            # Create calendar event for the workout
            calendar_event = {
                'workoutId': int(workout_id),
                'date': workout['scheduledDate'],
                'startTime': workout['scheduledTime'],
                'workoutName': workout['workoutName'],
                'sportType': workout['sportType'],
                'estimatedDurationInSecs': workout['estimatedDurationInSecs'],
                'description': workout.get('description', ''),
                # Convert to Garmin's expected format
                'scheduledDate': int(dt.timestamp() * 1000),  # Garmin uses milliseconds
                'timeZoneId': 'Europe/Lisbon',  # You might want to make this configurable
            }
            
            # Try to schedule the workout using Garmin's calendar API
            # Note: This endpoint might need adjustment based on Garmin's actual API
            try:
                response = garth.connectapi(
                    "/calendar-service/calendar/workouts",
                    method="POST",
                    json=calendar_event
                )
                return response is not None
            except Exception as calendar_error:
                # Try alternative scheduling approach
                print(f"🔄 Trying alternative scheduling method...")
                return self._schedule_workout_alternative(workout_id, workout)
                
        except Exception as e:
            print(f"❌ Error scheduling workout: {e}")
            return False
    
    def _schedule_workout_alternative(self, workout_id: str, workout: Dict[str, Any]) -> bool:
        """
        Alternative method to schedule workout using training calendar.
        
        Args:
            workout_id: The ID of the uploaded workout
            workout: Workout dictionary with scheduling information
            
        Returns:
            True if scheduling was successful, False otherwise
        """
        try:
            # Try using the training calendar endpoint
            scheduled_date = workout.get('scheduledDate')
            if not scheduled_date:
                return False
            
            training_event = {
                'date': scheduled_date,
                'workoutId': int(workout_id),
                'completed': False,
                'scheduled': True
            }
            
            response = garth.connectapi(
                f"/calendar-service/calendar/{scheduled_date}/workouts",
                method="POST",
                json=training_event
            )
            
            return response is not None
            
        except Exception as e:
            print(f"❌ Alternative scheduling failed: {e}")
            return False
    
    def save_structured_workouts(self, workouts: List[Dict[str, Any]], filename: str) -> str:
        """
        Save structured workouts to a JSON file.
        
        Args:
            workouts: List of structured workout dictionaries
            filename: Output filename
            
        Returns:
            Full path to saved file
        """
        import json
        from pathlib import Path
        
        # Ensure filename has .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        # Convert to absolute path
        filepath = Path(filename).resolve()
        
        # Save workouts to JSON file
        with open(filepath, 'w') as f:
            json.dump(workouts, f, indent=2, default=str)
        
        return str(filepath)
    
    def upload_workouts_from_plan(self, plan_file: str) -> Dict[str, Any]:
        """
        Parse and upload all workouts from a plan file.
        
        Args:
            plan_file: Path to the workout plan file
            
        Returns:
            Dictionary with upload results
        """
        try:
            with open(plan_file, 'r', encoding='utf-8') as f:
                plan_text = f.read()
            
            print(f"📖 Parsing workout plan from {plan_file}")
            workouts = self.parse_workout_plan(plan_text)
            
            if not workouts:
                print("⚠️  No workouts found in the plan")
                return {'success': False, 'uploaded': 0, 'total': 0, 'errors': []}
            
            print(f"🏃 Found {len(workouts)} workouts to upload")
            
            uploaded_ids = []
            errors = []
            
            for workout in workouts:
                workout_id = self.upload_workout(workout)
                if workout_id:
                    uploaded_ids.append(workout_id)
                else:
                    errors.append(workout['workoutName'])
            
            result = {
                'success': len(uploaded_ids) > 0,
                'uploaded': len(uploaded_ids),
                'total': len(workouts),
                'workout_ids': uploaded_ids,
                'errors': errors
            }
            
            print(f"\n📊 Upload complete: {result['uploaded']}/{result['total']} workouts uploaded")
            if errors:
                print(f"❌ Failed uploads: {', '.join(errors)}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error processing plan file: {e}")
            return {'success': False, 'uploaded': 0, 'total': 0, 'errors': [str(e)]}
    
    def save_structured_workouts(self, workouts: List[Dict[str, Any]], output_file: str) -> str:
        """
        Save structured workouts to a JSON file.
        
        Args:
            workouts: List of structured workout dictionaries
            output_file: Output file path
            
        Returns:
            Path to the saved file
        """
        output_path = Path(output_file)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(workouts, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"💾 Structured workouts saved to: {output_path.absolute()}")
            return str(output_path.absolute())
            
        except Exception as e:
            error_msg = f"❌ Error saving structured workouts: {e}"
            print(error_msg)
            return error_msg
