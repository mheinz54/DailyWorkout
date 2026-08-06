from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.database import (
    get_schedule_for_day,
    get_workout_templates,
    save_schedule_for_day,
)


class ScheduleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Saved Workouts to Days")
        self.setMinimumWidth(660)

        layout = QVBoxLayout(self)
        grid = QGridLayout()
        layout.addLayout(grid)

        self.schedule_inputs = {}
        self.workout_templates = get_workout_templates()
        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        for row, day in enumerate(days):
            day_label = QLabel(f"<b>{day}:</b>")
            day_label.setFont(QFont("Arial", 11))
            grid.addWidget(day_label, row, 0)

            schedule_path, workout_template_id = get_schedule_for_day(day)

            workout_combo = QComboBox()
            workout_combo.addItem("Select saved workout", -1)
            for template_id, name, *_ in self.workout_templates:
                workout_combo.addItem(name, template_id)

            workout_combo.blockSignals(True)
            if workout_template_id is not None:
                index = workout_combo.findData(workout_template_id)
                if index != -1:
                    workout_combo.setCurrentIndex(index)
            workout_combo.blockSignals(False)
            workout_combo.currentIndexChanged.connect(
                lambda _, d=day, c=workout_combo: self.select_workout(d, c)
            )
            grid.addWidget(workout_combo, row, 1)

            clear_btn = QPushButton("Clear")
            clear_btn.clicked.connect(
                lambda checked, d=day, c=workout_combo: self.clear_selection(d, c)
            )
            grid.addWidget(clear_btn, row, 2)

            self.schedule_inputs[day] = workout_combo

        close_btn = QPushButton("Done")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def select_workout(self, day, combo):
        workout_id = combo.currentData()
        if workout_id in (None, -1):
            save_schedule_for_day(day, "", None)
        else:
            save_schedule_for_day(day, "", workout_id)

    def clear_selection(self, day, combo):
        combo.setCurrentIndex(0)
        save_schedule_for_day(day, "", None)
