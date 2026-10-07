# Daily Workout Viewer

A small PyQt6 desktop app for viewing program-scheduled workouts, tracking a stopwatch, and recording completed workouts to a local SQLite database.

## Project layout

```text
DailyWorkout/
├── README.md
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── workout_record_dialog.py
│   ├── workout_history_dialog.py
│   └── workout_history_edit_dialog.py
├── data/
│   └── workout_schedule.db
├── images/
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

## Formatting and linting

This project uses `black`, `isort`, and `ruff`. Configuration lives in `pyproject.toml`.

### Run locally

```bash
python3 -m black .
python3 -m isort .
python3 -m ruff check .
```

### VS Code tasks

- `Format Code` — formats with Black and isort
- `Check Formatting` — verifies Black/isort formatting
- `Lint` — runs Ruff

### GitHub Actions

A GitHub Actions workflow is configured at `.github/workflows/python-ci.yml` to run formatting and lint checks on push and pull requests to `main`.

### Changing rules

Update formatting and lint rules in `pyproject.toml`:

- `tool.black.line-length`
- `tool.isort.profile`
- `tool.isort.line_length`
- `tool.ruff.line-length`
- `tool.ruff.select`
- `tool.ruff.extend-ignore`

Then re-run the tasks.

## How it works

- Use the workout dropdown to select a saved workout template.
- Use Program Builder to define recurring workout programs and Active Programs to choose which programs are in use.
- Use the Start/Stop button to run the stopwatch.
- When you stop the timer, you can record the workout with the workout name, date, and duration.
- Use Workout History to review saved records grouped by workout, edit them, delete them, and see a calendar of recorded dates.

## Data storage

Workout history and program settings are stored in:

```text
data/workout_schedule.db
```

