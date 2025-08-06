# Nutrient & Workout Tracker - Build Instructions

This document explains how to build the Nutrient & Workout Tracker into standalone executables for Windows and Linux.

## Prerequisites

### Required Software
- **Python 3.7+** (with pip)
- **Internet connection** (for downloading dependencies)

### Required Python Packages
The build script will check for and help you install these:
- `pyinstaller` - For creating executables
- `rich` - For terminal UI
- `plotext` - For graphs
- `requests` - For API calls

## Quick Build

### Windows
1. Open Command Prompt or PowerShell
2. Navigate to the tracker directory
3. Run: `build.bat`

### Linux
1. Open Terminal
2. Navigate to the tracker directory  
3. Make the script executable: `chmod +x build.sh`
4. Run: `./build.sh`

## Manual Build

If you prefer to run the build script directly:

```bash
python build.py        # Windows
python3 build.py       # Linux
```

## Installing Dependencies

If you don't have the required packages installed:

```bash
pip install pyinstaller rich plotext requests
```

Or install from requirements if you have one:
```bash
pip install -r requirements.txt
```

## Build Output

The build process creates several files:

### Generated Files
- `dist/NutrientTracker.exe` (Windows) or `dist/NutrientTracker` (Linux) - The main executable
- `NutrientTracker-v1.0.0-[platform]-[arch]/` - Distribution folder with executable and documentation
- `NutrientTracker-v1.0.0-[platform]-[arch].zip/.tar.gz` - Compressed distribution package

### Build Artifacts (can be deleted)
- `build/` - Temporary build files
- `NutrientTracker.spec` - PyInstaller specification file

## Distribution

The built executable is completely standalone and can be distributed without requiring Python to be installed on the target system.

### What's Included in Distribution Package
- Main executable
- README.md with usage instructions
- tracker_data_template.json (sample data file)

## Troubleshooting

### Common Issues

**"Python not found"**
- Install Python from https://python.org (Windows) or using your package manager (Linux)
- Make sure Python is added to PATH

**"PyInstaller not found"**
- Install with: `pip install pyinstaller`

**"Module not found during build"**
- Install missing packages: `pip install rich plotext requests`
- Check that you're using the correct Python environment

**"Permission denied" (Linux)**
- Make build script executable: `chmod +x build.sh`
- Run with sudo if needed: `sudo ./build.sh`

**Large executable size**
- This is normal for PyInstaller builds (typically 20-50MB)
- The executable includes Python runtime and all dependencies

### Advanced Build Options

You can modify `build.py` to customize the build:

- **Change app name**: Modify `APP_NAME` variable
- **Add icon**: Add `--icon=myicon.ico` to PyInstaller args
- **Windowed mode**: Change `--console` to `--windowed` (hides terminal)
- **Additional files**: Add `--add-data` arguments

Example custom build command:
```bash
pyinstaller --onefile --console --name MyTracker --icon=icon.ico tracker.py
```

## Platform-Specific Notes

### Windows
- Builds create `.exe` files
- Windows Defender might flag the executable (false positive)
- Distribution uses ZIP compression

### Linux
- Builds create binary executables (no extension)
- May need to install development packages: `sudo apt install build-essential`
- Distribution uses tar.gz compression
- Built on one Linux distro should work on others with same architecture

### Cross-Platform Building
Currently, you must build on the target platform:
- Build Windows executables on Windows
- Build Linux executables on Linux

## File Structure After Build

```
NutrientTracker/
├── tracker.py              # Original Python script
├── build.py                # Build script
├── build.bat               # Windows build helper
├── build.sh                # Linux build helper
├── BUILD.md                # This file
├── dist/
│   └── NutrientTracker(.exe)   # Built executable
├── NutrientTracker-v1.0.0-*/  # Distribution folder
└── NutrientTracker-v1.0.0-*.zip/.tar.gz  # Distribution archive
```

## Version Management

To create a new version:
1. Update `VERSION` in `build.py`
2. Run the build process
3. New version will be reflected in distribution package names

## License and Distribution

The built executable can be freely distributed. It includes:
- Your application code
- Python runtime
- All required libraries
- No separate licensing requirements for end users

Make sure to comply with licenses of included packages (Rich, Plotext, etc.) which are generally permissive.