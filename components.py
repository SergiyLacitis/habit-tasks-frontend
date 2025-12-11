from datetime import date, timedelta
from typing import Set

from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from api_client import api
from constants import COLOR_ACCENT, COLOR_BG_CARD, COLOR_BG_EMPTY, COLOR_TEXT_DIM


class YearHeatmap(QWidget):
    dateClicked = Signal(date)

    def __init__(self, logs, interactive=False, parent=None):
        super().__init__(parent)
        self.completed_dates: Set[str] = {log["date"].split("T")[0] for log in logs}
        self.interactive = interactive

        # 7 рядків для днів тижня
        self.rows = 7
        self.total_days = 364
        self.cell_size = 16
        self.spacing = 4

        # Висота заголовка для місяців
        self.header_height = 24

        # Розрахунок кількості колонок
        self.cols = (self.total_days // self.rows)
        if self.total_days % self.rows != 0:
            self.cols += 1

        width = self.cols * (self.cell_size + self.spacing)
        # Загальна висота = сітка + заголовок
        height = self.rows * (self.cell_size + self.spacing) + self.header_height

        self.setFixedSize(width + 10, height + 10)

        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=self.total_days - 1)

        if self.interactive:
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip("Click on a cell to toggle status")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Налаштування шрифту для місяців
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)

        current_date = self.start_date
        last_month = -1

        for col in range(self.cols):
            # --- Малювання міток місяців ---
            # Визначаємо дату першого дня в поточній колонці (верхня комірка)
            col_first_date = self.start_date + timedelta(days=col * 7)

            # Якщо місяць змінився порівняно з попередньою колонкою, малюємо назву
            if col_first_date.month != last_month:
                month_name = col_first_date.strftime("%b")  # Скорочена назва (Jan, Feb...)
                x = col * (self.cell_size + self.spacing)

                painter.setPen(QColor(COLOR_TEXT_DIM))
                # Малюємо текст у просторі header_height
                painter.drawText(
                    QRect(x, 0, 40, self.header_height),
                    Qt.AlignLeft | Qt.AlignBottom,
                    month_name
                )
                last_month = col_first_date.month

            # --- Малювання комірок ---
            for row in range(self.rows):
                if current_date > self.end_date:
                    break

                x = col * (self.cell_size + self.spacing)
                # Зміщуємо сітку вниз на висоту заголовка
                y = row * (self.cell_size + self.spacing) + self.header_height

                date_str = current_date.isoformat()
                is_completed = date_str in self.completed_dates

                if is_completed:
                    bg_color = QColor(COLOR_ACCENT)
                else:
                    bg_color = QColor(COLOR_BG_EMPTY)

                painter.setBrush(QBrush(bg_color))

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
        # Коригуємо Y, віднімаючи висоту заголовка
        y = event.pos().y() - self.header_height

        # Якщо клік був по заголовку (y < 0), ігноруємо
        if y < 0:
            return

        col = x // (self.cell_size + self.spacing)
        row = y // (self.cell_size + self.spacing)

        if 0 <= row < self.rows and 0 <= col < self.cols:
            days_offset = col * self.rows + row
            clicked_date = self.start_date + timedelta(days=days_offset)

            if clicked_date <= date.today():
                self.dateClicked.emit(clicked_date)


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

        text_layout.addWidget(title)

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

        self.preview_layout = QHBoxLayout()
        self.load_mini_preview()
        layout.addLayout(self.preview_layout)

    def mouseReleaseEvent(self, event):
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