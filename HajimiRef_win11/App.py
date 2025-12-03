"""
Hajimi Ref (Windows) - Main Application Entry Point
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor, Qt, QIcon
from Views.MainWindow import MainWindow

if __name__ == "__main__":
    # 程序入口 / Program entry point
    app = QApplication(sys.argv)
    
    # Set App Icon
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Modern Dark Theme
    app.setStyle("Material")
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    # Menu Stylesheet / 菜单样式表
    app.setStyleSheet("""
        QMenu {
            background-color: #353535; /* 背景颜色 */
            color: #E0E0E0;            /* 字体颜色 (偏灰一点的白，不那么刺眼) */
            border: 1px solid #000;
        }
        QMenu::item:selected {
            background-color: #2a82da; /* 选中项背景色 */
            color: #ffffff;            /* 选中项字体色 */
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
