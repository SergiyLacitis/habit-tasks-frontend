from PySide6.QtCore import QRunnable, QThreadPool, Signal, Slot, QObject
# ... (імпорт інших PySide6 класів та api_client)

class WorkerSignals(QObject):
    # Сигнали Worker-а
    result = Signal(object)
    error = Signal(str)

class Worker(QRunnable):
    # ... (реалізація Worker)

class MainView(QWidget):
    def __init__(self, api_client):
        # ... (ініціалізація GUI)
        self.api_client = api_client
        self.thread_pool = QThreadPool()
        self.load_tasks_for_today()

    @Slot()
    def load_tasks_for_today(self):
        self.load_button.setEnabled(False) # Блокуємо кнопку
        
        # Передаємо метод fetch_tasks() у Worker
        worker = Worker(self.api_client.fetch_tasks) 
        
        worker.signals.result.connect(self.on_tasks_loaded)
        worker.signals.error.connect(self.handle_api_error)
        
        self.thread_pool.start(worker)

    @Slot(object)
    def on_tasks_loaded(self, tasks_list):
        # Оновлення інтерфейсу відбувається тут, у головному потоці
        self.load_button.setEnabled(True)
        # ... (логіка оновлення QListWidget)
        
    @Slot(str)
    def handle_api_error(self, message):
        # ... (обробка помилок)
        self.load_button.setEnabled(True)
