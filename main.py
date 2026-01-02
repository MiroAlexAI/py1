import sys
import logging
import asyncio
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QLabel, QPushButton, QHBoxLayout, QTextEdit, 
                             QTableView, QHeaderView, QAbstractItemView, 
                             QMessageBox, QSplitter, QComboBox, QLineEdit, QFileDialog, 
                             QProgressBar, QTabWidget)
from PyQt6.QtCore import Qt, pyqtSlot, QAbstractTableModel, QVariant, QSortFilterProxyModel
from PyQt6.QtGui import QFont
from qasync import QEventLoop, asyncSlot
import json

import db
import models_logic
import network
from hf_space_chat import GLMChatWindow
from md_viewer import MarkdownViewer
from models_manager import ModelsManager
from results_journal import ResultsJournal

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

GLOBAL_STYLE = """
    QMainWindow, QDialog {
        background-color: #ECE9D8;
    }
    QWidget {
        color: #000000;
        font-family: 'Tahoma', 'Segoe UI', 'Arial';
        font-size: 11px;
    }
    QLabel {
        color: #000000;
    }
    QPushButton {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #dcdcdc);
        border: 1px solid #003C74;
        border-radius: 3px;
        padding: 5px 15px;
        color: #000000;
    }
    QPushButton:hover {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff5cc, stop:1 #ffcc00);
        border-color: #ff9900;
    }
    QPushButton:pressed {
        background-color: #dcdcdc;
    }
    QPushButton#send_btn {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4ba6ff, stop:1 #0056b3);
        color: white;
        font-weight: bold;
        border: 1px solid #003c74;
    }
    QTextEdit, QLineEdit {
        background-color: #ffffff;
        border: 2px inset #999999;
        color: #000000;
        selection-background-color: #316AC5;
    }
    QTableView {
        background-color: #ffffff;
        gridline-color: #d5d5d5;
        border: 2px inset #999999;
        selection-background-color: #316AC5;
        selection-color: #ffffff;
    }
    QHeaderView::section {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #dcdcdc);
        color: #000000;
        padding: 4px;
        border: 1px solid #aca899;
    }
    QComboBox {
        background-color: #ffffff;
        border: 1px solid #7F9DB9;
        padding: 2px;
    }
    QProgressBar {
        border: 1px solid #aca899;
        background: #ffffff;
        text-align: center;
    }
    QProgressBar::chunk {
        background-color: #00ac00;
        width: 10px;
        margin: 0.5px;
    }
    QScrollBar:vertical {
        background: #f0f0f0;
        width: 16px;
    }
    QScrollBar::handle:vertical {
        background: #dcdcdc;
        border: 1px solid #aca899;
    }
"""

class ResultsTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = ["Select", "Slot", "Model", "Response", "Status", "Preview"]

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 1: return self._data[row].get('slot', 'P1')
            if col == 2: return self._data[row]['model']
            if col == 3: return self._data[row]['response']
            if col == 4: return self._data[row]['status']
            if col == 5: return "🔍 Open"
        
        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            return Qt.CheckState.Checked if self._data[row].get('selected') else Qt.CheckState.Unchecked

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid(): return False
        
        row = index.row()
        col = index.column()

        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            if isinstance(value, int):
                checked = (value == Qt.CheckState.Checked.value)
            else:
                checked = (value == Qt.CheckState.Checked)
            self._data[row]['selected'] = checked
            self.dataChanged.emit(index, index, [role])
            return True
        
        if role == Qt.ItemDataRole.EditRole and col == 2:
            self._data[row]['response'] = value
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
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
        return None

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
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.results_model)
        self.proxy_model.setFilterKeyColumn(-1) # Filter all columns
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        self.init_ui()
        # Слушаем переключение вкладок для обновления истории
        self.prompt_tabs.currentChanged.connect(self.load_history)
        self.center()
        logger.info("Main UI Initialized.")

    def center(self):
        """Центрирование окна на экране (с учетом геометрии Windows)."""
        screen = self.screen().availableGeometry()
        size = self.frameGeometry()
        x = (screen.x() + (screen.width() - size.width()) // 2)
        y = (screen.y() + (screen.height() - size.height()) // 2)
        # Сдвигаем на 30 пикселей вниз, чтобы верхняя панель не обрезалась
        self.move(x, y + 30)

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setStyleSheet(GLOBAL_STYLE)
        main_layout = QVBoxLayout(central_widget)

        # --- Header ---
        header_layout = QHBoxLayout()
        title_label = QLabel("ChatList Professional")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #3b82f6; margin-bottom: 5px;")
        
        btn_special = QPushButton("🚀 GLM-4.5 Special Space")
        btn_special.clicked.connect(self.open_special_chat)
        
        btn_models = QPushButton("⚙️ Manage Models")
        btn_models.clicked.connect(self.open_models_manager)
        
        btn_journal = QPushButton("📜 Results Journal")
        btn_journal.clicked.connect(self.open_results_journal)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(btn_journal)
        header_layout.addWidget(btn_models)
        header_layout.addWidget(btn_special)
        main_layout.addLayout(header_layout)

        # --- Splitter (Prompt Input Top / Results Bottom) ---
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top Widget: Prompt Input
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        
        prompt_label = QLabel("Enter your prompt:")
        prompt_label.setStyleSheet("font-weight: bold; color: #888;")
        
        # История промтов
        history_layout = QHBoxLayout()
        history_label = QLabel("History:")
        history_label.setStyleSheet("color: #555; font-size: 11px;")
        self.prompt_history = QComboBox()
        self.prompt_history.setMinimumWidth(300)
        self.prompt_history.setMaximumWidth(600)
        # Удалили темный стиль QComboBox, теперь он берется из GLOBAL_STYLE (classic)
        self.prompt_history.addItem("-- Select from history --")
        self.prompt_history.activated.connect(self.on_history_selected)
        
        btn_save_prompt = QPushButton("💾 Save Prompt")
        btn_save_prompt.setStyleSheet("background-color: #1e293b; padding: 4px 12px; font-size: 12px;")
        btn_save_prompt.clicked.connect(self.on_save_prompt_clicked)
        
        btn_delete_prompt = QPushButton("🗑️")
        btn_delete_prompt.setToolTip("Delete selected prompt from history")
        btn_delete_prompt.setStyleSheet("background-color: #450a0a; color: #ef4444; border: 1px solid #7f1d1d; padding: 4px 8px;")
        btn_delete_prompt.clicked.connect(self.on_delete_prompt_clicked)
        
        history_layout.addWidget(history_label)
        history_layout.addWidget(self.prompt_history)
        history_layout.addWidget(btn_save_prompt)
        history_layout.addWidget(btn_delete_prompt)
        history_layout.addStretch()

        # Тройной промпт (Tab Widget)
        self.prompt_tabs = QTabWidget()
        self.prompt_tabs.setStyleSheet("QTabBar::tab { padding: 8px 30px; background: #dcdcdc; border: 1px solid #aca899; } QTabBar::tab:selected { background: #ffffff; border-bottom-color: white; }")
        
        self.p1_input = QTextEdit()
        self.p1_input.setPlaceholderText("Main Prompt / Task...")
        self.p2_input = QTextEdit()
        self.p2_input.setPlaceholderText("Context / Rules...")
        self.p3_input = QTextEdit()
        self.p3_input.setPlaceholderText("Format / Example...")
        
        self.prompt_tabs.addTab(self.p1_input, "🎯 Prompt 1")
        self.prompt_tabs.addTab(self.p2_input, "📖 Prompt 2")
        self.prompt_tabs.addTab(self.p3_input, "🏗️ Prompt 3")
        
        btn_send = QPushButton("Send Triple Prompt (Combined)")
        btn_send.setObjectName("send_btn")
        self.btn_send = btn_send
        self.btn_send.clicked.connect(self.on_send_clicked)

        input_layout.addWidget(prompt_label)
        input_layout.addLayout(history_layout)
        input_layout.addWidget(self.prompt_tabs)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #334155; border-radius: 4px; text-align: center; height: 10px; background: #0f1216; }
            QProgressBar::chunk { background-color: #3b82f6; width: 20px; }
        """)
        input_layout.addWidget(self.progress_bar)
        
        input_layout.addWidget(btn_send)
        
        # Bottom Widget: Results Table
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        # Search and Info
        table_header_layout = QHBoxLayout()
        table_label = QLabel("Model Responses Comparison:")
        table_label.setStyleSheet("font-weight: bold; color: #888;")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search in results...")
        self.search_input.setMaximumWidth(300)
        self.search_input.textChanged.connect(self.proxy_model.setFilterFixedString)
        
        table_header_layout.addWidget(table_label)
        table_header_layout.addStretch()
        table_header_layout.addWidget(self.search_input)
        table_label.setStyleSheet("font-weight: bold; color: #888;")
        
        self.results_table = QTableView()
        self.results_table.setModel(self.proxy_model)
        self.results_table.setSortingEnabled(True)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.results_table.setColumnWidth(0, 50)
        self.results_table.setColumnWidth(1, 150)
        self.results_table.setColumnWidth(4, 80)
        self.results_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setWordWrap(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.doubleClicked.connect(self.on_table_double_clicked)
        
        # Action Buttons for Results
        actions_layout = QHBoxLayout()
        btn_save = QPushButton("Save Selected to DB")
        btn_save.setStyleSheet("background-color: #10b981; color: white;") # specific accent for success
        btn_save.clicked.connect(self.save_selected)
        
        btn_export_md = QPushButton("Export Markdown")
        btn_export_md.clicked.connect(self.export_markdown)
        
        btn_export_json = QPushButton("Export JSON")
        btn_export_json.clicked.connect(self.export_json)

        btn_open = QPushButton("🔍 Open in MD")
        btn_open.setStyleSheet("background-color: #2563eb; color: white;")
        btn_open.clicked.connect(self.open_md_viewer)
        
        actions_layout.addWidget(btn_save)
        actions_layout.addWidget(btn_open)
        actions_layout.addWidget(btn_export_md)
        actions_layout.addWidget(btn_export_json)
        actions_layout.addStretch()

        results_layout.addLayout(table_header_layout)
        results_layout.addWidget(self.results_table)
        results_layout.addLayout(actions_layout)

        splitter.addWidget(input_widget)
        splitter.addWidget(results_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        self.setCentralWidget(central_widget)
        
        # Загружаем историю при старте
        self.load_history()

    def open_special_chat(self):
        if self.special_chat_window is None:
            self.special_chat_window = GLMChatWindow()
        self.special_chat_window.show()

    def open_models_manager(self):
        manager = ModelsManager(parent=self)
        manager.exec()

    def open_results_journal(self):
        journal = ResultsJournal(parent=self)
        journal.exec()

    @asyncSlot()
    async def on_send_clicked(self):
        p1 = self.p1_input.toPlainText().strip()
        p2 = self.p2_input.toPlainText().strip()
        p3 = self.p3_input.toPlainText().strip()
        
        if not any([p1, p2, p3]):
            return

        # Промпты объединяются перед отправкой
        combined_prompt = "\n\n".join([p for p in [p1, p2, p3] if p])

        active_models = models_logic.get_active_models_with_keys()
        if not active_models:
            QMessageBox.warning(self, "No Models", "No active models with API keys found in .env!")
            return

        self.btn_send.setEnabled(False)
        self.btn_send.setText("Processing Triple Request...")
        
        self.results_model.update_data([])
        
        self.progress_bar.setRange(0, len(active_models))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        try:
            completed = 0
            all_results = []
            delay_step = float(db.get_setting("request_delay", 0.0))
            timeout = float(db.get_setting("request_timeout", 60.0))
            
            tasks = [network.delayed_fetch(i * delay_step, m[0], m[1], m[2], combined_prompt, timeout) 
                     for i, m in enumerate(active_models)]
            
            for future in asyncio.as_completed(tasks):
                res = await future
                res['slot'] = "P1+P2+P3" 
                # Сохраняем компоненты в объекте результата для корректного сохранения в разные таблицы истории
                res['p1'] = p1
                res['p2'] = p2
                res['p3'] = p3
                all_results.append(res)
                completed += 1
                self.progress_bar.setValue(completed)
                self.results_model.update_data(all_results.copy())
                self.results_table.resizeRowsToContents()
                
        except Exception as e:
            logger.error(f"Error during triple send: {e}")
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self.btn_send.setEnabled(True)
            self.btn_send.setText("Send Triple Prompt (Combined)")
            self.progress_bar.setVisible(False)

    def save_selected(self):
        selected_data = [row for row in self.results_model._data if row.get('selected')]
        
        if not selected_data:
            QMessageBox.information(self, "Save", "Please select responses to save.")
            return

        saved_count = 0
        for item in selected_data:
            # Распределяем части по своим таблицам истории
            parts = {
                "prompts": item.get('p1', ""),
                "prompts2": item.get('p2', ""),
                "prompts3": item.get('p3', "")
            }
            
            p1_id = None
            for table_name, text in parts.items():
                if text:
                    pid = db.get_prompt_id(text, table=table_name)
                    if pid is None:
                        pid = db.add_prompt(text, table=table_name)
                    if table_name == "prompts":
                        p1_id = pid
            
            # Результат привязываем к P1 (если он есть) или к 0
            db.save_result(p1_id or 0, item['model'], item['response'], table="results")
            saved_count += 1
            
        QMessageBox.information(self, "Success", f"Saved {saved_count} items. Prompts sorted to slots.")
        self.load_history()

    def on_save_prompt_clicked(self):
        """Сохранение текущего активного промпта в его таблицу."""
        cur_idx = self.prompt_tabs.currentIndex()
        text = [self.p1_input, self.p2_input, self.p3_input][cur_idx].toPlainText().strip()
        if not text: return
        
        p_table = "prompts" if cur_idx == 0 else f"prompts{cur_idx+1}"
        
        existing_id = db.get_prompt_id(text, table=p_table)
        if existing_id:
            QMessageBox.information(self, "Status", f"Prompt already exists in history {cur_idx+1}.")
        else:
            db.add_prompt(text, table=p_table)
            QMessageBox.information(self, "Success", f"Prompt saved to history {cur_idx+1}.")
            self.load_history()

    def on_history_selected(self, index):
        """Вставка текста из истории в текущую активную вкладку."""
        if index > 0:
            full_text = self.prompt_history.itemData(index, Qt.ItemDataRole.UserRole)
            if full_text and isinstance(full_text, str):
                cur_tab = self.prompt_tabs.currentIndex()
                inputs = [self.p1_input, self.p2_input, self.p3_input]
                inputs[cur_tab].setPlainText(full_text)
                logger.info("Prompt loaded from history to current tab.")

    def on_delete_prompt_clicked(self):
        """Удаление промпта из таблицы текущей активной вкладки."""
        index = self.prompt_history.currentIndex()
        if index <= 0: return
        
        cur_tab = self.prompt_tabs.currentIndex()
        p_table = "prompts" if cur_tab == 0 else f"prompts{cur_tab+1}"
        
        prompt_id = self.prompt_history.itemData(index, Qt.ItemDataRole.UserRole + 1)
        confirm = QMessageBox.question(self, "Delete", f"Are you sure you want to delete this prompt from history {cur_tab+1}?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            db.delete_prompt(prompt_id, table=p_table)
            self.load_history()

    def load_history(self):
        """Загрузка истории для текущей активной вкладки промпта."""
        try:
            cur_tab = self.prompt_tabs.currentIndex()
            p_table = "prompts" if cur_tab == 0 else f"prompts{cur_tab+1}"
            
            prompts = db.get_prompts(table=p_table)
            self.prompt_history.blockSignals(True)
            self.prompt_history.clear()
            self.prompt_history.addItem(f"-- History for Slot {cur_tab+1} --")
            for p in prompts:
                short_text = (p[2][:50] + '...') if len(p[2]) > 50 else p[2]
                self.prompt_history.addItem(f"{p[1][:10]} | {short_text}", p[2])
                self.prompt_history.setItemData(self.prompt_history.count()-1, p[0], Qt.ItemDataRole.UserRole + 1)
            self.prompt_history.blockSignals(False)
        except Exception as e:
            logger.error(f"Error loading history for {p_table}: {e}")

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
            # Мапим индекс прокси-модели на исходную модель
            source_index = self.proxy_model.mapToSource(selected_indexes[0])
            row_data = self.results_model._data[source_index.row()]
        
        viewer = MarkdownViewer(row_data['model'], row_data['response'], self)
        viewer.exec()

    def on_table_double_clicked(self, index):
        """Открытие по двойному клику."""
        source_index = self.proxy_model.mapToSource(index)
        row_data = self.results_model._data[source_index.row()]
        viewer = MarkdownViewer(row_data['model'], row_data['response'], self)
        viewer.exec()

    def export_markdown(self):
        """Экспорт результатов в Markdown таблицу."""
        data = self.results_model._data
        if not data:
            QMessageBox.warning(self, "Export", "No data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Markdown", "", "Markdown Files (*.md)")
        if not file_path:
            return

        try:
            cur_tab = self.prompt_tabs.currentIndex()
            inputs = [self.p1_input, self.p2_input, self.p3_input]
            # Экспортируем полное объединение
            prompt = "\n\n".join([i.toPlainText().strip() for i in inputs if i.toPlainText().strip()])
            md_content = f"# ChatList Export (Triple Combined)\n\n**Full Prompt:**\n{prompt}\n\n"
            md_content += "| Model | Response | Status |\n"
            md_content += "|-------|----------|--------|\n"
            
            for row in data:
                resp = row['response'].replace('\n', '<br>')
                md_content += f"| {row['model']} | {resp} | {row['status']} |\n"
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            QMessageBox.information(self, "Success", "Exported to Markdown.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def export_json(self):
        """Экспорт результатов в JSON."""
        data = self.results_model._data
        if not data:
            QMessageBox.warning(self, "Export", "No data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save JSON", "", "JSON Files (*.json)")
        if not file_path:
            return

        try:
            prompt = self.prompt_input.toPlainText().strip()
            export_obj = {
                "prompt": prompt,
                "timestamp": db.datetime.now().isoformat(),
                "results": data
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_obj, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Success", "Exported to JSON.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")

def main():
    app = QApplication(sys.argv)
    
    # Установка Tahoma как стандартного шрифта, чтобы избежать ошибок с MS Serif
    default_font = QFont("Tahoma", 9)
    app.setFont(default_font)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = MainWindow()
    window.show()
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
