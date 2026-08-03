import sys
import os
import sqlite3
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QTextBrowser, 
    QFileDialog, QMessageBox, QDialog, QGridLayout
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer

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
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in days:
        cursor.execute("INSERT OR IGNORE INTO schedule (day_name, file_path) VALUES (?, ?)", (day, ""))
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
            self.render_markdown(saved_path)
            self.file_label.setText(f"Loaded today's scheduled file ({today_name}): {os.path.abspath(saved_path)}")
            self.file_label.setStyleSheet("color: #007acc; font-style: normal; margin-top: 4px; margin-bottom: 8px; margin-left: 2px;")
        else:
            self.display_area.setMarkdown(
                f"<h1>Welcome</h1><p>No workout file is assigned for <b>{today_name}</b> yet.</p>"
                "<p>Click <b>Manage Schedule</b> above to link your `.md` files to days of the week.</p>"
            )

    def load_markdown_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Markdown File", "", "Markdown Files (*.md *.markdown);;Text Files (*.txt);;All Files (*)"
        )
        if file_path:
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


if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    viewer = WorkoutViewerApp()
    viewer.show()
    sys.exit(app.exec())
