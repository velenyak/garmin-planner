from setuptools import setup, find_packages

setup(
    name="garmin-workout-planner",
    version="0.1.0",
    description="Download and save Garmin activities to JSON files",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "garth>=0.4.0",
        "python-dotenv>=1.0.0",
        "click>=8.0.0",
        "google-generativeai>=0.3.0",
    ],
    entry_points={
        "console_scripts": [
            "garmin-download=garmin_planner.cli:cli",
        ],
    },
    python_requires=">=3.8",
)
