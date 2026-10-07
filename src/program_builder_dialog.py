from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.database import (
    delete_program,
    get_program_by_id,
    get_program_workouts,
    get_programs,
    get_workout_templates,
    save_program,
)


class ProgramWorkoutRuleEditor(QWidget):
    WEEKDAYS = [
        ("Monday", 1),
        ("Tuesday", 2),
        ("Wednesday", 3),
        ("Thursday", 4),
        ("Friday", 5),
        ("Saturday", 6),
        ("Sunday", 7),
    ]

    def __init__(self, workout_templates, remove_callback, rule_number=1):
        super().__init__()
        self.weekday_checks = {}

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        group = QGroupBox(f"Workout {rule_number}")
        group_layout = QVBoxLayout(group)

        header_layout = QHBoxLayout()
        header_layout.addStretch()
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(lambda: remove_callback(self))
        header_layout.addWidget(remove_button)
        group_layout.addLayout(header_layout)

        form = QFormLayout()
        self.workout_combo = QComboBox()
        self.workout_combo.addItem("Select saved workout", -1)
        for workout_id, name, *_ in workout_templates:
            self.workout_combo.addItem(name, workout_id)
        form.addRow("Workout", self.workout_combo)

        self.start_date_input = QDateEdit(QDate.currentDate())
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Starts on", self.start_date_input)

        self.recurrence_combo = QComboBox()
        self.recurrence_combo.addItem("Daily", "daily")
        self.recurrence_combo.addItem("Weekly", "weekly")
        self.recurrence_combo.addItem("Monthly", "monthly")
        self.recurrence_combo.currentIndexChanged.connect(self.update_recurrence_controls)
        form.addRow("Repeats", self.recurrence_combo)

        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 365)
        self.interval_input.setValue(1)
        form.addRow("Every", self.interval_input)
        group_layout.addLayout(form)

        self.weekdays_widget = QWidget()
        weekdays_layout = QHBoxLayout(self.weekdays_widget)
        weekdays_layout.setContentsMargins(0, 0, 0, 0)
        for day_name, day_number in self.WEEKDAYS:
            check = QCheckBox(day_name[:3])
            check.setToolTip(day_name)
            self.weekday_checks[day_number] = check
            weekdays_layout.addWidget(check)
        group_layout.addWidget(QLabel("On weekdays"))
        group_layout.addWidget(self.weekdays_widget)

        month_form = QFormLayout()
        self.month_day_input = QSpinBox()
        self.month_day_input.setRange(1, 31)
        self.month_day_input.setValue(1)
        month_form.addRow("Day of month", self.month_day_input)
        self.month_widget = QWidget()
        self.month_widget.setLayout(month_form)
        group_layout.addWidget(self.month_widget)

        outer_layout.addWidget(group)
        self.update_recurrence_controls()

    def update_recurrence_controls(self, *_):
        recurrence_type = self.recurrence_combo.currentData()
        self.interval_input.setSuffix(
            {"daily": " day(s)", "weekly": " week(s)", "monthly": " month(s)"}[recurrence_type]
        )
        self.weekdays_widget.setVisible(recurrence_type == "weekly")
        self.month_widget.setVisible(recurrence_type == "monthly")

    def load_rule(self, rule):
        _, workout_id, recurrence_type, interval, weekdays, month_day, start_date, _ = rule
        workout_index = self.workout_combo.findData(workout_id)
        if workout_index != -1:
            self.workout_combo.setCurrentIndex(workout_index)
        recurrence_index = self.recurrence_combo.findData(recurrence_type)
        if recurrence_index != -1:
            self.recurrence_combo.setCurrentIndex(recurrence_index)
        self.interval_input.setValue(interval)
        self.month_day_input.setValue(month_day)
        self.start_date_input.setDate(QDate.fromString(start_date, "yyyy-MM-dd"))
        selected_days = {int(day) for day in weekdays.split(",") if day}
        for day_number, check in self.weekday_checks.items():
            check.setChecked(day_number in selected_days)

    def get_rule(self):
        workout_id = self.workout_combo.currentData()
        if workout_id in (None, -1):
            raise ValueError("Choose a saved workout for every program entry.")

        recurrence_type = self.recurrence_combo.currentData()
        selected_days = [
            str(day_number)
            for day_number, check in self.weekday_checks.items()
            if check.isChecked()
        ]
        if recurrence_type == "weekly" and not selected_days:
            raise ValueError("Choose at least one weekday for each weekly workout.")

        return {
            "workout_template_id": workout_id,
            "recurrence_type": recurrence_type,
            "recurrence_interval": self.interval_input.value(),
            "weekdays": ",".join(selected_days),
            "month_day": self.month_day_input.value(),
            "start_date": self.start_date_input.date().toString("yyyy-MM-dd"),
        }


class ProgramBuilderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Program Builder")
        self.resize(760, 720)
        self.program_id = None
        self.rule_editors = []
        self.workout_templates = get_workout_templates()

        layout = QVBoxLayout(self)
        program_form = QFormLayout()
        self.program_selector = QComboBox()
        self.program_selector.addItem("Create New Program", None)
        for program_id, name in get_programs():
            self.program_selector.addItem(name, program_id)
        self.program_selector.currentIndexChanged.connect(self.load_selected_program)
        program_form.addRow("Saved Program", self.program_selector)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Strength and Mobility")
        program_form.addRow("Program Name", self.name_input)
        layout.addLayout(program_form)

        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Workout Schedule"))
        title_layout.addStretch()
        self.delete_button = QPushButton("Delete Program")
        self.delete_button.clicked.connect(self.delete_selected_program)
        title_layout.addWidget(self.delete_button)
        layout.addLayout(title_layout)

        self.rules_scroll = QScrollArea()
        self.rules_scroll.setWidgetResizable(True)
        self.rules_widget = QWidget()
        self.rules_layout = QVBoxLayout(self.rules_widget)
        self.rules_layout.setContentsMargins(0, 0, 0, 0)
        self.rules_scroll.setWidget(self.rules_widget)
        layout.addWidget(self.rules_scroll, 1)

        add_rule_button = QPushButton("Add Workout")
        add_rule_button.clicked.connect(self.add_rule_editor)
        layout.addWidget(add_rule_button)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close
        )
        button_box.accepted.connect(self.save_current_program)
        button_box.rejected.connect(self.accept)
        layout.addWidget(button_box)

        self.reset_program_form()

    def clear_rule_editors(self):
        for editor in self.rule_editors:
            self.rules_layout.removeWidget(editor)
            editor.deleteLater()
        self.rule_editors = []

    def reset_program_form(self):
        self.program_id = None
        self.name_input.clear()
        self.clear_rule_editors()
        self.add_rule_editor()
        self.delete_button.setEnabled(False)

    def add_rule_editor(self, rule=None):
        editor = ProgramWorkoutRuleEditor(
            self.workout_templates,
            self.remove_rule_editor,
            rule_number=len(self.rule_editors) + 1,
        )
        if rule:
            editor.load_rule(rule)
        self.rule_editors.append(editor)
        self.rules_layout.addWidget(editor)

    def remove_rule_editor(self, editor):
        if len(self.rule_editors) == 1:
            QMessageBox.information(
                self, "Program needs a workout", "Keep at least one workout entry."
            )
            return
        self.rule_editors.remove(editor)
        self.rules_layout.removeWidget(editor)
        editor.deleteLater()

    def load_selected_program(self, index):
        program_id = self.program_selector.itemData(index)
        if program_id is None:
            self.reset_program_form()
            return

        program = get_program_by_id(program_id)
        if not program:
            return
        self.program_id, name = program
        self.name_input.setText(name)
        self.delete_button.setEnabled(True)
        self.clear_rule_editors()
        for rule in get_program_workouts(program_id):
            self.add_rule_editor(rule)
        if not self.rule_editors:
            self.add_rule_editor()

    def save_current_program(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing program name", "Enter a name for this program.")
            return

        try:
            rules = [editor.get_rule() for editor in self.rule_editors]
        except ValueError as error:
            QMessageBox.warning(self, "Incomplete workout schedule", str(error))
            return

        self.program_id = save_program(self.program_id, name, rules)
        self.refresh_program_selector()
        QMessageBox.information(self, "Program Saved", f"{name} was saved.")

    def refresh_program_selector(self):
        self.program_selector.blockSignals(True)
        self.program_selector.clear()
        self.program_selector.addItem("Create New Program", None)
        for program_id, name in get_programs():
            self.program_selector.addItem(name, program_id)
        selected_index = self.program_selector.findData(self.program_id)
        self.program_selector.setCurrentIndex(max(selected_index, 0))
        self.program_selector.blockSignals(False)
        self.delete_button.setEnabled(self.program_id is not None)

    def delete_selected_program(self):
        if self.program_id is None:
            return
        response = QMessageBox.question(
            self,
            "Delete Program",
            "Delete this program and all of its workout schedule entries?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        delete_program(self.program_id)
        self.program_selector.blockSignals(True)
        self.program_selector.removeItem(self.program_selector.findData(self.program_id))
        self.program_selector.blockSignals(False)
        self.program_selector.setCurrentIndex(0)
