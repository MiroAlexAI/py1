import sys
import logging
import asyncio
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QLabel, QPushButton, QHBoxLayout, QTextEdit, 
                             QTableView, QHeaderView, QAbstractItemView, 
                             QMessageBox, QSplitter)
from PyQt6.QtCore import Qt, pyqtSlot, QAbstractTableModel, QVariant
from qasync import QEventLoop, asyncSlot

import db
import models_logic
import network
from hf_space_chat import GLMChatWindow
from md_viewer import MarkdownViewer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("chatlist.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ChatList")

class ResultsTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = ["Select", "Model", "Response", "Status", "Preview"]

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QVariant()
        
        row = index.row()
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 1: return self._data[row]['model']
            if col == 2: return self._data[row]['response']
            if col == 3: return self._data[row]['status']
            if col == 4: return "🔍 Open"
        
        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            return Qt.CheckState.Checked if self._data[row].get('selected') else Qt.CheckState.Unchecked

        return QVariant()

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if index.isValid() and role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            self._data[index.row()]['selected'] = (value == Qt.CheckState.Checked)
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        if index.column() == 0:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return QVariant()

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        for item in self._data:
            item['selected'] = False
        self.endResetModel()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatList Professional")
        self.setMinimumSize(1100, 800)
        
        # Инициализация БД
        db.init_db()
        models_logic.setup_default_models()
        
        self.special_chat_window = None
        self.results_model = ResultsTableModel()
        
        self.init_ui()
        logger.info("Main UI Initialized.")

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #121212; color: #ffffff;")
        main_layout = QVBoxLayout(central_widget)

        # --- Header ---
        header_layout = QHBoxLayout()
        title_label = QLabel("ChatList Pro")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #00d4ff;")
        
        btn_special = QPushButton("🚀 GLM-4.5 Special Space")
        btn_special.setStyleSheet("""
            QPushButton { background-color: #1a1a1a; border: 1px solid #00d4ff; color: #00d4ff; padding: 8px 16px; border-radius: 4px; }
            QPushButton:hover { background-color: #00d4ff; color: #000; }
        """)
        btn_special.clicked.connect(self.open_special_chat)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(btn_special)
        main_layout.addLayout(header_layout)

        # --- Splitter (Prompt Input Top / Results Bottom) ---
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top Widget: Prompt Input
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        
        prompt_label = QLabel("Enter your prompt:")
        prompt_label.setStyleSheet("font-weight: bold; color: #888;")
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Paste your request here...")
        self.prompt_input.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333; padding: 10px; font-size: 14px;")
        
        btn_send = QPushButton("Send to All Active Models")
        btn_send.setStyleSheet("""
            QPushButton { background-color: #0078d4; color: white; padding: 12px; font-weight: bold; font-size: 14px; border-radius: 4px; }
            QPushButton:hover { background-color: #0086f1; }
            QPushButton:disabled { background-color: #333; color: #777; }
        """)
        self.btn_send = btn_send
        self.btn_send.clicked.connect(self.on_send_clicked)

        input_layout.addWidget(prompt_label)
        input_layout.addWidget(self.prompt_input)
        input_layout.addWidget(btn_send)
        
        # Bottom Widget: Results Table
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        table_label = QLabel("Model Responses Comparison:")
        table_label.setStyleSheet("font-weight: bold; color: #888;")
        
        self.results_table = QTableView()
        self.results_table.setModel(self.results_model)
        self.results_table.setStyleSheet("""
            QTableView { background-color: #1e1e1e; gridline-color: #333; border: 1px solid #333; }
            QHeaderView::section { background-color: #252525; color: #888; padding: 4px; border: 1px solid #333; }
        """)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.results_table.setColumnWidth(4, 80)
        self.results_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setWordWrap(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.doubleClicked.connect(self.on_table_double_clicked)
        
        # Action Buttons for Results
        actions_layout = QHBoxLayout()
        btn_save = QPushButton("Save Selected to DB")
        btn_save.setStyleSheet("background-color: #28a745; color: white; padding: 8px 16px; border-radius: 4px;")
        btn_save.clicked.connect(self.save_selected)
        
        btn_export = QPushButton("Export to Markdown")
        btn_export.setStyleSheet("background-color: #6c757d; color: white; padding: 8px 16px; border-radius: 4px;")
        
        btn_open = QPushButton("🔍 Open in MD")
        btn_open.setStyleSheet("background-color: #0078d4; color: white; padding: 8px 16px; border-radius: 4px;")
        btn_open.clicked.connect(self.open_md_viewer)
        
        actions_layout.addWidget(btn_save)
        actions_layout.addWidget(btn_open)
        actions_layout.addWidget(btn_export)
        actions_layout.addStretch()

        results_layout.addWidget(table_label)
        results_layout.addWidget(self.results_table)
        results_layout.addLayout(actions_layout)

        splitter.addWidget(input_widget)
        splitter.addWidget(results_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        self.setCentralWidget(central_widget)

    def open_special_chat(self):
        if self.special_chat_window is None:
            self.special_chat_window = GLMChatWindow()
        self.special_chat_window.show()

    @asyncSlot()
    async def on_send_clicked(self):
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            return

        active_models = models_logic.get_active_models_with_keys()
        if not active_models:
            QMessageBox.warning(self, "No Models", "No active models with API keys found in .env!")
            return

        self.btn_send.setEnabled(False)
        self.btn_send.setText("Processing models in parallel...")
        
        try:
            results = await network.send_parallel_prompts(active_models, prompt)
            self.results_model.update_data(results)
            self.results_table.resizeRowsToContents()
        except Exception as e:
            logger.error(f"Error during parallel send: {e}")
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self.btn_send.setEnabled(True)
            self.btn_send.setText("Send to All Active Models")

    def save_selected(self):
        prompt_text = self.prompt_input.toPlainText().strip()
        selected_data = [row for row in self.results_model._data if row.get('selected')]
        
        if not selected_data:
            QMessageBox.information(self, "Save", "Please select at least one response to save.")
            return

        # 1. Сохраняем промт
        prompt_id = db.add_prompt(prompt_text)
        
        # 2. Сохраняем ответы
        for item in selected_data:
            db.save_result(prompt_id, item['model'], item['response'])
            
        QMessageBox.information(self, "Success", f"Saved {len(selected_data)} responses to history.")

    def open_md_viewer(self):
        """Открывает Markdown viewer для первой выбранной строки."""
        selected_indexes = self.results_table.selectionModel().selectedRows()
        if not selected_indexes:
            # Если ничего не выделено курсором, ищем по чекбоксам
            selected_rows = [row for row in self.results_model._data if row.get('selected')]
            if not selected_rows:
                QMessageBox.information(self, "Preview", "Please select a row to open.")
                return
            row_data = selected_rows[0]
        else:
            row_index = selected_indexes[0].row()
            row_data = self.results_model._data[row_index]
        
        viewer = MarkdownViewer(row_data['model'], row_data['response'], self)
        viewer.exec()

    def on_table_double_clicked(self, index):
        """Открытие по двойному клику."""
        row_data = self.results_model._data[index.row()]
        viewer = MarkdownViewer(row_data['model'], row_data['response'], self)
        viewer.exec()

def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = MainWindow()
    window.show()
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
