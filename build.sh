#!/bin/bash

echo "Building Nutrient Tracker for Linux..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3 using your package manager"
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "Arch: sudo pacman -S python python-pip"
    exit 1
fi

# Check if build.py exists
if [ ! -f "build.py" ]; then
    echo "Error: build.py not found in current directory"
    exit 1
fi

# Run the build script
python3 build.py

echo
echo "Build complete! Check the dist folder for your executable."
read -p "Press Enter to continue..."