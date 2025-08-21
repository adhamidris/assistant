#!/usr/bin/env python3
"""
Setup script for AI Personal Business Assistant Backend
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}:")
        print(f"Command: {command}")
        print(f"Error: {e.stderr}")
        return None


def check_requirements():
    """Check if required software is installed"""
    print("🔍 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    
    # Check if Docker is available
    docker_check = run_command("docker --version", "Docker version check")
    if not docker_check:
        print("⚠️  Docker not found. You'll need to set up PostgreSQL, Redis, and MinIO manually.")
    
    # Check if Docker Compose is available
    compose_check = run_command("docker-compose --version", "Docker Compose version check")
    if not compose_check:
        print("⚠️  Docker Compose not found. You'll need to set up services manually.")
    
    return True


def setup_environment():
    """Set up the development environment"""
    print("\n🚀 Setting up AI Personal Business Assistant Backend...")
    
    # Check requirements
    if not check_requirements():
        return False
    
    # Create .env file if it doesn't exist
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from template")
        print("⚠️  Please update .env with your API keys before continuing")
    
    # Install Python dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    # Start Docker services
    if not run_command("docker-compose up -d", "Starting Docker services"):
        print("⚠️  Failed to start Docker services. Please start them manually.")
    
    # Wait a moment for services to start
    print("⏳ Waiting for services to start...")
    import time
    time.sleep(10)
    
    # Run database migrations
    if not run_command("python manage.py makemigrations", "Creating database migrations"):
        return False
    
    if not run_command("python manage.py migrate", "Applying database migrations"):
        return False
    
    # Create demo data
    if not run_command("python manage.py setup_demo_data", "Creating demo data"):
        print("⚠️  Failed to create demo data, but setup can continue")
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Update your .env file with API keys")
    print("2. Create a superuser: python manage.py createsuperuser")
    print("3. Start the development server: python manage.py runserver")
    print("4. Start Celery worker: celery -A assistant worker --loglevel=info")
    print("\nAccess the admin panel at: http://localhost:8000/admin/")
    
    return True


if __name__ == "__main__":
    setup_environment()

