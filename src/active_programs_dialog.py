from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.database import get_programs_with_activation, set_active_program_ids


class ActiveProgramsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Active Programs")
        self.resize(480, 520)
        self.program_checks = {}

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose which saved programs are active."))

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.programs_widget = QWidget()
        self.programs_layout = QVBoxLayout(self.programs_widget)
        self.programs_layout.setContentsMargins(0, 0, 0, 0)

        programs = get_programs_with_activation()
        for program_id, name, is_active in programs:
            check = QCheckBox(name)
            check.setChecked(bool(is_active))
            self.program_checks[program_id] = check
            self.programs_layout.addWidget(check)

        if not programs:
            self.programs_layout.addWidget(QLabel("No saved programs yet."))
        self.programs_layout.addStretch()
        self.scroll_area.setWidget(self.programs_widget)
        layout.addWidget(self.scroll_area, 1)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_active_programs)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def save_active_programs(self):
        active_program_ids = [
            program_id for program_id, check in self.program_checks.items() if check.isChecked()
        ]
        set_active_program_ids(active_program_ids)
        self.accept()
