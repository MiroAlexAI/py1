from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableView, 
                             QPushButton, QHeaderView, QMessageBox, QLabel, QDoubleSpinBox, QItemDelegate, QComboBox)
from PyQt6.QtSql import QSqlDatabase, QSqlTableModel
from PyQt6.QtCore import Qt
from notes_manager import NotesManager
import os
import db

class ModelsManager(QDialog):
    def __init__(self, db_path="chatlist.db", parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle("Manage AI Models")
        self.resize(800, 500)
        
        self.init_db()
        self.init_ui()

    def init_db(self):
        # Проверяем, есть ли уже соединение
        if not QSqlDatabase.contains("qt_sql_default_connection"):
            self.db = QSqlDatabase.addDatabase("QSQLITE")
            self.db.setDatabaseName(self.db_path)
            if not self.db.open():
                QMessageBox.critical(self, "DB Error", "Could not open database via QtSql")
        else:
            self.db = QSqlDatabase.database("qt_sql_default_connection")

        self.model = QSqlTableModel(self, self.db)
        self.model.setTable("models")
        self.model.setEditStrategy(QSqlTableModel.EditStrategy.OnFieldChange)
        
        # Заголовки
        self.model.setHeaderData(0, Qt.Orientation.Horizontal, "Model Name / ID")
        self.model.setHeaderData(1, Qt.Orientation.Horizontal, "API URL")
        self.model.setHeaderData(2, Qt.Orientation.Horizontal, "Env Key Name")
        self.model.setHeaderData(3, Qt.Orientation.Horizontal, "Active (1/0)")
        
        self.model.select()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Секция глобальных настроек
        settings_layout = QHBoxLayout()
        delay_label = QLabel("Parallel Request Delay (sec):")
        delay_label.setToolTip("Stagger concurrent requests to avoid 429 Too Many Requests errors.")
        
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 10.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setDecimals(1)
        
        # Загружаем текущее значение
        current_delay = float(db.get_setting("request_delay", 0.0))
        self.delay_spin.setValue(current_delay)
        self.delay_spin.valueChanged.connect(self.save_delay)
        
        settings_layout.addWidget(delay_label)
        settings_layout.addWidget(self.delay_spin)
        
        timeout_label = QLabel("  Timeout (sec):")
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(1.0, 300.0)
        self.timeout_spin.setSingleStep(5.0)
        self.timeout_spin.setValue(float(db.get_setting("request_timeout", 60.0)))
        self.timeout_spin.valueChanged.connect(self.save_timeout)
        
        settings_layout.addWidget(timeout_label)
        settings_layout.addWidget(self.timeout_spin)
        settings_layout.addStretch()
        
        layout.addLayout(settings_layout)

        info_label = QLabel("Double-click a cell to edit. Changes are saved automatically.")
        info_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(info_label)

        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_view)

        # Кнопки управления
        btns_layout = QHBoxLayout()
        
        btn_add = QPushButton("+ Add New Model")
        btn_add.clicked.connect(self.add_row)
        
        btn_delete = QPushButton("- Delete Selected")
        btn_delete.clicked.connect(self.delete_row)
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)

        btn_notes = QPushButton("📝 Notes")
        btn_notes.clicked.connect(self.open_notes)

        btns_layout.addWidget(btn_add)
        btns_layout.addWidget(btn_delete)
        btns_layout.addWidget(btn_notes)
        btns_layout.addStretch()
        btns_layout.addWidget(btn_close)
        
        layout.addLayout(btns_layout)
        
        # Делегат для выбора ключа API из списка популярных имен
        self.key_delegate = KeySelectionDelegate(self)
        self.table_view.setItemDelegateForColumn(2, self.key_delegate)

    def add_row(self):
        # Добавляем пустую строку в конец
        row = self.model.rowCount()
        self.model.insertRow(row)
        # Устанавливаем значения по умолчанию
        self.model.setData(self.model.index(row, 1), "https://api.openai.com/v1/chat/completions")
        self.model.setData(self.model.index(row, 2), "API_KEY_NAME")
        self.model.setData(self.model.index(row, 3), 1)

    def delete_row(self):
        selected_index = self.table_view.currentIndex()
        if selected_index.isValid():
            confirm = QMessageBox.question(self, "Delete", "Are you sure you want to delete this model?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                self.model.removeRow(selected_index.row())
                self.model.select() # Обновляем вид
        else:
            QMessageBox.warning(self, "Selection", "Please click on a row to delete.")

    def save_delay(self):
        db.set_setting("request_delay", self.delay_spin.value())

    def save_timeout(self):
        db.set_setting("request_timeout", self.timeout_spin.value())

    def open_notes(self):
        notes = NotesManager(parent=self)
        notes.exec()

class KeySelectionDelegate(QItemDelegate):
    """Делегат для удобного выбора имен ключей API из .env."""
    def __init__(self, parent=None):
        super().__init__(parent)
        # Список имен ключей, которые приложение умеет искать в .env
        self.available_keys = [
            "OPENROUTER_API_KEY", 
            "OPENROUTER_API_KEY2", 
            "OPENAI_API_KEY", 
            "DEEPSEEK_API_KEY", 
            "GROQ_API_KEY",
            "HF_TOKEN",
            "HF_API_KEY",
            "ZAI_API_KEY"
        ]

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.available_keys)
        editor.setEditable(True) # Позволяет вводить свои уникальные имена
        return editor

    def setEditorData(self, editor, index):
        text = index.data(Qt.ItemDataRole.EditRole)
        idx = editor.findText(text)
        if idx >= 0:
            editor.setCurrentIndex(idx)
        else:
            editor.setEditText(text)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)
