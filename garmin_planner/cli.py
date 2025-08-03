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
