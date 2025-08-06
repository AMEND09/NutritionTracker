# Nutrient & Workout Tracker

A terminal-based nutrition, workout, and fasting tracker with data visualization, meal planning, and more.  
Built for personal use, but flexible for anyone who wants to track their health and fitness journey.

---

## Features

- **Daily Food Logging**  
  Log foods by searching Open Food Facts, barcode, frequent foods, custom foods, or search history.
- **Workout Tracking**  
  Log workouts from a built-in exercise database or manually.
- **Water Intake Tracking**  
  Track your daily water consumption.
- **Weight Logging & Graphs**  
  Log your weight and visualize your progress over time.
- **Fasting Timer**  
  Start/end fasts and see your fasting progress.
- **Streaks**  
  Track streaks for hitting calorie and water goals.
- **Weekly/Monthly Reports**  
  See averages, trends, and get advice based on your data.
- **Meal Planning**  
  Plan meals for future dates.
- **Custom Foods & Recipes**  
  Add your own foods or multi-ingredient recipes.
- **Progress Photos**  
  Log and compare progress photos.
- **Data Backup**  
  Export your data as a backup.
- **Profile Editing**  
  Update your profile and goals at any time.

---

## Getting Started

### Requirements

- Python 3.8+
- [Rich](https://github.com/Textualize/rich)
- [plotext](https://github.com/piccolomo/plotext)
- [requests](https://docs.python-requests.org/)
- (Optional) [pyautogui](https://github.com/asweigart/pyautogui) for [main.py](main.py)

Install dependencies:
```sh
pip install rich plotext requests pyautogui
```

### Running the App

```sh
python tracker.py
```

### Building the App
Use the build scripts, there is are Windows and Linux scripts as well as a python file.

```sh
python build.py
```

The app will guide you through setting up your profile on first run.

---

## Usage

- **Dashboard:**  
  See your daily summary, streaks, fasting status, food log, and workouts.
- **Log Food:**  
  Choose from search, frequent foods, custom foods, barcode, or history.
- **Log Workout/Water/Weight:**  
  Quick prompts to add your data.
- **More Menu:**  
  Access reports, graphs, meal planner, custom foods, progress photos, backup, and profile editing.

**Navigation:**  
Use the menu options shown at the bottom of the dashboard.  
Use `<` and `>` to move between days.

---

## Data

All your data is stored locally in `tracker_data.json`.  
You can export a backup from the "More..." menu.

---

## Notes

- This is a terminal app. For best experience, use a terminal that supports colors and Unicode.
- No cloud sync or mobile app (yet).
- All data stays on your computer.

---

## License

Personal use.  
Feel free to modify for your own needs!

---

## Credits

- [Rich](https://github.com/Textualize/rich) for beautiful terminal UI
- [plotext](https://github.com/piccolomo/plotext) for plotting in the terminal
- [Open Food Facts](https://world.openfoodfacts.org/) for food data

