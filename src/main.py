import sys
from datetime import datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.database import (
    get_exercise_by_id,
    get_schedule_for_day,
    get_workout_phase_exercises_for_phase,
    get_workout_phases_for_template,
    get_workout_template_by_id,
    get_workout_templates,
    init_db,
    save_workout_record,
)
from src.exercise_builder_dialog import ExerciseBuilderDialog
from src.schedule_dialog import ScheduleDialog
from src.workout_builder_dialog import WorkoutBuilderDialog
from src.workout_history_dialog import WorkoutHistoryDialog
from src.workout_record_dialog import WorkoutRecordDialog


class WorkoutViewerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Daily Workout Viewer")
        self.setGeometry(100, 100, 850, 650)

        self.timer_seconds = 0
        self.current_workout_name = ""
        self.stopwatch = QTimer()
        self.stopwatch.timeout.connect(self.update_timer_display)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        top_layout = QHBoxLayout()

        left_btn_layout = QHBoxLayout()

        self.workout_selector = QComboBox()
        self.workout_selector.setMinimumWidth(240)
        self.workout_selector.addItem("Select saved workout", -1)
        for workout_id, name, *_ in get_workout_templates():
            self.workout_selector.addItem(name, workout_id)
        self.workout_selector.currentIndexChanged.connect(self.load_selected_workout_preview)
        left_btn_layout.addWidget(self.workout_selector)

        self.schedule_btn = QPushButton("📅 Manage Schedule")
        self.schedule_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.schedule_btn.setStyleSheet(
            """
            QPushButton { background-color: #28a745; color: white; border-radius: 4px; padding: 6px 12px; margin-left: 5px; }
            QPushButton:hover { background-color: #218838; }
        """
        )
        self.schedule_btn.clicked.connect(self.open_schedule_manager)
        left_btn_layout.addWidget(self.schedule_btn)

        self.history_btn = QPushButton("🕘 Workout History")
        self.history_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.history_btn.setStyleSheet(
            """
            QPushButton { background-color: #6f42c1; color: white; border-radius: 4px; padding: 6px 12px; margin-left: 5px; }
            QPushButton:hover { background-color: #553098; }
        """
        )
        self.history_btn.clicked.connect(self.open_history_view)
        left_btn_layout.addWidget(self.history_btn)

        self.exercise_builder_btn = QPushButton("🏋️ Exercise Builder")
        self.exercise_builder_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.exercise_builder_btn.setStyleSheet(
            """
            QPushButton { background-color: #ff7b00; color: white; border-radius: 4px; padding: 6px 12px; margin-left: 5px; }
            QPushButton:hover { background-color: #cc5d00; }
        """
        )
        self.exercise_builder_btn.clicked.connect(self.open_exercise_builder)
        left_btn_layout.addWidget(self.exercise_builder_btn)

        self.workout_builder_btn = QPushButton("🧩 Workout Builder")
        self.workout_builder_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.workout_builder_btn.setStyleSheet(
            """
            QPushButton { background-color: #0d6efd; color: white; border-radius: 4px; padding: 6px 12px; margin-left: 5px; }
            QPushButton:hover { background-color: #0b5ed7; }
        """
        )
        self.workout_builder_btn.clicked.connect(self.open_workout_builder)
        left_btn_layout.addWidget(self.workout_builder_btn)
        top_layout.addLayout(left_btn_layout)

        top_layout.addStretch()

        right_timer_layout = QHBoxLayout()
        self.timer_label = QLabel("00:00")
        self.timer_label.setFont(QFont("Courier New", 16, QFont.Weight.Bold))
        self.timer_label.setStyleSheet(
            "color: #333; background-color: #e9ecef; padding: 4px 10px; border-radius: 4px; border: 1px solid #ced4da; margin-right: 8px;"
        )
        right_timer_layout.addWidget(self.timer_label)

        self.start_stop_btn = QPushButton("Start")
        self.start_stop_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.start_stop_btn.setStyleSheet(
            """
            QPushButton { background-color: #4a4a4a; color: white; border-radius: 4px; padding: 6px 14px; }
            QPushButton:hover { background-color: #333333; }
        """
        )
        self.start_stop_btn.clicked.connect(self.toggle_timer)
        right_timer_layout.addWidget(self.start_stop_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.reset_btn.setStyleSheet(
            """
            QPushButton { background-color: #dc3545; color: white; border-radius: 4px; padding: 6px 14px; margin-left: 4px; }
            QPushButton:hover { background-color: #bd2130; }
        """
        )
        self.reset_btn.clicked.connect(self.reset_timer)
        right_timer_layout.addWidget(self.reset_btn)
        top_layout.addLayout(right_timer_layout)

        main_layout.addLayout(top_layout)

        self.file_label = QLabel("No workout selected")
        self.file_label.setFont(QFont("Arial", 10, QFont.Weight.Normal))
        self.file_label.setStyleSheet(
            "color: gray; font-style: italic; margin-top: 4px; margin-bottom: 8px; margin-left: 2px;"
        )
        main_layout.addWidget(self.file_label)

        self.display_area = QTextBrowser()
        main_layout.addWidget(self.display_area)

        self.check_and_load_today_workout()

    def toggle_timer(self):
        if self.stopwatch.isActive():
            self.stopwatch.stop()
            self.prompt_record_workout()
            self.set_start_button_state()
        else:
            self.stopwatch.start(1000)
            self.start_stop_btn.setText("Stop")
            self.start_stop_btn.setStyleSheet(
                """
                QPushButton { background-color: #e0a800; color: black; border-radius: 4px; padding: 6px 14px; }
                QPushButton:hover { background-color: #d39e00; }
            """
            )

    def set_start_button_state(self):
        self.start_stop_btn.setText("Start")
        self.start_stop_btn.setStyleSheet(
            """
            QPushButton { background-color: #4a4a4a; color: white; border-radius: 4px; padding: 6px 14px; }
            QPushButton:hover { background-color: #333333; }
        """
        )

    def prompt_record_workout(self):
        workout_name = self.current_workout_name or "Unknown Workout"
        dialog = WorkoutRecordDialog(
            self, workout_name=workout_name, total_seconds=self.timer_seconds
        )
        response = dialog.exec()

        if response == QDialog.DialogCode.Accepted:
            duration_seconds = dialog.get_duration_seconds()
            save_workout_record(
                workout_name,
                datetime.now().strftime("%Y-%m-%d"),
                duration_seconds,
            )

    def reset_timer(self):
        self.stopwatch.stop()
        self.timer_seconds = 0
        self.timer_label.setText("00:00")
        self.set_start_button_state()

    def update_timer_display(self):
        self.timer_seconds += 1
        minutes = self.timer_seconds // 60
        seconds = self.timer_seconds % 60
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

    def check_and_load_today_workout(self):
        today_name = datetime.now().strftime("%A")
        _, workout_template_id = get_schedule_for_day(today_name)

        if workout_template_id is not None:
            template = get_workout_template_by_id(workout_template_id)
            if template:
                self.current_workout_name = template[1]
                markdown_content = self.generate_workout_markdown(workout_template_id, template)
                self.display_area.setMarkdown(markdown_content)
                self.file_label.setText(
                    f"Loaded today's scheduled workout ({today_name}): {template[1]}"
                )
                self.file_label.setStyleSheet(
                    "color: #007acc; font-style: normal; margin-top: 4px; margin-bottom: 8px; margin-left: 2px;"
                )
                return

        self.current_workout_name = ""
        self.display_area.setMarkdown(
            f"<h1>Welcome</h1><p>No workout is assigned for <b>{today_name}</b> yet.</p>"
            "<p>Click <b>Manage Schedule</b> above to link a saved workout to a day of the week.</p>"
        )

    def load_selected_workout_preview(self, index):
        workout_id = self.workout_selector.itemData(index)
        if workout_id in (None, -1):
            self.display_area.setMarkdown(
                "<h1>Workout Preview</h1><p>Select a saved workout from the dropdown to generate and display its markdown preview.</p>"
            )
            self.file_label.setText("Previewing generated workout markdown")
            self.file_label.setStyleSheet(
                "color: #6c757d; font-style: italic; margin-top: 4px; margin-bottom: 8px; margin-left: 2px;"
            )
            return

        template = get_workout_template_by_id(workout_id)
        if not template:
            return

        markdown_content = self.generate_workout_markdown(workout_id, template)
        self.display_area.setMarkdown(markdown_content)
        self.file_label.setText(f"Previewing saved workout template: {template[1]}")
        self.file_label.setStyleSheet(
            "color: #0d6efd; font-style: normal; margin-top: 4px; margin-bottom: 8px; margin-left: 2px;"
        )

    def generate_workout_markdown(self, workout_id, template):
        _, name, description, equipment_needed, phase_rest_seconds = template
        lines = [
            f"# {name}",
            "",
            f"*   **Description:** {description}",
            f"*   **Equipment:** {equipment_needed or 'No equipment specified'}",
            f"*   **Rest Between Phases:** {phase_rest_seconds} seconds",
            "",
            "---",
            "",
        ]

        phases = get_workout_phases_for_template(workout_id)
        for phase_number, phase in enumerate(phases, start=1):
            (
                phase_id,
                _,
                phase_name,
                phase_description,
                repeat_count,
                rest_between_exercises,
            ) = phase
            lines.append(f"### Phase {phase_number}: {phase_name} ({repeat_count}x)")
            if phase_description:
                lines.append(f"*   **Phase Notes:** {phase_description}")
            lines.append(f"*   **Rest Between Exercises:** {rest_between_exercises} seconds")
            lines.append("")

            phase_exercises = get_workout_phase_exercises_for_phase(phase_id)
            for order_index, phase_exercise in enumerate(phase_exercises, start=1):
                exercise_id = phase_exercise[2]
                exercise = get_exercise_by_id(exercise_id)
                if not exercise:
                    continue

                exercise_name = exercise[1]
                instructions = exercise[2]
                image_path = exercise[3]
                measure_type = exercise[4]
                measure_value = exercise[5]
                duration_seconds = exercise[6]
                muscle_groups = exercise[9]

                lines.append(f"#### {order_index}. {exercise_name}")
                if instructions:
                    lines.append(f"*   **Directions:** {instructions}")
                if measure_type and measure_value is not None:
                    lines.append(f"*   **Reps/Time:** {measure_value} {measure_type}")
                elif duration_seconds:
                    lines.append(f"*   **Reps/Time:** {duration_seconds} seconds")
                if muscle_groups:
                    lines.append(f"*   **Muscle Groups:** {muscle_groups}")
                if image_path:
                    image_uri = self._resolve_preview_image_uri(image_path)
                    lines.append(f'<br/><img src="{image_uri}" width="350"  />')
                lines.append("<br/>")

        return "\n".join(lines)

    def _resolve_preview_image_uri(self, image_path):
        candidate = Path(image_path)
        if not candidate.is_absolute():
            candidate = (Path(__file__).resolve().parents[1] / candidate).resolve()
        return candidate.as_uri() if candidate.exists() else str(candidate)

    def open_schedule_manager(self):
        dialog = ScheduleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.check_and_load_today_workout()

    def open_history_view(self):
        dialog = WorkoutHistoryDialog(self)
        dialog.exec()

    def open_exercise_builder(self):
        dialog = ExerciseBuilderDialog(self)
        dialog.exec()

    def open_workout_builder(self):
        dialog = WorkoutBuilderDialog(self)
        dialog.exec()


def main():
    init_db()
    app = QApplication(sys.argv)
    viewer = WorkoutViewerApp()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
