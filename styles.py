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
