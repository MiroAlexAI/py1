import sys
import os
import webbrowser
import markdown2
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLineEdit, 
                              QPushButton, QHBoxLayout, QCheckBox, QLabel, QScrollArea, QSlider, 
                              QProgressBar, QApplication, QSplitter)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QEvent
from notes_manager import NotesManager
from gradio_client import Client
from dotenv import load_dotenv

class GradioWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, msg, sys_prompt, thinking, temperature):
        super().__init__()
        self.msg = msg
        self.sys_prompt = sys_prompt
        self.thinking = thinking
        self.temperature = temperature

    def run(self):
        try:
            load_dotenv()
            hf_token = os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN")
            client = Client("zai-org/GLM-4.5-Space", token=hf_token)
            
            result = client.predict(
                msg=self.msg,
                sys_prompt=self.sys_prompt,
                thinking_enabled=self.thinking,
                temperature=self.temperature,
                api_name="/chat_wrapper"
            )
            # result[0] - history, result[1] - string (usually last msg or status)
            # We want to extract the last response from history
            history = result[0]
            if history:
                last_msg = history[-1]['content']
                self.finished.emit(last_msg)
            else:
                self.finished.emit("No response content.")
        except Exception as e:
            self.error.emit(str(e))

class GLMChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("GLM-4.5 Air - Special Chat")
        self.resize(700, 850)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # --- Блок настроек (Windows XP стиль) ---
        settings_group = QWidget()
        settings_group.setStyleSheet("""
            QWidget {
                background-color: #ece9d8;
                border: 2px solid #003c74;
                border-radius: 4px;
                font-family: 'Tahoma', 'Segoe UI', sans-serif;
                font-size: 11px;
            }
        """)
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(8)
        
        # 1. Enable Thinking + Description
        thinking_layout = QVBoxLayout()
        self.cb_thinking = QCheckBox("Enable Thinking")
        self.cb_thinking.setChecked(True)
        self.cb_thinking.setStyleSheet("""
            QCheckBox {
                color: #000080;
                font-weight: bold;
                font-size: 12px;
                background: transparent;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
                border: 2px solid #808080;
                background-color: #ffffff;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #0056b3;
                border-color: #003c74;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDRMNSA5TDEgNSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
            }
            QCheckBox::indicator:hover {
                border-color: #0056b3;
            }
        """)
        
        thinking_desc = QLabel(
            "Enabled: Activates model's thinking capability.\n"
            "Disabled: Disables model's thinking capability."
        )
        thinking_desc.setWordWrap(True)
        thinking_desc.setStyleSheet("""
            QLabel {
                color: #555555;
                font-size: 10px;
                background: transparent;
                margin-left: 20px;
                margin-top: 2px;
            }
        """)
        
        thinking_layout.addWidget(self.cb_thinking)
        thinking_layout.addWidget(thinking_desc)
        settings_layout.addLayout(thinking_layout)

        # 2. Temperature Slider
        temp_header = QHBoxLayout()
        temp_label = QLabel("Temperature")
        temp_label.setStyleSheet("""
            QLabel {
                color: #000080;
                font-weight: bold;
                font-size: 12px;
                background-color: #d4d0c8;
                padding: 2px 8px;
                border: 1px solid #808080;
                border-radius: 3px;
            }
        """)
        self.temp_value_label = QLabel("0.4")
        self.temp_value_label.setStyleSheet("""
            QLabel {
                color: #000000;
                background-color: #ffffff;
                border: 1px solid #808080;
                padding: 2px 6px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        temp_header.addWidget(temp_label)
        temp_header.addStretch()
        temp_header.addWidget(self.temp_value_label)
        settings_layout.addLayout(temp_header)

        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 100)
        self.temp_slider.setValue(40)
        self.temp_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 20px;
                background: #d4d0c8;
                border: 2px inset #808080;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #ffffff, stop:1 #e0e0e0);
                border: 2px solid #808080;
                width: 16px;
                margin: -2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #f0f0f0, stop:1 #d0d0d0);
                border-color: #0056b3;
            }
        """)
        self.temp_slider.valueChanged.connect(lambda v: self.temp_value_label.setText(f"{v/100:.1f}"))
        settings_layout.addWidget(self.temp_slider)

        # 3. System Prompt
        sys_label = QLabel("System Prompt")
        sys_label.setStyleSheet("""
            QLabel {
                color: #000080;
                font-weight: bold;
                font-size: 12px;
                background-color: #d4d0c8;
                padding: 2px 8px;
                border: 1px solid #808080;
                border-radius: 3px;
            }
        """)
        settings_layout.addWidget(sys_label)
        
        self.sys_prompt_input = QTextEdit()
        self.sys_prompt_input.setPlaceholderText("Enter system instructions here...")
        self.sys_prompt_input.setFixedHeight(80)
        self.sys_prompt_input.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 2px inset #808080;
                color: #000000;
                font-family: 'Tahoma', 'Segoe UI', sans-serif;
                font-size: 11px;
                border-radius: 2px;
            }
            QTextEdit:focus {
                border-color: #0056b3;
            }
        """)
        settings_layout.addWidget(self.sys_prompt_input)

        layout.addWidget(settings_group)

        # Индикатор прогресса (изначально скрыт)
        self.progress_widget = QWidget()
        self.progress_widget.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.setContentsMargins(5, 5, 5, 5)
        
        progress_label = QLabel("Processing request...")
        progress_label.setStyleSheet("""
            QLabel {
                color: #000080;
                font-weight: bold;
                font-size: 11px;
                background-color: #d4d0c8;
                padding: 2px 8px;
                border: 1px solid #808080;
                border-radius: 3px;
            }
        """)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Бесконечный прогресс
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                text-align: center;
                color: #000000;
                background-color: #d4d0c8;
                border: 2px inset #808080;
                border-radius: 2px;
                height: 20px;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #0056b3;
                border-radius: 2px;
                width: 10px;
                margin: 1px;
            }
        """)
        
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_widget)

        # --- Splitter Area (Chat History + Multi-line Input) ---
        self.chat_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Область чата
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 2px inset #808080;
                color: #000000;
                font-family: 'Tahoma', 'Segoe UI', sans-serif;
                font-size: 11px;
                border-radius: 2px;
                padding: 10px;
            }
        """)
        # Добавляем базовые стили для Markdown
        self.chat_display.document().setDefaultStyleSheet("""
            code { background-color: #f4f4f4; padding: 2px 4px; border-radius: 4px; font-family: Consolas, monospace; }
            pre { background-color: #f8f8f8; padding: 10px; border-radius: 5px; border: 1px solid #ddd; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 1em; }
            th, td { border: 1px solid #ddd; padding: 5px; text-align: left; }
            th { background-color: #f2f2f2; }
            blockquote { border-left: 5px solid #ccc; margin: 10px; padding: 5px 10px; color: #666; font-style: italic; }
        """)
        
        self.chat_splitter.addWidget(self.chat_display)

        # Контейнер для ввода
        input_container = QWidget()
        input_container_layout = QVBoxLayout(input_container)
        input_container_layout.setContentsMargins(0, 0, 0, 0)
        input_container_layout.setSpacing(5)

        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Type your message here... (Ctrl+Enter to send)")
        self.input_field.installEventFilter(self) # Для перехвата Ctrl+Enter
        self.input_field.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 2px inset #808080;
                color: #000000;
                padding: 5px;
                font-family: 'Tahoma', 'Segoe UI', sans-serif;
                font-size: 11px;
                border-radius: 2px;
            }
            QTextEdit:focus {
                border-color: #0056b3;
            }
        """)
        input_container_layout.addWidget(self.input_field)
        
        # Поле кнопок
        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.setSpacing(5)
        
        self.btn_send = QPushButton("Send")
        self.btn_send.clicked.connect(self.send_message)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                   stop:0 #ffffff, stop:1 #d4d0c8);
                color: #000000;
                border: 2px solid #808080;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 11px;
                border-radius: 3px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                   stop:0 #f0f8ff, stop:1 #b0d0ff);
                border-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #d4d0c8;
                border-style: inset;
            }
            QPushButton:disabled {
                background-color: #d4d0c8;
                color: #808080;
                border-color: #a0a0a0;
            }
        """)
        
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset_chat)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                   stop:0 #ffffff, stop:1 #d4d0c8);
                color: #000000;
                border: 2px solid #808080;
                padding: 6px 12px;
                font-size: 11px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                   stop:0 #fff0f0, stop:1 #ffd0d0);
                border-color: #800000;
            }
            QPushButton:pressed {
                background-color: #d4d0c8;
                border-style: inset;
            }
        """)

        btn_notes = QPushButton("📝 Notes")
        btn_notes.clicked.connect(self.open_notes)
        btn_notes.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                   stop:0 #ffffff, stop:1 #d4d0c8);
                color: #000000;
                border: 2px solid #808080;
                padding: 6px 12px;
                font-size: 11px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                   stop:0 #f0fff0, stop:1 #d0ffd0);
                border-color: #008000;
            }
            QPushButton:pressed {
                background-color: #d4d0c8;
                border-style: inset;
            }
        """)

        btn_web = QPushButton("🌐 Web")
        btn_web.clicked.connect(self.open_web_version)
        btn_web.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                   stop:0 #ffffff, stop:1 #d4d0c8);
                color: #000000;
                border: 2px solid #808080;
                padding: 6px 12px;
                font-size: 11px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                   stop:0 #f0f0ff, stop:1 #d0d0ff);
                border-color: #000080;
            }
            QPushButton:pressed {
                background-color: #d4d0c8;
                border-style: inset;
            }
        """)

        bottom_buttons_layout.addStretch()
        bottom_buttons_layout.addWidget(self.btn_send)
        bottom_buttons_layout.addWidget(self.btn_reset)
        bottom_buttons_layout.addWidget(btn_notes)
        bottom_buttons_layout.addWidget(btn_web)
        
        input_container_layout.addLayout(bottom_buttons_layout)
        
        self.chat_splitter.addWidget(input_container)
        
        # Начальные размеры: 75% под чат, 25% под ввод
        self.chat_splitter.setStretchFactor(0, 3)
        self.chat_splitter.setStretchFactor(1, 1)
        
        layout.addWidget(self.chat_splitter)

        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: #ece9d8;
                color: #000000;
                font-family: 'Tahoma', 'Segoe UI', sans-serif;
                font-size: 11px;
            }
        """)

    def eventFilter(self, obj, event):
        """Перехват Ctrl+Enter для отправки сообщения из QTextEdit."""
        if obj is self.input_field and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def append_message(self, role, text):
        user_color = "#0000ff" # Синий для пользователя
        bot_color = "#006400"  # Темно-зеленый для бота
        role_color = user_color if role == "User" else bot_color
        
        if role == "GLM-4.5":
            try:
                # Рендерим Markdown в HTML
                html_body = markdown2.markdown(text, extras=["fenced-code-blocks", "tables", "break-on-newline", "blockquote"])
                msg_html = f"<div style='margin-bottom: 12px; border-bottom: 1px dotted #ccc; padding-bottom: 5px;'>" \
                           f"<b style='color: {role_color};'>{role}:</b><br>{html_body}</div>"
                self.chat_display.append(msg_html)
            except Exception as e:
                self.chat_display.append(f"<b style='color: {role_color};'>{role}:</b> {text}<br>")
        else:
            # Для пользователя или системы просто сохраняем переносы
            safe_text = text.replace('\n', '<br>').replace(' ', '&nbsp;')
            msg_html = f"<div style='margin-bottom: 10px; border-bottom: 1px solid #ddd; padding-bottom: 3px;'>" \
                       f"<b style='color: {role_color};'>{role}:</b><br>{safe_text}</div>"
            self.chat_display.append(msg_html)

    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return

        self.input_field.clear()
        self.append_message("User", text)
        self.set_loading(True)

        self.worker = GradioWorker(
            msg=text,
            sys_prompt=self.sys_prompt_input.toPlainText().strip() or "You are a helpful assistant.",
            thinking=self.cb_thinking.isChecked(),
            temperature=self.temp_slider.value() / 100.0
        )
        self.worker.finished.connect(self.handle_response)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def handle_response(self, text):
        self.set_loading(False)
        self.append_message("GLM-4.5", text)

    def handle_error(self, error_msg):
        self.set_loading(False)
        self.append_message("System Error", f"<i style='color: red;'>{error_msg}</i>")

    def set_loading(self, is_loading):
        self.btn_send.setEnabled(not is_loading)
        self.input_field.setEnabled(not is_loading)
        
        # Показываем/скрываем индикатор прогресса
        self.progress_widget.setVisible(is_loading)
        
        if is_loading:
            self.setWindowTitle("GLM-4.5 Air - Special Chat (Processing...)")
            # Анимация прогресса
            self.progress_timer = QTimer()
            self.progress_timer.timeout.connect(self.update_progress_animation)
            self.progress_animation_step = 0
            self.progress_timer.start(100)
        else:
            self.setWindowTitle("GLM-4.5 Air - Special Chat")
            if hasattr(self, 'progress_timer'):
                self.progress_timer.stop()
    
    def update_progress_animation(self):
        """Анимация индикатора прогресса"""
        self.progress_animation_step = (self.progress_animation_step + 1) % 4
        dots = "." * self.progress_animation_step
        self.progress_bar.setFormat(f"Processing{dots}")

    def reset_chat(self):
        self.chat_display.clear()
        self.append_message("System", "Chat context cleared.")
        # Вызов API /reset в фоне
        try:
            load_dotenv()
            hf_token = os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN")
            client = Client("zai-org/GLM-4.5-Space", token=hf_token)
            client.predict(api_name="/reset")
        except:
            pass

    def open_notes(self):
        notes = NotesManager(parent=self)
        notes.exec()

    def open_web_version(self):
        """Открыть веб-версию GLM-4.5 Space в браузере"""
        web_url = "https://huggingface.co/spaces/zai-org/GLM-4.5-Space"
        try:
            webbrowser.open(web_url)
            # Добавляем сообщение в чат об открытии
            self.append_message("System", f"Opening web version in browser: {web_url}")
        except Exception as e:
            self.append_message("System Error", f"Failed to open browser: {str(e)}")

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = GLMChatWindow()
    window.show()
    sys.exit(app.exec())
