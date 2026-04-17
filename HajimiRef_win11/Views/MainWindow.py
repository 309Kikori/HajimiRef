import sys
import os
import json
import base64
import math
import ctypes

from PySide6.QtCore import Qt, QByteArray, QBuffer, QRectF, QPointF, QTimer, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtWidgets import (QMainWindow, QGraphicsScene, QFileDialog, QMenu, QMessageBox, QApplication,
                                QToolButton, QWidget, QHBoxLayout, QSizePolicy, QDialog, QVBoxLayout, QLabel,
                                QGraphicsDropShadowEffect)
from PySide6.QtGui import QPixmap, QAction, QShortcut, QKeySequence, QImage, QPainter, QColor, QFont
from Config import Config, tr
from Views.Canvas import RefItem, RefView, GroupItem, GroupSettingsDialog
from Views.SettingsDialog import SettingsDialog
from ViewModels.MainViewModel import MainViewModel
from Models.UndoManager import UndoManager, MoveCommand, ScaleCommand, AddItemCommand, DeleteItemsCommand, ClearBoardCommand, OrganizeItemsCommand, GroupCommand, UngroupCommand, GroupMoveCommand
from Models.ColorDepthManager import ColorDepthManager, ColorDepthMode


class AboutDialog(QDialog):
    """
    关于对话框 / About dialog - 复刻macOS版本设计
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("about"))
        self.setFixedSize(350, 620)  # macOS版本宽度350
        self.setup_ui()
        
    def setup_ui(self):
        """
        设置UI / Setup UI - 严格按照macOS版本设计
        """
        # 主布局，整体spacing=20（对应SwiftUI的VStack(spacing: 20)）
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 1. Logo 图片区域 - 128x128，带阴影效果
        logo_label = QLabel()
        logo_pixmap = self.load_logo()
        if logo_pixmap:
            # 使用高质量缩放
            scaled_pixmap = logo_pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setText("🖼️")
            logo_label.setStyleSheet("font-size: 128px;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 添加阴影效果（对应SwiftUI的.shadow(color: .primary.opacity(0.2), radius: 10, y: 4)）
        logo_label.setStyleSheet("""
            QLabel {
                background: transparent;
            }
        """)
        # 使用QGraphicsDropShadowEffect添加阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 50))  # opacity 0.2
        shadow.setOffset(0, 4)  # y: 4
        logo_label.setGraphicsEffect(shadow)
        layout.addWidget(logo_label)
        
        # 2. 文本信息区域容器（对应SwiftUI的VStack(spacing: 8)）
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # 应用中文名称 - 24px bold（对应.font(.system(size: 24, weight: .bold))）
        title_cn = QLabel("哈基米 参考")
        title_cn.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
        title_cn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(title_cn)
        
        # 应用英文名称 - 16px bold（对应.font(.system(size: 16, weight: .bold))）
        title_en = QLabel("Hajimi Ref")
        title_en.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_en.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(title_en)
        
        # 版本号信息 - subheadline字体，secondary颜色
        version_label = QLabel("Version 0.0.2 (Windows GPU)")
        version_label.setStyleSheet("color: #666; font-size: 11px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(version_label)
        
        # 软件描述文案 - body字体，居中对齐，水平padding
        desc_label = QLabel("传奇神人与圆头耄耋的设计图像参考软件")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("font-size: 13px; padding: 0 20px;")
        info_layout.addWidget(desc_label)
        
        # Meme 图片区域 - 高度150，圆角8px，垂直padding 5
        meme_label = QLabel()
        meme_pixmap = self.load_meme()
        if meme_pixmap:
            # 保持比例，高度150，圆角8px
            scaled_meme = meme_pixmap.scaledToHeight(150, Qt.TransformationMode.SmoothTransformation)
            meme_label.setPixmap(scaled_meme)
            meme_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            meme_label.setStyleSheet("border-radius: 8px; padding: 5px 0;")
            info_layout.addWidget(meme_label)
        
        # 技术栈标识 - 玻璃效果徽章
        # HStack布局，橙色图标 + 文字
        # padding: horizontal 12, vertical 6
        # 玻璃效果，橙色半透明tint
        # capsule形状
        # 顶部padding 5
        tech_frame = QWidget()
        tech_frame.setFixedHeight(32)
        tech_frame.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 165, 0, 51);
                border-radius: 16px;
                border: 1px solid rgba(255, 165, 0, 76);
            }
        """)
        tech_layout = QHBoxLayout(tech_frame)
        tech_layout.setContentsMargins(12, 6, 12, 6)
        tech_layout.setSpacing(5)
        
        # Swift图标对应的emoji（macOS用的是systemName: "swift"）
        tech_icon = QLabel("🚀")
        tech_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        tech_layout.addWidget(tech_icon)
        
        tech_text = QLabel("Built with PySide6 & GPU Acceleration")
        tech_text.setStyleSheet("color: #666; font-size: 11px; background: transparent; border: none;")
        tech_layout.addWidget(tech_text)
        tech_layout.addStretch()
        
        # 添加顶部padding 5（对应SwiftUI的.padding(.top, 5)）
        info_layout.addSpacing(5)
        info_layout.addWidget(tech_frame)
        
        layout.addWidget(info_widget)
        
        # 分割线 - 对应SwiftUI的Divider()
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #d0d0d0;")
        layout.addWidget(line)
        
        # 3. 底部版权信息 - caption字体，secondary颜色
        copyright_label = QLabel("Copyright © 2025 Xhinonome. All rights reserved.")
        copyright_label.setStyleSheet("color: #666; font-size: 10px;")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright_label)
        
    def load_logo(self):
        """
        加载Logo图片 / Load logo image
        """
        # 优先使用icon目录下的原始高清图标 (1024x1024)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "icon", "Appicon-macOS-Default-1024x1024@1x.png")
        if os.path.exists(icon_path):
            return QPixmap(icon_path)
        
        # 备用：使用assets目录下的图标
        fallback_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.png")
        if os.path.exists(fallback_path):
            return QPixmap(fallback_path)
        return None
    
    def load_meme(self):
        """
        加载Meme图片 / Load meme image
        """
        # 加载Meme图片（从macOS项目复制过来的）
        meme_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "Meme.PNG")
        if os.path.exists(meme_path):
            return QPixmap(meme_path)
        return None


