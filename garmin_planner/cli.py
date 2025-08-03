#!/usr/bin/env python3
"""
Command-line interface for Garmin activity downloader.
"""

import click
import os
from pathlib import Path
from dotenv import load_dotenv
from .downloader import GarminActivityDownloader


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


# For backwards compatibility, create a main function that calls the CLI
def main():
    """Main entry point for backwards compatibility."""
    cli()


if __name__ == '__main__':
    cli()
