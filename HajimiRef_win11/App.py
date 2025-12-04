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
    
    # --- 设置现代暗色主题 / Modern Dark Theme Setup ---
    # 使用 "Material" 风格，这会影响控件的基础外观 / Use "Material" style for a modern base look
    app.setStyle("Material")
    
    # 创建一个调色板对象来定制颜色 / Create a palette object for color customization
    palette = app.palette()
    
    # --- 窗口和文本颜色 / Window and Text Colors ---
    palette.setColor(QPalette.Window, QColor(53, 53, 53))       # 窗口背景色 (深灰) / Window background color (dark gray)
    palette.setColor(QPalette.WindowText, Qt.white)            # 窗口前景色 (文字) / Window foreground color (text)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))         # 输入框等控件的背景色 (更深的灰色) / Background for input widgets (darker gray)
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53)) # 列表和表格的交替行颜色 / Alternate row color for lists/tables
    palette.setColor(QPalette.ToolTipBase, Qt.white)           # 工具提示的背景色 / Tooltip background color
    palette.setColor(QPalette.ToolTipText, Qt.white)           # 工具提示的文字颜色 / Tooltip text color
    palette.setColor(QPalette.Text, Qt.white)                  # 输入框等控件的文字颜色 / Text color for input widgets
    
    # --- 按钮颜色 / Button Colors ---
    palette.setColor(QPalette.Button, QColor(53, 53, 53))      # 按钮背景色 / Button background color
    palette.setColor(QPalette.ButtonText, Qt.white)            # 按钮文字颜色 / Button text color
    
    # --- 高亮和链接颜色 / Highlight and Link Colors ---
    palette.setColor(QPalette.BrightText, Qt.red)              # 用于需要特别突出的文本 (例如，验证失败时的警告) / Bright text for emphasis (e.g., validation errors)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))       # 超链接颜色 / Hyperlink color
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))  # 选中项的背景色 (例如，列表中的选中项) / Highlight color for selected items
    palette.setColor(QPalette.HighlightedText, Qt.black)       # 选中项的文字颜色 / Text color for selected items
    
    # 应用调色板到整个应用程序 / Apply the customized palette to the entire application
    app.setPalette(palette)

    # --- 菜单样式表 / Menu Stylesheet ---
    # 使用 QSS (Qt Style Sheets) 对特定控件进行更精细的样式控制 / Use QSS for fine-grained styling of specific widgets
    app.setStyleSheet("""
        QMenu {
            background-color: #353535; /* 菜单背景颜色 (深灰) / Menu background color (dark gray) */
            color: #E0E0E0;            /* 菜单文字颜色 (灰白色) / Menu text color (off-white) */
            border: 1px solid #000;    /* 菜单边框 / Menu border */
        }
        QMenu::item:selected {
            background-color: #2a82da; /* 菜单项被选中时的背景颜色 (蓝色) / Background color for selected menu items (blue) */
            color: #ffffff;            /* 菜单项被选中时的文字颜色 (白色) / Text color for selected menu items (white) */
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
