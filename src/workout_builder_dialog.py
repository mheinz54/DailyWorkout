from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPlainTextEdit,
    QComboBox, QSpinBox, QCheckBox, QPushButton, QLabel,
    QMessageBox, QHBoxLayout, QDialogButtonBox, QSizePolicy,
    QWidget, QScrollArea, QGroupBox, QFrame,
)
from PyQt6.QtGui import QTextOption
from PyQt6.QtCore import Qt

from src.database import (
    get_exercises,
    get_workout_templates,
    get_workout_template_by_id,
    save_workout_template,
    update_workout_template,
    save_workout_phase,
    save_workout_phase_exercise,
    get_workout_phases_for_template,
    get_workout_phase_exercises_for_phase,
    delete_workout_phases_for_template,
)


class WorkoutPhaseEditor(QWidget):
    def __init__(self, phase_number=1):
        super().__init__()
        self.exercise_entries = []
        self.exercise_lookup = {exercise_id: name for exercise_id, name, *_ in get_exercises()}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        group = QGroupBox(f"Phase {phase_number}")
        group_layout = QVBoxLayout(group)

        phase_form = QFormLayout()
        self.phase_name_input = QLineEdit()
        self.phase_name_input.setMinimumWidth(200)
        phase_form.addRow("Phase Name", self.phase_name_input)

        self.phase_description_input = QPlainTextEdit()
        self.phase_description_input.setMinimumHeight(80)
        self.phase_description_input.setMinimumWidth(200)
        self.phase_description_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.phase_description_input.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.phase_description_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        phase_form.addRow("Phase Description", self.phase_description_input)

        self.repeat_count_input = QSpinBox()
        self.repeat_count_input.setRange(1, 100)
        self.repeat_count_input.setValue(1)
        phase_form.addRow("Complete This Phase", self.repeat_count_input)

        self.rest_between_exercises_input = QSpinBox()
        self.rest_between_exercises_input.setRange(0, 600)
        self.rest_between_exercises_input.setSuffix(" sec")
        self.rest_between_exercises_input.setValue(30)
        phase_form.addRow("Rest Between Exercises", self.rest_between_exercises_input)

        group_layout.addLayout(phase_form)

        self.exercise_combo = QComboBox()
        self.exercise_combo.addItem("Select saved exercise", -1)
        for exercise_id, name, *_ in get_exercises():
            self.exercise_combo.addItem(name, exercise_id)
        self.exercise_combo.setMinimumWidth(250)

        add_exercise_btn = QPushButton("Add Exercise")
        add_exercise_btn.clicked.connect(self.add_selected_exercise)

        exercise_control_layout = QHBoxLayout()
        exercise_control_layout.addWidget(self.exercise_combo)
        exercise_control_layout.addWidget(add_exercise_btn)
        group_layout.addLayout(exercise_control_layout)

        self.exercises_container = QWidget()
        self.exercises_layout = QVBoxLayout(self.exercises_container)
        self.exercises_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(self.exercises_container)

        layout.addWidget(group)

    def add_selected_exercise(self):
        exercise_id = self.exercise_combo.currentData()
        if exercise_id in (None, -1):
            QMessageBox.warning(self, "Select an exercise", "Choose a saved exercise from the dropdown first.")
            return

        self.add_exercise_by_id(exercise_id)

    def add_exercise_by_id(self, exercise_id):
        exercise_name = self.exercise_lookup.get(exercise_id, f"Exercise {exercise_id}")
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(exercise_name)
        row_layout.addWidget(label)

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_exercise_row(row, exercise_id))
        row_layout.addWidget(remove_btn)

        self.exercises_layout.addWidget(row)
        self.exercise_entries.append((exercise_id, exercise_name, row))

    def remove_exercise_row(self, row_widget, exercise_id):
        self.exercises_layout.removeWidget(row_widget)
        row_widget.deleteLater()
        self.exercise_entries = [(saved_id, name, existing_row) for saved_id, name, existing_row in self.exercise_entries if existing_row is not row_widget]


class WorkoutBuilderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workout Builder")
        self.resize(900, 760)
        self.editing_workout_id = None
        self.phase_editors = []

        top_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.workout_selector = QComboBox()
        self.workout_selector.setMinimumWidth(200)
        self.workout_selector.addItem("Create New Workout", -1)
        for workout_id, name, *_ in get_workout_templates():
            self.workout_selector.addItem(name, workout_id)
        self.workout_selector.currentIndexChanged.connect(self.load_selected_workout)
        form_layout.addRow("Load Saved Workout", self.workout_selector)

        self.name_input = QLineEdit()
        self.name_input.setMinimumWidth(200)
        self.name_input.setPlaceholderText("e.g. Upper Back & Shoulder Circuit")
        form_layout.addRow("Workout Name", self.name_input)

        self.description_input = QPlainTextEdit()
        self.description_input.setMinimumHeight(80)
        self.description_input.setMinimumWidth(200)
        self.description_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.description_input.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.description_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        form_layout.addRow("Workout Description", self.description_input)

        self.equipment_input = QLineEdit()
        self.equipment_input.setMinimumWidth(200)
        self.equipment_input.setPlaceholderText("e.g. Elastic band, dumbbells, barbell")
        form_layout.addRow("Equipment Needed", self.equipment_input)

        self.phase_rest_input = QSpinBox()
        self.phase_rest_input.setRange(0, 600)
        self.phase_rest_input.setSuffix(" sec")
        self.phase_rest_input.setValue(30)
        form_layout.addRow("Rest Between Phases", self.phase_rest_input)

        top_layout.addLayout(form_layout, 1)

        phases_label = QLabel("Workout Phases")
        phases_label.setStyleSheet("font-weight: bold;")
        top_layout.addWidget(phases_label)

        self.phases_scroll = QScrollArea()
        self.phases_scroll.setWidgetResizable(True)
        self.phases_widget = QWidget()
        self.phases_layout = QVBoxLayout(self.phases_widget)
        self.phases_layout.setContentsMargins(0, 0, 0, 0)
        self.phases_scroll.setWidget(self.phases_widget)
        top_layout.addWidget(self.phases_scroll, 3)

        add_phase_btn = QPushButton("Add Phase")
        add_phase_btn.clicked.connect(self.add_phase_editor)
        top_layout.addWidget(add_phase_btn)

        self.add_phase_editor()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_workout)
        button_box.rejected.connect(self.reject)
        top_layout.addWidget(button_box)

    def add_phase_editor(self):
        editor = WorkoutPhaseEditor(phase_number=len(self.phase_editors) + 1)
        self.phase_editors.append(editor)
        self.phases_layout.addWidget(editor)

    def load_selected_workout(self, index):
        workout_id = self.workout_selector.itemData(index)
        if workout_id in (None, -1):
            self.editing_workout_id = None
            self.name_input.clear()
            self.description_input.clear()
            self.equipment_input.clear()
            self.phase_rest_input.setValue(30)
            for editor in self.phase_editors:
                editor.deleteLater()
            self.phase_editors = []
            self.add_phase_editor()
            return

        template = get_workout_template_by_id(workout_id)
        if not template:
            return

        self.editing_workout_id = template[0]
        _, name, description, equipment_needed, phase_rest_seconds = template
        self.name_input.setText(name)
        self.description_input.setPlainText(description)
        self.equipment_input.setText(equipment_needed or "")
        self.phase_rest_input.setValue(phase_rest_seconds or 30)

        for editor in self.phase_editors:
            editor.deleteLater()
        self.phase_editors = []

        phases = get_workout_phases_for_template(workout_id)
        if not phases:
            self.add_phase_editor()
            return

        for phase_number, phase in enumerate(phases, start=1):
            phase_id, _, phase_name, phase_description, repeat_count, rest_between_exercises = phase
            editor = WorkoutPhaseEditor(phase_number=phase_number)
            editor.phase_name_input.setText(phase_name)
            editor.phase_description_input.setPlainText(phase_description or "")
            editor.repeat_count_input.setValue(repeat_count or 1)
            editor.rest_between_exercises_input.setValue(rest_between_exercises or 0)

            phase_exercises = get_workout_phase_exercises_for_phase(phase_id)
            for phase_exercise in phase_exercises:
                editor.add_exercise_by_id(phase_exercise[2])

            self.phase_editors.append(editor)
            self.phases_layout.addWidget(editor)

    def save_workout(self):
        workout_name = self.name_input.text().strip()
        description = self.description_input.toPlainText().strip()
        equipment_needed = self.equipment_input.text().strip()

        if not workout_name or not description:
            QMessageBox.warning(self, "Missing details", "Workout name and description are required.")
            return

        phase_rest_seconds = self.phase_rest_input.value()

        if self.editing_workout_id is None:
            workout_id = save_workout_template(
                name=workout_name,
                description=description,
                equipment_needed=equipment_needed,
                phase_rest_seconds=phase_rest_seconds,
            )
        else:
            update_workout_template(
                self.editing_workout_id,
                name=workout_name,
                description=description,
                equipment_needed=equipment_needed,
                phase_rest_seconds=phase_rest_seconds,
            )
            workout_id = self.editing_workout_id
            delete_workout_phases_for_template(workout_id)

        for editor in self.phase_editors:
            phase_name = editor.phase_name_input.text().strip()
            phase_description = editor.phase_description_input.toPlainText().strip()
            repeat_count = editor.repeat_count_input.value()
            rest_between_exercises = editor.rest_between_exercises_input.value()

            if not phase_name:
                QMessageBox.warning(self, "Invalid phase", "Each phase needs a name.")
                return

            phase_id = save_workout_phase(
                workout_id=workout_id,
                phase_name=phase_name,
                description=phase_description,
                repeat_count=repeat_count,
                rest_between_exercises_seconds=rest_between_exercises,
            )

            for order_index, (exercise_id, exercise_name, row_widget) in enumerate(editor.exercise_entries, start=1):
                save_workout_phase_exercise(
                    phase_id=phase_id,
                    exercise_id=exercise_id,
                    display_order=order_index,
                )

        QMessageBox.information(self, "Workout Saved", f"{workout_name} was saved to the database.")
        self.accept()
