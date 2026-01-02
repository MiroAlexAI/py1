from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableView, 
                             QPushButton, QHeaderView, QMessageBox, QLabel, QLineEdit, QAbstractItemView, QItemDelegate, QComboBox)
from PyQt6.QtSql import QSqlDatabase, QSqlTableModel
from PyQt6.QtCore import Qt, QSortFilterProxyModel
from md_viewer import MarkdownViewer
import db

class ResultsJournal(QDialog):
    def __init__(self, db_path="chatlist.db", parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle("Saved Results Journal")
        self.resize(1000, 600)
        
        self.init_db()
        self.init_ui()

    def init_db(self):
        if not QSqlDatabase.contains("qt_sql_default_connection"):
            self.db = QSqlDatabase.addDatabase("QSQLITE")
            self.db.setDatabaseName(self.db_path)
            if not self.db.open():
                QMessageBox.critical(self, "DB Error", "Could not open database via QtSql")
        else:
            self.db = QSqlDatabase.database("qt_sql_default_connection")

        self.model = QSqlTableModel(self, self.db)
        self.model.setTable("results")
        self.model.setEditStrategy(QSqlTableModel.EditStrategy.OnFieldChange)
        
        # Headers: id, prompt_id, model_name, response, date
        self.model.setHeaderData(0, Qt.Orientation.Horizontal, "ID")
        self.model.setHeaderData(1, Qt.Orientation.Horizontal, "Prompt ID")
        self.model.setHeaderData(2, Qt.Orientation.Horizontal, "Model")
        self.model.setHeaderData(3, Qt.Orientation.Horizontal, "Response")
        self.model.setHeaderData(4, Qt.Orientation.Horizontal, "Date")
        
        self.model.select()

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        title = QLabel("📦 Archived AI Responses")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6;")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filter results...")
        self.search_input.textChanged.connect(self.proxy_model.setFilterFixedString)
        self.search_input.setMaximumWidth(300)

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(self.search_input)
        layout.addLayout(header_row)

        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.doubleClicked.connect(self.on_double_clicked)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_view.setColumnWidth(0, 50)
        self.table_view.setColumnWidth(1, 70)
        self.table_view.setColumnWidth(2, 120)
        self.table_view.setColumnWidth(4, 150)
        
        # Removed dark styling to match global classic theme
        layout.addWidget(self.table_view)

        # Секция статистики
        self.stats_label = QLabel()
        self.update_stats()
        layout.addWidget(self.stats_label)

        # Buttons
        btns_layout = QHBoxLayout()
        
        btn_delete = QPushButton("🗑️ Delete Selected")
        btn_delete.clicked.connect(self.delete_row)
        btn_delete.setStyleSheet("background-color: #450a0a; color: #ef4444; border: 1px solid #7f1d1d;")
        
        btn_open = QPushButton("🔍 Open in MD")
        btn_open.clicked.connect(self.view_selected)
        btn_open.setStyleSheet("background-color: #2563eb; color: white;")

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self.model.select)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)

        btns_layout.addWidget(btn_delete)
        btns_layout.addWidget(btn_open)
        btns_layout.addWidget(btn_refresh)
        btns_layout.addStretch()
        btns_layout.addWidget(btn_close)
        
        layout.addLayout(btns_layout)

    def delete_row(self):
        selected_index = self.table_view.currentIndex()
        if selected_index.isValid():
            source_index = self.proxy_model.mapToSource(selected_index)
            confirm = QMessageBox.question(self, "Delete Result", "Delete this saved response permanently?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                self.model.removeRow(source_index.row())
                self.model.select()
        else:
            QMessageBox.warning(self, "Selection", "Please select a row to delete.")

    def view_selected(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            self.on_double_clicked(index)
        else:
            QMessageBox.warning(self, "Selection", "Please select a response to view.")

    def on_double_clicked(self, index):
        source_index = self.proxy_model.mapToSource(index)
        row = source_index.row()
        model_name = self.model.index(row, 2).data()
        response_text = self.model.index(row, 3).data()
        
        viewer = MarkdownViewer(model_name, response_text, self)
        viewer.exec()

    def update_stats(self):
        """Подсчет рейтинга моделей по количеству сохраненных записей."""
        counts = {}
        for row in range(self.model.rowCount()):
            # Индекс 2 - это model_name
            m_name = self.model.index(row, 2).data()
            if m_name:
                counts[m_name] = counts.get(m_name, 0) + 1
        
        if not counts:
            self.stats_label.setText("📊 Статистика: сохраненных ответов пока нет.")
            return

        sorted_stats = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        top_str = " | ".join([f"🏆 {name}: {count}" for name, count in sorted_stats[:5]])
        self.stats_label.setText(f"🔥 Рейтинг моделей (ТОП-5): {top_str}")
