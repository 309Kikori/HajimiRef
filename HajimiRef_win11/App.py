"""
Hajimi Ref (Windows) - Main Application Entry Point
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor, Qt, QIcon
from PySide6.QtCore import QSize
from Views.MainWindow import MainWindow
from Config import Config
from Models.ColorDepthManager import ColorDepthManager, ColorDepthMode

if __name__ == "__main__":
    # 程序入口 / Program entry point
    
    # ── 自适应色深：必须在 QApplication 创建之前配置 OpenGL Surface Format ──
    # Adaptive color depth: MUST configure OpenGL Surface Format BEFORE QApplication creation
    Config.load()  # 先加载配置，获取色深模式 / Load config first to get color depth mode
    
    color_depth_mgr = ColorDepthManager(
        ColorDepthManager.get_mode_from_string(Config.color_depth_mode)
    )
    # 亚克力模式需要 ≥ 8bit alpha 通道以支持 DWM 透明穿透
    # Acrylic mode needs ≥ 8bit alpha for DWM transparent passthrough
    surface_fmt = color_depth_mgr.configure_surface_format(need_alpha=Config.acrylic_enabled)
    ColorDepthManager.apply_surface_format(surface_fmt)
    
    app = QApplication(sys.argv)
    
    # 将色深管理器挂载到 app 上，供全局访问 / Attach color depth manager to app for global access
    app.color_depth_manager = color_depth_mgr
    
    # Set App Icon    
    # Set App Icon - 为不同尺寸添加图标，确保任务栏显示正常
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.exists(icon_path):
        icon = QIcon()
        # 添加多个尺寸，让 Windows 任务栏能正确显示
        for size in [16, 24, 32, 48, 64, 128, 256]:
            icon.addFile(icon_path, QSize(size, size))
        app.setWindowIcon(icon)
    
    # --- 设置现代暗色主题 / Modern Dark Theme Setup ---
    # 使用 "Material" 风格，这会影响控件的基础外观 / Use "Material" style for a modern base look
    app.setStyle("Material")
    
    # 创建一个调色板对象来定制颜色 / Create a palette object for color customization
    palette = app.palette()
    
    # --- 窗口和文本颜色 / Window and Text Colors ---
    # 亚克力模式：QPalette.Window 使用与 QSS 一致的 alpha 值，
    # 防止 palette 在未被 QSS 覆盖的边缘区域绘制不透明底色造成黑边
    # 非亚克力模式：使用不透明底色
    window_alpha = Config.bg_opacity if Config.acrylic_enabled else 255
    palette.setColor(QPalette.Window, QColor(53, 53, 53, window_alpha))  # 窗口背景色 / Window background color
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
            background-color: #2d2d2d;
            color: #E0E0E0;
            border: 1px solid #404040;
            border-radius: 6px;
            padding: 4px 0px;
        }
        QMenu::item {
            padding: 6px 28px 6px 20px;
            border-radius: 4px;
            margin: 2px 4px;
        }
        QMenu::item:selected {
            background-color: rgba(255, 255, 255, 0.1);
            color: #ffffff;
        }
        QMenu::separator {
            height: 1px;
            background: #404040;
            margin: 4px 8px;
        }
        QMenuBar {
            background: transparent;
        }
    """)

    window = MainWindow()
    window.show()
    # 窗口显示后立即应用 Win11 特效（需要窗口句柄已创建）
    window.apply_win11_effects()
    sys.exit(app.exec())