class MainWindow(QMainWindow):
    """
    主窗口类 / Main window class
    """
    def __init__(self):
        """
        初始化主窗口，设置场景、视图、菜单和快捷键 / Initialize main window, set scene, view, menu and shortcuts
        """
        super().__init__()
        self.setWindowTitle("HajimiRef") # 设置主窗口标题 / Set main window title
        self.resize(1024, 768)
        
        self.vm = MainViewModel()
        
        # 撤销/重做管理器 / Undo/Redo manager
        self.undo_manager = UndoManager(max_history=100)
        
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-50000, -50000, 100000, 100000) # Infinite-ish canvas
        
        self.view = RefView(self.scene, self)
        self.setCentralWidget(self.view)
        
        # 组管理 / Group management
        self.groups = {}  # group_id -> GroupItem
        
        self.setup_menu()
        
        # Shortcuts
        self.del_shortcut = QShortcut(QKeySequence.Delete, self)
        self.del_shortcut.activated.connect(self.delete_selected)
        
        self.paste_shortcut = QShortcut(QKeySequence.Paste, self)
        self.paste_shortcut.activated.connect(self.paste_image)
        
        # Ctrl+C 复制选中图片快捷键 / Ctrl+C copy selected images shortcut
        self.copy_shortcut = QShortcut(QKeySequence.Copy, self)
        self.copy_shortcut.activated.connect(self.copy_selected_items)
        
        # 应用内剪贴板：直接索引，零编解码 / In-app clipboard: direct reference, zero encoding
        self._copied_items = []
        
        # G键打组快捷键 / G key grouping shortcut
        self.group_shortcut = QShortcut(QKeySequence("G"), self)
        self.group_shortcut.activated.connect(self.group_selected_items)
        
        # 注意：撤销/重做快捷键已通过菜单栏 QAction 的 setShortcut 设置
        # 不再需要额外的 QShortcut，否则会导致 "Ambiguous shortcut overload" 冲突
        
        # Auto reset board timer
        self.auto_reset_timer = QTimer(self)
        self.auto_reset_timer.timeout.connect(self.auto_reset_board)
        self.update_auto_reset_timer()

        # 应用 Win11 窗口特效（透明度 / 亚克力）
        self.apply_win11_effects()

    def setup_menu(self):
        """
        设置可折叠汉堡菜单栏 / Setup collapsible hamburger menu bar
        """
        # 隐藏原生菜单栏 / Hide native menu bar
        self.menuBar().hide()

        # --- 构建菜单数据（QMenu 对象）/ Build menu data (QMenu objects) ---
        self._file_menu = QMenu(tr("file"), self)
        act_add = QAction(tr("open_image"), self)
        act_add.triggered.connect(self.add_images)
        self._file_menu.addAction(act_add)
        self._file_menu.addSeparator()
        act_save = QAction(tr("save_board"), self)
        act_save.triggered.connect(self.save_board)
        self._file_menu.addAction(act_save)
        act_load = QAction(tr("load_board"), self)
        act_load.triggered.connect(self.load_board)
        self._file_menu.addAction(act_load)
        self._file_menu.addSeparator()
        act_export = QAction(tr("export_image"), self)
        act_export.triggered.connect(self.export_board_to_image)
        self._file_menu.addAction(act_export)
        act_export_clipboard = QAction(tr("export_to_clipboard"), self)
        act_export_clipboard.triggered.connect(self.export_board_to_clipboard)
        self._file_menu.addAction(act_export_clipboard)
        self._file_menu.addSeparator()
        act_clear = QAction(tr("clear_board"), self)
        act_clear.triggered.connect(self.clear_board)
        self._file_menu.addAction(act_clear)
        self._file_menu.addSeparator()
        act_exit = QAction(tr("exit"), self)
        act_exit.triggered.connect(self.close)
        self._file_menu.addAction(act_exit)

        self._settings_menu = QMenu(tr("settings"), self)
        act_prefs = QAction(tr("preferences"), self)
        act_prefs.triggered.connect(self.show_settings)
        self._settings_menu.addAction(act_prefs)
        self._settings_menu.addSeparator()
        self.act_top = QAction(tr("always_on_top"), self)
        self.act_top.setCheckable(True)
        self.act_top.triggered.connect(self.toggle_always_on_top)
        self._settings_menu.addAction(self.act_top)

        self._edit_menu = QMenu(tr("edit"), self)
        self.act_undo = QAction(tr("undo"), self)
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_undo.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.act_undo.triggered.connect(self.undo_action)
        self._edit_menu.addAction(self.act_undo)
        self.act_redo = QAction(tr("redo"), self)
        self.act_redo.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        self.act_redo.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.act_redo.triggered.connect(self.redo_action)
        self._edit_menu.addAction(self.act_redo)

        self._help_menu = QMenu(tr("help"), self)
        act_about = QAction(tr("about"), self)
        act_about.triggered.connect(self.show_about)
        self._help_menu.addAction(act_about)

        # 确保快捷键即使菜单隐藏也能工作 / Ensure shortcuts work even when menu is hidden
        self.addAction(self.act_undo)
        self.addAction(self.act_redo)

        # --- 浮动汉堡菜单（叠在画布上方，不占布局空间）/ Floating hamburger menu overlay ---
        # 浮动容器：包含汉堡按钮 + 展开的菜单按钮 / Float container: hamburger btn + expanded menu btns
        self._menu_float = QWidget(self)
        self._menu_float.setObjectName("menuFloat")
        self._menu_float.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self._menu_float.setStyleSheet("""
            QWidget#menuFloat {
                background: transparent;
            }
        """)
        self._menu_float_layout = QHBoxLayout(self._menu_float)
        self._menu_float_layout.setContentsMargins(8, 8, 0, 0)
        self._menu_float_layout.setSpacing(8)
        self._menu_float_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # 汉堡按钮 / Hamburger button
        self._hamburger_btn = QToolButton(self._menu_float)
        self._hamburger_btn.setText("☰")
        self._hamburger_btn.setToolTip(tr("menu_tooltip"))
        self._hamburger_btn.setObjectName("hamburgerBtn")
        self._hamburger_btn.setFixedSize(30, 30)
        self._hamburger_btn.setStyleSheet("""
            QToolButton#hamburgerBtn {
                background-color: rgba(255, 255, 255, 0.10);
                color: #b0b0b0;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
                font-size: 15px;
            }
            QToolButton#hamburgerBtn:hover {
                background-color: rgba(255, 255, 255, 0.16);
                color: #e0e0e0;
            }
            QToolButton#hamburgerBtn:pressed {
                background-color: rgba(255, 255, 255, 0.22);
            }
        """)
        self._hamburger_btn.clicked.connect(self._toggle_menu_expand)
        self._menu_float_layout.addWidget(self._hamburger_btn)

        # 可展开的菜单按钮容器 / Expandable menu button container
        self._menu_container = QWidget(self._menu_float)
        self._menu_container.setObjectName("menuContainer")
        self._menu_container_layout = QHBoxLayout(self._menu_container)
        self._menu_container_layout.setContentsMargins(0, 0, 0, 0)
        self._menu_container_layout.setSpacing(6)

        # 创建各菜单的 QToolButton / Create QToolButton for each menu
        menu_items = [
            (tr("file"), self._file_menu),
            (tr("settings"), self._settings_menu),
            (tr("edit"), self._edit_menu),
            (tr("help"), self._help_menu),
        ]
        self._menu_buttons = []
        for label, menu in menu_items:
            btn = QToolButton(self._menu_container)
            btn.setText(label)
            btn.setMenu(menu)
            btn.setPopupMode(QToolButton.InstantPopup)
            btn.setObjectName("menuBtn")
            btn.setFixedHeight(30)
            btn.setStyleSheet("""
                QToolButton#menuBtn {
                    background-color: rgba(255, 255, 255, 0.10);
                    color: #b0b0b0;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 8px;
                    padding: 0px 14px;
                    font-size: 12px;
                }
                QToolButton#menuBtn:hover {
                    background-color: rgba(255, 255, 255, 0.16);
                    color: #e0e0e0;
                }
                QToolButton#menuBtn:pressed {
                    background-color: rgba(255, 255, 255, 0.22);
                }
                QToolButton#menuBtn::menu-indicator {
                    image: none;
                }
            """)
            self._menu_container_layout.addWidget(btn)
            self._menu_buttons.append(btn)

        self._menu_container.setFixedHeight(30)
        self._menu_container.setMaximumWidth(0)  # 初始收起 / Initially collapsed
        self._menu_container.setStyleSheet("background: transparent;")
        self._menu_float_layout.addWidget(self._menu_container)

        # 设置浮动层大小和位置 / Set float layer size and position
        self._menu_float.setFixedHeight(46)
        self._menu_float.raise_()  # 确保在最上层 / Ensure on top

        # 展开/收起状态 / Expand/collapse state
        self._menu_expanded = False

        # 自动收起计时器 / Auto-collapse timer
        self._auto_collapse_timer = QTimer(self)
        self._auto_collapse_timer.setSingleShot(True)
        self._auto_collapse_timer.setInterval(5000)  # 5秒无操作自动收起 / 5s inactivity auto-collapse
        self._auto_collapse_timer.timeout.connect(self._collapse_menu)

        # 监听菜单弹出/关闭来重置计时器 / Listen to menu show/hide to reset timer
        for menu in [self._file_menu, self._settings_menu, self._edit_menu, self._help_menu]:
            menu.aboutToShow.connect(self._on_menu_about_to_show)
            menu.aboutToHide.connect(self._on_menu_about_to_hide)

        # Context Menu
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)

    def _toggle_menu_expand(self):
        """切换菜单展开/收起 / Toggle menu expand/collapse"""
        if self._menu_expanded:
            self._collapse_menu()
        else:
            self._expand_menu()

    def _make_spring_curve(self, overshoot=1.70158):
        """
        创建 iOS 风格弹簧缓动曲线 / Create iOS-style spring easing curve
        基于 CSS cubic-bezier(0.175, 0.885, 0.32, 1.275) 的近似
        overshoot 控制回弹幅度：1.70158 是经典值，越大越 Q 弹
        """
        curve = QEasingCurve(QEasingCurve.OutBack)
        curve.setOvershoot(overshoot)
        return curve

    def _expand_menu(self):
        """
        展开菜单栏（iOS 灵动弹簧动画）/ Expand menu bar with iOS-style spring animation
        原理：容器宽度 OutBack 弹性展开 + 每个按钮交错 OutBack 弹入（从 0 宽弹到目标宽）
        效果：按钮像弹簧一样逐个"弹"出来，会微微超过目标位置再弹回
        """
        if self._menu_expanded:
            return
        self._menu_expanded = True

        # 记录每个按钮的目标宽度 / Record target width for each button
        btn_target_widths = [btn.sizeHint().width() for btn in self._menu_buttons]
        target_width = sum(btn_target_widths) + 6 * (len(self._menu_buttons) - 1) + 10

        # 先把所有按钮宽度设为 0（隐藏）/ Set all buttons to 0 width (hidden)
        for btn in self._menu_buttons:
            btn.setFixedWidth(0)
            btn.setVisible(True)

        # 容器宽度弹性展开 / Container spring expand
        self._expand_group = QParallelAnimationGroup(self)

        width_anim = QPropertyAnimation(self._menu_container, b"maximumWidth", self)
        width_anim.setDuration(380)
        width_anim.setStartValue(0)
        width_anim.setEndValue(target_width)
        width_anim.setEasingCurve(self._make_spring_curve(1.2))
        self._expand_group.addAnimation(width_anim)

        self._expand_group.finished.connect(self._update_float_width)
        self._expand_group.start()

        # 每个按钮交错弹入（60ms 间隔，OutBack 带回弹）
        # Staggered spring-in for each button (60ms delay, OutBack with overshoot)
        self._btn_spring_anims = []  # 防止 GC / Prevent GC
        spring_curve = self._make_spring_curve(2.0)  # 按钮用更大的回弹幅度，更 Q 弹
        for i, (btn, tw) in enumerate(zip(self._menu_buttons, btn_target_widths)):
            anim = QPropertyAnimation(btn, b"minimumWidth", self)
            anim.setDuration(350)
            anim.setStartValue(0)
            anim.setEndValue(tw)
            anim.setEasingCurve(spring_curve)
            QTimer.singleShot(i * 60, anim.start)
            self._btn_spring_anims.append(anim)

            # 同步设置 maximumWidth 防止按钮被拉伸 / Sync maximumWidth to prevent stretching
            anim_max = QPropertyAnimation(btn, b"maximumWidth", self)
            anim_max.setDuration(350)
            anim_max.setStartValue(0)
            anim_max.setEndValue(tw)
            anim_max.setEasingCurve(spring_curve)
            QTimer.singleShot(i * 60, anim_max.start)
            self._btn_spring_anims.append(anim_max)

        # 启动自动收起计时器 / Start auto-collapse timer
        self._auto_collapse_timer.start()

    def _collapse_menu(self):
        """
        收起菜单栏（iOS 灵动弹簧动画）/ Collapse menu bar with iOS-style spring animation
        原理：按钮反向交错收缩（InBack 先微微膨胀再快速缩小）+ 容器收缩
        效果：按钮像被吸回去一样，先微微鼓起再迅速消失
        """
        if not self._menu_expanded:
            return
        self._menu_expanded = False
        self._auto_collapse_timer.stop()

        # 按钮反向交错收缩 / Reverse staggered spring-out
        self._btn_collapse_anims = []  # 防止 GC / Prevent GC
        collapse_curve = QEasingCurve(QEasingCurve.InBack)
        collapse_curve.setOvershoot(1.5)  # 收起时先微微膨胀再缩小

        reversed_btns = list(reversed(self._menu_buttons))
        for i, btn in enumerate(reversed_btns):
            cur_w = btn.width()
            anim = QPropertyAnimation(btn, b"minimumWidth", self)
            anim.setDuration(250)
            anim.setStartValue(cur_w)
            anim.setEndValue(0)
            anim.setEasingCurve(collapse_curve)
            QTimer.singleShot(i * 45, anim.start)
            self._btn_collapse_anims.append(anim)

            anim_max = QPropertyAnimation(btn, b"maximumWidth", self)
            anim_max.setDuration(250)
            anim_max.setStartValue(cur_w)
            anim_max.setEndValue(0)
            anim_max.setEasingCurve(collapse_curve)
            QTimer.singleShot(i * 45, anim_max.start)
            self._btn_collapse_anims.append(anim_max)

        # 容器宽度收缩（等按钮开始收缩后再收容器）
        # Container collapse (delayed to let buttons start collapsing)
        total_delay = len(self._menu_buttons) * 45
        QTimer.singleShot(total_delay, self._start_collapse_width_anim)

    def _start_collapse_width_anim(self):
        """启动容器宽度收缩动画 / Start container width collapse animation"""
        anim = QPropertyAnimation(self._menu_container, b"maximumWidth", self)
        anim.setDuration(280)
        anim.setStartValue(self._menu_container.maximumWidth())
        anim.setEndValue(0)
        collapse_curve = QEasingCurve(QEasingCurve.InBack)
        collapse_curve.setOvershoot(0.8)
        anim.setEasingCurve(collapse_curve)
        anim.finished.connect(self._update_float_width)
        anim.start()
        self._collapse_anim = anim  # 防止被 GC / Prevent GC

    def _update_float_width(self):
        """更新浮动层宽度以适应内容 / Update float layer width to fit content"""
        self._menu_float.adjustSize()

    def resizeEvent(self, event):
        """窗口大小改变时更新浮动菜单位置 / Update float menu position on resize"""
        super().resizeEvent(event)
        if hasattr(self, '_menu_float'):
            self._menu_float.setFixedWidth(self.width())
            self._menu_float.raise_()

    def _on_menu_about_to_show(self):
        """菜单弹出时停止自动收起计时器 / Stop auto-collapse when menu opens"""
        self._auto_collapse_timer.stop()

    def _on_menu_about_to_hide(self):
        """菜单关闭后重启自动收起计时器 / Restart auto-collapse after menu closes"""
        self._auto_collapse_timer.start()

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
        self.setWindowTitle("HajimiRef") # 更新主窗口标题 / Update main window title
        # Rebuild menu is complex in Qt dynamic, simpler to just restart or update texts.
        # For simplicity, we just update title and let user restart or re-open menus.
        # A full reload would require clearing menuBar and calling setup_menu again.
        # 移除旧浮动菜单并重建 / Remove old float menu and rebuild
        if hasattr(self, '_menu_float'):
            self._menu_float.deleteLater()
        self.setup_menu()

    def toggle_always_on_top(self):
        """
        切换窗口置顶状态 / Toggle always on top
        
        setWindowFlags() 会销毁并重建原生窗口，因此需要：
        1. 保存窗口几何信息和当前完整标志
        2. 显式构建新标志，确保包含所有必要的窗口装饰标志
        3. show() 后重新应用 DWM 特效和画布 viewport 状态
        
        setWindowFlags() destroys and recreates the native window, so we must:
        1. Save window geometry and current flags
        2. Explicitly build new flags ensuring all decoration flags are preserved
        3. Re-apply DWM effects and canvas viewport state after show()
        """
        # 保存当前几何信息 / Save current geometry
        geo = self.geometry()
        was_maximized = self.isMaximized()
        
        # 构建新标志：以 Qt.Window 为基础，显式包含所有标题栏按钮标志
        # Build new flags: start with Qt.Window base, explicitly include all title bar button flags
        base_flags = (
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        
        if self.act_top.isChecked():
            new_flags = base_flags | Qt.WindowStaysOnTopHint
        else:
            new_flags = base_flags
        
        self.setWindowFlags(new_flags)
        
        # 恢复窗口几何和显示状态 / Restore geometry and display state
        if was_maximized:
            self.showMaximized()
        else:
            self.setGeometry(geo)
            self.show()
        
        # 重新应用 DWM 亚克力特效（HWND 已重建）/ Re-apply DWM acrylic effects (HWND was recreated)
        self.apply_win11_effects()
        
        # 重新应用画布 viewport 模式（亚克力穿透 vs GPU 加速）
        # Re-apply canvas viewport mode (acrylic passthrough vs GPU acceleration)
        if hasattr(self, 'view'):
            self.view.set_acrylic_mode(Config.acrylic_enabled)

    def apply_win11_effects(self):
        """
        应用 Windows 11 窗口特效（亚克力背景 + 背景 alpha 通道透明）
        Apply Windows 11 window effects (acrylic background + background alpha channel transparency)
        
        实现原理：
        1. 设置 WA_TranslucentBackground 让 Qt 不绘制窗口底色
        2. 调用 DwmExtendFrameIntoClientArea 将 DWM 渲染扩展到客户区
        3. 调用 DwmSetWindowAttribute 设置亚克力/云母背景材质
        4. 通过 QSS 中 rgba 的 alpha 通道控制各区域的透明程度
        5. 禁用 DWM 非客户区渲染，消除窗口边缘黑边
        """
        if sys.platform != "win32":
            return

        try:
            hwnd = int(self.winId())
            dwmapi = ctypes.windll.dwmapi

            if Config.acrylic_enabled:
                # --- 步骤1：设置 Qt 透明背景属性 ---
                self.setAttribute(Qt.WA_TranslucentBackground, True)

                # --- 步骤1.5：禁用 DWM 非客户区渲染，消除窗口边缘 DWM 绘制的黑边 ---
                # DWMWA_NCRENDERING_POLICY = 2
                # 值 2 = DWMNCRP_DISABLED（禁用非客户区渲染）
                # 这可以阻止 DWM 在窗口边缘绘制默认边框，消除 1-2px 的黑边
                DWMWA_NCRENDERING_POLICY = 2
                ncr_disabled = ctypes.c_int(2)
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_NCRENDERING_POLICY,
                    ctypes.byref(ncr_disabled),
                    ctypes.sizeof(ncr_disabled)
                )

                # --- 步骤2：将 DWM 帧扩展到整个客户区 ---
                class MARGINS(ctypes.Structure):
                    _fields_ = [
                        ("cxLeftWidth", ctypes.c_int),
                        ("cxRightWidth", ctypes.c_int),
                        ("cyTopHeight", ctypes.c_int),
                        ("cyBottomHeight", ctypes.c_int),
                    ]
                margins = MARGINS(-1, -1, -1, -1)  # -1 = 扩展到整个窗口
                dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

                # --- 步骤3：启用亚克力效果 ---
                # DWMWA_SYSTEMBACKDROP_TYPE = 38（Win11 22H2+）
                # 值 3 = DWMSBT_TRANSIENTWINDOW（亚克力 Acrylic）
                DWMWA_SYSTEMBACKDROP_TYPE = 38
                DWMSBT_ACRYLIC = ctypes.c_int(3)
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_SYSTEMBACKDROP_TYPE,
                    ctypes.byref(DWMSBT_ACRYLIC),
                    ctypes.sizeof(DWMSBT_ACRYLIC)
                )

                # --- 步骤4：开启暗色标题栏以匹配深色主题 ---
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                dark = ctypes.c_int(1)
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_USE_IMMERSIVE_DARK_MODE,
                    ctypes.byref(dark),
                    ctypes.sizeof(dark)
                )

                # --- 步骤4.5：隐藏 DWM 窗口边框颜色，彻底消除 1px 黑边 ---
                # DWMWA_BORDER_COLOR = 34（Win11 22H2+）
                # DWMWA_COLOR_NONE = 0xFFFFFFFE（隐藏边框颜色）
                # 这是 Win11 官方 API，比 DWMWA_NCRENDERING_POLICY 更彻底
                try:
                    DWMWA_BORDER_COLOR = 34
                    DWMWA_COLOR_NONE = ctypes.c_uint(0xFFFFFFFE)
                    dwmapi.DwmSetWindowAttribute(
                        hwnd,
                        DWMWA_BORDER_COLOR,
                        ctypes.byref(DWMWA_COLOR_NONE),
                        ctypes.sizeof(DWMWA_COLOR_NONE)
                    )
                except Exception:
                    pass  # 旧版 Win11 可能不支持此属性

                # --- 步骤5：通过 QSS 设置背景 alpha 通道 ---
                self._apply_transparent_stylesheet()

            else:
                # 关闭亚克力效果，恢复默认
                self.setAttribute(Qt.WA_TranslucentBackground, False)

                # 恢复 DWM 非客户区渲染策略 / Restore DWM NC rendering policy
                DWMWA_NCRENDERING_POLICY = 2
                ncr_auto = ctypes.c_int(0)  # DWMNCRP_AUTO = 0
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_NCRENDERING_POLICY,
                    ctypes.byref(ncr_auto),
                    ctypes.sizeof(ncr_auto)
                )

                DWMWA_SYSTEMBACKDROP_TYPE = 38
                DWMSBT_DISABLE = ctypes.c_int(1)
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_SYSTEMBACKDROP_TYPE,
                    ctypes.byref(DWMSBT_DISABLE),
                    ctypes.sizeof(DWMSBT_DISABLE)
                )

                # 重置 DWM 帧扩展
                class MARGINS(ctypes.Structure):
                    _fields_ = [
                        ("cxLeftWidth", ctypes.c_int),
                        ("cxRightWidth", ctypes.c_int),
                        ("cyTopHeight", ctypes.c_int),
                        ("cyBottomHeight", ctypes.c_int),
                    ]
                margins = MARGINS(0, 0, 0, 0)
                dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

                # 恢复不透明背景样式
                self._restore_opaque_stylesheet()

        except Exception as e:
            # 旧版 Windows 不支持该 API，静默忽略
            print(f"[Win11Effects] 应用效果失败: {e}")

    def _apply_transparent_stylesheet(self):
        """
        在亚克力模式下，通过 QSS rgba alpha 通道让背景半透明。
        Apply transparent background stylesheet using rgba alpha channel in acrylic mode.
        
        修复黑边：
        - QMainWindow 添加 margin: 0px; border: none; 防止 Qt 在窗口边缘绘制默认边框
        - QMenuBar / QToolBar 同样设置 border: none
        - 边缘黑边来源：Qt 默认的控件边框 + QPalette.Window alpha 混合 + DWM 窗口边框残留
        """
        alpha = Config.bg_opacity  # 0~255
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: rgba(53, 53, 53, {alpha});
                margin: 0px;
                border: none;
            }}
            QMenuBar {{
                background-color: rgba(53, 53, 53, {min(alpha + 30, 255)});
                border: none;
            }}
            QToolBar {{
                background-color: rgba(53, 53, 53, {min(alpha + 20, 255)});
                border: none;
            }}
        """)

    def _restore_opaque_stylesheet(self):
        """
        恢复不透明的默认背景样式。
        Restore opaque default background stylesheet.
        """
        self.setStyleSheet("")  # 清除自定义样式，恢复 App.py 中的全局调色板

    def show_about(self):
        """
        显示关于对话框 / Show about dialog
        """
        dialog = AboutDialog(self)
        dialog.exec()

    def show_context_menu(self, pos):
        """
        显示右键菜单 / Show context menu
        """
        menu = QMenu(self)
        
        # 撤销/重做选项 / Undo/Redo options
        undo_action = menu.addAction(tr("undo"), self.undo_action)
        undo_action.setEnabled(self.undo_manager.can_undo())
        
        redo_action = menu.addAction(tr("redo"), self.redo_action)
        redo_action.setEnabled(self.undo_manager.can_redo())
        
        menu.addSeparator()
        
        # 检查是否右键点击了组 / Check if clicked on a group
        scene_pos = self.view.mapToScene(pos)
        clicked_item = self.scene.itemAt(scene_pos, self.view.transform())
        
        if isinstance(clicked_item, GroupItem):
            # 组的右键菜单 / Group context menu
            menu.addAction(tr("group_settings"), lambda: self.show_group_settings(clicked_item))
            menu.addAction(tr("ungroup"), lambda: self.ungroup(clicked_item))
            menu.addSeparator()
        
        # 仅当有选中的项目时，才显示"智能整理"和"层级"选项
        selected_items = self.scene.selectedItems()
        selected_ref_items = [item for item in selected_items if isinstance(item, RefItem)]
        
        if len(selected_ref_items) >= 2:
            # 打组选项 / Group option
            menu.addAction(tr("group_selected") + " (G)", self.group_selected_items)
        
        if selected_ref_items:
            menu.addAction(tr("organize_items"), lambda: self.organize_items(selected_ref_items))
            
            # 层级子菜单 / Layer submenu
            layer_menu = menu.addMenu(tr("layer"))
            layer_menu.addAction(tr("bring_forward"), lambda: self.bring_forward(selected_ref_items))
            layer_menu.addAction(tr("send_backward"), lambda: self.send_backward(selected_ref_items))
            layer_menu.addSeparator()
            layer_menu.addAction(tr("bring_to_front"), lambda: self.bring_to_front(selected_ref_items))
            layer_menu.addAction(tr("send_to_back"), lambda: self.send_to_back(selected_ref_items))
            
            menu.addSeparator()

        menu.addAction(tr("open_image"), self.add_images)
        menu.addSeparator()
        menu.addAction(tr("save_board"), self.save_board)
        menu.addAction(tr("load_board"), self.load_board)
        menu.addSeparator()
        menu.addAction(tr("export_image"), self.export_board_to_image)
        menu.addAction(tr("export_to_clipboard"), self.export_board_to_clipboard)
        menu.addSeparator()
        menu.addAction(tr("reset_board"), self.reset_board_to_fit_images)
        menu.addSeparator()
        # 智能对齐开关 / Smart Guides toggle
        snap_label = tr("smart_guides_on") if self.view._snap_enabled else tr("smart_guides_off")
        menu.addAction(snap_label, self.toggle_snap_guides)
        menu.exec(self.view.mapToGlobal(pos))

    def organize_items(self, items):
        """
        使用物理模拟布局算法进行紧凑的无重叠放置。
        算法思路：将图片视为刚体，通过斥力（防重叠）+ 向心引力（趋向紧凑）+ 阻尼迭代收敛到自然美观的布局。
        
        Physics simulation layout algorithm:
        - Repulsion force: push overlapping images apart
        - Attraction force: pull images toward centroid for compactness
        - Damping: ensure convergence
        """
        if not items:
            return
        
        ref_items = [item for item in items if isinstance(item, RefItem)]
        if not ref_items:
            return
        
        # 记录原始位置用于撤销 / Record original positions for undo
        original_positions = [(item, QPointF(item.pos())) for item in ref_items]

        # 1) 快照每个 item 的尺寸和位置信息 / Snapshot size and position info
        bodies = []  # list of dict: {item, x, y, w, h, vx, vy}
        for item in ref_items:
            r = item.sceneBoundingRect()
            bodies.append({
                'item': item,
                'x': r.center().x(),       # 中心点坐标
                'y': r.center().y(),
                'w': r.width(),
                'h': r.height(),
                'vx': 0.0,
                'vy': 0.0,
            })
        
        n = len(bodies)
        if n == 0:
            return
        
        # 2) 物理模拟参数 / Physics simulation parameters
        # ─────────────────────────────────────────────────────────────────────
        # spacing: 图片之间的最小期望间距（像素），值越大图片排列越稀疏
        # Minimum desired gap (px) between images. Larger = more spread out.
        spacing = 12.0
        
        # repulsion_strength: 斥力强度系数，控制重叠图片被推开的速度
        #   值范围建议 0.5~2.0，越大越快消除重叠，但过大可能导致抖动
        #   相比向心引力需要足够大以确保斥力占主导，避免收敛时残留重叠
        # Repulsion coefficient. Controls how fast overlapping images are pushed apart.
        # Recommended range: 0.5~2.0. Must dominate over attraction to prevent residual overlap.
        repulsion_strength = 1.2
        
        # attraction_strength: 向心引力系数，将所有图片拉向共同质心以保持紧凑
        #   值范围建议 0.005~0.05，越大布局越紧凑，过大会与斥力冲突导致振荡
        #   必须远小于 repulsion_strength，否则会在收敛阶段将图片拉回重叠状态
        # Attraction coefficient. Pulls all images toward their centroid for compactness.
        # Recommended range: 0.005~0.05. Must be much smaller than repulsion to avoid re-overlap.
        attraction_strength = 0.01
        
        # damping: 速度阻尼系数（0~1），每帧速度乘以此值
        #   越接近 1 收敛越慢但更平滑，越接近 0 收敛越快但可能突变
        #   建议 0.75~0.90，过高会导致斥力产生的位移被快速吃掉从而推不开
        # Velocity damping factor (0~1). Each frame velocity is multiplied by this value.
        # Recommended: 0.75~0.90. Too high dampens repulsion displacement, preventing separation.
        damping = 0.80
        
        # max_iterations: 最大模拟迭代次数，防止极端情况下无限循环
        #   通常 80~200 足够收敛，图片数量越多可能需要更多迭代
        # Maximum simulation iterations. Prevents infinite loops in edge cases.
        # Usually 80~200 is sufficient. More images may need more iterations.
        max_iterations = 150
        
        # convergence_threshold: 收敛速度阈值，当所有物体最大速度低于此值时提前终止
        #   值越小结果越精确，但耗时越长。建议 0.1~0.5
        # Convergence speed threshold. Simulation stops early when max velocity drops below this.
        # Smaller = more precise result but longer computation. Recommended: 0.1~0.5.
        convergence_threshold = 0.1
        
        # max_force: 单步最大力限制，防止极端重叠导致图片弹射过远
        #   作为安全阀，一般不需要调整
        # Maximum force per step. Safety cap to prevent extreme overlap from catapulting images.
        # Generally no need to adjust.
        max_force = 300.0
        
        # 3) 迭代物理模拟 / Iterative physics simulation
        for iteration in range(max_iterations):
            # 计算质心 / Calculate centroid
            cx = sum(b['x'] for b in bodies) / n
            cy = sum(b['y'] for b in bodies) / n
            
            # 初始化力 / Initialize forces
            forces = [{'fx': 0.0, 'fy': 0.0} for _ in range(n)]
            
            # 检测是否还有重叠，用于后半段关闭引力 / Track if any overlap remains
            has_overlap = False
            
            # 3a) 斥力：防止重叠 / Repulsion: prevent overlap
            for i in range(n):
                for j in range(i + 1, n):
                    a = bodies[i]
                    b = bodies[j]
                    
                    # 计算两个矩形之间的 AABB 重叠（含间距）/ Calculate AABB overlap (including spacing)
                    half_w_a = a['w'] / 2.0 + spacing / 2.0
                    half_h_a = a['h'] / 2.0 + spacing / 2.0
                    half_w_b = b['w'] / 2.0 + spacing / 2.0
                    half_h_b = b['h'] / 2.0 + spacing / 2.0
                    
                    dx = b['x'] - a['x']
                    dy = b['y'] - a['y']
                    
                    overlap_x = (half_w_a + half_w_b) - abs(dx)
                    overlap_y = (half_h_a + half_h_b) - abs(dy)
                    
                    if overlap_x > 0 and overlap_y > 0:
                        has_overlap = True
                        # 存在重叠，沿最小重叠方向推开 / Overlap exists, push along minimum overlap axis
                        if overlap_x < overlap_y:
                            # 沿 X 轴推开 / Push along X axis
                            force = overlap_x * repulsion_strength
                            force = min(force, max_force)
                            if dx >= 0:
                                forces[i]['fx'] -= force
                                forces[j]['fx'] += force
                            else:
                                forces[i]['fx'] += force
                                forces[j]['fx'] -= force
                        else:
                            # 沿 Y 轴推开 / Push along Y axis
                            force = overlap_y * repulsion_strength
                            force = min(force, max_force)
                            if dy >= 0:
                                forces[i]['fy'] -= force
                                forces[j]['fy'] += force
                            else:
                                forces[i]['fy'] += force
                                forces[j]['fy'] -= force
            
            # 3b) 向心引力：保持紧凑（仅在无重叠时施加，避免把已分离的图片拉回重叠）
            # Attraction: keep compact (only when no overlap, to avoid pulling separated images back)
            if not has_overlap:
                for i in range(n):
                    dx_to_center = cx - bodies[i]['x']
                    dy_to_center = cy - bodies[i]['y']
                    forces[i]['fx'] += dx_to_center * attraction_strength
                    forces[i]['fy'] += dy_to_center * attraction_strength
            
            # 3c) 更新速度和位置 / Update velocity and position
            max_vel = 0.0
            for i in range(n):
                bodies[i]['vx'] = (bodies[i]['vx'] + forces[i]['fx']) * damping
                bodies[i]['vy'] = (bodies[i]['vy'] + forces[i]['fy']) * damping
                bodies[i]['x'] += bodies[i]['vx']
                bodies[i]['y'] += bodies[i]['vy']
                
                vel = math.sqrt(bodies[i]['vx'] ** 2 + bodies[i]['vy'] ** 2)
                if vel > max_vel:
                    max_vel = vel
            
            # 3d) 检查收敛（必须同时无重叠且速度低于阈值才终止）
            # Converge only when no overlap AND velocity is below threshold
            if max_vel < convergence_threshold and not has_overlap:
                break
        
        # 3e) 强制去重叠后处理：模拟结束后逐对检查，直接位移消除残留重叠
        #      确保 100% 无重叠，作为物理模拟的最终安全网
        # Post-processing: forcefully resolve any remaining overlaps after simulation.
        # Iteratively push apart overlapping pairs by direct displacement (no velocity).
        # This is the final safety net ensuring zero overlap.
        for _pass in range(50):  # 最多 50 轮强制去重叠 / Up to 50 passes
            any_overlap = False
            for i in range(n):
                for j in range(i + 1, n):
                    a = bodies[i]
                    b = bodies[j]
                    
                    half_w_a = a['w'] / 2.0 + spacing / 2.0
                    half_h_a = a['h'] / 2.0 + spacing / 2.0
                    half_w_b = b['w'] / 2.0 + spacing / 2.0
                    half_h_b = b['h'] / 2.0 + spacing / 2.0
                    
                    dx = b['x'] - a['x']
                    dy = b['y'] - a['y']
                    
                    overlap_x = (half_w_a + half_w_b) - abs(dx)
                    overlap_y = (half_h_a + half_h_b) - abs(dy)
                    
                    if overlap_x > 0 and overlap_y > 0:
                        any_overlap = True
                        # 沿最小重叠轴直接位移一半距离 / Displace each body by half the overlap along min axis
                        if overlap_x < overlap_y:
                            shift = overlap_x / 2.0 + 0.5  # +0.5 确保完全分离 / +0.5 ensures full separation
                            if dx >= 0:
                                bodies[i]['x'] -= shift
                                bodies[j]['x'] += shift
                            else:
                                bodies[i]['x'] += shift
                                bodies[j]['x'] -= shift
                        else:
                            shift = overlap_y / 2.0 + 0.5
                            if dy >= 0:
                                bodies[i]['y'] -= shift
                                bodies[j]['y'] += shift
                            else:
                                bodies[i]['y'] += shift
                                bodies[j]['y'] -= shift
            if not any_overlap:
                break
        
        # 4) 紧凑化压缩：反复尝试将每张图片向质心方向移动以消除多余间隙
        #    只有在不产生新重叠的前提下才保留移动，确保布局尽可能紧凑
        # Compaction phase: iteratively move each image toward centroid to eliminate
        # excess gaps. A move is kept only if it doesn't create new overlaps.
        # ─────────────────────────────────────────────────────────────────────
        # compact_step: 每次向质心移动的步长（像素），值越大压缩越快但精度越低
        # Step size (px) for each compaction move toward centroid. Larger = faster but less precise.
        compact_step = 4.0
        # compact_passes: 紧凑化的最大轮数，每轮尝试移动所有图片
        # Maximum compaction passes. Each pass tries to move all images.
        compact_passes = 60
        
        def has_overlap_with_others(idx, bods, sp):
            """检查第 idx 个 body 是否与其他任何 body 重叠 / Check if body at idx overlaps any other body"""
            a = bods[idx]
            for k in range(len(bods)):
                if k == idx:
                    continue
                b = bods[k]
                hw_a = a['w'] / 2.0 + sp / 2.0
                hh_a = a['h'] / 2.0 + sp / 2.0
                hw_b = b['w'] / 2.0 + sp / 2.0
                hh_b = b['h'] / 2.0 + sp / 2.0
                if (hw_a + hw_b) - abs(b['x'] - a['x']) > 0 and (hh_a + hh_b) - abs(b['y'] - a['y']) > 0:
                    return True
            return False
        
        for _cp in range(compact_passes):
            moved_any = False
            ccx = sum(b['x'] for b in bodies) / n
            ccy = sum(b['y'] for b in bodies) / n
            for i in range(n):
                dx_to_c = ccx - bodies[i]['x']
                dy_to_c = ccy - bodies[i]['y']
                dist = math.sqrt(dx_to_c ** 2 + dy_to_c ** 2)
                if dist < 1.0:
                    continue
                # 归一化方向，移动 compact_step / Normalize direction, move by compact_step
                step = min(compact_step, dist)
                mx = dx_to_c / dist * step
                my = dy_to_c / dist * step
                # 暂存旧位置，尝试移动 / Save old position, try move
                old_x, old_y = bodies[i]['x'], bodies[i]['y']
                bodies[i]['x'] += mx
                bodies[i]['y'] += my
                # 如果产生了新重叠，回退 / If new overlap, revert
                if has_overlap_with_others(i, bodies, spacing):
                    bodies[i]['x'] = old_x
                    bodies[i]['y'] = old_y
                else:
                    moved_any = True
            if not moved_any:
                break
        
        # 5) 计算偏移，锚定到原始选区的质心 / Calculate offset, anchor to original selection centroid
        orig_group_rect = QRectF()
        for item in ref_items:
            orig_group_rect = orig_group_rect.united(item.sceneBoundingRect())
        orig_center_x = orig_group_rect.center().x()
        orig_center_y = orig_group_rect.center().y()
        
        # 新布局质心 / New layout centroid
        new_cx = sum(b['x'] for b in bodies) / n
        new_cy = sum(b['y'] for b in bodies) / n
        
        # 偏移：让新布局的质心对齐到原始质心 / Offset to align new centroid to original centroid
        offset_x = orig_center_x - new_cx
        offset_y = orig_center_y - new_cy
        
        # 6) 计算每个 item 的目标位置 / Calculate target position for each item
        target_positions = []  # [(item, target_pos)]
        for body in bodies:
            item = body['item']
            final_cx = body['x'] + offset_x
            final_cy = body['y'] + offset_y
            
            # 将中心点坐标转换为 item 的 pos / Convert center coords to item pos
            cur_rect = item.sceneBoundingRect()
            cur_center = cur_rect.center()
            dx = final_cx - cur_center.x()
            dy = final_cy - cur_center.y()
            target_pos = item.pos() + QPointF(dx, dy)
            target_positions.append((item, target_pos))
        
        # 7) 弹簧动画过渡：使用 QTimer 驱动逐帧插值动画
        #    采用阻尼弹簧物理模型（与 macOS SwiftUI .spring() 一致），
        #    实现 overshoot 回弹的"Q弹灵动"效果
        # Spring animation transition: QTimer-driven frame-by-frame interpolation
        # using a damped spring physics model (matching macOS SwiftUI .spring()),
        # producing overshoot bounce for a lively, springy feel.
        # ─────────────────────────────────────────────────────────────────────
        # anim_frames: 动画总帧数，45帧 × 16ms ≈ 720ms，与 macOS spring(response:0.5) 视觉接近
        # Total animation frames. 45 × 16ms ≈ 720ms, visually close to macOS spring(response:0.5).
        anim_frames = 45
        # anim_interval_ms: 每帧间隔（毫秒），16ms ≈ 60fps
        # Interval per frame (ms). 16ms ≈ 60fps.
        anim_interval_ms = 16
        
        # 构建动画数据 / Build animation data
        anim_data = []
        for item, target_pos in target_positions:
            start_pos = QPointF(item.pos())
            anim_data.append({
                'item': item,
                'start': start_pos,
                'target': target_pos,
            })
        
        # 记录整理操作到撤销历史（在动画开始前记录，确保撤销能恢复到原始位置）
        # Record organize action to undo history (before animation, so undo restores original)
        items_positions = []
        for item, old_pos in original_positions:
            for ad in anim_data:
                if ad['item'] is item:
                    new_pos = ad['target']
                    if (old_pos - new_pos).manhattanLength() > 1:
                        items_positions.append((item, old_pos, new_pos))
                    break
        
        if items_positions:
            self.undo_manager.push(OrganizeItemsCommand(items_positions))
        
        # 收集受影响的组ID / Collect affected group IDs
        affected_group_ids = set()
        for item in ref_items:
            if hasattr(item, 'group_id') and item.group_id is not None:
                affected_group_ids.add(item.group_id)
        
        # 预计算受影响组的起始 rect 和目标 rect，用于同步动画插值
        # Pre-calculate start/target rects for affected groups, for synchronized animation interpolation
        group_anim_data = {}  # {group_id: {'group': GroupItem, 'start_rect': QRectF, 'target_rect': QRectF}}
        padding = 20  # 与 GroupItem.update_bounds 中的 padding 一致
        for gid in affected_group_ids:
            if gid not in self.groups:
                continue
            group_item = self.groups[gid]
            # 起始 rect = 组当前的 rect / Start rect = group's current rect
            start_rect = QRectF(group_item.rect())
            
            # 计算目标 rect：基于组成员的目标位置 / Calculate target rect based on members' target positions
            target_union = QRectF()
            for ad in anim_data:
                item = ad['item']
                if hasattr(item, 'group_id') and item.group_id == gid:
                    # 计算该图片到达目标位置后的场景矩形
                    # Calculate the scene rect of this image at its target position
                    cur_rect = item.sceneBoundingRect()
                    # 目标位置偏移 = target_pos - current_pos
                    dx = ad['target'].x() - item.pos().x()
                    dy = ad['target'].y() - item.pos().y()
                    target_item_rect = QRectF(cur_rect.x() + dx, cur_rect.y() + dy, cur_rect.width(), cur_rect.height())
                    target_union = target_union.united(target_item_rect)
            
            if not target_union.isEmpty():
                target_union.adjust(-padding, -padding, padding, padding)
                group_anim_data[gid] = {
                    'group': group_item,
                    'start_rect': start_rect,
                    'target_rect': target_union,
                }
        
        # 使用闭包捕获动画状态 / Use closure to capture animation state
        frame_counter = [0]
        
        def spring_damped(t, damping_ratio=0.75, frequency=2.0 * math.pi / 0.5):
            """
            阻尼弹簧缓动函数（与 macOS SwiftUI .spring(response:0.5, dampingFraction:0.75) 等效）
            Damped spring easing (equivalent to macOS SwiftUI .spring(response:0.5, dampingFraction:0.75))
            
            - damping_ratio < 1.0 → 欠阻尼，产生 overshoot 回弹（"Q弹"感）
            - damping_ratio = 1.0 → 临界阻尼，无回弹但最快收敛
            - frequency: 弹簧固有频率 ω₀ = 2π / response
            
            数学模型 / Math model:
                x(t) = 1 - e^(-ζω₀t) * (cos(ωd·t) + (ζω₀/ωd)·sin(ωd·t))
                其中 ωd = ω₀ · √(1 - ζ²)  (阻尼振荡频率)
            """
            if t >= 1.0:
                return 1.0
            zeta = damping_ratio
            omega0 = frequency
            omega_d = omega0 * math.sqrt(1.0 - zeta * zeta)
            decay = math.exp(-zeta * omega0 * t)
            cos_part = math.cos(omega_d * t)
            sin_part = (zeta * omega0 / omega_d) * math.sin(omega_d * t)
            return 1.0 - decay * (cos_part + sin_part)
        
        def animate_frame():
            frame_counter[0] += 1
            t = frame_counter[0] / anim_frames
            if t >= 1.0:
                t = 1.0
            
            progress = spring_damped(t)
            
            # 插值图片位置 / Interpolate image positions
            for ad in anim_data:
                current_x = ad['start'].x() + (ad['target'].x() - ad['start'].x()) * progress
                current_y = ad['start'].y() + (ad['target'].y() - ad['start'].y()) * progress
                ad['item'].setPos(current_x, current_y)
            
            # 同步插值组边界（与图片动画完全同步，实现优雅的过渡效果）
            # Synchronously interpolate group bounds (perfectly synced with image animation for elegant transition)
            for gid, gdata in group_anim_data.items():
                s = gdata['start_rect']
                e = gdata['target_rect']
                interp_rect = QRectF(
                    s.x() + (e.x() - s.x()) * progress,
                    s.y() + (e.y() - s.y()) * progress,
                    s.width() + (e.width() - s.width()) * progress,
                    s.height() + (e.height() - s.height()) * progress,
                )
                gdata['group'].setRect(interp_rect)
            
            self.view.viewport().update()
            
            if t >= 1.0:
                # 动画完成，停止定时器 / Animation complete, stop timer
                self._organize_anim_timer.stop()
                self._organize_anim_timer = None
                
                # 动画结束后精确更新组边界（修正插值累积误差）
                # Final precise update after animation (correct interpolation accumulated errors)
                for gid in affected_group_ids:
                    if gid in self.groups:
                        self.update_group_bounds(self.groups[gid])
        
        # 如果有正在进行的动画，先停止 / Stop any ongoing animation
        if hasattr(self, '_organize_anim_timer') and self._organize_anim_timer is not None:
            self._organize_anim_timer.stop()
        
        # 启动动画定时器 / Start animation timer
        self._organize_anim_timer = QTimer(self)
        self._organize_anim_timer.timeout.connect(animate_frame)
        self._organize_anim_timer.start(anim_interval_ms)

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

    def _get_color_depth_manager(self) -> ColorDepthManager:
        """
        获取全局色深管理器实例 / Get global color depth manager instance
        """
        app = QApplication.instance()
        if hasattr(app, 'color_depth_manager'):
            return app.color_depth_manager
        # 回退：创建默认实例 / Fallback: create default instance
        return ColorDepthManager(ColorDepthManager.get_mode_from_string(Config.color_depth_mode))

    def create_item_from_image(self, image, x, y):
        """
        从 QImage 创建图片项（自适应色深转换）/ Create image item from QImage (adaptive color depth)
        """
        if not image.isNull():
            # ── 自适应色深：根据图像原始位深选择最佳渲染格式 ──
            # Adaptive color depth: select optimal rendering format based on image's original bit depth
            cdm = self._get_color_depth_manager()
            image = cdm.convert_image(image)
            # QImage → QPixmap
            pixmap = QPixmap.fromImage(image)
            if not pixmap.isNull():
                item = RefItem(pixmap)  # image_data 为 None，惰性生成 / image_data is None, lazy generation
                item.setPos(x, y)
                self.scene.addItem(item)
                self.undo_manager.push(AddItemCommand(self.scene, item))
                self.view.markBoardBoundsDirty()
                self.view.scheduleViewportUpdate()
                return item
        return None

    def create_item_from_data(self, data, x, y, scale=1.0, rotation=0, zIndex=0, group_id=None, record_undo=True):
        """
        从二进制数据创建图片项（自适应色深）/ Create image item from binary data (adaptive color depth)
        record_undo: 是否记录到撤销历史 / Whether to record to undo history
        """
        # ── 自适应色深：先检测数据位深，再选择最佳格式加载 ──
        cdm = self._get_color_depth_manager()
        depth_info = cdm.detect_depth_from_data(data)
        
        # 如果是高位深图像且非强制8bit模式，使用 QImage 加载以保留精度
        if depth_info.is_high_bit_depth and cdm.mode != ColorDepthMode.FORCE_8BIT:
            image = QImage()
            if image.loadFromData(data):
                image = cdm.convert_image(image)
                pixmap = QPixmap.fromImage(image)
            else:
                pixmap = QPixmap()
                pixmap.loadFromData(data)
        else:
            pixmap = QPixmap()
            pixmap.loadFromData(data)
        if not pixmap.isNull():
            item = RefItem(pixmap, data)
            item.setPos(x, y)
            item.setScale(scale)
            item.setRotation(rotation)
            item.setZValue(zIndex)  # 设置图层顺序 / Set layer order
            item.group_id = group_id  # 设置组ID / Set group ID
            self.scene.addItem(item)
            
            # 记录添加操作到撤销历史 / Record add action to undo history
            if record_undo:
                self.undo_manager.push(AddItemCommand(self.scene, item))
            
            self.view.markBoardBoundsDirty()
            self.view.scheduleViewportUpdate()
            return item
        else:
            print("Failed to load pixmap from data")
            return None

    def delete_selected(self):
        """
        删除选中的图片或解散选中的组 / Delete selected images or ungroup selected groups
        """
        all_selected = self.scene.selectedItems()
        
        # 处理选中的组：解散组（组内图片保留）/ Handle selected groups: ungroup (keep member images)
        selected_groups = [item for item in all_selected if isinstance(item, GroupItem)]
        for group_item in selected_groups:
            self.ungroup(group_item)
        
        # 处理选中的图片：删除 / Handle selected images: delete
        selected_items = [item for item in all_selected if isinstance(item, RefItem)]
        if not selected_items:
            return
        
        # 记录删除操作到撤销历史 / Record delete action to undo history
        self.undo_manager.push(DeleteItemsCommand(self.scene, selected_items))
        
        for item in selected_items:
            self.scene.removeItem(item)
        
        self.view.markBoardBoundsDirty()
        self.view.scheduleViewportUpdate()

    def copy_selected_items(self):
        """
        复制选中的图片到应用内剪贴板（直接索引，零开销）/ Copy selected images to in-app clipboard (direct reference, zero overhead)
        """
        selected = [item for item in self.scene.selectedItems() if isinstance(item, RefItem)]
        if not selected:
            return
        
        # 直接存储引用信息：pixmap、image_data、位置、缩放、旋转、组ID
        # Direct reference: pixmap, image_data, position, scale, rotation, group_id
        self._copied_items = []
        for item in selected:
            self._copied_items.append({
                'pixmap': item.pixmap(),         # QPixmap 引用，零拷贝
                'image_data': item.image_data,   # bytes 引用，零拷贝
                'x': item.x(),
                'y': item.y(),
                'scale': item.scale(),
                'rotation': item.rotation(),
                'zIndex': item.zValue(),
            })
    
    def paste_image(self):
        """
        粘贴图片：优先从应用内缓存粘贴（零编解码），其次从系统剪贴板
        Paste image: prefer in-app cache (zero encoding), then system clipboard
        """
        center = self.view.mapToScene(self.view.viewport().rect().center())
        
        # 1. 优先从应用内缓存粘贴（直接索引，瞬时完成）
        # Priority: paste from in-app cache (direct reference, instant)
        if self._copied_items:
            offset = 30  # 偏移避免重叠 / Offset to avoid overlap
            new_items = []
            for info in self._copied_items:
                item = RefItem(info['pixmap'], info['image_data'])
                item.setPos(info['x'] + offset, info['y'] + offset)
                item.setScale(info['scale'])
                item.setRotation(info['rotation'])
                item.setZValue(info['zIndex'])
                self.scene.addItem(item)
                self.undo_manager.push(AddItemCommand(self.scene, item))
                new_items.append(item)
            
            # 选中新粘贴的图片 / Select newly pasted items
            self.scene.clearSelection()
            for item in new_items:
                item.setSelected(True)
            self.view.markBoardBoundsDirty()
            self.view.scheduleViewportUpdate()
            return
        
        # 2. 从系统剪贴板粘贴 / Paste from system clipboard
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                # 直接 QImage → QPixmap，跳过 PNG 编解码
                # Direct QImage → QPixmap, skip PNG encode/decode
                self.create_item_from_image(image, center.x(), center.y())
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
        items = [item for item in self.scene.items() if isinstance(item, RefItem)]
        if items:
            # 记录清空操作到撤销历史 / Record clear action to undo history
            self.undo_manager.push(ClearBoardCommand(self.scene, items))
        
        # 移除所有 RefItem（而不是 clear，以便保留其他可能的场景元素）
        for item in items:
            self.scene.removeItem(item)
    
    def reset_board_to_fit_images(self):
        """
        根据实际图片分布重置画板大小 / Reset board size based on actual image distribution
        """
        self.view.resetBoardToFitImages()
    
    def toggle_snap_guides(self):
        """
        切换智能对齐开关 / Toggle smart guides on/off
        """
        self.view._snap_enabled = not self.view._snap_enabled

    def update_auto_reset_timer(self):
        """
        更新自动重置画板定时器 / Update auto reset board timer
        """
        if Config.auto_reset_board_enabled:
            # 将分钟转换为毫秒
            interval_ms = Config.auto_reset_interval * 60 * 1000
            self.auto_reset_timer.start(interval_ms)
        else:
            self.auto_reset_timer.stop()
    
    def auto_reset_board(self):
        """
        自动重置画板（定时器回调）/ Auto reset board (timer callback)
        """
        self.view.resetBoardToFitImages()

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
        
        # 保存组信息 / Save group info
        groups_data = []
        for group_id, group_item in self.groups.items():
            groups_data.append(group_item.to_dict())
        
        # 构建包含组信息的数据 / Build data with group info
        board_data = {
            "version": 4,  # 版本4添加组功能 / Version 4 adds group feature
            "images": items_data,
            "groups": groups_data
        }
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(board_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, tr("error"), tr("save_error").format(str(e)))

    def export_board_to_image(self):
        """
        导出画布为图片 / Export board as image
        """
        # 获取场景中所有内容的边界矩形
        items = [item for item in self.scene.items() if isinstance(item, RefItem)]
        if not items:
            QMessageBox.warning(self, tr("warning"), tr("no_images_to_export"))
            return
        
        rect = self.scene.itemsBoundingRect()
        if rect.isEmpty():
            QMessageBox.warning(self, tr("warning"), tr("no_images_to_export"))
            return
        
        # 添加一些边距
        margin = 20
        rect = rect.adjusted(-margin, -margin, margin, margin)
        
        # 弹出文件保存对话框
        path, selected_filter = QFileDialog.getSaveFileName(
            self, 
            tr("export_image"), 
            "", 
            "PNG Image (*.png);;JPEG Image (*.jpg);;BMP Image (*.bmp)"
        )
        if not path:
            return
        
        # 根据文件扩展名确定格式
        if not (path.lower().endswith('.png') or path.lower().endswith('.jpg') or 
                path.lower().endswith('.jpeg') or path.lower().endswith('.bmp')):
            if 'PNG' in selected_filter:
                path += '.png'
            elif 'JPEG' in selected_filter or 'JPG' in selected_filter:
                path += '.jpg'
            else:
                path += '.bmp'
        
        # 创建足够大的 QImage（自适应色深）/ Create QImage with adaptive color depth
        width = int(rect.width())
        height = int(rect.height())
        
        # ── 自适应色深导出 ──
        cdm = self._get_color_depth_manager()
        file_ext = path.rsplit('.', 1)[-1].lower() if '.' in path else 'png'
        
        # 检测画布上图像的最高位深
        max_depth_info = None
        for item in items:
            if isinstance(item, RefItem) and item.image_data:
                info = cdm.detect_depth_from_data(item.image_data)
                if max_depth_info is None or info.bits_per_channel > max_depth_info.bits_per_channel:
                    max_depth_info = info
        if max_depth_info is None:
            from Models.ColorDepthManager import ImageColorDepthInfo
            max_depth_info = ImageColorDepthInfo()
        
        need_alpha = path.lower().endswith('.png')
        export_format = cdm.get_export_format(max_depth_info, file_ext, need_alpha)
        image = QImage(width, height, export_format)
        
        # 根据格式选择透明背景或白色背景
        if need_alpha:
            image.fill(Qt.transparent)
        else:
            image.fill(Qt.white)
        
        # 使用 QPainter 将场景渲染到图片
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # target: 目标绘制区域（整个图片）
        # source: 场景中要渲染的区域
        target = QRectF(0, 0, width, height)
        self.scene.render(painter, target, rect)
        painter.end()
        
        # 保存图片
        if image.save(path):
            QMessageBox.information(self, tr("success"), tr("export_success").format(path))
        else:
            QMessageBox.critical(self, tr("error"), tr("export_error"))

    def export_board_to_clipboard(self):
        """
        导出画布到剪贴板 / Export board to clipboard
        """
        # 获取场景中所有内容的边界矩形
        items = [item for item in self.scene.items() if isinstance(item, RefItem)]
        if not items:
            QMessageBox.warning(self, tr("warning"), tr("no_images_to_export"))
            return
        
        rect = self.scene.itemsBoundingRect()
        if rect.isEmpty():
            QMessageBox.warning(self, tr("warning"), tr("no_images_to_export"))
            return
        
        # 添加一些边距
        margin = 20
        rect = rect.adjusted(-margin, -margin, margin, margin)
        
        # 创建足够大的 QImage（自适应色深，使用透明背景）/ Create QImage with adaptive color depth
        width = int(rect.width())
        height = int(rect.height())
        
        # ── 自适应色深导出到剪贴板 ──
        cdm = self._get_color_depth_manager()
        max_depth_info = None
        for item in items:
            if isinstance(item, RefItem) and item.image_data:
                info = cdm.detect_depth_from_data(item.image_data)
                if max_depth_info is None or info.bits_per_channel > max_depth_info.bits_per_channel:
                    max_depth_info = info
        if max_depth_info is None:
            from Models.ColorDepthManager import ImageColorDepthInfo
            max_depth_info = ImageColorDepthInfo()
        
        export_format = cdm.get_export_format(max_depth_info, 'png', True)
        image = QImage(width, height, export_format)
        image.fill(Qt.transparent)
        
        # 使用 QPainter 将场景渲染到图片
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # target: 目标绘制区域（整个图片）
        # source: 场景中要渲染的区域
        target = QRectF(0, 0, width, height)
        self.scene.render(painter, target, rect)
        painter.end()
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setImage(image)

    def load_board(self):
        """
        从文件加载看板 / Load board from file
        """
        path, _ = QFileDialog.getOpenFileName(self, tr("load_board"), "", "SimpleRef Board (*.sref);;JSON (*.json)")
        if not path:
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                board_data = json.load(f)
            
            # 清空画布但不记录撤销（加载看板是完整替换）
            items = [item for item in self.scene.items() if isinstance(item, RefItem)]
            for item in items:
                self.scene.removeItem(item)
            
            # 清空现有组 / Clear existing groups
            for group_item in self.groups.values():
                self.scene.removeItem(group_item)
            self.groups.clear()
            
            # 清空撤销历史 / Clear undo history
            self.undo_manager.clear()
            
            # 处理不同版本的存档格式 / Handle different save format versions
            if isinstance(board_data, list):
                # 旧版本格式（纯数组）/ Old format (pure array)
                images_data = board_data
                groups_data = []
            else:
                # 新版本格式（带版本号的对象）/ New format (object with version)
                images_data = board_data.get("images", [])
                groups_data = board_data.get("groups", [])
            
            # 解码图片数据 / Decode image data
            for img_data in images_data:
                b64_data = img_data.get("data", "")
                try:
                    decoded_data = base64.b64decode(b64_data)
                except:
                    continue
                
                self.create_item_from_data(
                    decoded_data, 
                    img_data.get("x", 0), 
                    img_data.get("y", 0),
                    img_data.get("scale", 1.0),
                    img_data.get("rotation", 0),
                    img_data.get("zIndex", 0),
                    img_data.get("groupId", None),
                    record_undo=False
                )
            
            # 加载组信息 / Load group info
            for group_data in groups_data:
                group_item = GroupItem(
                    group_id=group_data.get("id"),
                    name=group_data.get("name", ""),
                    color=QColor(group_data.get("color", "#6495ED")),
                    opacity=group_data.get("opacity", 0.3),
                    font_size=group_data.get("font_size", 14)
                )
                rect = QRectF(
                    group_data.get("x", 0),
                    group_data.get("y", 0),
                    group_data.get("width", 100),
                    group_data.get("height", 100)
                )
                group_item.setRect(rect)
                self.scene.addItem(group_item)
                self.groups[group_item.group_id] = group_item
            
            # 更新所有组的边界（几何交集会自动判定成员，无需显式维护 member_ids）
            # Update all group bounds (geometric intersection auto-determines members, no member_ids needed)
            for group_item in self.groups.values():
                self.update_group_bounds(group_item)
            
        except Exception as e:
            QMessageBox.critical(self, tr("error"), tr("load_error").format(str(e)))

    # ========== 撤销/重做相关方法 / Undo/Redo related methods ==========
    
    def undo_action(self):
        """
        撤销操作 / Undo action
        """
        if self.undo_manager.undo():
            self.view.viewport().update()
    
    def redo_action(self):
        """
        重做操作 / Redo action
        """
        if self.undo_manager.redo():
            self.view.viewport().update()
    
    def record_move_action(self, items_data):
        """
        记录移动操作到撤销历史 / Record move action to undo history
        items_data: [(item, old_pos, new_pos), ...]
        """
        if items_data:
            self.undo_manager.push(MoveCommand(items_data))
            
            # 检查移动的图片是否移出了组 / Check if moved images are out of their groups
            for item, old_pos, new_pos in items_data:
                if isinstance(item, RefItem):
                    self.check_image_out_of_group(item)
    
    def record_scale_action(self, items_data):
        """
        记录缩放操作到撤销历史 / Record scale action to undo history
        items_data: [(item, old_scale, new_scale, old_pos, new_pos), ...]
        """
        if items_data:
            self.undo_manager.push(ScaleCommand(items_data))
    
    # ========== 图层管理方法 / Layer management methods ==========
    
    def bring_forward(self, items):
        """
        将选中的图片上移一层 / Bring selected items one layer forward
        """
        ref_items = [item for item in items if isinstance(item, RefItem)]
        if not ref_items:
            return
        
        # 获取所有 RefItem 并按 z-value 排序
        all_items = [item for item in self.scene.items() if isinstance(item, RefItem)]
        all_items.sort(key=lambda x: x.zValue())
        
        # 找到最大 z-value
        max_z = max(item.zValue() for item in all_items) if all_items else 0
        
        # 按 z-value 从高到低处理选中的项目，避免冲突
        ref_items.sort(key=lambda x: x.zValue(), reverse=True)
        
        for item in ref_items:
            current_z = item.zValue()
            # 找到比当前 z-value 高一层的项目
            higher_items = [i for i in all_items if i.zValue() > current_z and i not in ref_items]
            if higher_items:
                # 与最近的上层项目交换 z-value
                next_higher = min(higher_items, key=lambda x: x.zValue())
                item.setZValue(next_higher.zValue())
                next_higher.setZValue(current_z)
            else:
                # 已经是最高层，增加 z-value
                item.setZValue(max_z + 1)
                max_z += 1
        
        self.view.viewport().update()
    
    def send_backward(self, items):
        """
        将选中的图片下移一层 / Send selected items one layer backward
        """
        ref_items = [item for item in items if isinstance(item, RefItem)]
        if not ref_items:
            return
        
        # 获取所有 RefItem 并按 z-value 排序
        all_items = [item for item in self.scene.items() if isinstance(item, RefItem)]
        all_items.sort(key=lambda x: x.zValue())
        
        # 找到最小 z-value
        min_z = min(item.zValue() for item in all_items) if all_items else 0
        
        # 按 z-value 从低到高处理选中的项目，避免冲突
        ref_items.sort(key=lambda x: x.zValue())
        
        for item in ref_items:
            current_z = item.zValue()
            # 找到比当前 z-value 低一层的项目
            lower_items = [i for i in all_items if i.zValue() < current_z and i not in ref_items]
            if lower_items:
                # 与最近的下层项目交换 z-value
                next_lower = max(lower_items, key=lambda x: x.zValue())
                item.setZValue(next_lower.zValue())
                next_lower.setZValue(current_z)
            else:
                # 已经是最低层，减小 z-value
                item.setZValue(min_z - 1)
                min_z -= 1
        
        self.view.viewport().update()
    
    def bring_to_front(self, items):
        """
        将选中的图片移至最顶层 / Bring selected items to front
        """
        ref_items = [item for item in items if isinstance(item, RefItem)]
        if not ref_items:
            return
        
        # 获取所有 RefItem 的最大 z-value
        all_items = [item for item in self.scene.items() if isinstance(item, RefItem)]
        max_z = max(item.zValue() for item in all_items) if all_items else 0
        
        # 按原始 z-value 排序，保持相对顺序
        ref_items.sort(key=lambda x: x.zValue())
        
        for i, item in enumerate(ref_items):
            item.setZValue(max_z + 1 + i)
        
        self.view.viewport().update()
    
    def send_to_back(self, items):
        """
        将选中的图片移至最底层 / Send selected items to back
        """
        ref_items = [item for item in items if isinstance(item, RefItem)]
        if not ref_items:
            return
        
        # 获取所有 RefItem 的最小 z-value
        all_items = [item for item in self.scene.items() if isinstance(item, RefItem)]
        min_z = min(item.zValue() for item in all_items) if all_items else 0
        
        # 按原始 z-value 排序（降序），保持相对顺序
        ref_items.sort(key=lambda x: x.zValue(), reverse=True)
        
        for i, item in enumerate(ref_items):
            item.setZValue(min_z - 1 - i)
        
        self.view.viewport().update()

    # ========== 组管理相关方法 / Group management methods ==========
    
    def group_selected_items(self):
        """
        将选中的图片打组 / Group selected images
        """
        selected_items = [item for item in self.scene.selectedItems() if isinstance(item, RefItem)]
        
        if len(selected_items) < 2:
            return
        
        # 创建新组 / Create new group
        group_item = GroupItem()
        self.scene.addItem(group_item)
        self.groups[group_item.group_id] = group_item
        
        # 为选中的图片设置 group_id 标记 / Set group_id tag for selected images
        for item in selected_items:
            item.group_id = group_item.group_id
        
        # 更新组边界（基于几何位置自动判定成员）/ Update group bounds (members auto-determined by geometry)
        group_item.update_bounds(selected_items)
        
        # 记录撤销 / Record undo
        self.undo_manager.push(GroupCommand(self.scene, group_item, selected_items, self.groups))
        
        self.view.viewport().update()
    
    def _get_group_members(self, group_item):
        """
        通过几何交集实时判定组成员（位置就是真相）
        图片与组框的交集面积 >= 图片面积 * 5% 即为成员
        Determine group members by geometric intersection in real-time (position is truth).
        An image is a member if intersection_area >= image_area * 5%.
        """
        return group_item.get_members_by_intersection(threshold=0.05)
    
    def update_group_bounds(self, group_item):
        """
        更新组的边界 / Update group bounds
        """
        members = self._get_group_members(group_item)
        group_item.update_bounds(members)
    
    def update_all_group_bounds(self):
        """
        更新所有组的边界 / Update all group bounds
        """
        for group_item in self.groups.values():
            self.update_group_bounds(group_item)
    
    def show_group_settings(self, group_item):
        """
        显示组设置对话框 / Show group settings dialog
        """
        dialog = GroupSettingsDialog(group_item, self)
        if dialog.exec():
            settings = dialog.get_settings()
            group_item.group_name = settings['name']
            group_item.font_size = settings['font_size']
            group_item.group_color = settings['color']
            group_item.group_opacity = settings['opacity']
            group_item.update_appearance()
            self.view.viewport().update()
    
    def ungroup(self, group_item):
        """
        解散组 / Ungroup
        """
        members = self._get_group_members(group_item)
        
        # 记录撤销 / Record undo
        self.undo_manager.push(UngroupCommand(self.scene, group_item, members, self.groups))
        
        # 移除成员的组ID / Remove group ID from members
        for item in members:
            item.group_id = None
        
        # 从场景和字典中移除组 / Remove group from scene and dict
        if group_item.group_id in self.groups:
            del self.groups[group_item.group_id]
        self.scene.removeItem(group_item)
        
        self.view.viewport().update()
    
    def record_group_move_action(self, group_item, old_pos, new_pos):
        """
        记录组移动操作到撤销历史 / Record group move action to undo history
        """
        members = self._get_group_members(group_item)
        
        # 计算移动偏移 / Calculate movement delta
        delta = new_pos - old_pos
        
        # 获取每个成员的旧位置和新位置 / Get old and new positions for each member
        members_data = []
        for item in members:
            # 新位置 = 当前位置，旧位置 = 当前位置 - delta
            new_item_pos = QPointF(item.pos())
            old_item_pos = new_item_pos - delta
            members_data.append((item, old_item_pos, new_item_pos))
        
        # 将 pos() 的偏移合并到 rect() 中，并重置 pos() 为原点
        # Merge pos() offset into rect() and reset pos() to origin
        current_rect = group_item.rect()
        new_rect = current_rect.translated(delta)
        group_item.setRect(new_rect)
        group_item.setPos(0, 0)  # 重置 pos() 为原点
        
        if members_data:
            self.undo_manager.push(GroupMoveCommand(group_item, old_pos, new_pos, members_data))
    
    def check_images_in_group_bounds(self, group_item):
        """
        检测组边界调整后的成员变化 / Check member changes after group bounds resize
        1. 通过几何交集自动拉入框内图片
        2. 自动移出不再在框内的图片
        """
        # 使用几何交集实时判定当前成员（位置就是真相）
        # Determine current members by geometric intersection (position is truth)
        current_members = self._get_group_members(group_item)
        
        # 更新成员的 group_id 标记 / Update group_id tags for members
        # 先清除所有旧标记 / Clear old tags first
        for item in self.scene.items():
            if isinstance(item, RefItem) and hasattr(item, 'group_id') and item.group_id == group_item.group_id:
                if item not in current_members:
                    item.group_id = None
        
        # 为新成员设置 group_id / Set group_id for new members
        for item in current_members:
            # 如果图片之前在其他组中，先从那个组移除 / If image was in another group, remove from that group first
            if hasattr(item, 'group_id') and item.group_id is not None and item.group_id != group_item.group_id:
                old_group_id = item.group_id
                if old_group_id in self.groups:
                    old_group = self.groups[old_group_id]
                    item.group_id = None  # 先清除，避免循环
                    # 检查旧组是否还有足够成员 / Check if old group still has enough members
                    old_remaining = old_group.get_members_by_intersection()
                    if len(old_remaining) < 2:
                        self.ungroup(old_group)
            item.group_id = group_item.group_id
        
        # 如果成员不足2个，自动解散 / Auto ungroup if less than 2 members
        if len(current_members) < 2:
            self.ungroup(group_item)
            self.view.viewport().update()
            return
        
        self.view.viewport().update()
    
    def check_image_out_of_group(self, item):
        """
        检测图片移动后是否离开了组（基于几何交集实时判定）
        Check if image has left its group after moving (real-time geometric intersection).
        如果交集面积 < 图片面积 * 5%，则认为图片已离开组
        """
        if not hasattr(item, 'group_id') or item.group_id is None:
            return
        
        group_id = item.group_id
        if group_id not in self.groups:
            return
        
        group_item = self.groups[group_id]
        group_rect = group_item.sceneBoundingRect()
        item_rect = item.sceneBoundingRect()
        
        # 计算交集面积占比 / Calculate intersection area ratio
        intersection = group_rect.intersected(item_rect)
        item_area = item_rect.width() * item_rect.height()
        
        is_outside = True
        if item_area > 1e-6 and not intersection.isEmpty():
            intersection_area = intersection.width() * intersection.height()
            if intersection_area / item_area >= 0.05:  # 5% 阈值 / 5% threshold
                is_outside = False
        
        if is_outside:
            # 图片已离开组 / Image has left the group
            item.group_id = None
            
            # 如果组剩余成员不足2个，自动解散 / Auto ungroup if less than 2 remaining members
            remaining = group_item.get_members_by_intersection()
            if len(remaining) < 2:
                self.ungroup(group_item)
            
            self.view.viewport().update()
