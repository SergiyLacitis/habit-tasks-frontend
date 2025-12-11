from PySide6.QtWidgets import QMainWindow, QTabWidget

from api_client import api
from constants import WINDOW_HEIGHT, WINDOW_WIDTH
from tabs import AdminTab, HabitsTab, ProfileTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("HabitTasks")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

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