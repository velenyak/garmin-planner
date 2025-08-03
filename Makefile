.PHONY: install dev test lint format clean run download list plan upload plan-upload help

# Install dependencies
install:
	pipenv install

# Install dev dependencies
dev:
	pipenv install --dev

# Install package in development mode
install-dev:
	pipenv run pip install -e .

# Run the application (legacy)
run:
	pipenv run python -m garmin_planner.cli

# Download activities (default: 2 weeks)
download:
	pipenv run python -m garmin_planner.cli download --weeks 2

# Download activities for specific weeks
download-weeks:
	@read -p "Enter number of weeks: " weeks; \
	pipenv run python -m garmin_planner.cli download --weeks $$weeks

# List downloaded activities
list:
	pipenv run python -m garmin_planner.cli list-activities

# Generate workout plan using Gemini AI
plan:
	pipenv run python -m garmin_planner.cli generate-plan

# Generate workout plan for specific weeks
plan-weeks:
	@read -p "Enter number of weeks to plan: " weeks; \
	pipenv run python -m garmin_planner.cli generate-plan --weeks $$weeks

# Integrated: Generate plan and upload scheduled workouts
plan-upload:
	pipenv run python -m garmin_planner.cli plan-and-upload --verbose

# Integrated: Generate plan and upload for specific weeks
plan-upload-weeks:
	@read -p "Enter number of weeks to plan: " weeks; \
	pipenv run python -m garmin_planner.cli plan-and-upload --weeks $$weeks --verbose

# Upload workouts to Garmin Connect
upload:
	@read -p "Enter workout plan file: " plan_file; \
	pipenv run python -m garmin_planner.cli upload-workouts "$$plan_file"

# Upload workouts with dry run (preview only)
upload-preview:
	@read -p "Enter workout plan file: " plan_file; \
	pipenv run python -m garmin_planner.cli upload-workouts "$$plan_file" --dry-run --verbose

# Run tests
test:
	pipenv run pytest

# Lint code
lint:
	pipenv run flake8 garmin_planner/
	pipenv run mypy garmin_planner/

# Format code
format:
	pipenv run black garmin_planner/

# Clean up generated files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/

# Show help
help:
	@echo "Available commands:"
	@echo "  install      - Install dependencies"
	@echo "  dev          - Install dev dependencies"
	@echo "  install-dev  - Install package in development mode"
	@echo "  run          - Run the application"
	@echo "  download     - Download last 2 weeks of activities"
	@echo "  download-weeks - Download activities for specific weeks"
	@echo "  list         - List downloaded activities"
	@echo "  plan         - Generate workout plan using Gemini AI"
	@echo "  plan-weeks   - Generate workout plan for specific weeks"
	@echo "  plan-upload  - 🚀 Generate plan and upload scheduled workouts"
	@echo "  plan-upload-weeks - 🚀 Generate and upload for specific weeks"
	@echo "  upload       - Upload workouts to Garmin Connect"
	@echo "  upload-preview - Preview workout upload (dry run)"
	@echo "  test         - Run tests"
	@echo "  lint         - Lint code"
	@echo "  format       - Format code"
	@echo "  clean        - Clean up generated files"
