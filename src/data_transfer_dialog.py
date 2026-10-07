import sqlite3

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.data_transfer import export_bundle, import_bundle


class DataTransferDialog(QDialog):
    CATEGORY_LABELS = {
        "exercises": "Exercises",
        "workouts": "Workouts",
        "programs": "Programs",
        "history": "Workout History",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import / Export Data")
        self.resize(540, 440)
        self.imported = False
        self._updating_categories = False
        self.category_checks = {}

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_export_tab(), "Export")
        self.tabs.addTab(self.create_import_tab(), "Import")
        layout.addWidget(self.tabs)

        close_button = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button.rejected.connect(self.reject)
        layout.addWidget(close_button)

    def create_export_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Choose which data to include in the export bundle."))

        self.category_checks["all"] = QCheckBox("All data")
        self.category_checks["all"].toggled.connect(
            lambda checked: self.update_categories("all", checked)
        )
        layout.addWidget(self.category_checks["all"])

        for category, label in self.CATEGORY_LABELS.items():
            check = QCheckBox(label)
            check.toggled.connect(
                lambda checked, selected=category: self.update_categories(selected, checked)
            )
            self.category_checks[category] = check
            layout.addWidget(check)

        layout.addWidget(
            QLabel("Workouts include exercises. Programs include workouts and exercises.")
        )
        layout.addStretch()

        export_button = QPushButton("Export Bundle")
        export_button.clicked.connect(self.choose_export_destination)
        layout.addWidget(export_button)
        return page

    def create_import_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Choose a Daily Workout export bundle to import."))

        file_layout = QHBoxLayout()
        self.import_path_input = QLineEdit()
        self.import_path_input.setReadOnly(True)
        self.import_path_input.setPlaceholderText("No file selected")
        file_layout.addWidget(self.import_path_input, 1)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.choose_import_file)
        file_layout.addWidget(browse_button)
        layout.addLayout(file_layout)

        layout.addStretch()
        self.import_button = QPushButton("Import Bundle")
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.import_selected_file)
        layout.addWidget(self.import_button)
        return page

    def update_categories(self, category, checked):
        if self._updating_categories:
            return

        self._updating_categories = True
        try:
            if category == "all":
                for name, check in self.category_checks.items():
                    if name != "all":
                        check.setChecked(checked)
            elif checked and category == "programs":
                self.category_checks["workouts"].setChecked(True)
                self.category_checks["exercises"].setChecked(True)
            elif checked and category == "workouts":
                self.category_checks["exercises"].setChecked(True)
            elif not checked and category == "exercises":
                self.category_checks["workouts"].setChecked(False)
                self.category_checks["programs"].setChecked(False)
            elif not checked and category == "workouts":
                self.category_checks["programs"].setChecked(False)

            everything_selected = all(
                check.isChecked() for name, check in self.category_checks.items() if name != "all"
            )
            self.category_checks["all"].setChecked(everything_selected)
        finally:
            self._updating_categories = False

    def choose_export_destination(self):
        categories = [
            name
            for name, check in self.category_checks.items()
            if name != "all" and check.isChecked()
        ]
        if not categories:
            QMessageBox.warning(self, "Choose data", "Select at least one type of data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Workout Data",
            "daily_workout_export.dwb",
            "Daily Workout Bundle (*.dwb)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".dwb"):
            file_path += ".dwb"

        try:
            counts = export_bundle(file_path, categories)
        except (OSError, sqlite3.Error, ValueError) as error:
            QMessageBox.critical(self, "Export Failed", str(error))
            return

        summary = "\n".join(
            f"{self.CATEGORY_LABELS[category]}: {count}" for category, count in counts.items()
        )
        QMessageBox.information(self, "Export Complete", f"Bundle created.\n\n{summary}")

    def choose_import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Workout Data",
            "",
            "Daily Workout Bundle (*.dwb *.zip);;All Files (*)",
        )
        if not file_path:
            return
        self.import_path_input.setText(file_path)
        self.import_button.setEnabled(True)

    def import_selected_file(self):
        file_path = self.import_path_input.text()
        if not file_path:
            return
        try:
            result = import_bundle(file_path)
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as error:
            QMessageBox.critical(self, "Import Failed", str(error))
            return

        if result.get("already_imported"):
            QMessageBox.information(
                self,
                "Already Imported",
                "This exact bundle has already been imported.",
            )
            return

        self.imported = True
        summary = "\n".join(
            f"{self.CATEGORY_LABELS[category]}: {count}" for category, count in result.items()
        )
        QMessageBox.information(self, "Import Complete", f"Data imported.\n\n{summary}")
