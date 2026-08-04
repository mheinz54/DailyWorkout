import os

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton, QFileDialog
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from src.database import get_file_for_day, save_file_for_day


class ScheduleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Workouts to Days")
        self.setMinimumWidth(600)

        layout = QVBoxLayout(self)
        grid = QGridLayout()
        layout.addLayout(grid)

        self.file_inputs = {}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for row, day in enumerate(days):
            day_label = QLabel(f"<b>{day}:</b>")
            day_label.setFont(QFont("Arial", 11))
            grid.addWidget(day_label, row, 0)

            current_path = get_file_for_day(day)
            display_text = os.path.basename(current_path) if current_path else "No file assigned"

            path_label = QLabel(display_text)
            path_label.setStyleSheet("color: #555; font-style: italic;")
            grid.addWidget(path_label, row, 1)

            self.file_inputs[day] = (current_path, path_label)

            browse_btn = QPushButton("Browse...")
            browse_btn.clicked.connect(lambda checked, d=day: self.browse_file(d))
            grid.addWidget(browse_btn, row, 2)

            clear_btn = QPushButton("Clear")
            clear_btn.clicked.connect(lambda checked, d=day: self.clear_file(d))
            grid.addWidget(clear_btn, row, 3)

        close_btn = QPushButton("Done")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def browse_file(self, day):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select Workout for {day}", "", "Markdown Files (*.md *.markdown);;All Files (*)"
        )
        if file_path:
            save_file_for_day(day, file_path)
            _, label = self.file_inputs[day]
            self.file_inputs[day] = (file_path, label)
            label.setText(os.path.basename(file_path))

    def clear_file(self, day):
        save_file_for_day(day, "")
        _, label = self.file_inputs[day]
        self.file_inputs[day] = ("", label)
        label.setText("No file assigned")
