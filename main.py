import sys
from datetime import date, timedelta
from typing import Set

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

from api_client import api

COLOR_ACCENT = "#26a69a"
COLOR_BG_EMPTY = "#37474f"
COLOR_BG_CARD = "#263238"
COLOR_TEXT_DIM = "#b0bec5"


class YearHeatmap(QWidget):
    dateClicked = Signal(date)

    def __init__(self, logs, interactive=False, parent=None):
        super().__init__(parent)
        self.completed_dates: Set[str] = {log["date"].split("T")[0] for log in logs}
        self.interactive = interactive

        self.rows = 5
        self.total_days = 365
        self.cell_size = 16
        self.spacing = 4

        self.cols = (self.total_days // self.rows) + 1
        width = self.cols * (self.cell_size + self.spacing)
        height = self.rows * (self.cell_size + self.spacing)
        self.setFixedSize(width + 10, height + 10)

        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=self.total_days - 1)

        if self.interactive:
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip("Click on a cell to toggle status")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        current_date = self.start_date

        for col in range(self.cols):
            for row in range(self.rows):
                if current_date > self.end_date:
                    break

                x = col * (self.cell_size + self.spacing)
                y = row * (self.cell_size + self.spacing)

                date_str = current_date.isoformat()
                is_completed = date_str in self.completed_dates

                if is_completed:
                    bg_color = QColor(COLOR_ACCENT)
                else:
                    bg_color = QColor(COLOR_BG_EMPTY)

                path = QBrush(bg_color)
                painter.setBrush(path)

                if current_date == date.today():
                    painter.setPen(QPen(QColor("white"), 2))
                else:
                    painter.setPen(Qt.NoPen)

                painter.drawRoundedRect(x, y, self.cell_size, self.cell_size, 3, 3)

                current_date += timedelta(days=1)

    def mousePressEvent(self, event):
        if not self.interactive:
            return

        x = event.pos().x()
        y = event.pos().y()

        col = x // (self.cell_size + self.spacing)
        row = y // (self.cell_size + self.spacing)

        if 0 <= row < self.rows and 0 <= col < self.cols:
            days_offset = col * self.rows + row
            clicked_date = self.start_date + timedelta(days=days_offset)

            if clicked_date <= date.today():
                self.dateClicked.emit(clicked_date)


