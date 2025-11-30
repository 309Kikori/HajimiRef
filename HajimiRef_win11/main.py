import sys
import os
import json
import base64
import io
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                               QGraphicsPixmapItem, QFileDialog, QMenu, QMessageBox, QGraphicsItem)
from PySide6.QtCore import Qt, QByteArray, QBuffer, QPointF, QRectF, QEvent
from PySide6.QtGui import QPixmap, QImage, QPainter, QAction, QCursor, QTransform, QShortcut, QKeySequence
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PIL import ImageGrab

# --- Localization ---
LANGUAGES = {
    "en": {
        "title": "SimpleRef (GPU Accelerated)",
        "file": "File",
        "open_image": "Add Images",
        "save_board": "Save Board",
        "load_board": "Load Board",
        "clear_board": "Clear Board",
        "settings": "Settings",
        "language": "Language",
        "always_on_top": "Always on Top",
        "help": "Help",
        "about": "About",
        "exit": "Exit",
        "about_text": "SimpleRef (GPU)\nA GPU-accelerated reference image viewer.\n\nControls:\n- Right Click: Menu\n- Left Drag: Move Image\n- Middle Drag / Space + Left Drag: Pan Canvas\n- Wheel: Zoom Canvas\n- Ctrl + Wheel: Scale Image\n- Delete: Remove Image",
        "error": "Error",
        "save_error": "Failed to save file: {}",
        "load_error": "Failed to load file: {}",
    },
    "zh_cn": {
        "title": "SimpleRef (GPU 加速版)",
        "file": "文件",
        "open_image": "添加图片",
        "save_board": "保存看板",
        "load_board": "读取看板",
        "clear_board": "清空看板",
        "settings": "设置",
        "language": "语言",
        "always_on_top": "始终置顶",
        "help": "帮助",
        "about": "关于",
        "exit": "退出",
        "about_text": "SimpleRef (GPU)\n一个基于 GPU 加速的参考图查看器。\n\n操作说明:\n- 右键: 菜单\n- 左键拖拽: 移动图片\n- 中键拖拽 / 空格+左键: 移动画布\n- 滚轮: 缩放画布\n- Ctrl + 滚轮: 缩放选中图片\n- Delete: 删除图片",
        "error": "错误",
        "save_error": "保存文件失败: {}",
        "load_error": "读取文件失败: {}",
    }
}

class Config:
    language = "zh_cn"

def tr(key):
    return LANGUAGES.get(Config.language, LANGUAGES["en"]).get(key, key)

# --- Graphics Item ---
class RefItem(QGraphicsPixmapItem):
    def __init__(self, pixmap, data=None):
        super().__init__(pixmap)
        self.image_data = data # QByteArray or bytes
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setTransformationMode(Qt.SmoothTransformation) # High quality scaling on GPU
        self.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
        
        # Center the origin
        self.setOffset(-pixmap.width()/2, -pixmap.height()/2)

    def to_dict(self):
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
    def __init__(self, scene, parent=None):
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
        self.setBackgroundBrush(Qt.darkGray)
        
        # State
        self._is_panning = False
        self._pan_start = QPointF()
        self._space_pressed = False

    def wheelEvent(self, event):
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
        # Middle Click or Space+Left -> Pan
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and self._space_pressed):
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
            
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
            
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self._space_pressed = True
            if not self._is_panning:
                self.setCursor(Qt.OpenHandCursor)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space:
            self._space_pressed = False
            if not self._is_panning:
                self.setCursor(Qt.ArrowCursor)
        super().keyReleaseEvent(event)

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
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

    def change_language(self, lang):
        Config.language = lang
        self.setWindowTitle(tr("title"))
        # Rebuild menu is complex in Qt dynamic, simpler to just restart or update texts.
        # For simplicity, we just update title and let user restart or re-open menus.
        # A full reload would require clearing menuBar and calling setup_menu again.
        self.menuBar().clear()
        self.setup_menu()

    def toggle_always_on_top(self):
        if self.act_top.isChecked():
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def show_about(self):
        QMessageBox.information(self, tr("about"), tr("about_text"))

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction(tr("open_image"), self.add_images)
        menu.addSeparator()
        menu.addAction(tr("save_board"), self.save_board)
        menu.addAction(tr("load_board"), self.load_board)
        menu.exec(self.view.mapToGlobal(pos))

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, tr("open_image"), "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if files:
            center = self.view.mapToScene(self.view.viewport().rect().center())
            offset = 0
            for f in files:
                self.load_image_file(f, center.x() + offset, center.y() + offset)
                offset += 20

    def load_image_file(self, path, x, y):
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.create_item_from_data(data, x, y)
        except Exception as e:
            print(f"Error loading {path}: {e}")

    def create_item_from_data(self, data, x, y, scale=1.0):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            item = RefItem(pixmap, data)
            item.setPos(x, y)
            item.setScale(scale)
            self.scene.addItem(item)
        else:
            print("Failed to load pixmap from data")

    def delete_selected(self):
        for item in self.scene.selectedItems():
            self.scene.removeItem(item)

    def paste_image(self):
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
        self.scene.clear()

    def save_board(self):
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
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
