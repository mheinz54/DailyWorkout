import sys
import os
import sqlite3
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QTextBrowser, 
    QFileDialog, QMessageBox, QDialog, QGridLayout, 
    QSpinBox, QFormLayout, QDialogButtonBox, QGroupBox,
    QScrollArea, QLineEdit, QDateEdit, QCalendarWidget
)
from PyQt6.QtGui import QFont, QBrush, QTextCharFormat
from PyQt6.QtCore import Qt, QTimer, QDate

# --- DATABASE SETUP ---
DB_NAME = "workout_schedule.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            day_name TEXT PRIMARY KEY,
            file_path TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_name TEXT NOT NULL,
            workout_date TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL
        )
    """)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in days:
        cursor.execute("INSERT OR IGNORE INTO schedule (day_name, file_path) VALUES (?, ?)", (day, ""))
    conn.commit()
    conn.close()


def save_workout_record(workout_name, workout_date, duration_seconds):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO workout_history (workout_name, workout_date, duration_seconds) VALUES (?, ?, ?)",
        (workout_name, workout_date, duration_seconds),
    )
    conn.commit()
    conn.close()


def get_workout_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, workout_name, workout_date, duration_seconds FROM workout_history ORDER BY workout_name ASC, workout_date DESC, duration_seconds DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_workout_record(record_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, workout_name, workout_date, duration_seconds FROM workout_history WHERE id = ?",
        (record_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def delete_workout_record(record_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM workout_history WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def update_workout_record(record_id, workout_name, workout_date, duration_seconds):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE workout_history SET workout_name = ?, workout_date = ?, duration_seconds = ? WHERE id = ?",
        (workout_name, workout_date, duration_seconds, record_id),
    )
    conn.commit()
    conn.close()


def get_file_for_day(day_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM schedule WHERE day_name = ?", (day_name,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""

def save_file_for_day(day_name, file_path):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE schedule SET file_path = ? WHERE day_name = ?", (file_path, day_name))
    conn.commit()
    conn.close()


# --- RECORD WORKOUT DIALOG ---
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


# --- WORKOUT HISTORY EDIT DIALOG ---
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


# --- WORKOUT HISTORY VIEW DIALOG ---
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
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
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
            record_id, workout_name, workout_date, duration_seconds = record
            grouped_records.setdefault(workout_name, []).append(record)

        for workout_name, workout_entries in grouped_records.items():
            group = QGroupBox(f"{workout_name}")
            group_layout = QVBoxLayout(group)

            for record_id, _, workout_date, duration_seconds in workout_entries:
                entry_layout = QHBoxLayout()
                duration_minutes = duration_seconds // 60
                duration_seconds_remaining = duration_seconds % 60
                duration_text = f"{duration_minutes:02d}:{duration_seconds_remaining:02d}"

                entry_label = QLabel(f"{workout_date} • {duration_text}")
                entry_layout.addWidget(entry_label)
                entry_layout.addStretch()

                edit_btn = QPushButton("Edit")
                edit_btn.clicked.connect(lambda checked, record_id=record_id: self.edit_record(record_id))
                entry_layout.addWidget(edit_btn)

                delete_btn = QPushButton("Delete")
                delete_btn.clicked.connect(lambda checked, record_id=record_id: self.delete_record(record_id))
                entry_layout.addWidget(delete_btn)

                group_layout.addLayout(entry_layout)

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


# --- ASSIGNMENT MODAL WINDOW (7-DAY SCHEDULER) ---
class ScheduleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Workouts to Days")
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout(self)
        grid = QGridLayout()
        layout.addLayout(grid)
        
        self.file_inputs = {}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for row, day in enumerate(days):
            day_label = QLabel(f"<b>{day}:</b>")
            day_label.setFont(QFont("Arial", 11))
            grid.addWidget(day_label, row, 0)
            
            current_path = get_file_for_day(day)
            display_text = os.path.basename(current_path) if current_path else "No file assigned"
            
            path_label = QLabel(display_text)
            path_label.setStyleSheet("color: #555; font-style: italic;")
            grid.addWidget(path_label, row, 1)
            
            self.file_inputs[day] = (current_path, path_label)
            
            browse_btn = QPushButton("Browse...")
            browse_btn.clicked.connect(lambda checked, d=day: self.browse_file(d))
            grid.addWidget(browse_btn, row, 2)
            
            clear_btn = QPushButton("Clear")
            clear_btn.clicked.connect(lambda checked, d=day: self.clear_file(d))
            grid.addWidget(clear_btn, row, 3)

        close_btn = QPushButton("Done")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def browse_file(self, day):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select Workout for {day}", "", "Markdown Files (*.md *.markdown);;All Files (*)"
        )
        if file_path:
            save_file_for_day(day, file_path)
            _, label = self.file_inputs[day]
            self.file_inputs[day] = (file_path, label)
            label.setText(os.path.basename(file_path))

    def clear_file(self, day):
        save_file_for_day(day, "")
        _, label = self.file_inputs[day]
        self.file_inputs[day] = ("", label)
        label.setText("No file assigned")


# --- MAIN APPLICATION WINDOW ---
class WorkoutViewerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Daily Workout Viewer")
        self.setGeometry(100, 100, 850, 650)

        # Core Timer State Variables
        self.timer_seconds = 0
        self.current_workout_path = ""
        self.stopwatch = QTimer()
        self.stopwatch.timeout.connect(self.update_timer_display)

        # Main Layout Container
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 1. Main Action Toolbar (Horizontal Row)
        top_layout = QHBoxLayout()
        
        # Left Side Container for Workout Management Buttons
        left_btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("📁 Select Markdown File")
        self.select_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.select_btn.setStyleSheet("""
            QPushButton { background-color: #007acc; color: white; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background-color: #005999; }
        """)
        self.select_btn.clicked.connect(self.load_markdown_file)
        left_btn_layout.addWidget(self.select_btn)

        self.schedule_btn = QPushButton("📅 Manage Schedule")
        self.schedule_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.schedule_btn.setStyleSheet("""
            QPushButton { background-color: #28a745; color: white; border-radius: 4px; padding: 6px 12px; margin-left: 5px; }
            QPushButton:hover { background-color: #218838; }
        """)
        self.schedule_btn.clicked.connect(self.open_schedule_manager)
        left_btn_layout.addWidget(self.schedule_btn)

        self.history_btn = QPushButton("🕘 Workout History")
        self.history_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.history_btn.setStyleSheet("""
            QPushButton { background-color: #6f42c1; color: white; border-radius: 4px; padding: 6px 12px; margin-left: 5px; }
            QPushButton:hover { background-color: #553098; }
        """)
        self.history_btn.clicked.connect(self.open_history_view)
        left_btn_layout.addWidget(self.history_btn)
        top_layout.addLayout(left_btn_layout)

        # Push items apart so timer snaps precisely to the right margin side
        top_layout.addStretch()

        # Right Side Container for Stopwatch Dashboard Components
        right_timer_layout = QHBoxLayout()
        
        self.timer_label = QLabel("00:00")
        self.timer_label.setFont(QFont("Courier New", 16, QFont.Weight.Bold))
        self.timer_label.setStyleSheet("color: #333; background-color: #e9ecef; padding: 4px 10px; border-radius: 4px; border: 1px solid #ced4da; margin-right: 8px;")
        right_timer_layout.addWidget(self.timer_label)

        self.start_stop_btn = QPushButton("Start")
        self.start_stop_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.start_stop_btn.setStyleSheet("""
            QPushButton { background-color: #4a4a4a; color: white; border-radius: 4px; padding: 6px 14px; }
            QPushButton:hover { background-color: #333333; }
        """)
        self.start_stop_btn.clicked.connect(self.toggle_timer)
        right_timer_layout.addWidget(self.start_stop_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.reset_btn.setStyleSheet("""
            QPushButton { background-color: #dc3545; color: white; border-radius: 4px; padding: 6px 14px; margin-left: 4px; }
            QPushButton:hover { background-color: #bd2130; }
        """)
        self.reset_btn.clicked.connect(self.reset_timer)
        right_timer_layout.addWidget(self.reset_btn)
        top_layout.addLayout(right_timer_layout)

        main_layout.addLayout(top_layout)

        # 2. Status Label (Repositioned immediately underneath the top command row layout)
        self.file_label = QLabel("No file selected")
        self.file_label.setFont(QFont("Arial", 10, QFont.Weight.Normal))
        self.file_label.setStyleSheet("color: gray; font-style: italic; margin-top: 4px; margin-bottom: 8px; margin-left: 2px;")
        main_layout.addWidget(self.file_label)

        # 3. Rich Text Render Engine Panel Window
        self.display_area = QTextBrowser()
        main_layout.addWidget(self.display_area)

        # Auto-run scheduled loader logic routine
        self.check_and_load_today_workout()

    # --- STOPWATCH ENGINE METHODS ---
    def toggle_timer(self):
        """Starts or pauses the countdown routine cycle and adjusts label layout."""
        if self.stopwatch.isActive():
            self.stopwatch.stop()
            self.prompt_record_workout()
            self.start_stop_btn.setText("Start")
            self.start_stop_btn.setStyleSheet("""
                QPushButton { background-color: #4a4a4a; color: white; border-radius: 4px; padding: 6px 14px; }
                QPushButton:hover { background-color: #333333; }
            """)
        else:
            self.stopwatch.start(1000) # Fires precise system interrupt intervals every 1000ms (1 second)
            self.start_stop_btn.setText("Stop")
            self.start_stop_btn.setStyleSheet("""
                QPushButton { background-color: #e0a800; color: black; border-radius: 4px; padding: 6px 14px; }
                QPushButton:hover { background-color: #d39e00; }
            """)

    def prompt_record_workout(self):
        workout_name = os.path.basename(self.current_workout_path) if self.current_workout_path else "Unknown Workout"
        duration_label = self.timer_label.text()
        dialog = WorkoutRecordDialog(self, workout_name=workout_name, total_seconds=self.timer_seconds)
        response = dialog.exec()

        if response == QDialog.DialogCode.Accepted:
            duration_seconds = dialog.get_duration_seconds()
            save_workout_record(
                workout_name,
                datetime.now().strftime("%Y-%m-%d"),
                duration_seconds,
            )

    def reset_timer(self):
        """Halts the counter execution frame instantly and resets numerical layout digits."""
        self.stopwatch.stop()
        self.timer_seconds = 0
        self.timer_label.setText("00:00")
        self.start_stop_btn.setText("Start")
        self.start_stop_btn.setStyleSheet("""
            QPushButton { background-color: #4a4a4a; color: white; border-radius: 4px; padding: 6px 14px; }
            QPushButton:hover { background-color: #333333; }
        """)

    def update_timer_display(self):
        """Triggered every second by QTimer timeout signals to adjust display fields."""
        self.timer_seconds += 1
        minutes = self.timer_seconds // 60
        seconds = self.timer_seconds % 60
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

    # --- MARKDOWN CONTENT ROUTINES ---
    def check_and_load_today_workout(self):
        today_name = datetime.now().strftime("%A")
        saved_path = get_file_for_day(today_name)

        if saved_path and os.path.exists(saved_path):
            self.current_workout_path = saved_path
            self.render_markdown(saved_path)
            self.file_label.setText(f"Loaded today's scheduled file ({today_name}): {os.path.abspath(saved_path)}")
            self.file_label.setStyleSheet("color: #007acc; font-style: normal; margin-top: 4px; margin-bottom: 8px; margin-left: 2px;")
        else:
            self.current_workout_path = ""
            self.display_area.setMarkdown(
                f"<h1>Welcome</h1><p>No workout file is assigned for <b>{today_name}</b> yet.</p>"
                "<p>Click <b>Manage Schedule</b> above to link your `.md` files to days of the week.</p>"
            )

    def load_markdown_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Markdown File", "", "Markdown Files (*.md *.markdown);;Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.current_workout_path = file_path
            self.render_markdown(file_path)
            self.file_label.setText(os.path.abspath(file_path))
            self.file_label.setStyleSheet("color: green; font-style: normal; margin-top: 4px; margin-bottom: 8px; margin-left: 2px;")

    def render_markdown(self, path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                md_content = file.read()
            self.display_area.setMarkdown(md_content)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read or parse file:\n{str(e)}")

    def open_schedule_manager(self):
        dialog = ScheduleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.check_and_load_today_workout()

    def open_history_view(self):
        dialog = WorkoutHistoryDialog(self)
        dialog.exec()


if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    viewer = WorkoutViewerApp()
    viewer.show()
    sys.exit(app.exec())
