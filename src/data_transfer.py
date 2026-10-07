import hashlib
import json
import re
import sqlite3
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

import src.database as database

BUNDLE_FORMAT = "daily-workout-data"
BUNDLE_VERSION = 1
EXPORT_OPTIONS = {"exercises", "workouts", "programs", "history"}
MAX_BUNDLE_SIZE = 512 * 1024 * 1024
MAX_MANIFEST_SIZE = 64 * 1024 * 1024


def normalize_export_categories(categories):
    selected = set(categories)
    if "all" in selected:
        return set(EXPORT_OPTIONS)
    if "programs" in selected:
        selected.update({"workouts", "exercises"})
    if "workouts" in selected:
        selected.add("exercises")
    invalid = selected - EXPORT_OPTIONS
    if invalid:
        raise ValueError(f"Unsupported export category: {', '.join(sorted(invalid))}")
    return selected


def _fetch_dicts(cursor, query, parameters=()):
    cursor.execute(query, parameters)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]


def _portable_image_path(image_path, archive, assets):
    if not image_path:
        return ""
    candidate = Path(image_path)
    if not candidate.is_absolute():
        candidate = database.BASE_DIR / candidate
    if not candidate.is_file():
        return ""

    image_bytes = candidate.read_bytes()
    digest = hashlib.sha256(image_bytes).hexdigest()
    suffix = candidate.suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
        suffix = ".img"
    asset_path = f"assets/{digest}{suffix}"
    if asset_path not in assets:
        archive.writestr(asset_path, image_bytes)
        assets.add(asset_path)
    return asset_path


def export_bundle(file_path, categories):
    selected = normalize_export_categories(categories)
    if not selected:
        raise ValueError("Select at least one type of data to export.")

    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    manifest = {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "bundle_id": str(uuid.uuid4()),
        "categories": sorted(selected),
    }

    try:
        with zipfile.ZipFile(file_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            assets = set()
            if "exercises" in selected:
                exercises = _fetch_dicts(
                    cursor,
                    "SELECT id, name, instructions, image_path, measure_type, measure_value, "
                    "duration_seconds, alternates_sides, side_switch_seconds, muscle_groups "
                    "FROM exercises ORDER BY id",
                )
                for exercise in exercises:
                    exercise["image_path"] = _portable_image_path(
                        exercise["image_path"], bundle, assets
                    )
                manifest["exercises"] = exercises

            if "workouts" in selected:
                workouts = _fetch_dicts(
                    cursor,
                    "SELECT id, name, description, equipment_needed, phase_rest_seconds "
                    "FROM workout_templates ORDER BY id",
                )
                for workout in workouts:
                    phases = _fetch_dicts(
                        cursor,
                        "SELECT id, phase_name, description, repeat_count, "
                        "rest_between_exercises_seconds FROM workout_phases "
                        "WHERE workout_template_id = ? ORDER BY id",
                        (workout["id"],),
                    )
                    for phase in phases:
                        phase["exercises"] = _fetch_dicts(
                            cursor,
                            "SELECT id, exercise_id, measure_value, display_order "
                            "FROM workout_phase_exercises WHERE phase_id = ? "
                            "ORDER BY display_order, id",
                            (phase["id"],),
                        )
                    workout["phases"] = phases
                manifest["workouts"] = workouts

            if "programs" in selected:
                programs = _fetch_dicts(
                    cursor,
                    "SELECT id, name, active FROM programs ORDER BY id",
                )
                for program in programs:
                    program["workouts"] = _fetch_dicts(
                        cursor,
                        "SELECT id, workout_template_id, recurrence_type, recurrence_interval, "
                        "weekdays, month_day, start_date, display_order FROM program_workouts "
                        "WHERE program_id = ? ORDER BY display_order, id",
                        (program["id"],),
                    )
                manifest["programs"] = programs

            if "history" in selected:
                history = _fetch_dicts(
                    cursor,
                    "SELECT id, workout_name, workout_date, duration_seconds "
                    "FROM workout_history ORDER BY id",
                )
                for record in history:
                    record["exercises"] = _fetch_dicts(
                        cursor,
                        "SELECT id, exercise_name, exercise_id, measure_type, measure_value, "
                        "round_number, display_order FROM workout_record_exercises "
                        "WHERE workout_record_id = ? ORDER BY display_order, id",
                        (record["id"],),
                    )
                manifest["history"] = history

            bundle.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )
    finally:
        conn.close()

    return {category: len(manifest.get(category, [])) for category in selected}


