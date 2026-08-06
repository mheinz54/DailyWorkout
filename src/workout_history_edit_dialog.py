from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from src.database import get_workout_record, update_workout_record


class WorkoutHistoryEditDialog(QDialog):
    def __init__(self, parent=None, record_id=None):
        super().__init__(parent)
        self.record_id = record_id
        self.setWindowTitle("Edit Workout Record")
        self.setMinimumWidth(340)

        record = get_workout_record(record_id)
        if not record:
            self.reject()
            return

        _, workout_name, workout_date, duration_seconds = record
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_input = QLineEdit(workout_name)
        self.date_input = QDateEdit(QDate.fromString(workout_date, "yyyy-MM-dd"))
        self.date_input.setCalendarPopup(True)

        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 999)
        self.minutes_spin.setValue(duration_seconds // 60)
        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 59)
        self.seconds_spin.setValue(duration_seconds % 60)

        form_layout.addRow("Workout Name:", self.name_input)
        form_layout.addRow("Date:", self.date_input)
        form_layout.addRow("Minutes:", self.minutes_spin)
        form_layout.addRow("Seconds:", self.seconds_spin)
        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_record)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save_record(self):
        workout_name = self.name_input.text().strip()
        if not workout_name:
            QMessageBox.warning(self, "Invalid Input", "Workout name cannot be blank.")
            return

        workout_date = self.date_input.date().toString("yyyy-MM-dd")
        duration_seconds = (self.minutes_spin.value() * 60) + self.seconds_spin.value()
        update_workout_record(self.record_id, workout_name, workout_date, duration_seconds)
        self.accept()
