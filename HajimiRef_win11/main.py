'''
Author: Xhinonome
Date: 2025-12-01 11:46:20
LastEditors: shiragawayoren
LastEditTime: 2025-12-01 17:48:07
Description: Description
hajimi 
'''
import sys
import os
import json
import base64
import io
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                               QGraphicsPixmapItem, QFileDialog, QMenu, QMessageBox, QGraphicsItem,
                               QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QColorDialog, QSpinBox, QCheckBox)
from PySide6.QtCore import Qt, QByteArray, QBuffer, QPointF, QRectF, QEvent
from PySide6.QtGui import QPixmap, QImage, QPainter, QAction, QCursor, QTransform, QShortcut, QKeySequence, QColor, QPen, QPalette
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PIL import ImageGrab
from localization import LANGUAGES

class Config:
    # 配置类 / Configuration class
    language = "zh_cn"
    bg_color = QColor(40, 40, 40)
    grid_color = QColor(60, 60, 60)
    grid_size = 40
    grid_enabled = True

def tr(key):
    # 翻译函数 / Translation function
    return LANGUAGES.get(Config.language, LANGUAGES["en"]).get(key, key)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("preferences"))
        self.resize(300, 250)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Background Color
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel(tr("bg_color")))
        self.btn_bg_color = QPushButton()
        self.btn_bg_color.setFixedSize(50, 25)
        self.update_color_btn(self.btn_bg_color, Config.bg_color)
        self.btn_bg_color.clicked.connect(self.pick_bg_color)
        bg_layout.addWidget(self.btn_bg_color)
        layout.addLayout(bg_layout)

        # Grid Color
        grid_c_layout = QHBoxLayout()
        grid_c_layout.addWidget(QLabel(tr("grid_color")))
        self.btn_grid_color = QPushButton()
        self.btn_grid_color.setFixedSize(50, 25)
        self.update_color_btn(self.btn_grid_color, Config.grid_color)
        self.btn_grid_color.clicked.connect(self.pick_grid_color)
        grid_c_layout.addWidget(self.btn_grid_color)
        layout.addLayout(grid_c_layout)

        # Grid Size
        grid_s_layout = QHBoxLayout()
        grid_s_layout.addWidget(QLabel(tr("grid_size")))
        self.spin_grid_size = QSpinBox()
        self.spin_grid_size.setRange(10, 200)
        self.spin_grid_size.setValue(Config.grid_size)
        self.spin_grid_size.valueChanged.connect(self.set_grid_size)
        grid_s_layout.addWidget(self.spin_grid_size)
        layout.addLayout(grid_s_layout)

        # Show Grid
        self.chk_grid = QCheckBox(tr("show_grid"))
        self.chk_grid.setChecked(Config.grid_enabled)
        self.chk_grid.toggled.connect(self.set_grid_enabled)
        layout.addWidget(self.chk_grid)

        layout.addStretch()
        
        btn_ok = QPushButton(tr("ok"))
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)

    def update_color_btn(self, btn, color):
        btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555;")

    def pick_bg_color(self):
        color = QColorDialog.getColor(Config.bg_color, self, tr("pick_color"))
        if color.isValid():
            Config.bg_color = color
            self.update_color_btn(self.btn_bg_color, color)
            self.parent().view.viewport().update()

    def pick_grid_color(self):
        color = QColorDialog.getColor(Config.grid_color, self, tr("pick_color"))
        if color.isValid():
            Config.grid_color = color
            self.update_color_btn(self.btn_grid_color, color)
            self.parent().view.viewport().update()

    def set_grid_size(self, val):
        Config.grid_size = val
        self.parent().view.viewport().update()

    def set_grid_enabled(self, val):
        Config.grid_enabled = val
        self.parent().view.viewport().update()

# --- Graphics Item ---
class RefItem(QGraphicsPixmapItem):
    """
    自定义图形项，用于显示图片 / Custom graphics item for displaying images
    """
    def __init__(self, pixmap, data=None):
        """
        初始化图片项，设置标志和变换模式 / Initialize image item, set flags and transformation mode
        """
        super().__init__(pixmap)
        self.image_data = data # QByteArray or bytes
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setTransformationMode(Qt.SmoothTransformation) # High quality scaling on GPU
        self.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
        
        # Center the origin
        self.setOffset(-pixmap.width()/2, -pixmap.height()/2)

    def to_dict(self):
        """
        将图片信息序列化为字典，用于保存 / Serialize image info to dict for saving
        """
        pos = self.scenePos()
        # Convert bytes/QByteArray to base64 string
        if isinstance(self.image_data, QByteArray):
            b64_data = self.image_data.toBase64().data().decode('utf-8')
        else:
            b64_data = base64.b64encode(self.image_data).decode('utf-8')

        return {
            "x": pos.x(),
            "y": pos.y(),
            "scale": self.scale(),
            "rotation": self.rotation(),
            "data": b64_data
        }

