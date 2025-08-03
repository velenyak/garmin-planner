# Garmin Workout Planner

A Python tool to download and save Garmin Connect activities as JSON files and generate AI-powered workout plans using Google Gemini.

## Features

- Download activities from the last N weeks (default: 2 weeks)
- Save each activity as a detailed JSON file
- Generate summary file with all activities
- **🤖 AI-powered workout plan generation using Google Gemini**
- **📝 Customizable training context and goals**
- Command-line interface with multiple options
- Secure credential management via environment variables
- Resume existing Garmin sessions automatically

## Installation

### Using pipenv (recommended)

```bash
# Install dependencies
make install

# Install development dependencies (optional)
make dev

# Install package in development mode
make install-dev
```

### Manual installation

```bash
pip install -e .
```

## Configuration

Create a `.env` file in the project root with your credentials:

```env
GARMIN_EMAIL=your.email@example.com
GARMIN_PASSWORD=your_password
GEMINI_API_KEY=your_gemini_api_key_here
```

### Getting API Keys

- **Garmin Connect**: Use your regular Garmin Connect login credentials
- **Google Gemini**: Get your API key at [Google AI Studio](https://makersuite.google.com/app/apikey)

Alternatively, you can set environment variables:

```bash
export GARMIN_EMAIL="your.email@example.com"
export GARMIN_PASSWORD="your_password"
export GEMINI_API_KEY="your_gemini_api_key_here"
```

## Usage

### Command Line Interface

#### Basic usage (download last 2 weeks)
```bash
# Using make
make download

# Using Python module
python -m garmin_planner.cli

# Using installed command (if installed with pip)
garmin-download
```

#### Advanced usage
```bash
# Download last 4 weeks
python -m garmin_planner.cli --weeks 4

# Custom output directory
python -m garmin_planner.cli --output-dir my_activities

# Verbose output
python -m garmin_planner.cli --verbose

# Provide credentials via command line
python -m garmin_planner.cli --email your@email.com --password yourpass

# List downloaded activities
python -m garmin_planner.cli list-activities
```

#### 🤖 AI Workout Plan Generation

```bash
# Generate workout plan using Gemini AI
make plan

# Generate plan for multiple weeks
python -m garmin_planner.cli generate-plan --weeks 2

# Custom context file and output
python -m garmin_planner.cli generate-plan \
  --context-file my_goals.txt \
  --output-file my_plan.md \
  --verbose

# Interactive weeks selection
make plan-weeks
```

#### All CLI options
```bash
python -m garmin_planner.cli --help
python -m garmin_planner.cli generate-plan --help
```

### Programmatic Usage

```python
from garmin_planner import GarminActivityDownloader, GeminiWorkoutPlanner
import os

# Download activities
downloader = GarminActivityDownloader(
    email=os.getenv('GARMIN_EMAIL'),
    password=os.getenv('GARMIN_PASSWORD'),
    output_dir="my_activities"
)

result = downloader.download_activities(weeks=2)
print(f"Downloaded {result['downloaded']}/{result['total']} activities")

# Generate workout plan
planner = GeminiWorkoutPlanner(api_key=os.getenv('GEMINI_API_KEY'))

workout_plan = planner.generate_workout_plan(
    context_file="training_context.txt",
    activities_dir="my_activities",
    weeks=1
)

saved_file = planner.save_workout_plan(workout_plan, "my_plan.md")
print(f"Plan saved to: {saved_file}")
```

## Training Context

The AI workout planner uses a `training_context.txt` file to understand your goals and preferences. If this file doesn't exist, a default template will be created automatically.

### Example training_context.txt:
```markdown
# Training Context

## Goals
- Improve cardiovascular endurance
- Prepare for upcoming triathlon
- Build functional strength

## Current Focus
- Building aerobic base
- Balancing swim, bike, run training
- Recovery and injury prevention

## Preferences
- Swimming: 2-3 sessions per week
- Cycling: 2-3 sessions per week  
- Running: 2-3 sessions per week
- Strength training: 2 sessions per week
- Complete rest: 1 day per week

## Constraints
- Available training time: 1-2 hours per day
- Training days: Monday-Saturday
- Equipment: Garmin watch, bike trainer, pool access

## Upcoming Events
- Next race: Spring triathlon 2025
- Target: Improve overall endurance

## Notes
- Prefers morning training
- Values data-driven approach
- Enjoys training variety
```

## Output Format

### Individual Activity Files

Each activity is saved as `YYYY-MM-DD_HH-MM_TYPE_NAME_ID.json` with structure:

```json
{
  "metadata": {
    "activity_id": "123456789",
    "name": "Morning Run",
    "type": "running",
    "start_time": "2024-01-15T08:30:00",
    "download_timestamp": "2024-01-20T10:15:00",
    "duration": 1800,
    "distance": 5000,
    "calories": 350
  },
  "garmin_data": {
    "summary": { /* Garmin activity summary */ },
    "details": { /* Detailed metrics and data */ }
  }
}
```

### Summary File

`activities_summary.json` contains overview of all downloaded activities:

```json
{
  "download_info": {
    "total_activities": 10,
    "download_timestamp": "2024-01-20T10:15:00",
    "date_range": {
      "start": "2024-01-01T08:00:00",
      "end": "2024-01-15T18:30:00"
    }
  },
  "activities": [
    {
      "activity_id": "123456789",
      "name": "Morning Run",
      "type": "running",
      "start_time": "2024-01-15T08:30:00",
      "duration": 1800,
      "distance": 5000,
      "calories": 350
    }
  ]
}
```

### 🤖 AI-Generated Workout Plans

Workout plans are saved as Markdown files with:

- **Weekly Overview**: Training focus and objectives
- **Daily Workouts**: Detailed day-by-day plan with:
  - Activity type and duration
  - Intensity zones and specific workouts
  - Recovery recommendations
- **Training Principles**: Progression and periodization
- **Key Recommendations**: Focus areas and tips

## Make Commands

```bash
make help           # Show all available commands
make install        # Install dependencies
make dev            # Install dev dependencies
make download       # Download last 2 weeks of activities
make download-weeks # Download activities for specific weeks (interactive)
make list           # List downloaded activities
make plan           # Generate AI workout plan
make plan-weeks     # Generate plan for specific weeks (interactive)
make test           # Run tests
make lint           # Lint code
make format         # Format code with black
make clean          # Clean up generated files
```

## Project Structure

```
garmin-workout-planner/
├── garmin_planner/          # Main package
│   ├── __init__.py         # Package initialization
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration management
│   ├── downloader.py       # Core download functionality
│   └── gemini_client.py    # Google Gemini AI integration
├── tests/                   # Test files
├── training_context.txt     # Your training goals and context
├── .env                    # Environment variables (create this)
├── .gitignore             # Git ignore rules
├── Makefile               # Make commands
├── Pipfile                # Pipenv dependencies
├── README.md              # This file
└── setup.py               # Package setup
```

## Authentication

### Garmin Connect
The tool uses the `garth` library for Garmin Connect authentication. Session tokens are automatically saved and reused to minimize login requests.

Session files are stored in `~/.garth` and will be reused across runs.

### Google Gemini
Uses the official Google Generative AI library. Requires a valid API key from Google AI Studio.

## Error Handling

- Invalid credentials will show clear error messages
- Network issues are handled gracefully with retries
- Individual activity download failures won't stop the entire process
- AI generation errors are caught and reported clearly
- Verbose mode shows detailed error information

## Security Notes

- Never commit your `.env` file to version control
- Use environment variables in production environments
- Session tokens are stored securely in your home directory
- API keys are only used for their intended services

## Contributing

1. Install development dependencies: `make dev`
2. Format code: `make format`
3. Run linting: `make lint`
4. Run tests: `make test`

## License

This project is for personal use. Please respect Garmin's terms of service and Google's API usage policies when using this tool.
