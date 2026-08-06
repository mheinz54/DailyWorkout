from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QBrush, QFont, QTextCharFormat
from PyQt6.QtWidgets import (
    QCalendarWidget,
    QDialog,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.database import delete_workout_record, get_workout_history, get_workout_record
from src.workout_history_edit_dialog import WorkoutHistoryEditDialog


class WorkoutHistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workout History")
        self.resize(700, 650)

        self.layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.history_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)

        self.calendar_container = QWidget()
        self.calendar_layout = QVBoxLayout(self.calendar_container)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setHorizontalHeaderFormat(
            QCalendarWidget.HorizontalHeaderFormat.ShortDayNames
        )
        self.calendar_layout.addWidget(self.calendar)
        self.layout.addWidget(self.calendar_container)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        self.layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.refresh_history()

    def refresh_history(self):
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                for child in reversed(range(item.layout().count())):
                    child_item = item.layout().takeAt(child)
                    if child_item.widget():
                        child_item.widget().deleteLater()
                item.layout().deleteLater()

        records = get_workout_history()
        if not records:
            self.history_layout.addWidget(QLabel("No workout history recorded yet."))
            self.update_calendar_dates([])
            return

        grouped_records = {}
        for record in records:
            _, workout_name, workout_date, duration_seconds = record
            grouped_records.setdefault(workout_name, []).append(record)

        for workout_name, workout_entries in grouped_records.items():
            group = QGroupBox(f"{workout_name}")
            group_layout = QVBoxLayout(group)

            for record_id, _, workout_date, duration_seconds in workout_entries:
                entry_layout = QVBoxLayout()
                duration_minutes = duration_seconds // 60
                duration_seconds_remaining = duration_seconds % 60
                duration_text = f"{duration_minutes:02d}:{duration_seconds_remaining:02d}"

                entry_label = QLabel(f"{workout_date} • {duration_text}")
                entry_layout.addWidget(entry_label)

                actions_layout = QVBoxLayout()
                edit_btn = QPushButton("Edit")
                edit_btn.clicked.connect(
                    lambda checked, record_id=record_id: self.edit_record(record_id)
                )
                actions_layout.addWidget(edit_btn)

                delete_btn = QPushButton("Delete")
                delete_btn.clicked.connect(
                    lambda checked, record_id=record_id: self.delete_record(record_id)
                )
                actions_layout.addWidget(delete_btn)

                group_layout.addLayout(entry_layout)
                group_layout.addLayout(actions_layout)

            self.history_layout.addWidget(group)

        self.update_calendar_dates([record[2] for record in records])

    def update_calendar_dates(self, workout_dates):
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QBrush(Qt.GlobalColor.lightGray))
        highlight_format.setForeground(Qt.GlobalColor.black)
        highlight_format.setFontWeight(QFont.Weight.Bold)

        for workout_date in sorted(set(workout_dates)):
            try:
                calendar_date = QDate.fromString(workout_date, "yyyy-MM-dd")
                if calendar_date.isValid():
                    self.calendar.setDateTextFormat(calendar_date, highlight_format)
            except Exception:
                continue

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
