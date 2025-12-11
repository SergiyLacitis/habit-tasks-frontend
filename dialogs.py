from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from api_client import api
from components import YearHeatmap
from constants import (
    COLOR_ACCENT,
    COLOR_BG_CARD,
    COLOR_TEXT_DIM,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)


class HabitDetailWindow(QDialog):
    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.logs = []
        self.setWindowTitle(f"Habit Details: {task_data['title']}")

        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        header_group = QFrame()
        header_group.setStyleSheet(
            f"background-color: {COLOR_BG_CARD}; border-radius: 10px;"
        )
        header_layout = QGridLayout(header_group)

        self.title_edit = QLineEdit(task_data["title"])
        self.title_edit.setStyleSheet(
            "font-size: 18px; font-weight: bold; border: none; background: transparent; color: white;"
        )

        self.desc_edit = QLineEdit(task_data.get("description") or "")
        self.desc_edit.setPlaceholderText("Description (optional)")

        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet(f"background-color: {COLOR_ACCENT}; font-weight: bold;")
        save_btn.clicked.connect(self.save_changes)

        delete_btn = QPushButton("Delete Habit")
        delete_btn.setStyleSheet("background-color: #d32f2f; color: white;")
        delete_btn.clicked.connect(self.delete_habit)

        header_layout.addWidget(QLabel("Title:"), 0, 0)
        header_layout.addWidget(self.title_edit, 0, 1)
        header_layout.addWidget(QLabel("Description:"), 1, 0)
        header_layout.addWidget(self.desc_edit, 1, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(save_btn)
        header_layout.addLayout(btn_layout, 2, 1)

        main_layout.addWidget(header_group)

        stats_group = QFrame()
        stats_layout = QHBoxLayout(stats_group)

        self.lbl_streak = self.create_stat_label("Current Streak", "0")
        self.lbl_total = self.create_stat_label("Total Completions", "0")
        self.lbl_rate = self.create_stat_label("Win Rate (Year)", "0%")

        stats_layout.addWidget(self.lbl_streak)
        stats_layout.addWidget(self.lbl_total)
        stats_layout.addWidget(self.lbl_rate)

        main_layout.addWidget(stats_group)

        main_layout.addWidget(QLabel("Yearly Progress (Click cell to change):"))

        self.map_scroll = QScrollArea()
        self.map_scroll.setFixedHeight(180)
        self.map_scroll.setWidgetResizable(True)
        self.map_scroll.setStyleSheet("background: transparent; border: none;")

        self.map_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.map_container = QWidget()
        self.map_layout = QHBoxLayout(self.map_container)
        self.map_layout.setAlignment(Qt.AlignCenter)  # Центруємо календар

        self.map_scroll.setWidget(self.map_container)
        main_layout.addWidget(self.map_scroll)

        self.heatmap = None

        self.refresh_data()

    def create_stat_label(self, title, value):
        container = QFrame()
        container.setStyleSheet(
            f"background-color: {COLOR_BG_CARD}; border-radius: 8px; padding: 10px;"
        )
        l = QVBoxLayout(container)
        t = QLabel(title)
        t.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 12px;")
        v = QLabel(value)
        v.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 20px; font-weight: bold;")
        v.setAlignment(Qt.AlignCenter)
        l.addWidget(t)
        l.addWidget(v)
        return container

    def refresh_data(self):
        year_ago = date.today() - timedelta(days=364)
        self.logs = api.get_task_logs(self.task_data["id"], date_from=year_ago)

        self.calculate_stats()
        self.draw_heatmap()

    def calculate_stats(self):
        dates = {l["date"].split("T")[0] for l in self.logs}
        total = len(dates)

        streak = 0
        check = date.today()
        if check.isoformat() not in dates:
            check -= timedelta(days=1)

        while check.isoformat() in dates:
            streak += 1
            check -= timedelta(days=1)

        rate = int((total / 364) * 100) if total > 0 else 0

        self.lbl_streak.findChild(QLabel, "").nextInFocusChain().setText(str(streak))
        self.lbl_total.findChild(QLabel, "").nextInFocusChain().setText(str(total))
        self.lbl_rate.findChild(QLabel, "").nextInFocusChain().setText(f"{rate}%")

    def draw_heatmap(self):
        if self.heatmap:
            self.heatmap.deleteLater()

        self.heatmap = YearHeatmap(self.logs, interactive=True)
        self.heatmap.dateClicked.connect(self.toggle_log)
        self.map_layout.addWidget(self.heatmap)

    def toggle_log(self, clicked_date: date):
        date_str = clicked_date.isoformat()
        current_logs = {l["date"].split("T")[0] for l in self.logs}
        new_status = date_str not in current_logs

        if api.set_log_status(self.task_data["id"], clicked_date, new_status):
            self.refresh_data()
        else:
            QMessageBox.warning(self, "Error", "Connection error")

    def save_changes(self):
        if api.update_task(
                self.task_data["id"],
                self.title_edit.text(),
                self.desc_edit.text(),
        ):
            QMessageBox.information(self, "Saved", "Task updated.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to update.")

    def delete_habit(self):
        confirm = QMessageBox.question(
            self, "Confirm", "Are you sure you want to delete this habit?"
        )
        if confirm == QMessageBox.Yes:
            if api.delete_task(self.task_data["id"]):
                self.accept()


class CreateHabitDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Habit")

        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        main_layout = QVBoxLayout(self)

        form_frame = QFrame()
        form_layout = QFormLayout(form_frame)

        self.ti = QLineEdit()
        self.de = QLineEdit()

        btn = QPushButton("Create")
        btn.setFixedWidth(200)
        btn.setStyleSheet(f"background-color: {COLOR_ACCENT}; font-weight: bold; padding: 10px;")
        btn.clicked.connect(self.save)

        form_layout.addRow("Title", self.ti)
        form_layout.addRow("Description", self.de)
        form_layout.addRow("", btn)

        main_layout.addStretch()
        main_layout.addWidget(form_frame)
        main_layout.addStretch()

    def save(self):
        if not self.ti.text():
            return
        if api.create_task(self.ti.text(), self.de.text()):
            self.accept()