import sys
import logging
import asyncio
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QLabel, QPushButton, QHBoxLayout, QTextEdit, 
                             QTableView, QHeaderView, QAbstractItemView, 
                             QMessageBox, QSplitter, QComboBox, QLineEdit, QFileDialog, 
                             QProgressBar, QTabWidget, QGroupBox, QFormLayout, QDoubleSpinBox, 
                             QSpinBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSlot, QSortFilterProxyModel
from PyQt6.QtGui import QFont, QColor
from qasync import QEventLoop, asyncSlot
import json

from notes_manager import NotesManager
import db
import models_logic
import network
from hf_space_chat import GLMChatWindow
from md_viewer import MarkdownViewer
from models_manager import ModelsManager
from results_journal import ResultsJournal
from table_models import ResultsTableModel
from styles import GLOBAL_STYLE

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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatList Professional")
        self.setMinimumSize(1100, 800)
        
        # Инициализация БД
        db.init_db()
        models_logic.setup_default_models()
        
        self.special_chat_window = None
        self.models_manager_window = None
        self.results_journal_window = None
        self.notes_manager_window = None
        self.viewer_windows = [] # Список для хранения немодальных окон просмотра

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

        btn_notes = QPushButton("📝 Notes / Drafts")
        btn_notes.clicked.connect(self.open_notes_manager)
        btn_notes.setStyleSheet("background-color: #4b5563; color: white;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(btn_notes)
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
        btn_save_prompt.setStyleSheet("color: #3b82f6; padding: 4px 12px; font-size: 12px;")
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

        # Layout for Prompts + Settings
        prompts_settings_layout = QHBoxLayout()
        
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

        # Сигналы для индикации текста во вкладках
        self.p1_input.textChanged.connect(self.update_tab_indicators)
        self.p2_input.textChanged.connect(self.update_tab_indicators)
        self.p3_input.textChanged.connect(self.update_tab_indicators)
        self.update_tab_indicators() # Инициализация

        # Панель глобальных настроек ИИ
        settings_group = QGroupBox("⚙️ Global AI Settings")
        settings_group.setMaximumWidth(250)
        settings_group.setStyleSheet("QGroupBox { font-weight: bold; color: #3b82f6; border: 1px solid #ccc; margin-top: 10px; padding-top: 10px; }")
        settings_form = QFormLayout(settings_group)
        
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(0.0, 2.0)
        self.spin_temp.setSingleStep(0.1)
        self.spin_temp.setValue(float(db.get_setting("global_temp", 0.7)))
        self.spin_temp.valueChanged.connect(lambda v: db.set_setting("global_temp", v))
        
        self.spin_tokens = QSpinBox()
        self.spin_tokens.setRange(1, 32000)
        self.spin_tokens.setSingleStep(100)
        self.spin_tokens.setValue(int(db.get_setting("global_max_tokens", 2000)))
        self.spin_tokens.valueChanged.connect(lambda v: db.set_setting("global_max_tokens", v))
        
        self.spin_top_p = QDoubleSpinBox()
        self.spin_top_p.setRange(0.0, 1.0)
        self.spin_top_p.setSingleStep(0.05)
        self.spin_top_p.setValue(float(db.get_setting("global_top_p", 1.0)))
        self.spin_top_p.valueChanged.connect(lambda v: db.set_setting("global_top_p", v))
        
        self.cb_thinking = QCheckBox("Enable Thinking")
        self.cb_thinking.setToolTip("Activates reasoning/thinking for GLM and some other models.")
        self.cb_thinking.setChecked(db.get_setting("global_thinking", "0") == "1")
        self.cb_thinking.toggled.connect(lambda v: db.set_setting("global_thinking", "1" if v else "0"))
        
        settings_form.addRow("Temperature:", self.spin_temp)
        settings_form.addRow("Max Tokens:", self.spin_tokens)
        settings_form.addRow("Top P:", self.spin_top_p)
        settings_form.addRow(self.cb_thinking)
        
        prompts_settings_layout.addWidget(self.prompt_tabs, 3)
        prompts_settings_layout.addWidget(settings_group, 1)

        btn_send = QPushButton("Отправить тройной промпт")
        btn_send.setObjectName("send_btn")
        self.btn_send = btn_send
        self.btn_send.clicked.connect(self.on_send_clicked)
        
        btn_preview = QPushButton("🔍 Предпросмотр")
        btn_preview.clicked.connect(self.on_preview_prompt_clicked)
        
        btn_row_layout = QHBoxLayout()
        btn_row_layout.addWidget(btn_send, 4)
        btn_row_layout.addWidget(btn_preview, 1)

        input_layout.addWidget(prompt_label)
        input_layout.addLayout(history_layout)
        input_layout.addLayout(prompts_settings_layout) # Заменили prompt_tabs на новый layout
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #334155; border-radius: 4px; text-align: center; height: 10px; background: #0f1216; }
            QProgressBar::chunk { background-color: #3b82f6; width: 20px; }
        """)
        input_layout.addWidget(self.progress_bar)
        
        input_layout.addLayout(btn_row_layout)
        
        # Bottom Widget: Results Table
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        # Search and Info
        table_header_layout = QHBoxLayout()
        self.table_info_label = QLabel("Model Responses Comparison:")
        self.table_info_label.setStyleSheet("font-weight: bold; color: #888;")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search in results...")
        self.search_input.setMaximumWidth(300)
        self.search_input.textChanged.connect(self.proxy_model.setFilterFixedString)
        
        table_header_layout.addWidget(self.table_info_label)
        table_header_layout.addStretch()
        table_header_layout.addWidget(self.search_input)
        
        self.results_table = QTableView()
        self.results_table.setModel(self.proxy_model)
        self.results_table.setSortingEnabled(True)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Response stretch
        self.results_table.setColumnWidth(0, 40)  # Select
        self.results_table.setColumnWidth(1, 80)  # Slot
        self.results_table.setColumnWidth(2, 160) # Model (narrower)
        self.results_table.setColumnWidth(4, 70)  # Symbols
        self.results_table.setColumnWidth(5, 80)  # Status
        self.results_table.setColumnWidth(6, 80)  # Preview
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
        
        btn_retry = QPushButton("🔄 Retry Errors")
        btn_retry.clicked.connect(self.on_retry_errors_clicked)
        self.btn_retry = btn_retry
        
        actions_layout.addWidget(btn_save)
        actions_layout.addWidget(btn_open)
        actions_layout.addWidget(btn_retry)
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
        if self.models_manager_window is None:
            self.models_manager_window = ModelsManager(parent=self)
        self.models_manager_window.show()
        self.models_manager_window.raise_()

    def open_results_journal(self):
        if self.results_journal_window is None:
            self.results_journal_window = ResultsJournal(parent=self)
        self.results_journal_window.show()
        self.results_journal_window.raise_()

    def open_notes_manager(self):
        if self.notes_manager_window is None:
            self.notes_manager_window = NotesManager(parent=self)
        self.notes_manager_window.show()
        self.notes_manager_window.raise_()

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
        self.btn_send.setText("Подключение к моделям...")
        
        self.results_model.update_data([])
        # Подсвечиваем активные модели в таблице
        self.results_model.set_active_models([m[0] for m in active_models])
        
        self.progress_bar.setRange(0, len(active_models))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        try:
            completed = 0
            all_results = []
            delay_step = float(db.get_setting("request_delay", 0.0))
            timeout = float(db.get_setting("request_timeout", 60.0))
            
            # Предварительно загружаем метрики всех моделей для отображения в результатах
            all_metrics = db.get_all_metrics()
            
            # Считываем глобальные настройки из интерфейса
            temperature = self.spin_temp.value()
            max_tokens = self.spin_tokens.value()
            top_p = self.spin_top_p.value()
            thinking = self.cb_thinking.isChecked()

            async def wrap_task(task, model_info):
                res = await task
                res['api_url'] = model_info[1]
                res['api_key_name'] = model_info[2]
                res['slot'] = "P1+P2+P3" 
                res['p1'] = p1
                res['p2'] = p2
                res['p3'] = p3
                res['temperature'] = temperature
                res['max_tokens'] = max_tokens
                res['top_p'] = top_p
                res['thinking'] = thinking
                # Подтягиваем исторические метрики
                res['metrics'] = all_metrics.get(res['model'], {"avg_time": 0, "errors": 0})
                return res

            wrapped_tasks = [wrap_task(network.delayed_fetch(
                                 i * delay_step, m[0], m[1], m[2], combined_prompt, timeout,
                                 temperature=temperature, max_tokens=max_tokens, top_p=top_p, thinking=thinking
                              ), m) for i, m in enumerate(active_models)]
            
            for future in asyncio.as_completed(wrapped_tasks):
                res = await future
                all_results.append(res)
                completed += 1
                self.progress_bar.setValue(completed)
                self.btn_send.setText(f"Выполнено: {completed}/{len(active_models)}")
                self.table_info_label.setText(f"Сравнение ответов (Завершено: {completed}/{len(active_models)})")
                self.results_model.update_data(all_results.copy())
                self.results_table.resizeRowsToContents()
                
        except Exception as e:
            logger.error(f"Error during triple send: {e}")
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self.btn_send.setEnabled(True)
            self.btn_send.setText("Отправить тройной промпт")
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
            
            # Собираем полный промпт для сохранения в результат
            full_prompt_text = "\n\n".join([p for p in [parts["prompts"], parts["prompts2"], parts["prompts3"]] if p])
            
            # Результат привязываем к P1 (если он есть) или к 0, передаем полный текст и метрики
            db.save_result(p1_id or 0, item['model'], item['response'], table="results", 
                           full_prompt=full_prompt_text, resp_time=item.get('resp_time', 0.0), 
                           status=item.get('status', 'Success'))
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

    def on_preview_prompt_clicked(self):
        """Показ объединенного промпта перед отправкой."""
        p1 = self.p1_input.toPlainText().strip()
        p2 = self.p2_input.toPlainText().strip()
        p3 = self.p3_input.toPlainText().strip()
        
        combined = "\n\n".join([p for p in [p1, p2, p3] if p])
        if not combined:
            QMessageBox.information(self, "Preview", "Prompt is empty.")
            return
            
        viewer = MarkdownViewer("Prompt Preview", f"```text\n{combined}\n```", self)
        viewer.exec()

    @asyncSlot()
    async def on_retry_errors_clicked(self):
        """Повторный запрос для тех моделей, которые вернули ошибку."""
        data = self.results_model._data
        failed_indices = [i for i, item in enumerate(data) if item.get('status', '').startswith("Error")]
        
        if not failed_indices:
            QMessageBox.information(self, "Retry", "No errors found to retry.")
            return

        p1 = self.p1_input.toPlainText().strip()
        p2 = self.p2_input.toPlainText().strip()
        p3 = self.p3_input.toPlainText().strip()
        combined_prompt = "\n\n".join([p for p in [p1, p2, p3] if p])

        if not combined_prompt:
            QMessageBox.warning(self, "Retry", "Prompt is empty. Cannot retry.")
            return

        self.btn_retry.setEnabled(False)
        self.btn_retry.setText("Retrying...")
        
        try:
            delay_step = float(db.get_setting("request_delay", 0.0))
            timeout = float(db.get_setting("request_timeout", 60.0))
            
            # Считываем текущие настройки из интерфейса
            temperature = self.spin_temp.value()
            max_tokens = self.spin_tokens.value()
            top_p = self.spin_top_p.value()
            thinking = self.cb_thinking.isChecked()

            async def run_retry(idx, delay):
                item = data[idx]
                model_name = item['model']
                api_url = item.get('api_url')
                api_key_name = item.get('api_key_name')
                
                if not api_url or not api_key_name:
                    active_models = models_logic.get_active_models_with_keys()
                    found = False
                    for m in active_models:
                        if m[0] == model_name:
                            api_url, api_key_name = m[1], m[2]
                            found = True
                            break
                    if not found:
                        item['status'] = "Error: Model info missing"
                        return

                res = await network.delayed_fetch(
                    delay, model_name, api_url, api_key_name, combined_prompt, timeout,
                    temperature=temperature, max_tokens=max_tokens, top_p=top_p, thinking=thinking
                )
                item['response'] = res['response']
                item['status'] = res['status']
                item['api_url'] = api_url 
                item['api_key_name'] = api_key_name
                # Обновляем сохраненные настройки в элементе
                item['temperature'] = temperature
                item['max_tokens'] = max_tokens
                item['top_p'] = top_p
                item['thinking'] = thinking

            tasks = [run_retry(idx, i * delay_step) for i, idx in enumerate(failed_indices)]
            await asyncio.gather(*tasks)

            # Обновляем таблицу атомарно
            self.results_model.beginResetModel()
            self.results_model.endResetModel()
            self.results_table.resizeRowsToContents()
            QMessageBox.information(self, "Retry", f"Retry completed for {len(failed_indices)} items.")
            
        except Exception as e:
            logger.error(f"Retry error: {e}")
            QMessageBox.critical(self, "Error", f"Retry failed: {e}")
        finally:
            self.btn_retry.setEnabled(True)
            self.btn_retry.setText("🔄 Retry Errors")

    def update_tab_indicators(self):
        """Меняет цвет текста вкладок на салатовый, если в них есть текст."""
        inputs = [self.p1_input, self.p2_input, self.p3_input]
        for i, text_edit in enumerate(inputs):
            has_text = bool(text_edit.toPlainText().strip())
            # Салатовый #10b981 если есть текст, иначе черный (или темно-серый #444)
            color = "#10b981" if has_text else "#444444" 
            self.prompt_tabs.tabBar().setTabTextColor(i, QColor(color))

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
        viewer.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.viewer_windows.append(viewer)
        viewer.show()
        viewer.raise_()

    def on_table_double_clicked(self, index):
        """Открытие по двойному клику."""
        source_index = self.proxy_model.mapToSource(index)
        row_data = self.results_model._data[source_index.row()]
        viewer = MarkdownViewer(row_data['model'], row_data['response'], self)
        viewer.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.viewer_windows.append(viewer)
        viewer.show()
        viewer.raise_()

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
            md_content += "| Model | Response | Symbols | Status |\n"
            md_content += "|-------|----------|---------|--------|\n"
            
            for row in data:
                resp = row['response'].replace('\n', '<br>')
                sym_count = len(row['response'])
                md_content += f"| {row['model']} | {resp} | {sym_count} | {row['status']} |\n"
            
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
            p1 = self.p1_input.toPlainText().strip()
            p2 = self.p2_input.toPlainText().strip()
            p3 = self.p3_input.toPlainText().strip()
            combined_prompt = "\n\n".join([p for p in [p1, p2, p3] if p])
            
            export_obj = {
                "prompt": combined_prompt,
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
