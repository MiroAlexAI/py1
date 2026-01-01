from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableView, 
                             QPushButton, QHeaderView, QMessageBox, QLabel)
from PyQt6.QtSql import QSqlDatabase, QSqlTableModel
from PyQt6.QtCore import Qt
import os

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

        info_label = QLabel("Double-click a cell to edit. Changes are saved automatically.")
        info_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(info_label)

        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setStyleSheet("""
            QTableView { background-color: #f8f9fa; color: #333; }
            QHeaderView::section { background-color: #e9ecef; }
        """)
        layout.addWidget(self.table_view)

        # Кнопки управления
        btns_layout = QHBoxLayout()
        
        btn_add = QPushButton("+ Add New Model")
        btn_add.clicked.connect(self.add_row)
        btn_add.setStyleSheet("background-color: #28a745; color: white; padding: 10px; font-weight: bold;")
        
        btn_delete = QPushButton("- Delete Selected")
        btn_delete.clicked.connect(self.delete_row)
        btn_delete.setStyleSheet("background-color: #dc3545; color: white; padding: 10px; font-weight: bold;")
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("background-color: #6c757d; color: white; padding: 10px; font-weight: bold;")

        btns_layout.addWidget(btn_add)
        btns_layout.addWidget(btn_delete)
        btns_layout.addStretch()
        btns_layout.addWidget(btn_close)
        
        layout.addLayout(btns_layout)

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