class HabitDetailWindow(QDialog):
    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.logs = []
        self.setWindowTitle(f"Habit Details: {task_data['title']}")
        self.resize(800, 600)

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

        self.freq_edit = QLineEdit(task_data.get("frequency") or "")
        self.freq_edit.setPlaceholderText("Frequency (e.g. Daily)")

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
        header_layout.addWidget(QLabel("Frequency:"), 2, 0)
        header_layout.addWidget(self.freq_edit, 2, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(save_btn)
        header_layout.addLayout(btn_layout, 3, 1)

        main_layout.addWidget(header_group)

        # 2. Статистика
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
        self.map_scroll.setFixedHeight(140)
        self.map_scroll.setWidgetResizable(True)
        self.map_scroll.setStyleSheet("background: transparent; border: none;")

        self.map_container = QWidget()
        self.map_layout = QHBoxLayout(self.map_container)
        self.map_layout.setAlignment(Qt.AlignLeft)

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
        year_ago = date.today() - timedelta(days=365)
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

        rate = int((total / 365) * 100)

        self.lbl_streak.findChild(QLabel, "").nextInFocusChain().setText(str(streak))
        self.lbl_total.findChild(QLabel, "").nextInFocusChain().setText(str(total))
        self.lbl_rate.findChild(QLabel, "").nextInFocusChain().setText(f"{rate}%")

    def draw_heatmap(self):
        if self.heatmap:
            self.heatmap.deleteLater()

        self.heatmap = YearHeatmap(self.logs, interactive=True)
        self.heatmap.dateClicked.connect(self.toggle_log)
        self.map_layout.addWidget(self.heatmap)

        self.map_scroll.horizontalScrollBar().setValue(
            self.map_scroll.horizontalScrollBar().maximum()
        )

    def toggle_log(self, clicked_date: date):
        date_str = clicked_date.isoformat()
        current_logs = {l["date"].split("T")[0] for l in self.logs}

        # Інверсія статусу
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
            self.freq_edit.text(),
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


class HabitCard(QFrame):
    needsRefresh = Signal()
    cardClicked = Signal(dict)

    def __init__(self, task_data):
        super().__init__()
        self.task_data = task_data
        self.setStyleSheet(f"""
            HabitCard {{
                background-color: {COLOR_BG_CARD};
                border-radius: 12px;
                border: 1px solid transparent;
            }}
            HabitCard:hover {{
                border: 1px solid {COLOR_ACCENT};
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)

        header = QHBoxLayout()

        text_layout = QVBoxLayout()
        title = QLabel(task_data["title"])
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        freq = QLabel(task_data.get("frequency") or "General")
        freq.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_DIM};")

        text_layout.addWidget(title)
        text_layout.addWidget(freq)

        self.btn_check = QPushButton()
        self.btn_check.setFixedSize(40, 40)
        self.btn_check.setCheckable(True)
        self.btn_check.setChecked(task_data["is_completed"])
        self.btn_check.clicked.connect(self.on_check_click)
        self.update_btn_style()

        header.addLayout(text_layout)
        header.addStretch()
        header.addWidget(self.btn_check)

        layout.addLayout(header)

        # Міні Heatmap (Preview)
        self.preview_layout = QHBoxLayout()
        self.load_mini_preview()
        layout.addLayout(self.preview_layout)

    def mouseReleaseEvent(self, event):
        # Якщо клік не по кнопці - відкриваємо деталі
        if not self.btn_check.underMouse():
            self.cardClicked.emit(self.task_data)
        super().mouseReleaseEvent(event)

    def load_mini_preview(self):
        pass

    def on_check_click(self):
        success = api.toggle_today(self.task_data["id"], self.task_data["is_completed"])
        if success:
            self.task_data["is_completed"] = not self.task_data["is_completed"]
            self.update_btn_style()
        else:
            # Revert UI if fail
            self.btn_check.setChecked(self.task_data["is_completed"])

    def update_btn_style(self):
        checked = self.btn_check.isChecked()
        color = COLOR_ACCENT if checked else "transparent"
        border = "none" if checked else f"2px solid {COLOR_TEXT_DIM}"
        text = "✔" if checked else ""

        self.btn_check.setText(text)
        self.btn_check.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: {border};
                border-radius: 20px;
                color: white;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {COLOR_ACCENT};
            }}
        """)


class HabitsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.clicked.connect(self.load_tasks)

        add_btn = QPushButton("+ New Habit")
        add_btn.setStyleSheet(
            f"background-color: {COLOR_ACCENT}; font-weight: bold; padding: 5px 15px;"
        )
        add_btn.clicked.connect(self.add_task)

        top_bar.addWidget(QLabel("My Habits"))
        top_bar.addStretch()
        top_bar.addWidget(refresh_btn)
        top_bar.addWidget(add_btn)
        layout.addLayout(top_bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.container = QWidget()
        self.tasks_layout = QVBoxLayout(self.container)
        self.tasks_layout.setAlignment(Qt.AlignTop)
        self.tasks_layout.setSpacing(10)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def load_tasks(self):
        # Чистимо старі
        while self.tasks_layout.count():
            w = self.tasks_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        tasks = api.get_tasks()
        for t in tasks:
            card = HabitCard(t)
            card.cardClicked.connect(self.open_details)
            self.tasks_layout.addWidget(card)

    def open_details(self, task_data):
        dlg = HabitDetailWindow(task_data, self)
        if dlg.exec():
            self.load_tasks()

    def add_task(self):
        dlg = CreateHabitDialog(self)
        if dlg.exec():
            self.load_tasks()


class ProfileTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)

        self.info_frame = QFrame()
        self.info_frame.setStyleSheet(
            f"background-color: {COLOR_BG_CARD}; border-radius: 15px; padding: 20px;"
        )
        self.info_frame.setFixedWidth(300)

        fl = QFormLayout(self.info_frame)
        self.lbl_user = QLabel("Loading...")
        self.lbl_email = QLabel("Loading...")
        self.lbl_role = QLabel("Loading...")

        fl.addRow("Username:", self.lbl_user)
        fl.addRow("Email:", self.lbl_email)
        fl.addRow("Role:", self.lbl_role)

        self.layout.addWidget(self.info_frame)

        logout_btn = QPushButton("Logout")
        logout_btn.setFixedWidth(300)
        logout_btn.setStyleSheet("background-color: #d32f2f; margin-top: 20px;")
        logout_btn.clicked.connect(self.logout)
        self.layout.addWidget(logout_btn)

    def refresh(self):
        data = api.get_me()
        if data:
            self.lbl_user.setText(data.get("username", "-"))
            self.lbl_email.setText(data.get("email", "-"))
            self.lbl_role.setText(data.get("role", "user").upper())

    def logout(self):
        QApplication.quit()


class AdminTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        btn_refresh = QPushButton("Refresh Users")
        btn_refresh.clicked.connect(self.load_users)
        layout.addWidget(btn_refresh)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Role"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

    def load_users(self):
        users = api.get_all_users()
        self.table.setRowCount(len(users))
        for i, u in enumerate(users):
            self.table.setItem(i, 0, QTableWidgetItem(str(u["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(u["username"]))
            self.table.setItem(i, 2, QTableWidgetItem(u["role"]))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Habit Tracker Pro")
        self.resize(600, 800)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tab_habits = HabitsTab()
        self.tab_profile = ProfileTab()

        self.tabs.addTab(self.tab_habits, "Habits")
        self.tabs.addTab(self.tab_profile, "Profile")

        if api.user_role == "admin":
            self.tab_admin = AdminTab()
            self.tabs.addTab(self.tab_admin, "Admin Panel")

        self.tabs.currentChanged.connect(self.on_tab_change)

        self.tab_habits.load_tasks()

    def on_tab_change(self, index):
        widget = self.tabs.widget(index)
        if isinstance(widget, ProfileTab):
            widget.refresh()
        elif isinstance(widget, AdminTab):
            widget.load_users()


class CreateHabitDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Habit")
        self.resize(300, 200)
        l = QFormLayout(self)
        self.ti = QLineEdit()
        self.de = QLineEdit()
        self.fr = QLineEdit()
        btn = QPushButton("Create")
        btn.clicked.connect(self.save)
        l.addRow("Title", self.ti)
        l.addRow("Description", self.de)
        l.addRow("Frequency", self.fr)
        l.addRow(btn)

    def save(self):
        if not self.ti.text():
            return
        if api.create_task(self.ti.text(), self.de.text(), self.fr.text()):
            self.accept()


class AuthWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Welcome")
        self.resize(300, 250)
        self.layout = QVBoxLayout(self)

        self.stack = QWidget()  # Placeholder for current form
        self.layout.addWidget(self.stack)

        self.show_login()

    def show_login(self):
        self.clear_layout()
        w = QWidget()
        l = QFormLayout(w)
        l.addRow(QLabel("<h2>Login</h2>"))
        u = QLineEdit()
        p = QLineEdit()
        p.setEchoMode(QLineEdit.Password)
        l.addRow("Username", u)
        l.addRow("Password", p)

        btn_login = QPushButton("Login")
        btn_login.clicked.connect(lambda: self.do_login(u.text(), p.text()))

        btn_reg = QPushButton("Create Account")
        btn_reg.setFlat(True)
        btn_reg.clicked.connect(self.show_register)

        l.addRow(btn_login)
        l.addRow(btn_reg)
        self.layout.addWidget(w)

    def show_register(self):
        self.clear_layout()
        w = QWidget()
        l = QFormLayout(w)
        l.addRow(QLabel("<h2>Register</h2>"))
        u = QLineEdit()
        e = QLineEdit()
        p = QLineEdit()
        p.setEchoMode(QLineEdit.Password)
        l.addRow("Username", u)
        l.addRow("Email", e)
        l.addRow("Password", p)

        btn_reg = QPushButton("Register")
        btn_reg.clicked.connect(lambda: self.do_register(u.text(), e.text(), p.text()))

        btn_back = QPushButton("Back to Login")
        btn_back.setFlat(True)
        btn_back.clicked.connect(self.show_login)

        l.addRow(btn_reg)
        l.addRow(btn_back)
        self.layout.addWidget(w)

    def clear_layout(self):
        if self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def do_login(self, u, p):
        if api.login(u, p):
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials")

    def do_register(self, u, e, p):
        if api.register(u, e, p):
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Registration failed")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    apply_stylesheet(app, theme="dark_teal.xml")

    app.setStyleSheet(
        app.styleSheet()
        + """
        QLineEdit { padding: 5px; }
        QPushButton { padding: 8px; border-radius: 4px; }
    """
    )

    auth = AuthWindow()
    if auth.exec():
        w = MainWindow()
        w.show()
        sys.exit(app.exec())
