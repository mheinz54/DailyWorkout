import sys
from datetime import datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
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
    get_user_setting,
    get_workout_phase_exercises_for_phase,
    get_workout_phases_for_template,
    get_workout_template_by_id,
    get_workout_templates,
    init_db,
    save_user_setting,
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
        self.setGeometry(100, 100, 950, 700)

        self.timer_seconds = 0
        self.current_workout_name = ""
        self.current_workout_id = None
        self.markdown_font_size = self.load_saved_font_size()
        self.is_expanded_mode = False

        self.stopwatch = QTimer()
        self.stopwatch.timeout.connect(self.update_timer_display)

        # Central Widget & Global Horizontal Split
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        global_layout = QHBoxLayout(main_widget)
        global_layout.setContentsMargins(0, 0, 0, 0)
        global_layout.setSpacing(0)

        # ==========================================
        # LEFT SIDEBAR
        # ==========================================
        sidebar_widget = QWidget()
        sidebar_widget.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(15, 20, 15, 20)
        sidebar_layout.setSpacing(20)

        # Sidebar Title
        sidebar_title = QLabel("Workout Hub")
        sidebar_layout.addWidget(sidebar_title)

        # Navigation Buttons (Images removed)
        self.schedule_btn = QPushButton("Manage Schedule")
        self.schedule_btn.clicked.connect(self.open_schedule_manager)
        sidebar_layout.addWidget(self.schedule_btn)

        self.history_btn = QPushButton("Workout History")
        self.history_btn.clicked.connect(self.open_history_view)
        sidebar_layout.addWidget(self.history_btn)

        # Separator line in sidebar
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        sidebar_layout.addWidget(line)

        self.exercise_builder_btn = QPushButton("Exercise Builder")
        self.exercise_builder_btn.clicked.connect(self.open_exercise_builder)
        sidebar_layout.addWidget(self.exercise_builder_btn)

        self.workout_builder_btn = QPushButton("Workout Builder")
        self.workout_builder_btn.clicked.connect(self.open_workout_builder)
        sidebar_layout.addWidget(self.workout_builder_btn)

        sidebar_layout.addStretch()
        global_layout.addWidget(sidebar_widget)

        # ==========================================
        # MAIN CONTENT AREA (Right Side)
        # ==========================================
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 20, 15, 15)
        content_layout.setSpacing(5)

        # Top Bar: Selection & Status
        top_bar_layout = QHBoxLayout()

        self.workout_selector = QComboBox()
        self.workout_selector.setMinimumWidth(300)
        self.workout_selector.addItem("Select saved workout", -1)
        for workout_id, name, *_ in get_workout_templates():
            self.workout_selector.addItem(name, workout_id)
        self.workout_selector.currentIndexChanged.connect(self.load_selected_workout_preview)
        top_bar_layout.addWidget(self.workout_selector)

        top_bar_layout.addStretch()

        # Timer Section Group
        timer_container = QWidget()
        timer_container_layout = QHBoxLayout(timer_container)
        timer_container_layout.setContentsMargins(6, 6, 6, 6)
        timer_container_layout.setSpacing(8)

        # Target specific functionality buttons using Object Names for your QSS rules
        self.start_stop_btn = QPushButton("Start")
        self.start_stop_btn.clicked.connect(self.toggle_timer)
        timer_container_layout.addWidget(self.start_stop_btn)

        self.timer_label = QLabel("00:00")
        self.timer_label.setFont(QFont("Courier New", 20, QFont.Weight.Bold))
        timer_container_layout.addWidget(self.timer_label)

        self.reset_btn = QPushButton("Reset")
        # self.reset_btn.setObjectName("ClearBtn")
        self.reset_btn.clicked.connect(self.reset_timer)
        timer_container_layout.addWidget(self.reset_btn)

        top_bar_layout.addWidget(timer_container)
        content_layout.addLayout(top_bar_layout)

        # Center Display Area
        self.display_area = QTextBrowser()
        self.display_area.setStyleSheet(f"font-size: {self.markdown_font_size}px;")
        content_layout.addWidget(self.display_area)

        # ==========================================
        # FOOTER CONTROL BAR
        # ==========================================
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        # Font Sizing Controls Section
        font_layout = QHBoxLayout()
        font_layout.setSpacing(4)

        self.decrease_font_btn = QPushButton("-")
        self.decrease_font_btn.setFont(QFont("Courier New", 20, QFont.Weight.Bold))
        self.decrease_font_btn.setFixedSize(36, 32)
        self.decrease_font_btn.clicked.connect(self.decrease_font_size)
        font_layout.addWidget(self.decrease_font_btn)

        self.font_size_label = QLabel(f"{self.markdown_font_size}px")
        self.font_size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.font_size_label.setFixedWidth(50)
        font_layout.addWidget(self.font_size_label)

        self.increase_font_btn = QPushButton("+")
        self.increase_font_btn.setFont(QFont("Courier New", 20, QFont.Weight.Bold))
        self.increase_font_btn.setFixedSize(36, 32)
        self.increase_font_btn.clicked.connect(self.increase_font_size)
        font_layout.addWidget(self.increase_font_btn)

        footer_layout.addLayout(font_layout)
        content_layout.addLayout(footer_layout)

        # Store sidebar widget and content widget for toggling
        self.sidebar_widget = sidebar_widget
        self.content_widget = content_widget

        global_layout.addWidget(content_widget)

        self.check_and_load_today_workout()

    def toggle_timer(self):
        if self.stopwatch.isActive():
            self.stopwatch.stop()
            self.prompt_record_workout()
            self.set_start_button_state()
            self.set_expand_mode(False)
        else:
            self.stopwatch.start(1000)
            self.start_stop_btn.setText("Stop")
            self.start_stop_btn.setStyleSheet(
                """
                QPushButton { background-color: #e0a800; color: black; border-radius: 4px; padding: 6px 14px; }
                QPushButton:hover { background-color: #d39e00; }
            """
            )
            self.set_expand_mode(True)

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
            self,
            workout_name=workout_name,
            total_seconds=self.timer_seconds,
            exercises=self.get_current_workout_exercises(),
        )
        response = dialog.exec()

        if response == QDialog.DialogCode.Accepted:
            duration_seconds = dialog.get_duration_seconds()
            save_workout_record(
                workout_name,
                datetime.now().strftime("%Y-%m-%d"),
                duration_seconds,
                dialog.get_exercise_results(),
            )

    def get_current_workout_exercises(self):
        if self.current_workout_id is None:
            return []

        exercises = []
        for phase in get_workout_phases_for_template(self.current_workout_id):
            repeat_count = phase[4] or 1
            phase_exercises = get_workout_phase_exercises_for_phase(phase[0])
            for repeat_number in range(1, repeat_count + 1):
                for phase_exercise in phase_exercises:
                    exercise = get_exercise_by_id(phase_exercise[2])
                    if not exercise:
                        continue
                    measure_type = exercise[4]
                    default_value = phase_exercise[3]
                    if default_value is None:
                        default_value = exercise[5] if measure_type == "Reps" else exercise[6]
                    label = f"Round {repeat_number} - {exercise[1]}"
                    exercises.append(
                        (exercise[0], label, measure_type, default_value, repeat_number)
                    )
        return exercises

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

    def load_saved_font_size(self):
        saved_value = get_user_setting("markdown_font_size")
        try:
            font_size = int(saved_value)
        except (TypeError, ValueError):
            font_size = 14
        return font_size

    def increase_font_size(self):
        self.markdown_font_size += 1
        self.font_size_label.setText(f"{self.markdown_font_size}px")
        self.apply_markdown_font_size()
        save_user_setting("markdown_font_size", self.markdown_font_size)

    def decrease_font_size(self):
        if self.markdown_font_size > 8:
            self.markdown_font_size -= 1
            self.font_size_label.setText(f"{self.markdown_font_size}px")
            self.apply_markdown_font_size()
            save_user_setting("markdown_font_size", self.markdown_font_size)

    def apply_markdown_font_size(self):
        self.display_area.setStyleSheet(f"font-size: {self.markdown_font_size}px;")

    def set_expand_mode(self, expanded: bool):
        self.is_expanded_mode = expanded

        if self.is_expanded_mode:
            # Hide sidebar and controls
            self.sidebar_widget.setVisible(False)
            self.workout_selector.setVisible(False)
            self.timer_label.setFont(QFont("Courier New", 32, QFont.Weight.Bold))
        else:
            # Show sidebar and controls
            self.sidebar_widget.setVisible(True)
            self.workout_selector.setVisible(True)
            self.timer_label.setFont(QFont("Courier New", 20, QFont.Weight.Bold))

        # Refresh the current markdown display to update the layout structure dynamically
        if hasattr(self, "workout_selector") and self.workout_selector.currentIndex() != -1:
            self.load_selected_workout_preview(self.workout_selector.currentIndex())
        else:
            self.check_and_load_today_workout()

    def check_and_load_today_workout(self):
        today_name = datetime.now().strftime("%A")
        _, workout_template_id = get_schedule_for_day(today_name)

        if workout_template_id is not None:
            template = get_workout_template_by_id(workout_template_id)
            if template:
                self.current_workout_name = template[1]
                self.current_workout_id = workout_template_id

                # Find and set the correct index in the dropdown
                dropdown_index = self.workout_selector.findData(workout_template_id)
                if dropdown_index != -1:
                    self.workout_selector.blockSignals(True)
                    self.workout_selector.setCurrentIndex(dropdown_index)
                    self.workout_selector.blockSignals(False)

                markdown_content = self.generate_workout_markdown(workout_template_id, template)
                self.display_area.setMarkdown(markdown_content)
                return

        self.workout_selector.blockSignals(True)
        self.workout_selector.setCurrentIndex(0)
        self.workout_selector.blockSignals(False)

        self.current_workout_name = ""
        self.current_workout_id = None
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
            return

        template = get_workout_template_by_id(workout_id)
        if not template:
            return

        self.current_workout_name = template[1]
        self.current_workout_id = workout_id
        markdown_content = self.generate_workout_markdown(workout_id, template)
        self.display_area.setMarkdown(markdown_content)

    def generate_workout_markdown(self, workout_id, template):
        _, name, description, equipment_needed, phase_rest_seconds = template
        lines = [
            f"# {name}",
            "",
            f"*   **Description:** {description}",
            f"*   **Equipment:** {equipment_needed or 'No equipment specified'}",
            f"*   **Rest Between Phases:** {phase_rest_seconds} seconds",
            "---",
            "",
            "<br/>",
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
            lines.append("&nbsp;")
            lines.append("<br/>")
            lines.append("")

            phase_exercises = get_workout_phase_exercises_for_phase(phase_id)
            for order_index, phase_exercise in enumerate(phase_exercises, start=1):
                exercise_id = phase_exercise[2]
                exercise = get_exercise_by_id(exercise_id)
                if not exercise:
                    continue

                exercise_name = exercise[1]
                instructions = exercise[2].replace("\n", "<br/> - ") if exercise[2] else ""
                image_path = exercise[3]
                measure_type = exercise[4]
                measure_value = phase_exercise[3] if phase_exercise[3] is not None else exercise[5]
                duration_seconds = exercise[6]
                if measure_type == "Duration" and phase_exercise[3] is not None:
                    duration_seconds = phase_exercise[3]
                alternates_sides = exercise[7]
                muscle_groups = exercise[9]

                # Format layout based on mode
                if self.is_expanded_mode:
                    # Clean HTML formatting for Expanded Mode (Inside Table)
                    details = []
                    if instructions:
                        details.append(f"<b>Directions:</b><br/> - {instructions}")
                    if measure_type == "Reps" and measure_value is not None:
                        details.append(
                            f"<b>Reps/Time:</b> {measure_value} {measure_type} {'Per Side' if alternates_sides else ''}"
                        )
                    elif duration_seconds:
                        details.append(
                            f"<b>Reps/Time:</b> {duration_seconds} seconds {'Per Side' if alternates_sides else ''}"
                        )
                    if muscle_groups:
                        details.append(f"<b>Muscle Groups:</b> {muscle_groups}")

                    details_text = "<br/>".join(details) if details else ""

                    if image_path:
                        image_uri = self._resolve_preview_image_uri(image_path)
                        image_html = f'<img src="{image_uri}" width="350" />'

                        table_html = (
                            f"<h3>{order_index}. {exercise_name}</h3>"
                            f'<table border="0" cellpadding="10" width="100%">'
                            f"  <tr>"
                            f'    <td valign="top" width="60%">{details_text}</td>'
                            f'    <td valign="top" align="right" width="40%">{image_html}</td>'
                            f"  </tr>"
                            f"</table>"
                            f"<br/>"
                        )
                        lines.append(table_html)
                    else:
                        lines.append(f"### {order_index}. {exercise_name}")
                        if details_text:
                            lines.append(details_text)
                else:
                    # Standard Markdown formatting for Normal Mode
                    lines.append(f"#### {order_index}. {exercise_name}")
                    if instructions:
                        lines.append(f"*   **Directions:** <br/> - {instructions}")
                    if measure_type == "Reps" and measure_value is not None:
                        lines.append(
                            f"*   **Reps/Time:** {measure_value} {measure_type} {'Per Side' if alternates_sides else ''}"
                        )
                    elif duration_seconds:
                        lines.append(
                            f"*   **Reps/Time:** {duration_seconds} seconds {'Per Side' if alternates_sides else ''}"
                        )
                    if muscle_groups:
                        lines.append(f"*   **Muscle Groups:** {muscle_groups}")
                    if image_path:
                        image_uri = self._resolve_preview_image_uri(image_path)
                        lines.append(f'<br/><img src="{image_uri}" width="350"  />')

            lines.append("")
            lines.append("&nbsp;")
            lines.append("")
            lines.append("---")
            lines.append("")

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
    # Load external styling sheet
    with open("src/style.qss", "r") as f:
        app.setStyleSheet(f.read())

    viewer = WorkoutViewerApp()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