def _validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("The selected file does not contain a valid data bundle.")
    if manifest.get("format") != BUNDLE_FORMAT:
        raise ValueError("This file is not a Daily Workout export bundle.")
    if manifest.get("version") != BUNDLE_VERSION:
        raise ValueError("This export bundle version is not supported.")
    if not isinstance(manifest.get("bundle_id"), str) or not manifest["bundle_id"]:
        raise ValueError("The export bundle is missing its identifier.")

    categories = set(manifest.get("categories", []))
    if not categories or categories - EXPORT_OPTIONS:
        raise ValueError("The export bundle has an invalid category list.")
    if "programs" in categories and not {"workouts", "exercises"}.issubset(categories):
        raise ValueError("Program data must include its workouts and exercises.")
    if "workouts" in categories and "exercises" not in categories:
        raise ValueError("Workout data must include its exercises.")
    for category in categories:
        if not isinstance(manifest.get(category), list):
            raise ValueError(f"The export bundle is missing its {category} data.")
    return categories


def _insert_with_id(cursor, table, values):
    source_id = values.pop("id", None)
    columns = list(values)
    if source_id is not None:
        cursor.execute(f"SELECT 1 FROM {table} WHERE id = ?", (source_id,))
    if source_id is not None and cursor.fetchone() is None:
        columns.insert(0, "id")
        cursor.execute(
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"VALUES ({', '.join('?' for _ in columns)})",
            [source_id, *(values[column] for column in values)],
        )
        return source_id
    cursor.execute(
        f"INSERT INTO {table} ({', '.join(columns)}) "
        f"VALUES ({', '.join('?' for _ in columns)})",
        [values[column] for column in columns],
    )
    return cursor.lastrowid


def _import_image(bundle, asset_path, import_folder, copied_files):
    if not asset_path:
        return ""
    if not isinstance(asset_path, str) or not asset_path.startswith("assets/"):
        raise ValueError("An image reference in the export bundle is invalid.")
    try:
        image_info = bundle.getinfo(asset_path)
    except KeyError as error:
        raise ValueError("The export bundle is missing an image file.") from error
    if image_info.file_size > 50 * 1024 * 1024:
        raise ValueError("An image in the export bundle exceeds the 50 MB limit.")

    suffix = Path(asset_path).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
        suffix = ".img"
    relative_path = (
        Path("images") / "imported" / import_folder / f"image_{len(copied_files)}{suffix}"
    )
    destination = database.BASE_DIR / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(bundle.read(asset_path))
    copied_files.append(destination)
    return relative_path.as_posix()


def _import_exercises(cursor, bundle, exercises, import_folder, copied_files):
    exercise_ids = {}
    for source in exercises:
        image_path = _import_image(bundle, source.get("image_path"), import_folder, copied_files)
        values = {
            key: source.get(key)
            for key in (
                "name",
                "instructions",
                "image_path",
                "measure_type",
                "measure_value",
                "duration_seconds",
                "alternates_sides",
                "side_switch_seconds",
                "muscle_groups",
            )
        }
        values["image_path"] = image_path
        exercise_ids[source["id"]] = _insert_with_id(
            cursor, "exercises", {"id": source["id"], **values}
        )
    return exercise_ids


def _import_workouts(cursor, workouts, exercise_ids):
    workout_ids = {}
    for source in workouts:
        workout_values = {
            key: source.get(key)
            for key in ("name", "description", "equipment_needed", "phase_rest_seconds")
        }
        local_workout_id = _insert_with_id(
            cursor,
            "workout_templates",
            {"id": source["id"], **workout_values},
        )
        workout_ids[source["id"]] = local_workout_id
        for phase in source.get("phases", []):
            phase_values = {
                "workout_template_id": local_workout_id,
                "phase_name": phase.get("phase_name"),
                "description": phase.get("description"),
                "repeat_count": phase.get("repeat_count", 1),
                "rest_between_exercises_seconds": phase.get("rest_between_exercises_seconds", 0),
            }
            local_phase_id = _insert_with_id(
                cursor,
                "workout_phases",
                {"id": phase["id"], **phase_values},
            )
            for phase_exercise in phase.get("exercises", []):
                source_exercise_id = phase_exercise["exercise_id"]
                if source_exercise_id not in exercise_ids:
                    raise ValueError("A workout refers to an exercise that was not exported.")
                _insert_with_id(
                    cursor,
                    "workout_phase_exercises",
                    {
                        "id": phase_exercise.get("id"),
                        "phase_id": local_phase_id,
                        "exercise_id": exercise_ids[source_exercise_id],
                        "measure_value": phase_exercise.get("measure_value"),
                        "display_order": phase_exercise.get("display_order", 0),
                    },
                )
    return workout_ids


