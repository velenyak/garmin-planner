#!/usr/bin/env python3
"""
Command-line interface for Garmin activity downloader.
"""

import click
import os
from pathlib import Path
from dotenv import load_dotenv
from .downloader import GarminActivityDownloader
from .gemini_client import GeminiWorkoutPlanner
from .garmin_uploader import GarminWorkoutUploader


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    '--weeks', '-w',
    default=2,
    help='Number of weeks to look back for activities (default: 2)'
)
@click.option(
    '--output-dir', '-o',
    default='garmin_activities',
    help='Output directory for JSON files (default: garmin_activities)'
)
@click.option(
    '--email', '-e',
    help='Garmin Connect email (can also use GARMIN_EMAIL env var)'
)
@click.option(
    '--password', '-p',
    help='Garmin Connect password (can also use GARMIN_PASSWORD env var)'
)
@click.option(
    '--env-file',
    default='.env',
    help='Path to .env file (default: .env)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def cli(ctx, weeks, output_dir, email, password, env_file, verbose):
    """
    Garmin Workout Planner - Download and analyze Garmin activities.
    
    If no subcommand is provided, downloads activities from the last N weeks.
    """
    # If no subcommand was invoked, run the download functionality
    if ctx.invoked_subcommand is None:
        download_activities(weeks, output_dir, email, password, env_file, verbose)


def download_activities(weeks, output_dir, email, password, env_file, verbose):
    """Core download functionality."""
    # Load environment variables
    if Path(env_file).exists():
        load_dotenv(env_file)
        if verbose:
            click.echo(f"Loaded environment from {env_file}")
    
    # Get credentials
    garmin_email = email or os.getenv('GARMIN_EMAIL')
    garmin_password = password or os.getenv('GARMIN_PASSWORD')
    
    if not garmin_email or not garmin_password:
        click.echo("❌ Error: Garmin credentials not provided!", err=True)
        click.echo("\nPlease provide credentials via:")
        click.echo("  1. Command line: --email EMAIL --password PASSWORD")
        click.echo("  2. Environment variables: GARMIN_EMAIL, GARMIN_PASSWORD")
        click.echo("  3. .env file with GARMIN_EMAIL and GARMIN_PASSWORD")
        raise click.Abort()
    
    if verbose:
        click.echo(f"Email: {garmin_email}")
        click.echo(f"Weeks: {weeks}")
        click.echo(f"Output directory: {output_dir}")
    
    try:
        # Initialize downloader
        downloader = GarminActivityDownloader(
            email=garmin_email,
            password=garmin_password,
            output_dir=output_dir
        )
        
        # Download activities
        result = downloader.download_activities(weeks=weeks)
        
        if result['success']:
            click.echo(f"\n🎉 Successfully downloaded {result['downloaded']}/{result['total']} activities")
            click.echo(f"📁 Files saved to: {result['output_dir']}")
            
            # List created files
            output_path = Path(result['output_dir'])
            json_files = list(output_path.glob("*.json"))
            
            if verbose and json_files:
                click.echo(f"\n📄 Created {len(json_files)} files:")
                for file in sorted(json_files):
                    size_kb = file.stat().st_size / 1024
                    click.echo(f"   {file.name} ({size_kb:.1f} KB)")
        else:
            click.echo("❌ Download failed - no activities found", err=True)
            raise click.Abort()
            
    except KeyboardInterrupt:
        click.echo("\n⏹️  Download interrupted by user")
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        raise click.Abort()


@cli.command()
@click.option(
    '--weeks', '-w',
    default=2,
    help='Number of weeks to look back for activities (default: 2)'
)
@click.option(
    '--output-dir', '-o',
    default='garmin_activities',
    help='Output directory for JSON files (default: garmin_activities)'
)
@click.option(
    '--email', '-e',
    help='Garmin Connect email (can also use GARMIN_EMAIL env var)'
)
@click.option(
    '--password', '-p',
    help='Garmin Connect password (can also use GARMIN_PASSWORD env var)'
)
@click.option(
    '--env-file',
    default='.env',
    help='Path to .env file (default: .env)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def download(weeks, output_dir, email, password, env_file, verbose):
    """Download Garmin Connect activities and save them as JSON files."""
    download_activities(weeks, output_dir, email, password, env_file, verbose)


@cli.command()
@click.argument('directory', default='garmin_activities')
def list_activities(directory):
    """List downloaded activities in a directory."""
    output_path = Path(directory)
    
    if not output_path.exists():
        click.echo(f"❌ Directory {directory} does not exist", err=True)
        return
    
    json_files = list(output_path.glob("*.json"))
    json_files = [f for f in json_files if f.name != "activities_summary.json"]
    
    if not json_files:
        click.echo(f"No activity files found in {directory}")
        return
    
    click.echo(f"📊 Found {len(json_files)} activities in {directory}:")
    
    for file in sorted(json_files):
        size_kb = file.stat().st_size / 1024
        # Parse filename to extract info
        parts = file.stem.split('_')
        if len(parts) >= 3:
            date_time = parts[0] + '_' + parts[1]
            activity_type = parts[2]
            click.echo(f"   {date_time} | {activity_type:12} | {file.name} ({size_kb:.1f} KB)")
        else:
            click.echo(f"   {file.name} ({size_kb:.1f} KB)")


@cli.command()
@click.option(
    '--context-file', '-c',
    default='training_context.txt',
    help='Path to training context file (default: training_context.txt)'
)
@click.option(
    '--activities-dir', '-a',
    default='garmin_activities',
    help='Directory containing Garmin activities (default: garmin_activities)'
)
@click.option(
    '--weeks', '-w',
    default=1,
    help='Number of weeks to plan for (default: 1)'
)
@click.option(
    '--output-file', '-o',
    help='Output file for the workout plan (default: workout_plan_TIMESTAMP.md)'
)
@click.option(
    '--env-file',
    default='.env',
    help='Path to .env file (default: .env)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def generate_plan(context_file, activities_dir, weeks, output_file, env_file, verbose):
    """
    Generate a workout plan using Google Gemini AI.
    
    This command uses your recent Garmin activities and training context
    to generate a personalized workout plan for the next week(s).
    
    Requirements:
    - GEMINI_API_KEY in environment variables or .env file
    - Recent activities downloaded (use 'download' command first)
    - Optional: training_context.txt file with your goals and preferences
    """
    
    # Load environment variables
    if Path(env_file).exists():
        load_dotenv(env_file)
        if verbose:
            click.echo(f"Loaded environment from {env_file}")
    
    # Get Gemini API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        click.echo("❌ Error: GEMINI_API_KEY not found!", err=True)
        click.echo("\nPlease add your Google Gemini API key to:")
        click.echo("  1. Environment variable: GEMINI_API_KEY")
        click.echo("  2. .env file: GEMINI_API_KEY=your_api_key_here")
        click.echo("\nGet your API key at: https://makersuite.google.com/app/apikey")
        raise click.Abort()
    
    # Check if activities directory exists
    if not Path(activities_dir).exists():
        click.echo(f"❌ Activities directory {activities_dir} not found!", err=True)
        click.echo("Please download activities first using the 'download' command")
        raise click.Abort()
    
    # Check if context file exists, create default if not
    context_path = Path(context_file)
    if not context_path.exists():
        click.echo(f"📝 Creating default training context file: {context_file}")
        create_default_context_file(context_path)
    
    if verbose:
        click.echo(f"Context file: {context_file}")
        click.echo(f"Activities directory: {activities_dir}")
        click.echo(f"Planning weeks: {weeks}")
        if output_file:
            click.echo(f"Output file: {output_file}")
    
    try:
        # Initialize Gemini client
        planner = GeminiWorkoutPlanner(api_key=api_key)
        
        # Generate workout plan
        workout_plan = planner.generate_workout_plan(
            context_file=context_file,
            activities_dir=activities_dir,
            weeks=weeks
        )
        
        # Save the plan
        saved_file = planner.save_workout_plan(workout_plan, output_file)
        
        click.echo(f"\n🎯 Workout plan generated successfully!")
        click.echo(f"📄 Plan saved to: {saved_file}")
        
        # Show preview if verbose
        if verbose:
            click.echo("\n📖 Plan preview (first 500 characters):")
            click.echo("-" * 50)
            click.echo(workout_plan[:500] + "..." if len(workout_plan) > 500 else workout_plan)
            click.echo("-" * 50)
            
    except KeyboardInterrupt:
        click.echo("\n⏹️  Plan generation interrupted by user")
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Error generating workout plan: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        raise click.Abort()


@cli.command()
@click.option(
    '--weeks', '-w',
    default=1,
    help='Number of weeks to plan for (default: 1)'
)
@click.option(
    '--context-file',
    default='training_context.txt',
    help='Path to training context file (default: training_context.txt)'
)
@click.option(
    '--activities-dir',
    default='garmin_activities',
    help='Directory containing Garmin activities (default: garmin_activities)'
)
@click.option(
    '--email', '-e',
    help='Garmin Connect email (can also use GARMIN_EMAIL env var)'
)
@click.option(
    '--password', '-p',
    help='Garmin Connect password (can also use GARMIN_PASSWORD env var)'
)
@click.option(
    '--env-file',
    default='.env',
    help='Path to .env file (default: .env)'
)
@click.option(
    '--save-plan',
    help='Save the generated plan to a file'
)
@click.option(
    '--save-structured',
    help='Save structured workouts to JSON file'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Generate plan and parse workouts without uploading'
)
@click.option(
    '--save-calendar',
    help='Export workout schedule to calendar CSV file'
)
@click.option(
    '--show-schedule',
    is_flag=True,
    help='Show detailed scheduling summary'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def plan_and_upload(weeks, context_file, activities_dir, email, password, env_file, 
                   save_plan, save_structured, save_calendar, show_schedule, dry_run, verbose):
    """
    Generate AI workout plan and upload scheduled workouts to Garmin Connect.
    
    This command provides an integrated workflow:
    1. Generate AI-powered workout plan using Google Gemini
    2. Parse workouts with dates and times
    3. Upload structured workouts to Garmin Connect
    4. Schedule workouts in Garmin's calendar
    
    Requirements:
    - GARMIN_EMAIL, GARMIN_PASSWORD, and GEMINI_API_KEY in environment variables or .env file
    - Training context file (will create default if missing)
    - Recent Garmin activities for AI analysis
    
    Example:
        python -m garmin_planner.cli plan-and-upload --weeks 2 --verbose
    """
    
    # Load environment variables
    if Path(env_file).exists():
        load_dotenv(env_file)
        if verbose:
            click.echo(f"Loaded environment from {env_file}")
    
    # Get credentials
    garmin_email = email or os.getenv('GARMIN_EMAIL')
    garmin_password = password or os.getenv('GARMIN_PASSWORD')
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    
    if not garmin_email or not garmin_password:
        click.echo("❌ Error: Garmin credentials not provided!", err=True)
        click.echo("\nPlease provide credentials via:")
        click.echo("  1. Command line: --email EMAIL --password PASSWORD")
        click.echo("  2. Environment variables: GARMIN_EMAIL, GARMIN_PASSWORD")
        click.echo("  3. .env file with GARMIN_EMAIL and GARMIN_PASSWORD")
        raise click.Abort()
    
    if not gemini_api_key:
        click.echo("❌ Error: GEMINI_API_KEY not found!", err=True)
        click.echo("\nPlease set GEMINI_API_KEY in:")
        click.echo("  1. Environment variable: export GEMINI_API_KEY=your_key")
        click.echo("  2. .env file: GEMINI_API_KEY=your_key")
        raise click.Abort()
    
    if verbose:
        click.echo(f"Planning weeks: {weeks}")
        click.echo(f"Context file: {context_file}")
        click.echo(f"Activities directory: {activities_dir}")
        click.echo(f"Email: {garmin_email}")
        click.echo(f"Dry run: {dry_run}")
    
    try:
        # Step 1: Generate AI workout plan
        click.echo("🤖 Step 1: Generating AI workout plan...")
        
        planner = GeminiWorkoutPlanner(api_key=gemini_api_key)
        workout_plan = planner.generate_workout_plan(
            context_file=context_file,
            activities_dir=activities_dir,
            weeks=weeks
        )
        
        if workout_plan.startswith("❌"):
            click.echo(f"Failed to generate plan: {workout_plan}", err=True)
            raise click.Abort()
        
        # Save plan if requested
        if save_plan:
            plan_file = planner.save_workout_plan(workout_plan, save_plan)
            click.echo(f"💾 Plan saved to: {plan_file}")
        
        # Step 2: Parse and structure workouts
        click.echo("🔧 Step 2: Parsing workouts with scheduling information...")
        
        uploader = GarminWorkoutUploader(
            email=garmin_email,
            password=garmin_password
        )
        
        workouts = uploader.parse_workout_plan(workout_plan)
        
        if not workouts:
            click.echo("⚠️  No workouts found in the generated plan")
            return
        
        click.echo(f"🏃 Found {len(workouts)} workouts with scheduling information")
        
        # Show workout preview
        if verbose:
            click.echo("\n📋 Workout schedule preview:")
            for i, workout in enumerate(workouts, 1):
                scheduled_info = ""
                if workout.get('scheduledDate') and workout.get('scheduledTime'):
                    scheduled_info = f" → {workout['scheduledDate']} at {workout['scheduledTime']}"
                click.echo(f"  {i}. {workout['workoutName']}{scheduled_info}")
        
        # Save structured workouts if requested
        if save_structured:
            saved_file = uploader.save_structured_workouts(workouts, save_structured)
            click.echo(f"💾 Structured workouts saved to: {saved_file}")
        
        # Create calendar export if requested
        if save_calendar:
            calendar_file = uploader.create_calendar_export(workouts, save_calendar)
            if calendar_file:
                click.echo(f"📅 Calendar export saved to: {calendar_file}")
        
        # Show scheduling summary if requested
        if show_schedule or verbose:
            schedule_summary = uploader.create_scheduling_summary(workouts)
            click.echo(f"\n{schedule_summary}")
        
        if dry_run:
            click.echo("\n🔍 Dry run complete - no workouts uploaded")
            if not save_calendar and len(workouts) > 0:
                click.echo("💡 Use --save-calendar to export schedule for your calendar app")
            return
        
        # Step 3: Upload workouts
        click.echo("🚀 Step 3: Uploading workouts to Garmin Connect...")
        
        uploaded_ids = []
        errors = []
        
        for workout in workouts:
            workout_id = uploader.upload_workout(workout)
            if workout_id:
                uploaded_ids.append(workout_id)
            else:
                errors.append(workout['workoutName'])
        
        # Create calendar export automatically if workouts were uploaded
        if uploaded_ids and not save_calendar:
            calendar_file = uploader.create_calendar_export(workouts, "workout_schedule")
        
        # Summary
        click.echo(f"\n📊 Integration complete:")
        click.echo(f"   Generated plan: ✅")
        click.echo(f"   Uploaded workouts: {len(uploaded_ids)}/{len(workouts)}")
        
        if uploaded_ids:
            click.echo(f"   Workout IDs: {', '.join(uploaded_ids)}")
        
        if errors:
            click.echo(f"   Failed uploads: {', '.join(errors)}")
        
        if len(uploaded_ids) > 0:
            click.echo(f"\n🎉 Successfully uploaded {len(uploaded_ids)} workouts!")
            click.echo(f"📱 NEXT STEPS:")
            click.echo(f"   1. Open Garmin Connect app/website")
            click.echo(f"   2. Go to Training → Workouts")
            click.echo(f"   3. Find your workouts (they include date/time in the name)")
            click.echo(f"   4. Tap 'Schedule' to add them to your calendar")
            click.echo(f"   5. Or import workout_schedule.csv into your calendar app")
            
            if not show_schedule:
                click.echo(f"\n💡 Use --show-schedule to see detailed scheduling information")
        else:
            click.echo("❌ No workouts were uploaded successfully", err=True)
            
    except KeyboardInterrupt:
        click.echo("\n⏹️  Process interrupted by user")
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Error in integrated workflow: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        raise click.Abort()


@cli.command()
@click.argument('plan_file')
@click.option(
    '--email', '-e',
    help='Garmin Connect email (can also use GARMIN_EMAIL env var)'
)
@click.option(
    '--password', '-p',
    help='Garmin Connect password (can also use GARMIN_PASSWORD env var)'
)
@click.option(
    '--env-file',
    default='.env',
    help='Path to .env file (default: .env)'
)
@click.option(
    '--save-structured',
    help='Save structured workouts to JSON file before uploading'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Parse and structure workouts without uploading'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def upload_workouts(plan_file, email, password, env_file, save_structured, dry_run, verbose):
    """
    Upload structured workouts to Garmin Connect from a workout plan.
    
    This command parses a Gemini-generated workout plan and uploads
    the structured workouts to your Garmin Connect account.
    
    Requirements:
    - GARMIN_EMAIL and GARMIN_PASSWORD in environment variables or .env file
    - A workout plan file generated by the generate-plan command
    
    Example:
        python -m garmin_planner.cli upload-workouts workout_plan_20250803_1836.md
    """
    
    # Load environment variables
    if Path(env_file).exists():
        load_dotenv(env_file)
        if verbose:
            click.echo(f"Loaded environment from {env_file}")
    
    # Get credentials
    garmin_email = email or os.getenv('GARMIN_EMAIL')
    garmin_password = password or os.getenv('GARMIN_PASSWORD')
    
    if not garmin_email or not garmin_password:
        click.echo("❌ Error: Garmin credentials not provided!", err=True)
        click.echo("\nPlease provide credentials via:")
        click.echo("  1. Command line: --email EMAIL --password PASSWORD")
        click.echo("  2. Environment variables: GARMIN_EMAIL, GARMIN_PASSWORD")
        click.echo("  3. .env file with GARMIN_EMAIL and GARMIN_PASSWORD")
        raise click.Abort()
    
    # Check if plan file exists
    if not Path(plan_file).exists():
        click.echo(f"❌ Plan file {plan_file} not found!", err=True)
        raise click.Abort()
    
    if verbose:
        click.echo(f"Plan file: {plan_file}")
        click.echo(f"Email: {garmin_email}")
        click.echo(f"Dry run: {dry_run}")
        if save_structured:
            click.echo(f"Save structured to: {save_structured}")
    
    try:
        # Initialize uploader
        uploader = GarminWorkoutUploader(
            email=garmin_email,
            password=garmin_password
        )
        
        # Parse workouts from plan
        with open(plan_file, 'r', encoding='utf-8') as f:
            plan_text = f.read()
        
        workouts = uploader.parse_workout_plan(plan_text)
        
        if not workouts:
            click.echo("⚠️  No workouts found in the plan file")
            return
        
        click.echo(f"🏃 Found {len(workouts)} workouts in the plan")
        
        # Save structured workouts if requested
        if save_structured:
            saved_file = uploader.save_structured_workouts(workouts, save_structured)
            click.echo(f"💾 Structured workouts saved to: {saved_file}")
        
        # Show workout preview
        if verbose:
            click.echo("\n📋 Workout preview:")
            for i, workout in enumerate(workouts, 1):
                click.echo(f"  {i}. {workout['workoutName']} ({workout['estimatedDurationInSecs']//60} min)")
        
        if dry_run:
            click.echo("\n🔍 Dry run complete - no workouts uploaded")
            return
        
        # Upload workouts
        result = uploader.upload_workouts_from_plan(plan_file)
        
        if result['success']:
            click.echo(f"\n🎉 Successfully uploaded {result['uploaded']}/{result['total']} workouts!")
            if result['workout_ids']:
                click.echo(f"📋 Workout IDs: {', '.join(result['workout_ids'])}")
        else:
            click.echo("❌ No workouts were uploaded successfully", err=True)
        
        if result['errors']:
            click.echo(f"⚠️  Failed uploads: {', '.join(result['errors'])}")
            
    except KeyboardInterrupt:
        click.echo("\n⏹️  Upload interrupted by user")
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Error uploading workouts: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        raise click.Abort()


def create_default_context_file(context_path: Path) -> None:
    """Create a default training context file."""
    default_context = """# Training Context

## Goals
- Maintain general fitness and health
- Improve cardiovascular endurance
- Build strength and prevent injuries
- Prepare for upcoming events (specify if any)

## Current Focus
- Building aerobic base
- Consistent training routine
- Balancing different training modalities

## Preferences
- Mix of running, cycling, and swimming
- 2-3 strength training sessions per week
- 1-2 yoga/flexibility sessions per week
- 1-2 complete rest days per week

## Constraints
- Available training time: [specify your available hours per day]
- Training days: [specify preferred days, e.g., Mon-Fri mornings]
- Equipment available: [list available equipment]
- Any injuries or limitations: [specify if any]

## Upcoming Events
- Next race/event: [specify date and type if any]
- Target performance: [specify goals]

## Notes
- Preferred training intensity: [easy/moderate/hard]
- Recovery preferences: [active recovery, complete rest, etc.]
- Any other relevant information

---
Edit this file to personalize your training context!
"""
    
    try:
        with open(context_path, 'w', encoding='utf-8') as f:
            f.write(default_context)
        click.echo(f"✅ Created default context file. Please edit {context_path} to customize your training goals.")
    except Exception as e:
        click.echo(f"❌ Error creating context file: {e}", err=True)


# For backwards compatibility, create a main function that calls the CLI
def main():
    """Main entry point for backwards compatibility."""
    cli()


if __name__ == '__main__':
    cli()
