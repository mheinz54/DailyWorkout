# Daily Workout Viewer

A small PyQt6 desktop app for viewing scheduled markdown workout routines, tracking a stopwatch, and recording completed workouts to a local SQLite database.

## Project layout

```text
DailyWorkout/
├── README.md
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── schedule_dialog.py
│   ├── workout_record_dialog.py
│   ├── workout_history_dialog.py
│   └── workout_history_edit_dialog.py
├── data/
│   └── workout_schedule.db
├── workouts/
│   ├── Ankle_Knee_Routine.md
│   ├── Back_Shoulders_Routine.md
│   ├── Chest_Hamstrings_Routine.md
│   ├── Core_Glute_Routine.md
│   └── images/
└── .gitignore
```

## Requirements

- Python 3.10+
- PyQt6

Install the app dependency with:

```bash
pip3 install PyQt6
```

## Run the app

From the repository root:

```bash
cd /Users/matthew.heinz/Projects/DailyWorkout
python3 src/main.py
```

If you are already in the project directory, this is enough:

```bash
python3 src/main.py
```

## How it works

- Use the Select Markdown File button to load a workout routine.
- Use Manage Schedule to assign markdown workout files to each weekday.
- Use the Start/Stop button to run the stopwatch.
- When you stop the timer, you can record the workout with the workout name, date, and duration.
- Use Workout History to review saved records grouped by workout, edit them, delete them, and see a calendar of recorded dates.

## Data storage

Workout history and schedule settings are stored in:

```text
data/workout_schedule.db
```

