from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
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

        # Main Layout container
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Content Grid
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)  # Day Column
        grid.setColumnStretch(1, 4)  # Dropdown Column
        grid.setColumnStretch(2, 0)  # Clear Button Column (Hug contents)
        main_layout.addLayout(grid)

        self.schedule_inputs = {}
        self.clear_buttons = {}
        self.initial_state = {}  # Tracks database state for rollback
        self.workout_templates = get_workout_templates()

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for row, day in enumerate(days):
            # 1. Day Label styling
            day_label = QLabel(day)
            day_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
            grid.addWidget(day_label, row, 0, Qt.AlignmentFlag.AlignVCenter)

            # 2. Setup the Dropdown
            workout_combo = QComboBox()
            workout_combo.setFont(QFont("Segoe UI", 10))
            workout_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            workout_combo.addItem("Select saved workout", -1)

            for template_id, name, *_ in self.workout_templates:
                workout_combo.addItem(name, template_id)

            # Load initial data smoothly without triggering early save signals
            workout_combo.blockSignals(True)
            schedule_path, workout_template_id = get_schedule_for_day(day)

            # Store snapshot data for rollback history
            self.initial_state[day] = workout_template_id

            if workout_template_id is not None:
                index = workout_combo.findData(workout_template_id)
                if index != -1:
                    workout_combo.setCurrentIndex(index)
            workout_combo.blockSignals(False)

            grid.addWidget(workout_combo, row, 1)
            self.schedule_inputs[day] = workout_combo

            # 3. Setup sleek Clear Button
            clear_btn = QPushButton("×")
            clear_btn.setObjectName("ClearBtn")
            clear_btn.setToolTip(f"Clear workout assignment for {day}")
            clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            grid.addWidget(clear_btn, row, 2)
            self.clear_buttons[day] = clear_btn

            # Dynamic visibility based on selection presence
            clear_btn.setVisible(workout_combo.currentIndex() > 0)

            # Connect selection changes to update visibility state instantly
            workout_combo.currentIndexChanged.connect(
                lambda _, d=day, c=workout_combo: self.select_workout(d, c)
            )
            clear_btn.clicked.connect(
                lambda checked, d=day, c=workout_combo: self.clear_selection(d, c)
            )

        # Divider line above action items
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("color: #dee2e6;")
        main_layout.addWidget(divider)

        # 4. Dialog Actions Footer
        footer_layout = QHBoxLayout()

        # Cancel Button (Triggers rollback)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.clicked.connect(self.rollback_and_reject)

        # Done Button
        close_btn = QPushButton("Done")
        close_btn.setObjectName("DoneBtn")
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.clicked.connect(self.accept)

        footer_layout.addStretch()
        footer_layout.addWidget(cancel_btn)
        footer_layout.addWidget(close_btn)
        main_layout.addLayout(footer_layout)

    def select_workout(self, day, combo):
        workout_id = combo.currentData()
        if workout_id in (None, -1):
            save_schedule_for_day(day, "", None)
        else:
            save_schedule_for_day(day, "", workout_id)
        # Update clear button visibility
        if day in self.clear_buttons:
            self.clear_buttons[day].setVisible(combo.currentIndex() > 0)

    def clear_selection(self, day, combo):
        combo.setCurrentIndex(0)
        save_schedule_for_day(day, "", None)

    def rollback_and_reject(self):
        """Restores database assignments to what they were when dialog opened."""
        for day, original_workout_id in self.initial_state.items():
            save_schedule_for_day(day, "", original_workout_id)
        self.reject()
