import sqlite3
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "workout_schedule.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS workout_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_name TEXT NOT NULL,
            workout_date TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            instructions TEXT NOT NULL,
            image_path TEXT,
            measure_type TEXT NOT NULL,
            measure_value INTEGER,
            duration_seconds INTEGER,
            alternates_sides INTEGER NOT NULL DEFAULT 0,
            side_switch_seconds INTEGER NOT NULL DEFAULT 0,
            muscle_groups TEXT
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS workout_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            equipment_needed TEXT,
            phase_rest_seconds INTEGER NOT NULL DEFAULT 0
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    cursor.execute("PRAGMA table_info(programs)")
    program_columns = [row[1] for row in cursor.fetchall()]
    if "active" not in program_columns:
        cursor.execute("ALTER TABLE programs ADD COLUMN active INTEGER NOT NULL DEFAULT 0")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS program_workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_id INTEGER NOT NULL,
            workout_template_id INTEGER NOT NULL,
            recurrence_type TEXT NOT NULL,
            recurrence_interval INTEGER NOT NULL DEFAULT 1,
            weekdays TEXT NOT NULL DEFAULT '',
            month_day INTEGER NOT NULL DEFAULT 1,
            start_date TEXT NOT NULL,
            display_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (program_id) REFERENCES programs (id),
            FOREIGN KEY (workout_template_id) REFERENCES workout_templates (id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS workout_phases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_template_id INTEGER NOT NULL,
            phase_name TEXT NOT NULL,
            description TEXT,
            repeat_count INTEGER NOT NULL DEFAULT 1,
            rest_between_exercises_seconds INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (workout_template_id) REFERENCES workout_templates (id) ON DELETE CASCADE
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS workout_phase_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phase_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            measure_value INTEGER,
            display_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (phase_id) REFERENCES workout_phases (id) ON DELETE CASCADE,
            FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE
        )
    """
    )
    cursor.execute("PRAGMA table_info(workout_phase_exercises)")
    phase_exercise_columns = [row[1] for row in cursor.fetchall()]
    if "measure_value" not in phase_exercise_columns:
        cursor.execute("ALTER TABLE workout_phase_exercises ADD COLUMN measure_value INTEGER")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            name TEXT PRIMARY KEY,
            value TEXT
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS workout_record_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_record_id INTEGER NOT NULL,
            exercise_name TEXT,
            exercise_id INTEGER,
            measure_type TEXT NOT NULL,
            measure_value INTEGER NOT NULL,
            round_number INTEGER NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (workout_record_id) REFERENCES workout_history (id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute("PRAGMA table_info(workout_record_exercises)")
    record_exercise_columns = [row[1] for row in cursor.fetchall()]
    if "exercise_id" not in record_exercise_columns:
        cursor.execute("ALTER TABLE workout_record_exercises ADD COLUMN exercise_id INTEGER")
    if "round_number" not in record_exercise_columns:
        cursor.execute(
            "ALTER TABLE workout_record_exercises ADD COLUMN round_number INTEGER NOT NULL DEFAULT 1"
        )
    conn.commit()
    conn.close()


def save_workout_record(workout_name, workout_date, duration_seconds, exercises=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO workout_history (workout_name, workout_date, duration_seconds) VALUES (?, ?, ?)",
        (workout_name, workout_date, duration_seconds),
    )
    record_id = cursor.lastrowid
    for order_index, (
        exercise_id,
        exercise_name,
        measure_type,
        measure_value,
        round_number,
    ) in enumerate(exercises or [], start=1):
        cursor.execute(
            "INSERT INTO workout_record_exercises (workout_record_id, exercise_name, exercise_id, measure_type, measure_value, round_number, display_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                record_id,
                exercise_name,
                exercise_id,
                measure_type,
                measure_value,
                round_number,
                order_index,
            ),
        )
    conn.commit()
    conn.close()


def get_workout_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, workout_name, workout_date, duration_seconds FROM workout_history ORDER BY workout_name ASC, workout_date DESC, duration_seconds DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_workout_record_counts_for_date(workout_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT workout_name, COUNT(*) FROM workout_history "
        "WHERE workout_date = ? GROUP BY workout_name",
        (workout_date,),
    )
    rows = cursor.fetchall()
    conn.close()
    return dict(rows)


def get_workout_record(record_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, workout_name, workout_date, duration_seconds FROM workout_history WHERE id = ?",
        (record_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def get_workout_record_exercises(record_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT exercise_id, exercise_name, measure_type, measure_value, round_number FROM workout_record_exercises WHERE workout_record_id = ? ORDER BY display_order ASC",
        (record_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_workout_record(record_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM workout_history WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def update_workout_record(record_id, workout_name, workout_date, duration_seconds):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE workout_history SET workout_name = ?, workout_date = ?, duration_seconds = ? WHERE id = ?",
        (workout_name, workout_date, duration_seconds, record_id),
    )
    conn.commit()
    conn.close()


def get_user_setting(name, default=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM user_settings WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return default
    return row[0]


def save_user_setting(name, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_settings (name, value) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET value = excluded.value",
        (name, str(value)),
    )
    conn.commit()
    conn.close()


def save_exercise_record(
    name,
    instructions,
    image_path,
    measure_type,
    measure_value,
    duration_seconds,
    alternates_sides,
    side_switch_seconds,
    muscle_groups,
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO exercises (
            name,
            instructions,
            image_path,
            measure_type,
            measure_value,
            duration_seconds,
            alternates_sides,
            side_switch_seconds,
            muscle_groups
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            instructions,
            image_path,
            measure_type,
            measure_value,
            duration_seconds,
            alternates_sides,
            side_switch_seconds,
            muscle_groups,
        ),
    )
    conn.commit()
    conn.close()


def get_exercise_by_id(exercise_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, instructions, image_path, measure_type, measure_value, duration_seconds, alternates_sides, side_switch_seconds, muscle_groups FROM exercises WHERE id = ?",
        (exercise_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def update_exercise_record(
    exercise_id,
    name,
    instructions,
    image_path,
    measure_type,
    measure_value,
    duration_seconds,
    alternates_sides,
    side_switch_seconds,
    muscle_groups,
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE exercises
        SET name = ?, instructions = ?, image_path = ?, measure_type = ?, measure_value = ?,
            duration_seconds = ?, alternates_sides = ?, side_switch_seconds = ?, muscle_groups = ?
        WHERE id = ?
        """,
        (
            name,
            instructions,
            image_path,
            measure_type,
            measure_value,
            duration_seconds,
            alternates_sides,
            side_switch_seconds,
            muscle_groups,
            exercise_id,
        ),
    )
    conn.commit()
    conn.close()


