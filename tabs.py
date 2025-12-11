from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from api_client import api
from components import HabitCard
from constants import COLOR_ACCENT, COLOR_BG_CARD
from dialogs import CreateHabitDialog, HabitDetailWindow


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
        self.info_frame.setFixedWidth(500)

        fl = QFormLayout(self.info_frame)
        self.lbl_user = QLabel("Loading...")
        self.lbl_email = QLabel("Loading...")
        self.lbl_role = QLabel("Loading...")

        fl.addRow("Username:", self.lbl_user)
        fl.addRow("Email:", self.lbl_email)
        fl.addRow("Role:", self.lbl_role)

        self.layout.addWidget(self.info_frame)

        logout_btn = QPushButton("Logout")
        logout_btn.setFixedWidth(500)
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