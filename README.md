# Garmin Workout Planner

A Python tool to download and save Garmin Connect activities as JSON files for analysis and planning.

## Features

- Download activities from the last N weeks (default: 2 weeks)
- Save each activity as a detailed JSON file
- Generate summary file with all activities
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

Create a `.env` file in the project root with your Garmin Connect credentials:

```env
GARMIN_EMAIL=your.email@example.com
GARMIN_PASSWORD=your_password
```

Alternatively, you can set environment variables:

```bash
export GARMIN_EMAIL="your.email@example.com"
export GARMIN_PASSWORD="your_password"
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

#### All CLI options
```bash
python -m garmin_planner.cli --help
```

### Programmatic Usage

```python
from garmin_planner import GarminActivityDownloader
import os

# Initialize downloader
downloader = GarminActivityDownloader(
    email=os.getenv('GARMIN_EMAIL'),
    password=os.getenv('GARMIN_PASSWORD'),
    output_dir="my_activities"
)

# Download activities
result = downloader.download_activities(weeks=2)

print(f"Downloaded {result['downloaded']}/{result['total']} activities")
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

## Make Commands

```bash
make help           # Show all available commands
make install        # Install dependencies
make dev            # Install dev dependencies
make download       # Download last 2 weeks of activities
make download-weeks # Download activities for specific weeks (interactive)
make list           # List downloaded activities
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
│   └── downloader.py       # Core download functionality
├── tests/                   # Test files (future)
├── .env                    # Environment variables (create this)
├── .gitignore             # Git ignore rules
├── Makefile               # Make commands
├── Pipfile                # Pipenv dependencies
├── README.md              # This file
└── setup.py               # Package setup
```

## Authentication

The tool uses the `garth` library for Garmin Connect authentication. Session tokens are automatically saved and reused to minimize login requests.

Session files are stored in `~/.garth` and will be reused across runs.

## Error Handling

- Invalid credentials will show clear error messages
- Network issues are handled gracefully with retries
- Individual activity download failures won't stop the entire process
- Verbose mode shows detailed error information

## Security Notes

- Never commit your `.env` file to version control
- Use environment variables in production environments
- Session tokens are stored securely in your home directory

## Contributing

1. Install development dependencies: `make dev`
2. Format code: `make format`
3. Run linting: `make lint`
4. Run tests: `make test`

## License

This project is for personal use. Please respect Garmin's terms of service when using this tool.