def save_workout_template(name, description, equipment_needed, phase_rest_seconds):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO workout_templates (name, description, equipment_needed, phase_rest_seconds) VALUES (?, ?, ?, ?)",
        (name, description, equipment_needed, phase_rest_seconds),
    )
    workout_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return workout_id


def update_workout_template(workout_id, name, description, equipment_needed, phase_rest_seconds):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE workout_templates SET name = ?, description = ?, equipment_needed = ?, phase_rest_seconds = ? WHERE id = ?",
        (name, description, equipment_needed, phase_rest_seconds, workout_id),
    )
    conn.commit()
    conn.close()


def get_workout_templates():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, description, equipment_needed, phase_rest_seconds FROM workout_templates ORDER BY name ASC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_workout_template_by_id(workout_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, description, equipment_needed, phase_rest_seconds FROM workout_templates WHERE id = ?",
        (workout_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def get_programs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM programs ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_programs_with_activation():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, active FROM programs ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def set_active_program_ids(program_ids):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE programs SET active = 0")
    cursor.executemany(
        "UPDATE programs SET active = 1 WHERE id = ?",
        [(program_id,) for program_id in program_ids],
    )
    conn.commit()
    conn.close()


def get_active_program_workouts_for_date(workout_date):
    target_date = date.fromisoformat(workout_date)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT pw.workout_template_id, pw.recurrence_type, pw.recurrence_interval, "
        "pw.weekdays, pw.month_day, pw.start_date "
        "FROM programs AS p JOIN program_workouts AS pw ON pw.program_id = p.id "
        "JOIN workout_templates AS wt ON wt.id = pw.workout_template_id "
        "WHERE p.active = 1 ORDER BY p.id ASC, pw.display_order ASC, pw.id ASC"
    )
    rules = cursor.fetchall()
    conn.close()

    matching_workouts = []
    for workout_id, recurrence_type, interval, weekdays, month_day, start_date in rules:
        start = date.fromisoformat(start_date)
        if target_date < start:
            continue

        if recurrence_type == "daily":
            matches = (target_date - start).days % interval == 0
        elif recurrence_type == "weekly":
            selected_weekdays = {int(day) for day in weekdays.split(",") if day}
            week_start = start - timedelta(days=start.weekday())
            week_number = (target_date - week_start).days // 7
            matches = target_date.isoweekday() in selected_weekdays and week_number % interval == 0
        elif recurrence_type == "monthly":
            month_number = (target_date.year - start.year) * 12 + target_date.month - start.month
            matches = target_date.day == month_day and month_number % interval == 0
        else:
            matches = False

        if matches:
            matching_workouts.append(workout_id)

    return matching_workouts


def get_program_by_id(program_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM programs WHERE id = ?", (program_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_program_workouts(program_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, workout_template_id, recurrence_type, recurrence_interval, weekdays, "
        "month_day, start_date, display_order FROM program_workouts "
        "WHERE program_id = ? ORDER BY display_order ASC, id ASC",
        (program_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def save_program(program_id, name, workout_rules):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        if program_id is None:
            cursor.execute("INSERT INTO programs (name) VALUES (?)", (name,))
            program_id = cursor.lastrowid
        else:
            cursor.execute("UPDATE programs SET name = ? WHERE id = ?", (name, program_id))
            cursor.execute("DELETE FROM program_workouts WHERE program_id = ?", (program_id,))

        for order_index, rule in enumerate(workout_rules, start=1):
            cursor.execute(
                "INSERT INTO program_workouts (program_id, workout_template_id, recurrence_type, "
                "recurrence_interval, weekdays, month_day, start_date, display_order) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    program_id,
                    rule["workout_template_id"],
                    rule["recurrence_type"],
                    rule["recurrence_interval"],
                    rule["weekdays"],
                    rule["month_day"],
                    rule["start_date"],
                    order_index,
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return program_id


def delete_program(program_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM program_workouts WHERE program_id = ?", (program_id,))
    cursor.execute("DELETE FROM programs WHERE id = ?", (program_id,))
    conn.commit()
    conn.close()


def delete_workout_phases_for_template(workout_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("DELETE FROM workout_phases WHERE workout_template_id = ?", (workout_id,))
    conn.commit()
    conn.close()


def save_workout_phase(
    workout_id, phase_name, description, repeat_count, rest_between_exercises_seconds
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute(
        "INSERT INTO workout_phases (workout_template_id, phase_name, description, repeat_count, rest_between_exercises_seconds) VALUES (?, ?, ?, ?, ?)",
        (
            workout_id,
            phase_name,
            description,
            repeat_count,
            rest_between_exercises_seconds,
        ),
    )
    phase_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return phase_id


def get_workout_phases_for_template(workout_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, workout_template_id, phase_name, description, repeat_count, rest_between_exercises_seconds FROM workout_phases WHERE workout_template_id = ? ORDER BY id ASC",
        (workout_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def save_workout_phase_exercise(phase_id, exercise_id, measure_value, display_order):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO workout_phase_exercises (phase_id, exercise_id, measure_value, display_order) VALUES (?, ?, ?, ?)",
        (phase_id, exercise_id, measure_value, display_order),
    )
    conn.commit()
    conn.close()


def get_workout_phase_exercises_for_phase(phase_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, phase_id, exercise_id, measure_value, display_order FROM workout_phase_exercises WHERE phase_id = ? ORDER BY display_order ASC",
        (phase_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_exercises():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, instructions, image_path, measure_type, measure_value, duration_seconds, alternates_sides, side_switch_seconds, muscle_groups FROM exercises ORDER BY name ASC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows
