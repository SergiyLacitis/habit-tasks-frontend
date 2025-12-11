import sys

from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

from auth import AuthWindow
from main_window import MainWindow

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