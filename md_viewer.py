from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import Qt
import markdown2

class MarkdownViewer(QDialog):
    def __init__(self, model_name, content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Response Preview - {model_name}")
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Виджет для отображения отрендеренного HTML
        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setStyleSheet("background-color: #ffffff; color: #000000; padding: 10px;")
        
        # Конвертация Markdown в HTML
        try:
            # Используем экстра-фичи для лучшего рендеринга таблиц и списков
            html_content = markdown2.markdown(content, extras=["fenced-code-blocks", "tables", "break-on-newline"])
            
            # Добавляем базовые стили CSS для красоты
            styled_html = f"""
            <html>
            <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
                code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 4px; font-family: Consolas, monospace; }}
                pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 5px; border: 1px solid #ddd; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                blockquote {{ border-left: 5px solid #ccc; margin: 1.5em 10px; padding: 0.5em 10px; color: #666; font-style: italic; }}
            </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            self.viewer.setHtml(styled_html)
        except Exception as e:
            self.viewer.setPlainText(f"Error rendering Markdown: {e}\n\nOriginal text:\n{content}")
            
        layout.addWidget(self.viewer)
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet("background-color: #0078d4; color: white; padding: 8px; font-weight: bold;")
        layout.addWidget(btn_close)
