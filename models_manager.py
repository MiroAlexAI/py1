from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableView, QWidget,
                             QPushButton, QHeaderView, QMessageBox, QLabel, QDoubleSpinBox, QItemDelegate, QComboBox, QGroupBox, QFrame)
from PyQt6.QtSql import QSqlDatabase, QSqlTableModel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from notes_manager import NotesManager
from dotenv import load_dotenv
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
        self.update_env_status() # Первичная валидация
        self.update_rating()     # Загрузка рейтинга

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

        # Секция валидации .env
        env_group = QGroupBox("🔑 .env Keys Validation")
        env_group.setStyleSheet("QGroupBox { font-weight: bold; color: #3b82f6; border: 1px solid #ccc; margin-top: 5px; padding-top: 15px; }")
        self.env_layout = QHBoxLayout(env_group)
        self.env_layout.setContentsMargins(10, 5, 10, 5)
        
        self.btn_refresh_env = QPushButton("🔄 Scan .env")
        self.btn_refresh_env.setFixedWidth(100)
        self.btn_refresh_env.clicked.connect(self.update_env_status)
        self.env_layout.addWidget(self.btn_refresh_env)
        
        # Контейнер для индикаторов
        self.indicators_container = QWidget()
        self.indicators_layout = QHBoxLayout(self.indicators_container)
        self.indicators_layout.setContentsMargins(0,0,0,0)
        self.env_layout.addWidget(self.indicators_container)
        
        layout.addWidget(env_group)

        # Секция рейтинга моделей
        rating_group = QGroupBox("🏆 Model Popularity Rating")
        rating_group.setStyleSheet("QGroupBox { font-weight: bold; color: #f59e0b; border: 1px solid #ccc; margin-top: 5px; padding-top: 15px; }")
        self.rating_layout = QHBoxLayout(rating_group)
        self.rating_label = QLabel("Loading rating...")
        self.rating_label.setStyleSheet("color: #4b5563; font-weight: normal;")
        self.rating_layout.addWidget(self.rating_label)
        layout.addWidget(rating_group)

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

    def update_env_status(self):
        """Проверяет наличие ключей в .env и обновляет индикаторы."""
        load_dotenv(override=True) # Перезагружаем переменные окружения
        
        # Очищаем старые индикаторы
        for i in reversed(range(self.indicators_layout.count())): 
            self.indicators_layout.itemAt(i).widget().setParent(None)

        keys_to_check = [
            "OPENROUTER_API_KEY", "OPENROUTER_API_KEY2", 
            "OPENAI_API_KEY", "ZAI_API_KEY", "HF_TOKEN"
        ]
        
        for key in keys_to_check:
            val = os.getenv(key)
            has_key = bool(val and val.strip())
            
            lbl = QLabel(f"{key}")
            color = "#10b981" if has_key else "#ef4444" # Green if found, Red if missing
            status_text = "●" # Кружок-индикатор
            
            dot = QLabel(status_text)
            dot.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
            
            item_layout = QHBoxLayout()
            item_layout.setSpacing(2)
            item_layout.addWidget(dot)
            item_layout.addWidget(lbl)
            
            container = QWidget()
            container.setLayout(item_layout)
            self.indicators_layout.addWidget(container)
        
        self.indicators_layout.addStretch()

    def update_rating(self):
        """Загружает и отображает ТОП-5 популярных моделей."""
        try:
            rating = db.get_model_popularity_rating(limit=5)
            if not rating:
                self.rating_label.setText("No saved results yet.")
                return
            
            items = []
            for i, (name, count) in enumerate(rating):
                medal = ["🥇", "🥈", "🥉", "▫️", "▫️"][i] if i < 5 else "▫️"
                items.append(f"{medal} {name}: {count}")
            
            self.rating_label.setText(" | ".join(items))
        except Exception as e:
            self.rating_label.setText(f"Rating error: {e}")

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
