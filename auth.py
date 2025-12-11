from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from api_client import api


class AuthWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Welcome")
        self.resize(300, 250)
        self.layout = QVBoxLayout(self)

        self.stack = QWidget()
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