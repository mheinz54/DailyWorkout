from pathlib import Path
from shutil import copy2

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QTextOption
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
)

from src.database import (
    get_exercise_by_id,
    get_exercises,
    save_exercise_record,
    update_exercise_record,
)

BASE_DIR = Path(__file__).resolve().parents[1]
WORKOUTS_IMAGES_DIR = BASE_DIR / "images"
WORKOUTS_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


class ExerciseBuilderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exercise Builder")
        self.resize(640, 440)
        self.image_storage_path = ""
        self.editing_exercise_id = None

        # --- Instantiate Input Elements ---
        self.exercise_selector = QComboBox()
        self.exercise_selector.addItem("Create New Exercise", -1)
        for exercise_id, name, *_ in get_exercises():
            self.exercise_selector.addItem(name, exercise_id)
        self.exercise_selector.currentIndexChanged.connect(self.load_selected_exercise)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Dumbbell Row")
        self.name_input.setMinimumWidth(250)

        self.muscle_groups_input = QLineEdit()
        self.muscle_groups_input.setPlaceholderText("e.g. Chest, Shoulders, Triceps")
        self.muscle_groups_input.setMinimumWidth(250)

        instructions_label = QLabel("How to Do It")
        instructions_label.setStyleSheet("font-weight: bold;")
        self.instructions_input = QPlainTextEdit()
        self.instructions_input.setPlaceholderText("Describe how to perform the exercise")
        self.instructions_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.instructions_input.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.instructions_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.instructions_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.instructions_input.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.measure_type_combo = QComboBox()
        self.measure_type_combo.addItems(["Reps", "Duration"])

        self.reps_label = QLabel("Reps")
        self.reps_input = QSpinBox()
        self.reps_input.setRange(1, 500)
        self.reps_input.setValue(10)

        self.duration_label = QLabel("Duration")
        self.duration_input = QSpinBox()
        self.duration_input.setRange(1, 3600)
        self.duration_input.setValue(30)
        self.duration_input.setSuffix(" sec")
        self.duration_input.setEnabled(False)

        self.alternating_checkbox = QCheckBox("One side, then switch")
        self.side_switch_seconds_input = QSpinBox()
        self.side_switch_seconds_input.setRange(1, 600)
        self.side_switch_seconds_input.setValue(30)
        self.side_switch_seconds_input.setSuffix(" sec")
        self.side_switch_seconds_input.setEnabled(False)

        self.image_label = QLabel("No image selected")
        self.image_label.setFixedSize(160, 120)  # Expanded aspect ratio for the dashboard panel
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setObjectName("ImagePreviewLabel")

        select_image_btn = QPushButton("Choose Image")
        select_image_btn.clicked.connect(self.choose_image)

        # --- Signal Connections ---
        self.alternating_checkbox.toggled.connect(self.side_switch_seconds_input.setEnabled)
        self.measure_type_combo.currentTextChanged.connect(self.update_measure_visibility)

        # --- Two-Column Layout Engineering ---
        outer_layout = QVBoxLayout(self)
        content_layout = QHBoxLayout()

        # Left Column: Descriptions & Details
        left_panel = QVBoxLayout()
        form_layout_left = QFormLayout()
        form_layout_left.addRow("Load Exercise:", self.exercise_selector)
        form_layout_left.addRow("Name:", self.name_input)
        form_layout_left.addRow("Muscles:", self.muscle_groups_input)

        left_panel.addLayout(form_layout_left)
        left_panel.addSpacing(10)
        left_panel.addWidget(instructions_label)
        left_panel.addWidget(self.instructions_input, 1)

        # Right Column: Media Preview & Quantitative Mechanics
        right_panel = QVBoxLayout()
        right_panel.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Media Widget Grouping
        image_group = QVBoxLayout()
        image_group.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        image_group.addWidget(self.image_label, 0, Qt.AlignmentFlag.AlignCenter)
        image_group.addWidget(select_image_btn)
        right_panel.addLayout(image_group)
        right_panel.addSpacing(20)

        # Quantitative Config Form
        form_layout_right = QFormLayout()
        form_layout_right.addRow("Track By:", self.measure_type_combo)
        form_layout_right.addRow(self.reps_label, self.reps_input)
        form_layout_right.addRow(self.duration_label, self.duration_input)
        form_layout_right.addRow("Rotation:", self.alternating_checkbox)
        form_layout_right.addRow("Switch Time:", self.side_switch_seconds_input)
        right_panel.addLayout(form_layout_right)

        # Glue Columns Together (60% width Left, 40% width Right)
        content_layout.addLayout(left_panel, 60)
        content_layout.addSpacing(15)  # Gutter separation
        content_layout.addLayout(right_panel, 40)

        outer_layout.addLayout(content_layout, 1)

        # Dialog Action Row
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_exercise)
        button_box.rejected.connect(self.reject)

        save_btn = button_box.button(QDialogButtonBox.StandardButton.Save)
        if save_btn:
            save_btn.setObjectName("DoneBtn")

        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setObjectName("CancelBtn")

        outer_layout.addWidget(button_box)

        # Run initialization visibility check
        self.update_measure_visibility(self.measure_type_combo.currentText())

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
            return

        exercise = get_exercise_by_id(exercise_id)
        if not exercise:
            return

        self.editing_exercise_id = exercise[0]
        (
            _,
            name,
            instructions,
            image_path,
            measure_type,
            measure_value,
            duration_seconds,
            alternates_sides,
            side_switch_seconds,
            muscle_groups,
        ) = exercise

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
            self.image_label.setStyleSheet(
                "border: 1px solid #cccccc; color: gray; background: #f6f6f6;"
            )
            return

        image_path = BASE_DIR / self.image_storage_path
        if image_path.exists():
            pixmap = QPixmap(str(image_path))
            scaled_pixmap = pixmap.scaled(
                160,
                120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setStyleSheet("border: 1px solid #cccccc; background: #ffffff;")
        else:
            self.image_label.clear()
            self.image_label.setText("Image missing")
            self.image_label.setStyleSheet(
                "border: 1px solid #cccccc; color: gray; background: #f6f6f6;"
            )

    def choose_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Exercise Image",
            None,
            "Images (*.png *.jpg *.jpeg *.gif *.webp);;All Files (*)",
        )
        if not file_path:
            return

        original_name = Path(file_path).name
        destination = WORKOUTS_IMAGES_DIR / original_name
        if not destination.exists():
            copy2(file_path, destination)

        self.image_storage_path = str(destination.relative_to(BASE_DIR)).replace("\\", "/")
        self.update_image_preview()

    def save_exercise(self):
        name = self.name_input.text().strip()
        instructions = self.instructions_input.toPlainText().strip()
        muscle_groups = self.muscle_groups_input.text().strip()

        if not name or not instructions:
            QMessageBox.warning(
                self,
                "Missing information",
                "Exercise name and instructions are required.",
            )
            return

        measure_type = self.measure_type_combo.currentText()
        if measure_type == "Reps":
            measure_value = self.reps_input.value()
            duration_seconds = 0
        else:
            measure_value = 0
            duration_seconds = self.duration_input.value()

        alternates_sides = 1 if self.alternating_checkbox.isChecked() else 0
        side_switch_seconds = (
            self.side_switch_seconds_input.value() if self.alternating_checkbox.isChecked() else 0
        )

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
