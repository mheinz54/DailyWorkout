from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QBrush, QFont, QTextCharFormat
from PyQt6.QtWidgets import (
    QCalendarWidget,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.database import (
    delete_workout_record,
    get_workout_history,
    get_workout_record,
    get_workout_record_exercises,
)
from src.workout_history_edit_dialog import WorkoutHistoryEditDialog


class WorkoutHistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workout History")
        self.resize(850, 600)  # Widened to fit the side-by-side view cleanly

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)

        # Split Container (History Left, Calendar Right)
        self.split_layout = QHBoxLayout()
        self.split_layout.setSpacing(15)

        # Left Column: Scrollable History List (60% width stretch)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.history_layout = QVBoxLayout(self.scroll_content)
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        self.split_layout.addWidget(self.scroll_area, stretch=6)

        # Right Column: Sticky Calendar View (40% width stretch)
        self.calendar_container = QWidget()
        self.calendar_layout = QVBoxLayout(self.calendar_container)
        self.calendar_layout.setContentsMargins(0, 0, 0, 0)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setHorizontalHeaderFormat(
            QCalendarWidget.HorizontalHeaderFormat.ShortDayNames
        )
        # Connect interactive calendar scrolling
        self.calendar.clicked.connect(self.scroll_to_calendar_date)

        self.calendar_layout.addWidget(self.calendar)
        self.calendar_layout.addStretch()  # Prevent calendar stretching vertically
        self.split_layout.addWidget(self.calendar_container, stretch=4)

        self.main_layout.addLayout(self.split_layout)

        # Bottom Actions Bar
        self.bottom_layout = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("DoneBtn")  # Uses your primary style
        close_btn.clicked.connect(self.accept)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(close_btn)
        self.main_layout.addLayout(self.bottom_layout)

        # Dictionary to store references to group widgets for automatic scrolling mapping
        self.date_groups = {}

        self.refresh_history()

    def refresh_history(self):
        # Clean up existing items safely
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        self.date_groups.clear()
        records = get_workout_history()

        if not records:
            no_data_lbl = QLabel("No workout history recorded yet.")
            no_data_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_layout.addWidget(no_data_lbl)
            self.update_calendar_dates([])
            return

        # Sort records chronologically (newest dates first)
        records.sort(key=lambda x: x[2], reverse=True)

        # Group records by Date instead of exercise type
        grouped_by_date = {}
        for record in records:
            _, _, workout_date, _ = record
            grouped_by_date.setdefault(workout_date, []).append(record)

        for workout_date, entries in grouped_by_date.items():
            # Date group box header
            date_group = QGroupBox(f"🗓️ {workout_date}")
            date_group_layout = QVBoxLayout(date_group)
            date_group_layout.setSpacing(8)

            for record_id, workout_name, _, duration_seconds in entries:
                # Workout row layout
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(4, 2, 4, 2)

                # Format time string duration
                duration_minutes = duration_seconds // 60
                duration_seconds_remaining = duration_seconds % 60
                duration_text = f"{duration_minutes:02d}:{duration_seconds_remaining:02d}"

                # Compact textual hierarchy label
                entry_label = QLabel(f"<b>{workout_name}</b> ({duration_text})")
                row_layout.addWidget(entry_label, stretch=1)

                details_btn = QPushButton("Details")
                details_btn.clicked.connect(
                    lambda checked, r_id=record_id: self.show_record_details(r_id)
                )
                row_layout.addWidget(details_btn)

                # Edit Action Button
                edit_btn = QPushButton("Edit")
                edit_btn.setObjectName("EditBtn")  # Secondary neutral visual style
                # edit_btn.setFixedWidth(65)
                edit_btn.clicked.connect(lambda checked, r_id=record_id: self.edit_record(r_id))
                row_layout.addWidget(edit_btn)

                # Delete Action Button
                delete_btn = QPushButton("x")
                delete_btn.setObjectName("ClearBtn")  # Leverages your warning/red style definitions
                # delete_btn.setFixedWidth(65)
                delete_btn.clicked.connect(lambda checked, r_id=record_id: self.delete_record(r_id))
                row_layout.addWidget(delete_btn)

                date_group_layout.addWidget(row_widget)

            self.history_layout.addWidget(date_group)
            self.date_groups[workout_date] = date_group

        self.update_calendar_dates([record[2] for record in records])

    def show_record_details(self, record_id):
        exercises = get_workout_record_exercises(record_id)
        if not exercises:
            QMessageBox.information(self, "Workout Details", "No exercise details were recorded.")
            return

        details = "\n".join(
            f"{index}. Round {round_number} - {name}: {value} {'seconds' if measure_type == 'Duration' else 'reps'}"
            for index, (_exercise_id, name, measure_type, value, round_number) in enumerate(
                exercises, start=1
            )
        )
        QMessageBox.information(self, "Workout Details", details)

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())
            layout.deleteLater()

    def update_calendar_dates(self, workout_dates):
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QBrush(Qt.GlobalColor.lightGray))
        highlight_format.setForeground(Qt.GlobalColor.black)
        highlight_format.setFontWeight(QFont.Weight.Bold)

        # Clear existing text styling entries first to allow updates
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())

        for workout_date in sorted(set(workout_dates)):
            try:
                calendar_date = QDate.fromString(workout_date, "yyyy-MM-dd")
                if calendar_date.isValid():
                    self.calendar.setDateTextFormat(calendar_date, highlight_format)
            except Exception:
                continue

    def scroll_to_calendar_date(self, qdate):
        """Scrolls history left-panel to group block matching clicked date selection."""
        date_str = qdate.toString("yyyy-MM-dd")
        if date_str in self.date_groups:
            target_widget = self.date_groups[date_str]
            self.scroll_area.ensureWidgetVisible(target_widget)

    def edit_record(self, record_id):
        edit_dialog = WorkoutHistoryEditDialog(self, record_id=record_id)
        if edit_dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_history()

    def delete_record(self, record_id):
        record = get_workout_record(record_id)
        if not record:
            return
        confirm = QMessageBox.question(
            self,
            "Delete Workout Record",
            f"Delete '{record[1]}' from {record[2]}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            delete_workout_record(record_id)
            self.refresh_history()
