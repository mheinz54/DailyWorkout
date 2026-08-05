import sys
import os
from pathlib import Path
from datetime import datetime

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QTextBrowser,
    QFileDialog, QMessageBox, QDialog,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer

from src.database import init_db, save_workout_record, get_file_for_day
from src.schedule_dialog import ScheduleDialog
from src.workout_record_dialog import WorkoutRecordDialog
from src.workout_history_dialog import WorkoutHistoryDialog
from src.exercise_builder_dialog import ExerciseBuilderDialog


class WorkoutViewerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Daily Workout Viewer")
        self.setGeometry(100, 100, 850, 650)

        self.timer_seconds = 0
        self.current_workout_path = ""
        self.stopwatch = QTimer()
        self.stopwatch.timeout.connect(self.update_timer_display)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        top_layout = QHBoxLayout()

        left_btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("📁 Select Markdown File")
        self.select_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.select_btn.setStyleSheet("""
            QPushButton { background-color: #007acc; color: white; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background-color: #005999; }
        """)
        self.select_btn.clicked.connect(self.load_markdown_file)
        left_btn_layout.addWidget(self.select_btn)

        self.schedule_btn = QPushButton("📅 Manage Schedule")
        self.schedule_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.schedule_btn.setStyleSheet("""
            QPushButton { background-color: #28a745; color: white; border-radius: 4px; padding: 6px 12px; margin-left: 5px; }
            QPushButton:hover { background-color: #218838; }
        """)
        self.schedule_btn.clicked.connect(self.open_schedule_manager)
        left_btn_layout.addWidget(self.schedule_btn)

        self.history_btn = QPushButton("🕘 Workout History")
        self.history_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.history_btn.setStyleSheet("""
            QPushButton { background-color: #6f42c1; color: white; border-radius: 4px; padding: 6px 12px; margin-left: 5px; }
            QPushButton:hover { background-color: #553098; }
        """)
        self.history_btn.clicked.connect(self.open_history_view)
        left_btn_layout.addWidget(self.history_btn)

        self.exercise_builder_btn = QPushButton("🏋️ Exercise Builder")
        self.exercise_builder_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.exercise_builder_btn.setStyleSheet("""
            QPushButton { background-color: #ff7b00; color: white; border-radius: 4px; padding: 6px 12px; margin-left: 5px; }
            QPushButton:hover { background-color: #cc5d00; }
        """)
        self.exercise_builder_btn.clicked.connect(self.open_exercise_builder)
        left_btn_layout.addWidget(self.exercise_builder_btn)
        top_layout.addLayout(left_btn_layout)

        top_layout.addStretch()

        right_timer_layout = QHBoxLayout()
        self.timer_label = QLabel("00:00")
        self.timer_label.setFont(QFont("Courier New", 16, QFont.Weight.Bold))
        self.timer_label.setStyleSheet("color: #333; background-color: #e9ecef; padding: 4px 10px; border-radius: 4px; border: 1px solid #ced4da; margin-right: 8px;")
        right_timer_layout.addWidget(self.timer_label)

        self.start_stop_btn = QPushButton("Start")
        self.start_stop_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.start_stop_btn.setStyleSheet("""
            QPushButton { background-color: #4a4a4a; color: white; border-radius: 4px; padding: 6px 14px; }
            QPushButton:hover { background-color: #333333; }
        """)
        self.start_stop_btn.clicked.connect(self.toggle_timer)
        right_timer_layout.addWidget(self.start_stop_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.reset_btn.setStyleSheet("""
            QPushButton { background-color: #dc3545; color: white; border-radius: 4px; padding: 6px 14px; margin-left: 4px; }
            QPushButton:hover { background-color: #bd2130; }
        """)
        self.reset_btn.clicked.connect(self.reset_timer)
        right_timer_layout.addWidget(self.reset_btn)
        top_layout.addLayout(right_timer_layout)

        main_layout.addLayout(top_layout)

        self.file_label = QLabel("No file selected")
        self.file_label.setFont(QFont("Arial", 10, QFont.Weight.Normal))
        self.file_label.setStyleSheet("color: gray; font-style: italic; margin-top: 4px; margin-bottom: 8px; margin-left: 2px;")
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
            self.start_stop_btn.setStyleSheet("""
                QPushButton { background-color: #e0a800; color: black; border-radius: 4px; padding: 6px 14px; }
                QPushButton:hover { background-color: #d39e00; }
            """)

    def set_start_button_state(self):
        self.start_stop_btn.setText("Start")
        self.start_stop_btn.setStyleSheet("""
            QPushButton { background-color: #4a4a4a; color: white; border-radius: 4px; padding: 6px 14px; }
            QPushButton:hover { background-color: #333333; }
        """)

    def prompt_record_workout(self):
        workout_name = os.path.basename(self.current_workout_path) if self.current_workout_path else "Unknown Workout"
        dialog = WorkoutRecordDialog(self, workout_name=workout_name, total_seconds=self.timer_seconds)
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
        saved_path = get_file_for_day(today_name)

        if saved_path and os.path.exists(saved_path):
            self.current_workout_path = saved_path
            self.render_markdown(saved_path)
            self.file_label.setText(f"Loaded today's scheduled file ({today_name}): {os.path.abspath(saved_path)}")
            self.file_label.setStyleSheet("color: #007acc; font-style: normal; margin-top: 4px; margin-bottom: 8px; margin-left: 2px;")
        else:
            self.current_workout_path = ""
            self.display_area.setMarkdown(
                f"<h1>Welcome</h1><p>No workout file is assigned for <b>{today_name}</b> yet.</p>"
                "<p>Click <b>Manage Schedule</b> above to link your `.md` files to days of the week.</p>"
            )

    def load_markdown_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Markdown File", "", "Markdown Files (*.md *.markdown);;Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.current_workout_path = file_path
            self.render_markdown(file_path)
            self.file_label.setText(os.path.abspath(file_path))
            self.file_label.setStyleSheet("color: green; font-style: normal; margin-top: 4px; margin-bottom: 8px; margin-left: 2px;")

    def render_markdown(self, path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                md_content = file.read()

            markdown_dir = Path(path).resolve().parent
            image_dir_uri = (markdown_dir / "images").resolve().as_uri() + "/"
            md_content = md_content.replace('src="images/', f'src="{image_dir_uri}')
            md_content = md_content.replace('(images/', f'({image_dir_uri}')

            self.display_area.setMarkdown(md_content)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read or parse file:\n{str(e)}")

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


def main():
    init_db()
    app = QApplication(sys.argv)
    viewer = WorkoutViewerApp()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
