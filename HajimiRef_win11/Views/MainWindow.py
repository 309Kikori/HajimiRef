import sys
import os
import json
import base64
from PySide6.QtWidgets import (QMainWindow, QGraphicsScene, QFileDialog, QMenu, QMessageBox, QApplication)
from PySide6.QtCore import Qt, QByteArray, QBuffer
from PySide6.QtGui import QPixmap, QAction, QShortcut, QKeySequence
from Config import Config, tr
from Views.Canvas import RefItem, RefView
from Views.SettingsDialog import SettingsDialog
from ViewModels.MainViewModel import MainViewModel

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
        
        self.vm = MainViewModel()
        
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
        
        help_menu = menubar.addMenu(tr("help"))
        act_about = QAction(tr("about"), self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)

        # Context Menu
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)

    def show_settings(self):
        """
        显示设置对话框 / Show settings dialog
        """
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
        data = self.vm.read_image_file(path)
        if data:
            self.create_item_from_data(data, x, y)

    def create_item_from_image(self, image, x, y):
        """
        从 QImage 创建图片项 / Create image item from QImage
        """
        if not image.isNull():
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QBuffer.WriteOnly)
            image.save(buf, "PNG")
            data = ba.data()
            self.create_item_from_data(data, x, y)

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
        
        success, error = self.vm.save_board_data(path, items_data)
        if not success:
            QMessageBox.critical(self, tr("error"), tr("save_error").format(error))

    def load_board(self):
        """
        从文件加载看板 / Load board from file
        """
        path, _ = QFileDialog.getOpenFileName(self, tr("load_board"), "", "SimpleRef Board (*.sref);;JSON (*.json)")
        if not path:
            return
            
        success, result = self.vm.load_board_data(path)
        
        if success:
            self.clear_board()
            for img_data in result:
                self.create_item_from_data(
                    img_data["data"], 
                    img_data["x"], 
                    img_data["y"],
                    img_data["scale"]
                )
        else:
            QMessageBox.critical(self, tr("error"), tr("load_error").format(result))
