import sys
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLineEdit, 
                             QPushButton, QHBoxLayout, QCheckBox, QLabel, QScrollArea, QSlider)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
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
        layout.setSpacing(15)

        # --- Блок настроек (виджет с рамкой) ---
        settings_group = QWidget()
        settings_group.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333; border-radius: 8px;")
        settings_layout = QVBoxLayout(settings_group)
        
        # 1. Enable Thinking + Description
        thinking_layout = QVBoxLayout()
        self.cb_thinking = QCheckBox("Enable Thinking")
        self.cb_thinking.setChecked(True)
        self.cb_thinking.setStyleSheet("QCheckBox { color: #8888ff; font-weight: bold; font-size: 16px; border: none; }")
        
        thinking_desc = QLabel(
            "Enabled: Activates the model's thinking capability. The model will decide whether to think based on the situation.\n"
            "Disabled: Disables the model's thinking capability. The model will answer questions directly without reasoning."
        )
        thinking_desc.setWordWrap(True)
        thinking_desc.setStyleSheet("color: #ff4444; font-size: 11px; border: none; margin-top: 5px;")
        
        thinking_layout.addWidget(self.cb_thinking)
        thinking_layout.addWidget(thinking_desc)
        settings_layout.addLayout(thinking_layout)

        # 2. Temperature Slider
        temp_header = QHBoxLayout()
        temp_label = QLabel("Temperature")
        temp_label.setStyleSheet("color: #ffffff; background-color: #bbbbff; color: #4444ff; padding: 2px 10px; border-radius: 4px; border: none;")
        self.temp_value_label = QLabel("0.4")
        self.temp_value_label.setStyleSheet("color: #888; border: none; font-family: monospace;")
        temp_header.addWidget(temp_label)
        temp_header.addStretch()
        temp_header.addWidget(self.temp_value_label)
        settings_layout.addLayout(temp_header)

        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 100)
        self.temp_slider.setValue(40)
        self.temp_slider.setStyleSheet("""
            QSlider::handle:horizontal { background: #5555ff; width: 18px; border-radius: 9px; }
            QSlider::groove:horizontal { background: #333; height: 8px; border-radius: 4px; }
        """)
        self.temp_slider.valueChanged.connect(lambda v: self.temp_value_label.setText(f"{v/100:.1f}"))
        settings_layout.addWidget(self.temp_slider)

        # 3. System Prompt
        sys_label = QLabel("System Prompt")
        sys_label.setStyleSheet("color: #ffffff; background-color: #bbbbff; color: #4444ff; padding: 2px 10px; border-radius: 4px; border: none;")
        settings_layout.addWidget(sys_label)
        
        self.sys_prompt_input = QTextEdit()
        self.sys_prompt_input.setPlaceholderText("Enter system instructions here...")
        self.sys_prompt_input.setFixedHeight(80)
        self.sys_prompt_input.setStyleSheet("background-color: #121212; border: 1px solid #333; color: #ccc; border-radius: 5px;")
        settings_layout.addWidget(self.sys_prompt_input)

        layout.addWidget(settings_group)

        # Область чата
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333; color: #d4d4d4; font-size: 14px; border-radius: 8px;")
        layout.addWidget(self.chat_display)

        # Поле ввода и кнопки
        bottom_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.returnPressed.connect(self.send_message)
        self.input_field.setStyleSheet("background-color: #2d2d2d; color: white; padding: 10px; border-radius: 5px;")
        
        self.btn_send = QPushButton("Send")
        self.btn_send.clicked.connect(self.send_message)
        self.btn_send.setStyleSheet("background-color: #0078d4; color: white; padding: 10px 25px; border-radius: 5px; font-weight: bold;")
        
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset_chat)
        self.btn_reset.setStyleSheet("background-color: #441111; color: white; padding: 10px 15px; border-radius: 5px;")

        bottom_layout.addWidget(self.input_field)
        bottom_layout.addWidget(self.btn_send)
        bottom_layout.addWidget(self.btn_reset)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)
        self.setStyleSheet("background-color: #121212; color: #ffffff;")

    def append_message(self, role, text):
        color = "#569cd6" if role == "User" else "#ce9178"
        self.chat_display.append(f"<b style='color: {color};'>{role}:</b> {text}<br>")

    def send_message(self):
        text = self.input_field.text().strip()
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
        if is_loading:
            self.setWindowTitle("GLM-4.5 Air - Special Chat (Thinking...)")
        else:
            self.setWindowTitle("GLM-4.5 Air - Special Chat")

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

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = GLMChatWindow()
    window.show()
    sys.exit(app.exec())