def _import_programs(cursor, programs, workout_ids):
    for source in programs:
        local_program_id = _insert_with_id(
            cursor,
            "programs",
            {
                "id": source["id"],
                "name": source.get("name"),
                "active": source.get("active", 0),
            },
        )
        for rule in source.get("workouts", []):
            source_workout_id = rule["workout_template_id"]
            if source_workout_id not in workout_ids:
                raise ValueError("A program refers to a workout that was not exported.")
            _insert_with_id(
                cursor,
                "program_workouts",
                {
                    "id": rule.get("id"),
                    "program_id": local_program_id,
                    "workout_template_id": workout_ids[source_workout_id],
                    "recurrence_type": rule["recurrence_type"],
                    "recurrence_interval": rule.get("recurrence_interval", 1),
                    "weekdays": rule.get("weekdays", ""),
                    "month_day": rule.get("month_day", 1),
                    "start_date": rule["start_date"],
                    "display_order": rule.get("display_order", 0),
                },
            )


def _import_history(cursor, records, exercise_ids):
    for source in records:
        local_record_id = _insert_with_id(
            cursor,
            "workout_history",
            {
                "id": source["id"],
                "workout_name": source["workout_name"],
                "workout_date": source["workout_date"],
                "duration_seconds": source["duration_seconds"],
            },
        )
        for exercise in source.get("exercises", []):
            local_exercise_id = exercise_ids.get(exercise.get("exercise_id"))
            _insert_with_id(
                cursor,
                "workout_record_exercises",
                {
                    "id": exercise.get("id"),
                    "workout_record_id": local_record_id,
                    "exercise_name": exercise.get("exercise_name"),
                    "exercise_id": local_exercise_id,
                    "measure_type": exercise["measure_type"],
                    "measure_value": exercise["measure_value"],
                    "round_number": exercise.get("round_number", 1),
                    "display_order": exercise.get("display_order", 0),
                },
            )


def _import_bundle_data(cursor, bundle, manifest, categories, copied_files):
    counts = dict.fromkeys(categories, 0)
    exercise_ids = {}
    workout_ids = {}
    import_folder = uuid.uuid4().hex

    if "exercises" in categories:
        exercise_ids = _import_exercises(
            cursor, bundle, manifest["exercises"], import_folder, copied_files
        )
        counts["exercises"] = len(exercise_ids)
    if "workouts" in categories:
        workout_ids = _import_workouts(cursor, manifest["workouts"], exercise_ids)
        counts["workouts"] = len(workout_ids)
    if "programs" in categories:
        _import_programs(cursor, manifest["programs"], workout_ids)
        counts["programs"] = len(manifest["programs"])
    if "history" in categories:
        _import_history(cursor, manifest["history"], exercise_ids)
        counts["history"] = len(manifest["history"])
    return counts


def _bundle_is_imported(cursor, bundle_id):
    cursor.execute("SELECT 1 FROM imported_bundles WHERE bundle_id = ?", (bundle_id,))
    return cursor.fetchone() is not None


def _remove_copied_files(copied_files):
    for copied_file in copied_files:
        copied_file.unlink(missing_ok=True)


def _import_bundle_transaction(bundle, manifest, categories, copied_files):
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN")
        if _bundle_is_imported(cursor, manifest["bundle_id"]):
            conn.rollback()
            return {"already_imported": True}

        counts = _import_bundle_data(cursor, bundle, manifest, categories, copied_files)
        cursor.execute(
            "INSERT INTO imported_bundles (bundle_id, imported_at) VALUES (?, ?)",
            (manifest["bundle_id"], datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return counts
    except Exception:
        conn.rollback()
        _remove_copied_files(copied_files)
        raise
    finally:
        conn.close()


def _read_bundle_manifest(bundle):
    infos = bundle.infolist()
    if sum(info.file_size for info in infos) > MAX_BUNDLE_SIZE:
        raise ValueError("The export bundle exceeds the 512 MB import limit.")
    try:
        manifest_info = bundle.getinfo("manifest.json")
    except KeyError as error:
        raise ValueError("The export bundle is missing its manifest.") from error
    if manifest_info.file_size > MAX_MANIFEST_SIZE:
        raise ValueError("The export bundle manifest is too large.")
    try:
        manifest = json.loads(bundle.read("manifest.json").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("The export bundle manifest is not valid JSON.") from error
    return manifest, _validate_manifest(manifest)


def import_bundle(file_path):
    copied_files = []
    try:
        bundle = zipfile.ZipFile(file_path, "r")
    except (OSError, zipfile.BadZipFile) as error:
        raise ValueError("The selected file is not a readable export bundle.") from error

    with bundle:
        manifest, categories = _read_bundle_manifest(bundle)
        return _import_bundle_transaction(bundle, manifest, categories, copied_files)
