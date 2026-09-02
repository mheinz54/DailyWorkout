from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class WorkoutRecordDialog(QDialog):
    def __init__(
        self, parent=None, workout_name="Unknown Workout", total_seconds=0, exercises=None
    ):
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

        if exercises:
            layout.addWidget(QLabel("Actual Reps / Time"))
            exercise_widget = QWidget()
            exercise_layout = QFormLayout(exercise_widget)
            self.exercise_inputs = []
            for exercise_id, exercise_name, measure_type, default_value, round_number in exercises:
                value_input = QSpinBox()
                value_input.setRange(1, 3600 if measure_type == "Duration" else 500)
                value_input.setValue(default_value or 1)
                if measure_type == "Duration":
                    value_input.setSuffix(" sec")
                exercise_layout.addRow(exercise_name, value_input)
                self.exercise_inputs.append(
                    (exercise_id, exercise_name, measure_type, value_input, round_number)
                )
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(exercise_widget)
            layout.addWidget(scroll_area, 1)
        else:
            self.exercise_inputs = []

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_duration_seconds(self):
        return (self.minutes_spin.value() * 60) + self.seconds_spin.value()

    def get_exercise_results(self):
        return [
            (exercise_id, exercise_name, measure_type, value_input.value(), round_number)
            for exercise_id, exercise_name, measure_type, value_input, round_number in self.exercise_inputs
        ]
