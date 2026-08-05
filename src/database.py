import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "workout_schedule.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            day_name TEXT PRIMARY KEY,
            file_path TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_name TEXT NOT NULL,
            workout_date TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL
        )
    """)
    cursor.execute("""
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
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            equipment_needed TEXT,
            phase_rest_seconds INTEGER NOT NULL DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_phases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_template_id INTEGER NOT NULL,
            phase_name TEXT NOT NULL,
            description TEXT,
            repeat_count INTEGER NOT NULL DEFAULT 1,
            rest_between_exercises_seconds INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (workout_template_id) REFERENCES workout_templates (id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_phase_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phase_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            display_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (phase_id) REFERENCES workout_phases (id) ON DELETE CASCADE,
            FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE
        )
    """)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in days:
        cursor.execute("INSERT OR IGNORE INTO schedule (day_name, file_path) VALUES (?, ?)", (day, ""))
    conn.commit()
    conn.close()


def save_workout_record(workout_name, workout_date, duration_seconds):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO workout_history (workout_name, workout_date, duration_seconds) VALUES (?, ?, ?)",
        (workout_name, workout_date, duration_seconds),
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


def get_file_for_day(day_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM schedule WHERE day_name = ?", (day_name,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""


def save_file_for_day(day_name, file_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE schedule SET file_path = ? WHERE day_name = ?", (file_path, day_name))
    conn.commit()
    conn.close()


def save_exercise_record(name, instructions, image_path, measure_type, measure_value, duration_seconds, alternates_sides, side_switch_seconds, muscle_groups):
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


def update_exercise_record(exercise_id, name, instructions, image_path, measure_type, measure_value, duration_seconds, alternates_sides, side_switch_seconds, muscle_groups):
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


def delete_workout_phases_for_template(workout_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("DELETE FROM workout_phases WHERE workout_template_id = ?", (workout_id,))
    conn.commit()
    conn.close()


def save_workout_phase(workout_id, phase_name, description, repeat_count, rest_between_exercises_seconds):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute(
        "INSERT INTO workout_phases (workout_template_id, phase_name, description, repeat_count, rest_between_exercises_seconds) VALUES (?, ?, ?, ?, ?)",
        (workout_id, phase_name, description, repeat_count, rest_between_exercises_seconds),
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


def save_workout_phase_exercise(phase_id, exercise_id, display_order):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO workout_phase_exercises (phase_id, exercise_id, display_order) VALUES (?, ?, ?)",
        (phase_id, exercise_id, display_order),
    )
    conn.commit()
    conn.close()


def get_workout_phase_exercises_for_phase(phase_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, phase_id, exercise_id, display_order FROM workout_phase_exercises WHERE phase_id = ? ORDER BY display_order ASC",
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
