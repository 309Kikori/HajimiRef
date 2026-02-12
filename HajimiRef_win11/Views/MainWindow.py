import sys
import os
import json
import base64
import math
from PySide6.QtWidgets import (QMainWindow, QGraphicsScene, QFileDialog, QMenu, QMessageBox, QApplication)
from PySide6.QtCore import Qt, QByteArray, QBuffer, QRectF, QPointF, QTimer
from PySide6.QtGui import QPixmap, QAction, QShortcut, QKeySequence, QImage, QPainter, QColor
from Config import Config, tr
from Views.Canvas import RefItem, RefView, GroupItem, GroupSettingsDialog
from Views.SettingsDialog import SettingsDialog
from ViewModels.MainViewModel import MainViewModel
from Models.UndoManager import UndoManager, MoveCommand, ScaleCommand, AddItemCommand, DeleteItemsCommand, ClearBoardCommand, OrganizeItemsCommand, GroupCommand, UngroupCommand, GroupMoveCommand

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
        
        # G键打组快捷键 / G key grouping shortcut
        self.group_shortcut = QShortcut(QKeySequence("G"), self)
        self.group_shortcut.activated.connect(self.group_selected_items)
        
        # 注意：撤销/重做快捷键已通过菜单栏 QAction 的 setShortcut 设置
        # 不再需要额外的 QShortcut，否则会导致 "Ambiguous shortcut overload" 冲突
        
        # Auto reset board timer
        self.auto_reset_timer = QTimer(self)
        self.auto_reset_timer.timeout.connect(self.auto_reset_board)
        self.update_auto_reset_timer()

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
        
        file_menu.addSeparator()
        
        act_export = QAction(tr("export_image"), self)
        act_export.triggered.connect(self.export_board_to_image)
        file_menu.addAction(act_export)
        
        act_export_clipboard = QAction(tr("export_to_clipboard"), self)
        act_export_clipboard.triggered.connect(self.export_board_to_clipboard)
        file_menu.addAction(act_export_clipboard)
        
        file_menu.addSeparator()
        
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
        
        # 编辑菜单 / Edit menu
        edit_menu = menubar.addMenu(tr("edit"))
        
        self.act_undo = QAction(tr("undo"), self)
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_undo.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)  # 确保在任何地方都能触发
        self.act_undo.triggered.connect(self.undo_action)
        edit_menu.addAction(self.act_undo)
        
        self.act_redo = QAction(tr("redo"), self)
        self.act_redo.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        self.act_redo.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)  # 确保在任何地方都能触发
        self.act_redo.triggered.connect(self.redo_action)
        edit_menu.addAction(self.act_redo)
        
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
        self.setWindowTitle("HajimiRef") # 更新主窗口标题 / Update main window title
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
        
        # 4) 计算偏移，锚定到原始选区的左上角 / Calculate offset, anchor to original selection top-left
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
        
        # 5) 应用最终位置 / Apply final positions
        for body in bodies:
            item = body['item']
            final_cx = body['x'] + offset_x
            final_cy = body['y'] + offset_y
            
            # 将中心点坐标转换为 item 的 pos / Convert center coords to item pos
            cur_rect = item.sceneBoundingRect()
            cur_center = cur_rect.center()
            dx = final_cx - cur_center.x()
            dy = final_cy - cur_center.y()
            item.setPos(item.pos() + QPointF(dx, dy))
        
        # 记录整理操作到撤销历史 / Record organize action to undo history
        items_positions = []
        for item, old_pos in original_positions:
            new_pos = QPointF(item.pos())
            if (old_pos - new_pos).manhattanLength() > 1:
                items_positions.append((item, old_pos, new_pos))
        
        if items_positions:
            self.undo_manager.push(OrganizeItemsCommand(items_positions))
        
        # 整理后更新相关组的边界，避免图片溢出组框 / Update related group bounds after organizing to prevent overflow
        affected_group_ids = set()
        for item in ref_items:
            if hasattr(item, 'group_id') and item.group_id is not None:
                affected_group_ids.add(item.group_id)
        for gid in affected_group_ids:
            if gid in self.groups:
                self.update_group_bounds(self.groups[gid])

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

    def create_item_from_data(self, data, x, y, scale=1.0, rotation=0, zIndex=0, group_id=None, record_undo=True):
        """
        从二进制数据创建图片项 / Create image item from binary data
        record_undo: 是否记录到撤销历史 / Whether to record to undo history
        """
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
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
            
            return item
        else:
            print("Failed to load pixmap from data")
            return None

    def delete_selected(self):
        """
        删除选中的图片 / Delete selected images
        """
        selected = [item for item in self.scene.selectedItems() if isinstance(item, RefItem)]
        if not selected:
            return
        
        # 记录删除操作到撤销历史 / Record delete action to undo history
        self.undo_manager.push(DeleteItemsCommand(self.scene, selected))
        
        for item in selected:
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
        
        # 创建足够大的 QImage
        width = int(rect.width())
        height = int(rect.height())
        
        # 根据格式选择透明背景或白色背景
        if path.lower().endswith('.png'):
            image = QImage(width, height, QImage.Format_ARGB32)
            image.fill(Qt.transparent)
        else:
            image = QImage(width, height, QImage.Format_RGB32)
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
        
        # 创建足够大的 QImage（使用透明背景）
        width = int(rect.width())
        height = int(rect.height())
        
        image = QImage(width, height, QImage.Format_ARGB32)
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
            
            # 更新所有组的边界 / Update all group bounds
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
        
        # 将选中的图片添加到组 / Add selected images to group
        for item in selected_items:
            item.group_id = group_item.group_id
            group_item.add_member(item)
        
        # 更新组边界 / Update group bounds
        self.update_group_bounds(group_item)
        
        # 记录撤销 / Record undo
        self.undo_manager.push(GroupCommand(self.scene, group_item, selected_items, self.groups))
        
        self.view.viewport().update()
    
    def update_group_bounds(self, group_item):
        """
        更新组的边界 / Update group bounds
        """
        members = [item for item in self.scene.items() 
                   if isinstance(item, RefItem) and hasattr(item, 'group_id') and item.group_id == group_item.group_id]
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
        members = [item for item in self.scene.items() 
                   if isinstance(item, RefItem) and hasattr(item, 'group_id') and item.group_id == group_item.group_id]
        
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
        members = [item for item in self.scene.items() 
                   if isinstance(item, RefItem) and hasattr(item, 'group_id') and item.group_id == group_item.group_id]
        
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
        1. 将框内的新图片拉入组
        2. 将不再在框内的现有成员移出组
        """
        # 使用组的 rect() 获取当前边界（因为 pos() 可能有偏移，用 sceneBoundingRect 更准确）
        group_rect = group_item.sceneBoundingRect()
        
        # 第1步：检查现有成员是否仍在组框内，不在则移除 / Step 1: Remove members outside group bounds
        members_to_remove = []
        for item in self.scene.items():
            if not isinstance(item, RefItem):
                continue
            if not (hasattr(item, 'group_id') and item.group_id == group_item.group_id):
                continue
            # 使用图片中心点判定是否在组框内 / Use image center to check if inside group bounds
            item_center = item.sceneBoundingRect().center()
            if not group_rect.contains(item_center):
                members_to_remove.append(item)
        
        for item in members_to_remove:
            item.group_id = None
            group_item.remove_member(item)
        
        # 如果移除后成员不足2个，自动解散 / Auto ungroup if less than 2 members
        remaining_members = [i for i in self.scene.items() 
                            if isinstance(i, RefItem) and hasattr(i, 'group_id') and i.group_id == group_item.group_id]
        if len(remaining_members) < 2:
            self.ungroup(group_item)
            self.view.viewport().update()
            return
        
        # 第2步：检查框内的新图片并拉入组 / Step 2: Pull new images inside group bounds
        for item in self.scene.items():
            if not isinstance(item, RefItem):
                continue
            
            # 跳过已经在此组中的图片 / Skip images already in this group
            if hasattr(item, 'group_id') and item.group_id == group_item.group_id:
                continue
            
            # 获取图片的中心点 / Get image center point
            item_center = item.sceneBoundingRect().center()
            
            # 如果图片中心在组边界内，则将其加入组 / If image center is inside group bounds, add it to group
            if group_rect.contains(item_center):
                # 如果图片之前在其他组中，先从那个组移除 / If image was in another group, remove from that group first
                if hasattr(item, 'group_id') and item.group_id is not None:
                    old_group_id = item.group_id
                    if old_group_id in self.groups:
                        old_group = self.groups[old_group_id]
                        old_group.remove_member(item)
                        # 如果旧组只剩一个或零个成员，自动解散 / Auto ungroup if old group has 1 or 0 members left
                        old_members = [i for i in self.scene.items() 
                                       if isinstance(i, RefItem) and hasattr(i, 'group_id') and i.group_id == old_group_id]
                        if len(old_members) < 2:
                            self.ungroup(old_group)
                
                # 将图片加入新组 / Add image to new group
                item.group_id = group_item.group_id
                group_item.add_member(item)
        
        self.view.viewport().update()
    
    def check_image_out_of_group(self, item):
        """
        检测图片是否完全移出了组边界 / Check if image is completely outside group bounds
        如果是，则自动将其从组中移除
        """
        if not hasattr(item, 'group_id') or item.group_id is None:
            return
        
        group_id = item.group_id
        if group_id not in self.groups:
            return
        
        group_item = self.groups[group_id]
        # 使用 sceneBoundingRect 获取组在场景中的实际边界
        group_rect = group_item.sceneBoundingRect()
        
        # 使用图片中心点判定是否在组内（与 check_images_in_group_bounds 保持一致）
        # Use image center point to check (consistent with check_images_in_group_bounds)
        item_center = item.sceneBoundingRect().center()
        
        # 如果图片中心不在组边界内，则移出组 / If image center is outside group bounds, remove from group
        if not group_rect.contains(item_center):
            # 从组中移除图片 / Remove image from group
            item.group_id = None
            group_item.remove_member(item)
            
            # 如果组只剩一个或零个成员，自动解散 / Auto ungroup if group has 1 or 0 members left
            members = [i for i in self.scene.items() 
                       if isinstance(i, RefItem) and hasattr(i, 'group_id') and i.group_id == group_id]
            if len(members) < 2:
                self.ungroup(group_item)
            
            self.view.viewport().update()
