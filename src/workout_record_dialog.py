from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QSpinBox, QDialogButtonBox


class WorkoutRecordDialog(QDialog):
    def __init__(self, parent=None, workout_name="Unknown Workout", total_seconds=0):
        super().__init__(parent)
        self.setWindowTitle("Record Workout?")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Would you like to record '{workout_name}'?"))

        form_layout = QFormLayout()
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 999)
        self.minutes_spin.setValue(total_seconds // 60)
        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 59)
        self.seconds_spin.setValue(total_seconds % 60)

        form_layout.addRow("Minutes:", self.minutes_spin)
        form_layout.addRow("Seconds:", self.seconds_spin)
        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_duration_seconds(self):
        return (self.minutes_spin.value() * 60) + self.seconds_spin.value()
