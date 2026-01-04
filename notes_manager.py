import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableView, 
                             QPushButton, QHeaderView, QMessageBox, QLabel, 
                             QLineEdit, QTextEdit, QFormLayout, QWidget)
from PyQt6.QtSql import QSqlDatabase, QSqlTableModel
from PyQt6.QtCore import Qt, QDateTime
import db

class NotesManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Заметки к модулю / Черновики")
        self.resize(900, 600)
        
        self.init_db()
        self.init_ui()

    def init_db(self):
        if not QSqlDatabase.contains("qt_sql_default_connection"):
            self.db = QSqlDatabase.addDatabase("QSQLITE")
            self.db.setDatabaseName("chatlist.db")
            if not self.db.open():
                QMessageBox.critical(self, "DB Error", "Could not open database via QtSql")
        else:
            self.db = QSqlDatabase.database("qt_sql_default_connection")

        self.model = QSqlTableModel(self, self.db)
        self.model.setTable("notes")
        self.model.setEditStrategy(QSqlTableModel.EditStrategy.OnFieldChange)
        
        self.model.setHeaderData(0, Qt.Orientation.Horizontal, "ID")
        self.model.setHeaderData(1, Qt.Orientation.Horizontal, "Дата")
        self.model.setHeaderData(2, Qt.Orientation.Horizontal, "Тэг")
        self.model.setHeaderData(3, Qt.Orientation.Horizontal, "Заголовок")
        self.model.setHeaderData(4, Qt.Orientation.Horizontal, "Текст")
        
        self.model.select()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Верхняя панель управления
        top_layout = QHBoxLayout()
        title_label = QLabel("Управление заметками")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6;")
        top_layout.addWidget(title_label)
        
        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск по содержанию / тегам...")
        self.search_input.setFixedWidth(250)
        self.search_input.textChanged.connect(self.update_search_filter)
        top_layout.addWidget(self.search_input)
        
        top_layout.addStretch()
        
        btn_add = QPushButton("+ Добавить заметку")
        btn_add.setStyleSheet("background-color: #10b981; color: white; font-weight: bold;")
        btn_add.clicked.connect(self.add_note)
        top_layout.addWidget(btn_add)
        
        layout.addLayout(top_layout)

        # Таблица и редактор в сплиттере или просто рядом
        content_layout = QHBoxLayout()
        
        # Список заметок
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.setColumnHidden(0, True) # Скрываем ID
        self.table_view.setColumnWidth(1, 130)
        self.table_view.setColumnWidth(2, 100)
        self.table_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_view.setColumnHidden(4, True) # Скрываем длинный текст в таблице
        self.table_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        content_layout.addWidget(self.table_view, 2)
        
        # Поля редактирования справа
        self.edit_widget = QWidget()
        edit_layout = QVBoxLayout(self.edit_widget)
        
        form = QFormLayout()
        self.date_edit = QLineEdit()
        self.date_edit.setReadOnly(True)
        self.tag_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.content_edit = QTextEdit()
        
        form.addRow("Дата:", self.date_edit)
        form.addRow("Тэг:", self.tag_edit)
        form.addRow("Заголовок:", self.title_edit)
        edit_layout.addLayout(form)
        edit_layout.addWidget(QLabel("Текст заметки:"))
        edit_layout.addWidget(self.content_edit)
        
        # Кнопки сохранения/удаления в редакторе
        edit_btns = QHBoxLayout()
        btn_save = QPushButton("💾 Сохранить изменения")
        btn_save.clicked.connect(self.save_current_note)
        btn_delete = QPushButton("🗑️ Удалить")
        btn_delete.setStyleSheet("background-color: #ef4444; color: white;")
        btn_delete.clicked.connect(self.delete_note)
        
        edit_btns.addWidget(btn_save)
        edit_btns.addWidget(btn_delete)
        edit_layout.addLayout(edit_btns)
        
        content_layout.addWidget(self.edit_widget, 3)
        layout.addLayout(content_layout)

    def add_note(self):
        row = self.model.rowCount()
        self.model.insertRow(row)
        self.model.setData(self.model.index(row, 1), QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm"))
        self.model.setData(self.model.index(row, 2), "General")
        self.model.setData(self.model.index(row, 3), "Новая заметка")
        self.model.setData(self.model.index(row, 4), "")
        self.model.submitAll()
        self.table_view.selectRow(row)

    def on_selection_changed(self):
        indexes = self.table_view.selectionModel().selectedRows()
        if indexes:
            row = indexes[0].row()
            self.date_edit.setText(self.model.index(row, 1).data())
            self.tag_edit.setText(self.model.index(row, 2).data())
            self.title_edit.setText(self.model.index(row, 3).data())
            self.content_edit.setPlainText(self.model.index(row, 4).data())
        else:
            self.clear_edits()

    def clear_edits(self):
        self.date_edit.clear()
        self.tag_edit.clear()
        self.title_edit.clear()
        self.content_edit.clear()

    def save_current_note(self):
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return
        
        row = indexes[0].row()
        self.model.setData(self.model.index(row, 2), self.tag_edit.text())
        self.model.setData(self.model.index(row, 3), self.title_edit.text())
        self.model.setData(self.model.index(row, 4), self.content_edit.toPlainText())
        if self.model.submitAll():
            QMessageBox.information(self, "Успех", "Заметка сохранена.")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить в БД.")

    def delete_note(self):
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return
        
        confirm = QMessageBox.question(self, "Удаление", "Удалить выбранную заметку?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.model.removeRow(indexes[0].row())
            self.model.submitAll()
            self.model.select()
            self.clear_edits()

    def update_search_filter(self, text):
        """Фильтрация заметок по вводу."""
        if not text:
            self.model.setFilter("")
        else:
            # Простейшее экранирование для предотвращения ошибок SQL при вводе '
            safe_text = text.replace("'", "''")
            filter_str = f"(content LIKE '%{safe_text}%' OR title LIKE '%{safe_text}%' OR tag LIKE '%{safe_text}%')"
            self.model.setFilter(filter_str)
        self.model.select()