# --- Graphics View ---
class RefView(QGraphicsView):
    """
    自定义图形视图，支持 GPU 加速和交互 / Custom graphics view, supports GPU acceleration and interaction
    """
    def __init__(self, scene, parent=None):
        """
        初始化视图，启用 OpenGL，设置渲染提示和交互模式 / Initialize view, enable OpenGL, set render hints and interaction modes
        """
        super().__init__(scene, parent)
        
        # Enable GPU Acceleration
        self.setViewport(QOpenGLWidget())
        
        # Render Hints
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.TextAntialiasing)
        
        # Viewport behavior
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)
        
        # Background
        # self.setBackgroundBrush(Qt.darkGray) # Handled in drawBackground
        
        # State
        self._is_panning = False
        self._pan_start = QPointF()
        self._space_pressed = False

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, Config.bg_color)
        
        if Config.grid_enabled:
            grid_size = Config.grid_size
            # Calculate start points to align with the grid
            left = int(rect.left()) - (int(rect.left()) % grid_size)
            top = int(rect.top()) - (int(rect.top()) % grid_size)
            
            points = []
            # Draw dots
            for x in range(left, int(rect.right()) + grid_size, grid_size):
                for y in range(top, int(rect.bottom()) + grid_size, grid_size):
                    points.append(QPointF(x, y))
            
            painter.setPen(QPen(Config.grid_color, 2))
            painter.drawPoints(points)

    def wheelEvent(self, event):
        """
        处理滚轮事件，用于缩放画布或图片 / Handle wheel event for zooming canvas or scaling image
        """
        # Ctrl + Wheel -> Scale Item
        if event.modifiers() & Qt.ControlModifier:
            items = self.scene().selectedItems()
            if items:
                factor = 1.1 if event.angleDelta().y() > 0 else 0.9
                for item in items:
                    item.setScale(item.scale() * factor)
            return

        # Wheel -> Zoom Canvas
        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event):
        """
        处理鼠标按下事件，用于平移 / Handle mouse press for panning
        """
        # Middle Click or Space+Left -> Pan
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and self._space_pressed):
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
            
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        处理鼠标移动事件，用于平移 / Handle mouse move for panning
        """
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            
            # Map delta to scene coords to pan correctly regardless of zoom
            # Actually scroll is simpler:
            hs = self.horizontalScrollBar()
            vs = self.verticalScrollBar()
            hs.setValue(hs.value() - delta.x())
            vs.setValue(vs.value() - delta.y())
            event.accept()
            return
            
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        处理鼠标释放事件 / Handle mouse release
        """
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
            
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """
        处理按键按下事件 (空格键平移) / Handle key press (Space for panning)
        """
        if event.key() == Qt.Key_Space:
            self._space_pressed = True
            if not self._is_panning:
                self.setCursor(Qt.OpenHandCursor)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """
        处理按键释放事件 / Handle key release
        """
        if event.key() == Qt.Key_Space:
            self._space_pressed = False
            if not self._is_panning:
                self.setCursor(Qt.ArrowCursor)
        super().keyReleaseEvent(event)

