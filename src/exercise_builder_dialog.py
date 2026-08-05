from pathlib import Path
from shutil import copy2

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPlainTextEdit,
    QComboBox, QSpinBox, QCheckBox, QPushButton, QLabel,
    QFileDialog, QMessageBox, QHBoxLayout, QDialogButtonBox, QSizePolicy,
)
from PyQt6.QtGui import QTextOption, QPixmap
from PyQt6.QtCore import Qt

from src.database import save_exercise_record, get_exercise_by_id, update_exercise_record, get_exercises

BASE_DIR = Path(__file__).resolve().parents[1]
WORKOUTS_IMAGES_DIR = BASE_DIR / "workouts" / "images"
WORKOUTS_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


class ExerciseBuilderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exercise Builder")
        self.resize(640, 640)

        self.image_storage_path = ""
        self.editing_exercise_id = None

        outer_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.exercise_selector = QComboBox()
        self.exercise_selector.addItem("Create New Exercise", -1)
        for exercise_id, name, *_ in get_exercises():
            self.exercise_selector.addItem(name, exercise_id)
        self.exercise_selector.currentIndexChanged.connect(self.load_selected_exercise)
        form_layout.addRow("Load Saved Exercise", self.exercise_selector)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Dumbbell Row")
        self.name_input.setMinimumWidth(200)
        form_layout.addRow("Exercise Name", self.name_input)

        instructions_label = QLabel("How to Do It")
        instructions_label.setStyleSheet("font-weight: bold;")
        self.instructions_input = QPlainTextEdit()
        self.instructions_input.setPlaceholderText("Describe how to perform the exercise")
        self.instructions_input.setMinimumHeight(140)
        self.instructions_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.instructions_input.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.instructions_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.instructions_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.instructions_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.instructions_input.setMinimumWidth(520)
        instructions_layout = QVBoxLayout()
        instructions_layout.addWidget(instructions_label)
        instructions_layout.addWidget(self.instructions_input, 1)
        outer_layout.addLayout(instructions_layout, 1)

        self.measure_type_combo = QComboBox()
        self.measure_type_combo.addItems(["Reps", "Duration"])
        form_layout.addRow("Reps or Duration", self.measure_type_combo)

        self.reps_label = QLabel("Reps")
        self.reps_input = QSpinBox()
        self.reps_input.setRange(1, 500)
        self.reps_input.setValue(10)
        self.reps_input.setEnabled(True)
        form_layout.addRow(self.reps_label, self.reps_input)

        self.duration_label = QLabel("Duration")
        self.duration_input = QSpinBox()
        self.duration_input.setRange(1, 3600)
        self.duration_input.setValue(30)
        self.duration_input.setSuffix(" sec")
        self.duration_input.setEnabled(False)
        form_layout.addRow(self.duration_label, self.duration_input)

        self.alternating_checkbox = QCheckBox("Do one side, then switch to the other side")
        form_layout.addRow("Side Rotation", self.alternating_checkbox)

        self.side_switch_seconds_input = QSpinBox()
        self.side_switch_seconds_input.setRange(1, 600)
        self.side_switch_seconds_input.setValue(30)
        self.side_switch_seconds_input.setSuffix(" sec")
        self.side_switch_seconds_input.setEnabled(False)
        form_layout.addRow("Default Side Switch Time", self.side_switch_seconds_input)

        self.muscle_groups_input = QLineEdit()
        self.muscle_groups_input.setPlaceholderText("e.g. Chest, Shoulders, Triceps")
        self.muscle_groups_input.setMinimumWidth(200)
        form_layout.addRow("Muscle Groups", self.muscle_groups_input)

        self.image_label = QLabel("No image selected")
        self.image_label.setStyleSheet("color: gray;")
        self.image_label.setFixedSize(120, 90)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #cccccc; color: gray; background: #f6f6f6;")

        select_image_btn = QPushButton("Choose Image")
        select_image_btn.clicked.connect(self.choose_image)

        image_row_layout = QHBoxLayout()
        image_row_layout.addWidget(self.image_label)
        image_row_layout.addWidget(select_image_btn)
        form_layout.addRow("Exercise Image", image_row_layout)

        self.alternating_checkbox.toggled.connect(self.side_switch_seconds_input.setEnabled)
        self.measure_type_combo.currentTextChanged.connect(self.update_measure_visibility)
        self.update_measure_visibility(self.measure_type_combo.currentText())

        outer_layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_exercise)
        button_box.rejected.connect(self.reject)
        outer_layout.addWidget(button_box)

    def update_measure_visibility(self, measure_type):
        show_reps = measure_type == "Reps"
        self.reps_label.setVisible(show_reps)
        self.reps_input.setVisible(show_reps)
        self.duration_label.setVisible(not show_reps)
        self.duration_input.setVisible(not show_reps)

        self.reps_input.setEnabled(show_reps)
        self.duration_input.setEnabled(not show_reps)

    def load_selected_exercise(self, index):
        exercise_id = self.exercise_selector.itemData(index)
        if exercise_id in (None, -1):
            self.editing_exercise_id = None
            self.image_storage_path = ""
            self.name_input.clear()
            self.instructions_input.clear()
            self.measure_type_combo.setCurrentText("Reps")
            self.reps_input.setValue(10)
            self.duration_input.setValue(30)
            self.alternating_checkbox.setChecked(False)
            self.side_switch_seconds_input.setValue(30)
            self.muscle_groups_input.clear()
            self.image_label.clear()
            self.image_label.setText("No image selected")
            self.image_label.setStyleSheet("border: 1px solid #cccccc; color: gray; background: #f6f6f6;")
            return

        exercise = get_exercise_by_id(exercise_id)
        if not exercise:
            return

        self.editing_exercise_id = exercise[0]
        _, name, instructions, image_path, measure_type, measure_value, duration_seconds, alternates_sides, side_switch_seconds, muscle_groups = exercise

        self.name_input.setText(name)
        self.instructions_input.setPlainText(instructions)
        self.image_storage_path = image_path or ""
        self.muscle_groups_input.setText(muscle_groups or "")
        self.alternating_checkbox.setChecked(bool(alternates_sides))
        self.side_switch_seconds_input.setValue(side_switch_seconds or 30)

        if measure_type == "Duration":
            self.measure_type_combo.setCurrentText("Duration")
            self.duration_input.setValue(duration_seconds or 30)
            self.reps_input.setValue(measure_value or 10)
        else:
            self.measure_type_combo.setCurrentText("Reps")
            self.reps_input.setValue(measure_value or 10)
            self.duration_input.setValue(duration_seconds or 30)

        self.update_image_preview()

    def update_image_preview(self):
        if not self.image_storage_path:
            self.image_label.clear()
            self.image_label.setText("No image selected")
            self.image_label.setStyleSheet("border: 1px solid #cccccc; color: gray; background: #f6f6f6;")
            return

        image_path = BASE_DIR / self.image_storage_path
        if image_path.exists():
            pixmap = QPixmap(str(image_path))
            scaled_pixmap = pixmap.scaled(120, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setStyleSheet("border: 1px solid #cccccc; background: #ffffff;")
        else:
            self.image_label.clear()
            self.image_label.setText("Image missing")
            self.image_label.setStyleSheet("border: 1px solid #cccccc; color: gray; background: #f6f6f6;")

    def choose_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Exercise Image",
            str(BASE_DIR),
            "Images (*.png *.jpg *.jpeg *.gif *.webp);;All Files (*)",
        )
        if not file_path:
            return

        original_name = Path(file_path).name
        destination = WORKOUTS_IMAGES_DIR / original_name
        if destination.exists():
            destination = WORKOUTS_IMAGES_DIR / f"_{original_name}"
        copy2(file_path, destination)

        self.image_storage_path = str(destination.relative_to(BASE_DIR)).replace("\\", "/")
        self.update_image_preview()

    def save_exercise(self):
        name = self.name_input.text().strip()
        instructions = self.instructions_input.toPlainText().strip()
        muscle_groups = self.muscle_groups_input.text().strip()

        if not name or not instructions:
            QMessageBox.warning(self, "Missing information", "Exercise name and instructions are required.")
            return

        measure_type = self.measure_type_combo.currentText()
        if measure_type == "Reps":
            measure_value = self.reps_input.value()
            duration_seconds = 0
        else:
            measure_value = 0
            duration_seconds = self.duration_input.value()

        alternates_sides = 1 if self.alternating_checkbox.isChecked() else 0
        side_switch_seconds = self.side_switch_seconds_input.value() if self.alternating_checkbox.isChecked() else 0

        if self.editing_exercise_id is not None:
            update_exercise_record(
                self.editing_exercise_id,
                name=name,
                instructions=instructions,
                image_path=self.image_storage_path,
                measure_type=measure_type,
                measure_value=measure_value,
                duration_seconds=duration_seconds,
                alternates_sides=alternates_sides,
                side_switch_seconds=side_switch_seconds,
                muscle_groups=muscle_groups,
            )
            status_text = f"{name} was updated in the database."
        else:
            save_exercise_record(
                name=name,
                instructions=instructions,
                image_path=self.image_storage_path,
                measure_type=measure_type,
                measure_value=measure_value,
                duration_seconds=duration_seconds,
                alternates_sides=alternates_sides,
                side_switch_seconds=side_switch_seconds,
                muscle_groups=muscle_groups,
            )
            status_text = f"{name} was saved to the database."

        QMessageBox.information(self, "Exercise Saved", status_text)
        self.accept()
