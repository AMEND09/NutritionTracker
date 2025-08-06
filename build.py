#!/usr/bin/env python3
"""
Build script for Nutrient & Workout Tracker
Packages the application for Windows and Linux using PyInstaller
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

# Fix encoding issues on Windows
if platform.system() == "Windows":
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Configuration
APP_NAME = "NutrientTracker"
MAIN_SCRIPT = "tracker.py"
VERSION = "1.0.0"
AUTHOR = "Nutrient Tracker Team"

# Build directories
BUILD_DIR = Path("build")
DIST_DIR = Path("dist")
SPEC_DIR = Path(".")

def safe_print(message):
    """Print message with encoding fallback for Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Remove emojis and special characters for Windows console
        import re
        safe_message = re.sub(r'[^\x00-\x7F]+', '?', message)
        print(safe_message)

def check_dependencies():
    """Check if required dependencies are installed"""
    safe_print("Checking dependencies...")
    
    # Check PyInstaller by trying to run it
    try:
        result = subprocess.run(["pyinstaller", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            safe_print("PyInstaller not working properly")
            return False
        safe_print(f"PyInstaller {result.stdout.strip()} found")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        safe_print("PyInstaller not found or not working")
        safe_print("Please install it with: pip install pyinstaller")
        return False
    
    # Check other required packages
    required_modules = [
        ("rich", "rich"),
        ("plotext", "plotext"), 
        ("requests", "requests")
    ]
    
    missing_packages = []
    for package_name, module_name in required_modules:
        try:
            __import__(module_name)
            safe_print(f"{package_name} found")
        except ImportError:
            missing_packages.append(package_name)
            safe_print(f"{package_name} not found")
    
    if missing_packages:
        safe_print(f"\nMissing required packages: {', '.join(missing_packages)}")
        safe_print("Please install them with:")
        safe_print(f"pip install {' '.join(missing_packages)}")
        return False
    
    safe_print("All dependencies are available")
    return True

def clean_build_dirs():
    """Clean previous build artifacts"""
    safe_print("Cleaning previous build artifacts...")
    
    dirs_to_clean = [BUILD_DIR, DIST_DIR]
    files_to_clean = [f"{APP_NAME}.spec"]
    
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            safe_print(f"   Removed {dir_path}")
    
    for file_path in files_to_clean:
        if Path(file_path).exists():
            Path(file_path).unlink()
            safe_print(f"   Removed {file_path}")

def get_pyinstaller_args(target_platform="current"):
    """Get PyInstaller arguments based on platform"""
    if target_platform == "current":
        target_platform = platform.system().lower()
    
    base_args = [
        "pyinstaller",
        "--onefile",  # Create a single executable
        "--console",  # Keep console window (for terminal app)
        "--name", f"{APP_NAME}_{target_platform}",
        "--clean",
        "--noconfirm",
    ]
    
    # Add hidden imports for packages that might not be detected
    hidden_imports = [
        "rich.console",
        "rich.prompt", 
        "rich.panel",
        "rich.layout",
        "rich.table",
        "rich.progress_bar",
        "rich.text",
        "plotext",
        "requests",
        "json",
        "datetime",
        "statistics",
        "collections"
    ]
    
    for import_name in hidden_imports:
        base_args.extend(["--hidden-import", import_name])
    
    # Platform-specific arguments
    if target_platform == "windows":
        base_args.extend([
            "--icon=NONE",  # You can add an .ico file here if you have one
        ])
    elif target_platform == "linux":
        base_args.extend([
            "--strip",  # Strip debug symbols on Linux
        ])
    
    # Add the main script
    base_args.append(MAIN_SCRIPT)
    
    return base_args

def build_executable(target_platform="current"):
    """Build the executable using PyInstaller"""
    if target_platform == "current":
        target_platform = platform.system().lower()
    
    safe_print(f"Building {APP_NAME} for {target_platform}...")
    
    # Check if main script exists
    if not Path(MAIN_SCRIPT).exists():
        safe_print(f"Main script '{MAIN_SCRIPT}' not found!")
        return False
    
    # Get PyInstaller arguments
    args = get_pyinstaller_args(target_platform)
    
    safe_print(f"Running: {' '.join(args)}")
    
    try:
        # Run PyInstaller
        result = subprocess.run(args, check=True, capture_output=True, text=True)
        safe_print(f"Build completed successfully for {target_platform}!")
        return True
        
    except subprocess.CalledProcessError as e:
        safe_print(f"Build failed with error code {e.returncode}")
        safe_print("STDOUT:", e.stdout)
        safe_print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        safe_print("PyInstaller not found! Please install it with: pip install pyinstaller")
        return False

def create_distribution(target_platform="current"):
    """Create distribution package"""
    if target_platform == "current":
        target_platform = platform.system().lower()
    
    host_platform = platform.system().lower()
    arch = platform.machine().lower()
    
    # Determine executable extension
    exe_ext = ".exe" if target_platform == "windows" else ""
    executable_name = f"{APP_NAME}_{target_platform}{exe_ext}"
    
    # Source executable path
    exe_path = DIST_DIR / executable_name
    
    if not exe_path.exists():
        safe_print(f"Executable not found at {exe_path}")
        return False
    
    # Create distribution directory
    dist_name = f"{APP_NAME}-v{VERSION}-{target_platform}-{arch}"
    dist_path = Path(dist_name)
    
    if dist_path.exists():
        shutil.rmtree(dist_path)
    
    dist_path.mkdir()
    
    # Copy executable with clean name
    final_exe_name = f"{APP_NAME}{exe_ext}"
    shutil.copy2(exe_path, dist_path / final_exe_name)
    
    # Create README for distribution (without emojis)
    readme_content = f"""# {APP_NAME} v{VERSION}

A comprehensive CLI-style nutrition and fitness tracking application.

## Features
- Real-time nutrition tracking with progress bars
- Food search via OpenFoodFacts API
- Workout logging with calorie calculations  
- Weight tracking and trend analysis
- Intermittent fasting timer
- Goal streaks and achievements
- Meal planning for future dates
- Progress photo management

## Usage
Simply run the executable:

### Windows
```
{final_exe_name}
```

### Linux
```
./{final_exe_name}
```

## System Requirements
- {target_platform.title()} {arch}
- Internet connection (for food database API)

## Data Storage
Your data is stored locally in a file called `tracker_data.json` in the same directory as the executable.

## Author
{AUTHOR}

## Version
{VERSION}

Built on {host_platform.title()} for {target_platform.title()}
"""
    
    with open(dist_path / "README.md", "w", encoding='utf-8') as f:
        f.write(readme_content)
    
    # Create sample data file (optional)
    sample_data = {
        "profile": {},
        "daily_logs": {},
        "custom_foods": [],
        "weight_logs": {},
        "search_history": [],
        "fasting": {"active": False, "start_time": None, "duration_hours": 16},
        "streaks": {"calorie_goal": 0, "water_goal": 0, "last_checked_date": None},
        "meal_plans": {},
        "progress_photos": {}
    }
    
    import json
    with open(dist_path / "tracker_data_template.json", "w", encoding='utf-8') as f:
        json.dump(sample_data, f, indent=4)
    
    safe_print(f"Distribution created: {dist_path}")
    
    # Create archive
    archive_name = f"{dist_name}"
    if target_platform == "windows":
        # Create ZIP for Windows
        shutil.make_archive(archive_name, 'zip', '.', dist_name)
        safe_print(f"Archive created: {archive_name}.zip")
    else:
        # Create tar.gz for Linux
        shutil.make_archive(archive_name, 'gztar', '.', dist_name)
        safe_print(f"Archive created: {archive_name}.tar.gz")
    
    return True

def show_build_info():
    """Show build information"""
    safe_print("=" * 60)
    safe_print(f"{APP_NAME} Build Script v{VERSION}")
    safe_print("=" * 60)
    safe_print(f"Platform: {platform.system()} {platform.release()}")
    safe_print(f"Architecture: {platform.machine()}")
    safe_print(f"Python: {sys.version.split()[0]}")
    safe_print(f"Working Directory: {Path.cwd()}")
    safe_print("=" * 60)

def build_for_all_platforms():
    """Build for both Windows and Linux (current platform only)"""
    current_platform = platform.system().lower()
    platforms_to_build = [current_platform]
    
    # Note: Cross-platform building is complex and not reliable
    # We only build for the current platform
    safe_print(f"Building for current platform: {current_platform}")
    
    all_success = True
    for target_platform in platforms_to_build:
        safe_print(f"\n{'='*50}")
        safe_print(f"Building for {target_platform.upper()}")
        safe_print(f"{'='*50}")
        
        if not build_executable(target_platform):
            safe_print(f"Failed to build for {target_platform}")
            all_success = False
            continue
            
        if not create_distribution(target_platform):
            safe_print(f"Failed to create distribution for {target_platform}")
            all_success = False
            continue
            
        safe_print(f"Successfully built for {target_platform}")
    
    return all_success

def main():
    """Main build function"""
    show_build_info()
    
    # Check if we're in the right directory
    if not Path(MAIN_SCRIPT).exists():
        safe_print(f"ERROR: {MAIN_SCRIPT} not found in current directory!")
        safe_print("Please run this script from the directory containing tracker.py")
        return 1
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Clean previous builds
    clean_build_dirs()
    
    # Build for all platforms
    if not build_for_all_platforms():
        return 1
    
    safe_print("\nBuild completed successfully!")
    safe_print("\nFiles created:")
    
    current_platform = platform.system().lower()
    arch = platform.machine().lower()
    
    # List created files
    exe_ext = ".exe" if current_platform == "windows" else ""
    safe_print(f"  - {DIST_DIR}/{APP_NAME}_{current_platform}{exe_ext}")
    
    dist_name = f"{APP_NAME}-v{VERSION}-{current_platform}-{arch}"
    if current_platform == "windows":
        safe_print(f"  - {dist_name}.zip")
    else:
        safe_print(f"  - {dist_name}.tar.gz")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        safe_print("\nBuild cancelled by user")
        sys.exit(1)
    except Exception as e:
        safe_print(f"\nUnexpected error: {e}")
        sys.exit(1)