# --- Main Window ---
class MainWindow(QMainWindow):
    """
    主窗口类 / Main window class
    """
    def __init__(self):
        """
        初始化主窗口，设置场景、视图、菜单和快捷键 / Initialize main window, set scene, view, menu and shortcuts
        """
        super().__init__()
        self.setWindowTitle(tr("title"))
        self.resize(1024, 768)
        
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-50000, -50000, 100000, 100000) # Infinite-ish canvas
        
        self.view = RefView(self.scene, self)
        self.setCentralWidget(self.view)
        
        self.setup_menu()
        
        # Shortcuts
        self.del_shortcut = QShortcut(QKeySequence.Delete, self)
        self.del_shortcut.activated.connect(self.delete_selected)
        
        self.paste_shortcut = QShortcut(QKeySequence.Paste, self)
        self.paste_shortcut.activated.connect(self.paste_image)

    def setup_menu(self):
        """
        设置菜单栏 / Setup menu bar
        """
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu(tr("file"))
        
        act_add = QAction(tr("open_image"), self)
        act_add.triggered.connect(self.add_images)
        file_menu.addAction(act_add)
        
        file_menu.addSeparator()
        
        act_save = QAction(tr("save_board"), self)
        act_save.triggered.connect(self.save_board)
        file_menu.addAction(act_save)
        
        act_load = QAction(tr("load_board"), self)
        act_load.triggered.connect(self.load_board)
        file_menu.addAction(act_load)
        
        act_clear = QAction(tr("clear_board"), self)
        act_clear.triggered.connect(self.clear_board)
        file_menu.addAction(act_clear)
        
        file_menu.addSeparator()
        
        act_exit = QAction(tr("exit"), self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)
        
        settings_menu = menubar.addMenu(tr("settings"))

        act_prefs = QAction(tr("preferences"), self)
        act_prefs.triggered.connect(self.show_settings)
        settings_menu.addAction(act_prefs)
        
        settings_menu.addSeparator()
        
        self.act_top = QAction(tr("always_on_top"), self)
        self.act_top.setCheckable(True)
        self.act_top.triggered.connect(self.toggle_always_on_top)
        settings_menu.addAction(self.act_top)
        
        lang_menu = settings_menu.addMenu(tr("language"))
        act_en = QAction("English", self)
        act_en.triggered.connect(lambda: self.change_language("en"))
        lang_menu.addAction(act_en)
        
        act_zh = QAction("中文", self)
        act_zh.triggered.connect(lambda: self.change_language("zh_cn"))
        lang_menu.addAction(act_zh)
        
        help_menu = menubar.addMenu(tr("help"))
        act_about = QAction(tr("about"), self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)

        # Context Menu
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)

    def show_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def change_language(self, lang):
        """
        切换语言 / Change language
        """
        Config.language = lang
        self.setWindowTitle(tr("title"))
        # Rebuild menu is complex in Qt dynamic, simpler to just restart or update texts.
        # For simplicity, we just update title and let user restart or re-open menus.
        # A full reload would require clearing menuBar and calling setup_menu again.
        self.menuBar().clear()
        self.setup_menu()

    def toggle_always_on_top(self):
        """
        切换窗口置顶状态 / Toggle always on top
        """
        if self.act_top.isChecked():
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def show_about(self):
        """
        显示关于对话框 / Show about dialog
        """
        QMessageBox.information(self, tr("about"), tr("about_text"))

    def show_context_menu(self, pos):
        """
        显示右键菜单 / Show context menu
        """
        menu = QMenu(self)
        menu.addAction(tr("open_image"), self.add_images)
        menu.addSeparator()
        menu.addAction(tr("save_board"), self.save_board)
        menu.addAction(tr("load_board"), self.load_board)
        menu.exec(self.view.mapToGlobal(pos))

    def add_images(self):
        """
        打开文件对话框添加图片 / Open file dialog to add images
        """
        files, _ = QFileDialog.getOpenFileNames(self, tr("open_image"), "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if files:
            center = self.view.mapToScene(self.view.viewport().rect().center())
            offset = 0
            for f in files:
                self.load_image_file(f, center.x() + offset, center.y() + offset)
                offset += 20

    def load_image_file(self, path, x, y):
        """
        从文件路径加载图片 / Load image from file path
        """
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.create_item_from_data(data, x, y)
        except Exception as e:
            print(f"Error loading {path}: {e}")

    def create_item_from_data(self, data, x, y, scale=1.0):
        """
        从二进制数据创建图片项 / Create image item from binary data
        """
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            item = RefItem(pixmap, data)
            item.setPos(x, y)
            item.setScale(scale)
            self.scene.addItem(item)
        else:
            print("Failed to load pixmap from data")

    def delete_selected(self):
        """
        删除选中的图片 / Delete selected images
        """
        for item in self.scene.selectedItems():
            self.scene.removeItem(item)

    def paste_image(self):
        """
        从剪贴板粘贴图片 / Paste image from clipboard
        """
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        center = self.view.mapToScene(self.view.viewport().rect().center())

        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                # Convert QImage to bytes (PNG)
                ba = QByteArray()
                buf = QBuffer(ba)
                buf.open(QBuffer.WriteOnly)
                image.save(buf, "PNG")
                data = ba.data()
                
                self.create_item_from_data(data, center.x(), center.y())
        elif mime_data.hasUrls():
            offset = 0
            for url in mime_data.urls():
                if url.isLocalFile():
                    self.load_image_file(url.toLocalFile(), center.x() + offset, center.y() + offset)
                    offset += 20
        elif mime_data.hasText():
            # Try to parse paths from text
            text = mime_data.text()
            lines = text.split('\n')
            offset = 0
            for line in lines:
                path = line.strip().strip('"')
                if os.path.exists(path) and os.path.isfile(path):
                    self.load_image_file(path, center.x() + offset, center.y() + offset)
                    offset += 20

    def clear_board(self):
        """
        清空画布 / Clear board
        """
        self.scene.clear()

    def save_board(self):
        """
        保存看板到文件 / Save board to file
        """
        path, _ = QFileDialog.getSaveFileName(self, tr("save_board"), "", "SimpleRef Board (*.sref);;JSON (*.json)")
        if not path:
            return
            
        items_data = []
        for item in self.scene.items():
            if isinstance(item, RefItem):
                items_data.append(item.to_dict())
        
        data = {
            "version": 2,
            "images": items_data
        }
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            QMessageBox.critical(self, tr("error"), tr("save_error").format(e))

    def load_board(self):
        """
        从文件加载看板 / Load board from file
        """
        path, _ = QFileDialog.getOpenFileName(self, tr("load_board"), "", "SimpleRef Board (*.sref);;JSON (*.json)")
        if not path:
            return
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.clear_board()
            
            for img_data in data.get("images", []):
                b64_data = img_data.get("data")
                if b64_data:
                    img_bytes = base64.b64decode(b64_data)
                    self.create_item_from_data(
                        img_bytes, 
                        img_data.get("x", 0), 
                        img_data.get("y", 0),
                        img_data.get("scale", 1.0)
                    )
                    
        except Exception as e:
            QMessageBox.critical(self, tr("error"), tr("load_error").format(e))

if __name__ == "__main__":
    # 程序入口 / Program entry point
    app = QApplication(sys.argv)
    
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
    # 您可以在这里修改菜单的字体颜色 (color) 和背景颜色 (background-color)
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
