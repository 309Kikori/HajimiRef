import base64
import uuid
from PySide6.QtWidgets import (QGraphicsView, QGraphicsPixmapItem, QGraphicsItem, QStyleOptionGraphicsItem, 
                               QGraphicsRectItem, QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QSpinBox, QSlider, QPushButton, QColorDialog, QInputDialog)
from PySide6.QtCore import Qt, QByteArray, QBuffer, QPointF, QRectF, QMimeData, QLineF, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QCursor, QColor, QPen, QDragEnterEvent, QDropEvent, QMouseEvent, QBrush, QFont, QPainterPath, QFontMetricsF
import bisect
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from Config import Config, tr

# --- Group Settings Dialog ---
class GroupSettingsDialog(QDialog):
    """
    组设置对话框 / Group settings dialog
    """
    def __init__(self, group_item, parent=None):
        super().__init__(parent)
        self.group_item = group_item
        self.setWindowTitle(tr("group_settings"))
        self.setMinimumWidth(300)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 名称设置 / Name setting
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(tr("group_name")))
        self.name_edit = QLineEdit(self.group_item.group_name)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # 字体大小设置 / Font size setting
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel(tr("font_size")))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 72)
        self.font_spin.setValue(self.group_item.font_size)
        font_layout.addWidget(self.font_spin)
        layout.addLayout(font_layout)
        
        # 颜色设置 / Color setting
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel(tr("group_color")))
        self.color_btn = QPushButton()
        self.current_color = self.group_item.group_color
        self.update_color_button()
        self.color_btn.clicked.connect(self.pick_color)
        color_layout.addWidget(self.color_btn)
        layout.addLayout(color_layout)
        
        # 透明度设置 / Opacity setting
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel(tr("opacity")))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(int(self.group_item.group_opacity * 100))
        self.opacity_label = QLabel(f"{int(self.group_item.group_opacity * 100)}%")
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v}%"))
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        layout.addLayout(opacity_layout)
        
        # 按钮 / Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton(tr("ok"))
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def update_color_button(self):
        self.color_btn.setStyleSheet(f"background-color: {self.current_color.name()}; min-width: 60px; min-height: 25px;")
    
    def pick_color(self):
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.current_color = color
            self.update_color_button()
    
    def get_settings(self):
        return {
            'name': self.name_edit.text(),
            'font_size': self.font_spin.value(),
            'color': self.current_color,
            'opacity': self.opacity_slider.value() / 100.0
        }

# --- Group Item ---
class GroupItem(QGraphicsRectItem):
    """
    组项目，用于将多个图片打组 / Group item for grouping multiple images
    """
    # 预设的好看颜色 / Preset nice colors
    PRESET_COLORS = [
        QColor(100, 149, 237, 128),  # 矢车菊蓝
        QColor(144, 238, 144, 128),  # 浅绿色
        QColor(255, 182, 193, 128),  # 浅粉色
        QColor(255, 218, 185, 128),  # 桃色
        QColor(221, 160, 221, 128),  # 梅红色
        QColor(176, 224, 230, 128),  # 淡蓝色
        QColor(250, 250, 210, 128),  # 柠檬绸色
        QColor(230, 230, 250, 128),  # 薰衣草色
    ]
    _color_index = 0
    
    def __init__(self, group_id=None, name="", color=None, opacity=0.3, font_size=14):
        super().__init__()
        self.group_id = group_id or str(uuid.uuid4())
        self.group_name = name or tr("group")
        self.font_size = font_size
        self.group_opacity = opacity
        
        # 自动分配颜色 / Auto assign color
        if color is None:
            color = GroupItem.PRESET_COLORS[GroupItem._color_index % len(GroupItem.PRESET_COLORS)]
            GroupItem._color_index += 1
        self.group_color = color
        
        # 设置项目属性 / Set item properties
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setZValue(-100)  # 组在图片下方 / Group is below images
        
        # 撤销状态 / Undo state
        self._undo_start_pos = None
        self._is_dragging = False
        
        # 调整大小状态 / Resize state
        self._is_resizing = False
        self._resize_corner = None
        self._resize_start_rect = None
        self._resize_start_mouse = None
        
        self.update_appearance()
    
    def update_appearance(self):
        """更新组的外观 / Update group appearance"""
        color = QColor(self.group_color)
        color.setAlphaF(self.group_opacity)
        self.setBrush(QBrush(color))
        
        # 边框颜色稍深 / Border color slightly darker
        border_color = QColor(self.group_color)
        border_color.setAlphaF(min(self.group_opacity + 0.3, 1.0))
        pen = QPen(border_color)
        pen.setWidth(2)
        pen.setCosmetic(True)
        self.setPen(pen)
    
    def _name_label_local_rect(self, lod=None):
        """返回名称标签在 item 局部坐标中的区域 / Return name label rect in item local coords
        
        参数 lod: 当前缩放级别，传入后可精确匹配 paint() 中的绘制位置；
                  不传则使用保守的大区域确保在任意缩放下都能命中。
        """
        rect = self.rect()
        if lod is not None and lod > 0.00001:
            # 精确模式：与 paint() 中的绘制逻辑一致 / Precise mode: match paint() drawing logic
            font = QFont()
            font.setPixelSize(int(self.font_size / lod))
            fm = QFontMetricsF(font)
            text_width = fm.horizontalAdvance(self.group_name) if self.group_name else 100
            text_height = fm.height()
            padding_h = 6 / lod
            padding_v = 3 / lod
            bg_x = rect.left()
            bg_y = rect.top() - text_height - padding_v * 2
            bg_w = text_width + padding_h * 2
            bg_h = text_height + padding_v * 2
            return QRectF(bg_x, bg_y, bg_w, bg_h)
        else:
            # 保守模式：使用足够大的区域确保 boundingRect / shape 覆盖 / Conservative mode for boundingRect/shape
            # 考虑极端缩放情况，使用较大的容差 / Use generous tolerance for extreme zoom levels
            max_label_height = self.font_size * 20 + 40
            return QRectF(rect.left(), rect.top() - max_label_height, max(rect.width(), 500), max_label_height)
    
    def boundingRect(self):
        """重写 boundingRect，包含名称标签区域 / Override boundingRect to include name label area"""
        rect = super().boundingRect()
        if self.group_name:
            rect = rect.united(self._name_label_local_rect())
        return rect
    
    def shape(self):
        """重写 shape，包含名称标签区域，使 Qt 事件分发能正确路由到此 item / Override shape to include name label area for proper event routing"""
        path = QPainterPath()
        path.addRect(self.rect())
        if self.group_name:
            path.addRect(self._name_label_local_rect())
        return path
    
    def get_members_by_intersection(self, threshold=0.05):
        """
        通过几何交集实时判定组成员（位置就是真相）
        图片与组框的交集面积 >= 图片面积 * threshold 即为成员
        Determine group members by geometric intersection in real-time (position is truth).
        An image is a member if intersection_area >= image_area * threshold.
        
        参数 / Parameters:
            threshold: 交集面积占图片面积的最小比例，默认 0.05 (5%)
                       Minimum ratio of intersection area to image area, default 0.05 (5%)
        """
        members = []
        scene = self.scene()
        if not scene:
            return members
        
        group_rect = self.sceneBoundingRect()
        for item in scene.items():
            if not isinstance(item, RefItem):
                continue
            item_rect = item.sceneBoundingRect()
            intersection = group_rect.intersected(item_rect)
            if intersection.isEmpty():
                continue
            item_area = item_rect.width() * item_rect.height()
            if item_area < 1e-6:
                continue
            intersection_area = intersection.width() * intersection.height()
            if intersection_area / item_area >= threshold:
                members.append(item)
        return members
    
    def add_member(self, item):
        """添加成员到组（仅设置 group_id 标记）/ Add member to group (only set group_id tag)"""
        if hasattr(item, 'group_id'):
            item.group_id = self.group_id
    
    def remove_member(self, item):
        """从组中移除成员（仅清除 group_id 标记）/ Remove member from group (only clear group_id tag)"""
        if hasattr(item, 'group_id') and item.group_id == self.group_id:
            item.group_id = None
    
    def update_bounds(self, items):
        """根据成员项目更新组边界 / Update group bounds based on member items"""
        if not items:
            return
        
        # 计算所有成员的边界 / Calculate bounds of all members
        padding = 20
        union_rect = QRectF()
        for item in items:
            if isinstance(item, RefItem):
                union_rect = union_rect.united(item.sceneBoundingRect())
        
        if not union_rect.isEmpty():
            union_rect.adjust(-padding, -padding, padding, padding)
            self.setRect(union_rect)
    
    def paint(self, painter, option, widget=None):
        """绘制组和名称标签 / Paint group and name label"""
        super().paint(painter, option, widget)
        
        rect = self.rect()
        
        # 计算屏幕空间大小 / Calculate screen-space size
        lod = QStyleOptionGraphicsItem.levelOfDetailFromTransform(painter.worldTransform())
        if lod < 0.00001:
            lod = 1
        
        # 绘制名称标签（位于组外侧左上角）/ Draw name label (outside top-left)
        if self.group_name:
            font = QFont()
            font.setPixelSize(int(self.font_size / lod))
            painter.setFont(font)
            
            # 文字颜色 / Text color
            text_color = QColor(self.group_color)
            text_color.setAlphaF(1.0)
            painter.setPen(text_color)
            
            # 计算文本位置（左上角外侧）/ Calculate text position (outside top-left)
            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(self.group_name)
            text_height = fm.height()
            padding_h = 6 / lod
            padding_v = 3 / lod
            
            # 标签位于组左上角上方 / Label above the top-left corner of the group
            bg_x = rect.left()
            bg_y = rect.top() - text_height - padding_v * 2
            bg_w = text_width + padding_h * 2
            bg_h = text_height + padding_v * 2
            
            # 绘制背景 / Draw background
            bg_rect = QRectF(bg_x, bg_y, bg_w, bg_h)
            bg_color = QColor(40, 40, 40, 200)
            painter.fillRect(bg_rect, bg_color)
            
            # 绘制文字 / Draw text
            text_x = bg_x + padding_h
            text_y = bg_y + padding_v + fm.ascent()
            painter.drawText(QPointF(text_x, text_y), self.group_name)
        
        # 绘制选中状态和调整手柄 / Draw selection state and resize handles
        if self.isSelected():
            pen = QPen(QColor("#2a82da"))
            pen.setWidth(3)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)
            
            # 绘制调整大小手柄 / Draw resize handles
            handle_size = 10 / lod
            painter.setBrush(QColor("white"))
            pen = QPen(QColor("#2a82da"))
            pen.setWidth(1)
            pen.setCosmetic(True)
            painter.setPen(pen)
            
            corners = [
                rect.topLeft(),
                rect.topRight(), 
                rect.bottomLeft(),
                rect.bottomRight()
            ]
            for corner in corners:
                painter.drawEllipse(corner, handle_size / 2, handle_size / 2)
    
    def hoverMoveEvent(self, event):
        """处理鼠标悬停事件，检测调整大小手柄 / Handle hover event, detect resize handles"""
        if self.isSelected():
            pos = event.pos()
            rect = self.rect()
            
            # 计算边距 / Calculate margin
            views = self.scene().views() if self.scene() else []
            view_scale = views[0].transform().m11() if views else 1.0
            margin = 20 / view_scale
            
            corners = {
                "tl": rect.topLeft(),
                "tr": rect.topRight(),
                "bl": rect.bottomLeft(),
                "br": rect.bottomRight()
            }
            
            self._resize_corner = None
            for corner_name, corner_pos in corners.items():
                if (pos - corner_pos).manhattanLength() < margin:
                    if corner_name in ["tl", "br"]:
                        self.setCursor(Qt.SizeFDiagCursor)
                    else:
                        self.setCursor(Qt.SizeBDiagCursor)
                    self._resize_corner = corner_name
                    break
            else:
                self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        
        super().hoverMoveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 检查是否点击了调整手柄 / Check if clicked on resize handle
            if self._resize_corner:
                self._is_resizing = True
                self._resize_start_rect = QRectF(self.rect())
                self._resize_start_mouse = event.scenePos()
                event.accept()
                return
            
            self._is_dragging = True
            self._undo_start_pos = QPointF(self.pos())  # 使用 pos() 而不是 rect().topLeft()
            self._drag_start_rect_pos = QPointF(self.rect().topLeft())  # 保存 rect 的初始位置
            
            # 通过几何交集实时判定成员，并缓存到拖拽期间使用
            # Determine members by geometric intersection and cache for drag duration
            self._drag_members = []  # [(item, start_pos)] 缓存成员及起始位置
            for member in self.get_members_by_intersection():
                self._drag_members.append((member, QPointF(member.pos())))
        
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """处理双击事件，双击名称标签快速编辑 / Handle double click, edit name label"""
        if event.button() == Qt.LeftButton and self.group_name:
            click_pos = event.pos()  # item 局部坐标 / Item local coordinates
            # 获取当前缩放级别 / Get current zoom level
            lod = 1.0
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]
                lod = view.transform().m11()
                if lod < 0.00001:
                    lod = 1.0
            if self._name_label_local_rect(lod).contains(click_pos):
                self._edit_name()
                event.accept()
                return
        super().mouseDoubleClickEvent(event)
    
    def _edit_name(self):
        """打开名称编辑对话框 / Open name edit dialog"""
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        if view:
            text, ok = QInputDialog.getText(
                view, tr("group_name"), tr("group_name") + ":",
                QLineEdit.Normal, self.group_name
            )
            if ok and text:
                self.group_name = text
                self.update()
    
    def mouseMoveEvent(self, event):
        if self._is_resizing and self._resize_start_rect is not None:
            # 调整大小逻辑 / Resize logic
            delta = event.scenePos() - self._resize_start_mouse
            new_rect = QRectF(self._resize_start_rect)
            
            min_size = 50  # 最小尺寸
            
            if self._resize_corner == "br":
                new_rect.setBottomRight(new_rect.bottomRight() + QPointF(delta.x(), delta.y()))
            elif self._resize_corner == "bl":
                new_rect.setBottomLeft(new_rect.bottomLeft() + QPointF(delta.x(), delta.y()))
            elif self._resize_corner == "tr":
                new_rect.setTopRight(new_rect.topRight() + QPointF(delta.x(), delta.y()))
            elif self._resize_corner == "tl":
                new_rect.setTopLeft(new_rect.topLeft() + QPointF(delta.x(), delta.y()))
            
            # 确保最小尺寸 / Ensure minimum size
            if new_rect.width() >= min_size and new_rect.height() >= min_size:
                self.setRect(new_rect)
            
            event.accept()
            return
        
        if self._is_dragging and self._undo_start_pos is not None:
            # 先让 Qt 更新 GroupItem 的 pos()，再基于最新 pos 同步成员位置
            # Call super() FIRST so Qt updates GroupItem.pos(), then sync members
            # 这消除了成员落后一帧的延迟感 / Eliminates 1-frame lag for member positions
            super().mouseMoveEvent(event)
            
            # 计算移动量（基于最新 pos() 的变化）/ Calculate delta from updated pos()
            delta = self.pos() - self._undo_start_pos
            
            # 直接使用拖拽开始时缓存的成员列表（无需每帧重新判定）
            # Use members cached at drag start (no per-frame re-evaluation needed)
            for item, start_pos in self._drag_members:
                item.setPos(start_pos + delta)
            return
    
    def mouseReleaseEvent(self, event):
        if self._is_resizing:
            self._is_resizing = False
            
            # 调整组边界后检测拉入图片 / Check for images to pull into group after resize
            view = self.scene().views()[0] if self.scene() and self.scene().views() else None
            if view and hasattr(view, 'parent') and view.parent():
                main_window = view.parent()
                if hasattr(main_window, 'check_images_in_group_bounds'):
                    main_window.check_images_in_group_bounds(self)
            
            self._resize_corner = None
            self._resize_start_rect = None
            self._resize_start_mouse = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        
        if self._is_dragging:
            self._is_dragging = False
            
            # 创建撤销命令 / Create undo command
            view = self.scene().views()[0] if self.scene() and self.scene().views() else None
            if view and hasattr(view, 'parent') and view.parent():
                main_window = view.parent()
                if hasattr(main_window, 'record_group_move_action'):
                    if self._undo_start_pos is not None:
                        current_pos = self.pos()
                        delta = current_pos - self._undo_start_pos
                        if delta.manhattanLength() > 1:
                            main_window.record_group_move_action(self, self._undo_start_pos, current_pos)
            
            # 组拖拽完成后标记画板边界需要更新 / Mark board bounds dirty after group drag
            view = self.scene().views()[0] if self.scene() and self.scene().views() else None
            if view and hasattr(view, 'markBoardBoundsDirty'):
                view.markBoardBoundsDirty()
                view.scheduleViewportUpdate()
            
            self._undo_start_pos = None
            self._drag_members = []
        
        super().mouseReleaseEvent(event)
    
    def to_dict(self):
        """序列化组信息 / Serialize group info"""
        return {
            "id": self.group_id,
            "name": self.group_name,
            "color": self.group_color.name(),
            "opacity": self.group_opacity,
            "font_size": self.font_size,
            "x": self.rect().x(),
            "y": self.rect().y(),
            "width": self.rect().width(),
            "height": self.rect().height()
        }

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
        self.setAcceptHoverEvents(True)
        
        # Center the origin
        self.setOffset(-pixmap.width()/2, -pixmap.height()/2)

        # Resize state
        self._is_resizing = False
        self._resize_corner = None
        self._start_pos = None
        self._start_scale = 1.0
        self._start_mouse_pos = None
        self._anchor_scene_pos = None
        
        # Undo state: 记录拖动/缩放开始前的状态 / Record state before drag/scale
        self._undo_start_pos = None
        self._undo_start_scale = None
        self._is_dragging = False
        
        # 组ID / Group ID
        self.group_id = None

    def paint(self, painter, option, widget=None):
        """
        绘制图片项和选中框 / Paint image item and selection border
        """
        super().paint(painter, option, widget)
        
        if self.isSelected():
            # Draw selection border
            pen = QPen(QColor("#2a82da"))
            pen.setWidth(2)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            rect = self.boundingRect()
            painter.drawRect(rect)
            
            # Draw handles
            painter.setBrush(QColor("white"))
            
            # Calculate handle size to be constant on screen
            lod = QStyleOptionGraphicsItem.levelOfDetailFromTransform(painter.worldTransform())
            if lod < 0.00001: lod = 1
            
            handle_dia = 10 / lod
            radius = handle_dia / 2
            
            corners = [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]
            for corner in corners:
                painter.drawEllipse(corner, radius, radius)

    def hoverMoveEvent(self, event):
        """
        处理鼠标悬停事件，检测调整大小手柄 / Handle hover event, detect resize handles
        """
        # Detect corners for resizing
        if self.isSelected():
            pos = event.pos()
            rect = self.boundingRect()
            
            # Calculate margin in local coordinates to match constant screen size
            views = self.scene().views()
            view_scale = 1.0
            if views:
                view_scale = views[0].transform().m11()
            
            # Desired screen margin (e.g., 20px)
            screen_margin = 20
            margin = screen_margin / (self.scale() * view_scale)
            
            tl = rect.topLeft()
            tr = rect.topRight()
            bl = rect.bottomLeft()
            br = rect.bottomRight()
            
            if (pos - tl).manhattanLength() < margin:
                self.setCursor(Qt.SizeFDiagCursor)
                self._resize_corner = "tl"
            elif (pos - tr).manhattanLength() < margin:
                self.setCursor(Qt.SizeBDiagCursor)
                self._resize_corner = "tr"
            elif (pos - bl).manhattanLength() < margin:
                self.setCursor(Qt.SizeBDiagCursor)
                self._resize_corner = "bl"
            elif (pos - br).manhattanLength() < margin:
                self.setCursor(Qt.SizeFDiagCursor)
                self._resize_corner = "br"
            else:
                self.setCursor(Qt.ArrowCursor)
                self._resize_corner = None
        else:
            self.setCursor(Qt.ArrowCursor)
            self._resize_corner = None
            
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        """
        处理鼠标按下事件，开始调整大小 / Handle mouse press, start resizing
        """
        if event.button() == Qt.LeftButton and self._resize_corner:
            self._is_resizing = True
            self._start_mouse_pos = event.scenePos()
            
            # Calculate Group Bounding Rect
            selected_items = self.scene().selectedItems()
            group_rect = QRectF()
            for item in selected_items:
                if isinstance(item, RefItem):
                    group_rect = group_rect.united(item.sceneBoundingRect())
            
            # Determine anchor point based on the corner of the *interaction* relative to the group
            # If dragging BR handle, we want Group TL as anchor.
            if self._resize_corner == "tl":
                self._anchor_scene_pos = group_rect.bottomRight()
            elif self._resize_corner == "tr":
                self._anchor_scene_pos = group_rect.bottomLeft()
            elif self._resize_corner == "bl":
                self._anchor_scene_pos = group_rect.topRight()
            elif self._resize_corner == "br":
                self._anchor_scene_pos = group_rect.topLeft()
            
            # Store start scale and pos for all selected items (including undo state)
            # 同时记录初始联合边界用于缩放吸附 / Also record initial union bounds for resize snap
            self._resize_start_group_rect = QRectF(group_rect)
            for item in selected_items:
                if isinstance(item, RefItem):
                    item._start_scale = item.scale()
                    item._start_pos = item.scenePos()
                    # 记录撤销状态 / Record undo state
                    item._undo_start_pos = QPointF(item.pos())
                    item._undo_start_scale = item.scale()
            
            # [Smart Guides] 缩放开始时缓存参考线 / Cache guide lines at resize start
            view = self.scene().views()[0] if self.scene().views() else None
            if view and hasattr(view, '_snap_enabled') and view._snap_enabled:
                dragged_ids = set()
                for it in selected_items:
                    if isinstance(it, RefItem):
                        dragged_ids.add(id(it))
                view._buildSnapGuides(dragged_ids)
            
            event.accept()
        elif event.button() == Qt.LeftButton:
            # 记录拖动开始状态（用于撤销）/ Record drag start state (for undo)
            self._is_dragging = True
            selected_items = self.scene().selectedItems()
            for item in selected_items:
                if isinstance(item, RefItem):
                    item._undo_start_pos = QPointF(item.pos())
                    item._undo_start_scale = item.scale()
            
            # [Smart Guides] 拖拽开始时缓存参考线 / Cache guide lines at drag start
            view = self.scene().views()[0] if self.scene().views() else None
            if view and hasattr(view, '_snap_enabled') and view._snap_enabled:
                dragged_ids = set()
                for it in selected_items:
                    if isinstance(it, RefItem):
                        dragged_ids.add(id(it))
                view._buildSnapGuides(dragged_ids)
            
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        处理鼠标移动事件，执行调整大小 / Handle mouse move, perform resizing
        """
        if self._is_resizing:
            current_mouse_pos = event.scenePos()
            
            # Calculate scale factor based on distance from anchor
            start_dist = QLineF(self._anchor_scene_pos, self._start_mouse_pos).length()
            current_dist = QLineF(self._anchor_scene_pos, current_mouse_pos).length()
            
            if start_dist < 1e-5: return
            
            ratio = current_dist / start_dist
            
            # [Smart Guides] 缩放时参考线吸附 / Snap during resize
            view = self.scene().views()[0] if self.scene().views() else None
            if view and hasattr(view, '_snap_enabled') and view._snap_enabled:
                start_rect = getattr(self, '_resize_start_group_rect', None)
                if start_rect is not None:
                    ratio = view._performResizeSnap(
                        ratio, self._anchor_scene_pos, start_rect, self._resize_corner
                    )
            
            # Apply to all selected items (Unified Scaling)
            for item in self.scene().selectedItems():
                if isinstance(item, RefItem) and hasattr(item, '_start_scale'):
                    # Scale
                    item.setScale(item._start_scale * ratio)
                    # Position: anchor + (start_pos - anchor) * ratio
                    vec = item._start_pos - self._anchor_scene_pos
                    item.setPos(self._anchor_scene_pos + vec * ratio)
            
            event.accept()
        else:
            # [Smart Guides] 吸附检测 / Snap detection during drag
            super().mouseMoveEvent(event)
            
            if self._is_dragging:
                view = self.scene().views()[0] if self.scene().views() else None
                if view and hasattr(view, '_snap_enabled') and view._snap_enabled:
                    view._performSnap(self)

    def mouseReleaseEvent(self, event):
        """
        处理鼠标释放事件，结束调整大小 / Handle mouse release, finish resizing
        """
        # [Smart Guides] 清除辅助线 / Clear guide lines on release
        if self._is_dragging or self._is_resizing:
            view = self.scene().views()[0] if self.scene().views() else None
            if view and hasattr(view, '_active_snap_lines'):
                view._active_snap_lines = []
                view._snap_x_guides = []
                view._snap_y_guides = []
                view.viewport().update()
        
        if self._is_resizing:
            self._is_resizing = False
            self._resize_corner = None
            self.setCursor(Qt.ArrowCursor)
            
            # 创建缩放撤销命令 / Create scale undo command
            view = self.scene().views()[0] if self.scene().views() else None
            if view and hasattr(view, 'parent') and view.parent():
                main_window = view.parent()
                if hasattr(main_window, 'record_scale_action'):
                    items_data = []
                    for item in self.scene().selectedItems():
                        if isinstance(item, RefItem) and item._undo_start_scale is not None:
                            # 只有当缩放确实改变时才记录
                            if abs(item._undo_start_scale - item.scale()) > 0.001 or \
                               (item._undo_start_pos - item.pos()).manhattanLength() > 1:
                                items_data.append((
                                    item,
                                    item._undo_start_scale,
                                    item.scale(),
                                    item._undo_start_pos,
                                    QPointF(item.pos())
                                ))
                    if items_data:
                        main_window.record_scale_action(items_data)
            
            # Clean up temp attributes
            for item in self.scene().selectedItems():
                if isinstance(item, RefItem):
                    if hasattr(item, '_start_scale'): del item._start_scale
                    if hasattr(item, '_start_pos'): del item._start_pos
                    item._undo_start_pos = None
                    item._undo_start_scale = None
            
            # 缩放完成后标记画板边界需要更新 / Mark board bounds dirty after scale
            view = self.scene().views()[0] if self.scene().views() else None
            if view and hasattr(view, 'markBoardBoundsDirty'):
                view.markBoardBoundsDirty()
                view.scheduleViewportUpdate()
            
            event.accept()
        elif self._is_dragging:
            self._is_dragging = False
            
            # 创建移动撤销命令 / Create move undo command
            view = self.scene().views()[0] if self.scene().views() else None
            if view and hasattr(view, 'parent') and view.parent():
                main_window = view.parent()
                if hasattr(main_window, 'record_move_action'):
                    items_data = []
                    for item in self.scene().selectedItems():
                        if isinstance(item, RefItem) and item._undo_start_pos is not None:
                            # 只有当位置确实改变时才记录
                            if (item._undo_start_pos - item.pos()).manhattanLength() > 1:
                                items_data.append((
                                    item,
                                    item._undo_start_pos,
                                    QPointF(item.pos())
                                ))
                    if items_data:
                        main_window.record_move_action(items_data)
            
            # 清理撤销状态 / Clean up undo state
            for item in self.scene().selectedItems():
                if isinstance(item, RefItem):
                    item._undo_start_pos = None
                    item._undo_start_scale = None
            
            # 拖拽/缩放完成后标记画板边界需要更新 / Mark board bounds dirty after drag/scale
            view = self.scene().views()[0] if self.scene().views() else None
            if view and hasattr(view, 'markBoardBoundsDirty'):
                view.markBoardBoundsDirty()
                view.scheduleViewportUpdate()
            
            super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def apply_scale_with_anchor(self, new_scale):
        """
        应用缩放并保持锚点固定 / Apply scale and keep anchor fixed
        """
        self.setScale(new_scale)
        
        # Re-position to keep anchor fixed
        # We need to know where the anchor point is NOW in scene coords
        rect = self.boundingRect()
        if self._resize_corner == "tl":
            anchor_local = rect.bottomRight()
        elif self._resize_corner == "tr":
            anchor_local = rect.bottomLeft()
        elif self._resize_corner == "bl":
            anchor_local = rect.topRight()
        elif self._resize_corner == "br":
            anchor_local = rect.topLeft()
        else:
            return # Should not happen

        current_anchor_scene = self.mapToScene(anchor_local)
        diff = self._anchor_scene_pos - current_anchor_scene
        self.setPos(self.pos() + diff)

    def to_dict(self):
        """
        将图片信息序列化为字典，用于保存 / Serialize image info to dict for saving
        """
        pos = self.scenePos()
        # 惰性编码：image_data 为 None 时从 pixmap 生成 PNG bytes
        # Lazy encoding: generate PNG bytes from pixmap when image_data is None
        if self.image_data is None:
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QBuffer.WriteOnly)
            self.pixmap().save(buf, "PNG")
            self.image_data = ba.data()
        
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
            "zIndex": self.zValue(),  # 保存图层顺序 / Save layer order
            "data": b64_data,
            "groupId": self.group_id  # 保存组ID / Save group ID
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
        
        # GPU 加速 / GPU Acceleration
        # 始终使用 QOpenGLWidget 以获得 GPU 加速渲染
        # Always use QOpenGLWidget for GPU-accelerated rendering
        gl_widget = QOpenGLWidget()
        if Config.acrylic_enabled:
            # 亚克力模式：在 QOpenGLWidget 上启用透明穿透
            # Acrylic mode: enable transparent passthrough on QOpenGLWidget
            # 需要 QSurfaceFormat alphaBufferSize >= 8（在 App.py 中已配置）
            # Requires QSurfaceFormat alphaBufferSize >= 8 (configured in App.py)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            gl_widget.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setStyleSheet("background: transparent; border: 0px;")
        self.setViewport(gl_widget)
        
        # Render Hints
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.TextAntialiasing)
        
        # Viewport behavior
        # 使用 NoViewportUpdate + 手动 viewport().update() 避免不必要的全屏重绘
        # Use NoViewportUpdate + manual viewport().update() to avoid unnecessary full redraws
        # 注：OpenGL 视口不支持局部更新，所以用 NoViewportUpdate 配合手动控制时机
        self.setViewportUpdateMode(QGraphicsView.NoViewportUpdate)
        self._viewport_update_timer = QTimer()
        self._viewport_update_timer.setSingleShot(True)
        self._viewport_update_timer.setInterval(16)  # ~60fps
        self._viewport_update_timer.timeout.connect(self._doViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)
        
        # Background
        # self.setBackgroundBrush(Qt.darkGray) # Handled in drawBackground
        
        # State
        self._is_panning = False
        self._pan_start = QPointF()
        self._space_pressed = False
        
        # [Smart Guides] 智能对齐状态 / Smart alignment state
        self._snap_enabled = True
        self._snap_threshold = 5.0  # 屏幕像素吸附阈值 / Screen pixel snap threshold
        self._snap_x_guides = []   # [(value, item_id)] 排序后的 X 方向参考线
        self._snap_y_guides = []   # [(value, item_id)] 排序后的 Y 方向参考线
        self._active_snap_lines = []  # 当前活跃的辅助线 [(axis, value, start, end)]
        
        # 画板边界状态（只扩展不收缩）/ Board bounds state (expand only, never shrink)
        # 初始画板边界以原点为中心 / Initial board bounds centered at origin
        half_w = Config.initial_board_width / 2
        half_h = Config.initial_board_height / 2
        self._board_bounds = QRectF(-half_w, -half_h, Config.initial_board_width, Config.initial_board_height)
        self._board_bounds_dirty = True  # 脏标记，仅在需要时重新计算 / Dirty flag, recalculate only when needed
        
        # 画板扩展动画状态 / Board expansion animation state
        # _display_board_bounds: 用于实际绘制的插值边界（平滑过渡）
        # _board_bounds: 逻辑目标边界（瞬时更新）
        self._display_board_bounds = QRectF(self._board_bounds)
        self._board_anim_timer = QTimer()
        self._board_anim_timer.setInterval(16)  # ~60fps
        self._board_anim_timer.timeout.connect(self._animateBoardBounds)
        self._board_anim_lerp_speed = 0.15  # 每帧插值比例（0~1，越大越快）/ Per-frame lerp ratio
        
        # 组管理 / Group management
        self._groups = {}  # group_id -> GroupItem

    def set_acrylic_mode(self, enabled):
        """
        运行时切换亚克力模式 / Toggle acrylic mode at runtime
        始终使用 QOpenGLWidget（GPU 加速），亚克力模式通过 WA_TranslucentBackground 实现透明穿透。
        Always use QOpenGLWidget (GPU acceleration), acrylic mode uses WA_TranslucentBackground for passthrough.
        """
        # 始终使用 QOpenGLWidget / Always use QOpenGLWidget
        gl_widget = QOpenGLWidget()
        if enabled:
            # 亚克力模式：在 QOpenGLWidget 上启用透明穿透
            # Acrylic mode: enable transparent passthrough on QOpenGLWidget
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            gl_widget.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setStyleSheet("background: transparent; border: 0px;")
        else:
            # 非亚克力模式：关闭透明
            # Non-acrylic mode: disable transparency
            self.setAttribute(Qt.WA_TranslucentBackground, False)
            self.setStyleSheet("")
        self.setViewport(gl_widget)
        
        # 重新设置视口更新模式和渲染提示 / Re-apply viewport update mode and render hints
        self.setViewportUpdateMode(QGraphicsView.NoViewportUpdate)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.TextAntialiasing)
        
        # 触发重绘 / Trigger repaint
        self.viewport().update()

    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        处理拖拽进入事件 / Handle drag enter event
        """
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """
        处理拖拽移动事件 / Handle drag move event
        """
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        """
        处理拖拽放下事件 / Handle drop event
        """
        mime_data = event.mimeData()
        pos = self.mapToScene(event.position().toPoint())
        
        if mime_data.hasImage():
            img_obj = mime_data.imageData()
            if isinstance(img_obj, QImage):
                self.parent().create_item_from_image(img_obj, pos.x(), pos.y())
                event.acceptProposedAction()
                return

        if mime_data.hasUrls():
            offset = 0
            for url in mime_data.urls():
                if url.isLocalFile():
                    self.parent().load_image_file(url.toLocalFile(), pos.x() + offset, pos.y() + offset)
                    offset += 20
            self.markBoardBoundsDirty()
            self.scheduleViewportUpdate()
            event.acceptProposedAction()

    # ─────────────────────────────────────────────────────────────────────
    # [Smart Guides] 智能对齐核心算法
    # ─────────────────────────────────────────────────────────────────────
    def _buildSnapGuides(self, dragged_ids):
        """
        缓存所有非拖拽物体的参考线（拖拽开始时调用一次）
        Build snap guide cache from all non-dragged items (called once at drag start).
        每个 RefItem 提取 6 条参考线: left, right, centerX, top, bottom, centerY
        同时缓存每个参考物体的完整边界矩形用于辅助线范围计算
        """
        x_guides = []  # [(value, item_id)]
        y_guides = []  # [(value, item_id)]
        self._snap_item_rects = {}  # {item_id: QRectF} 缓存参考物体边界
        
        for item in self.scene().items():
            if not isinstance(item, RefItem):
                continue
            if id(item) in dragged_ids:
                continue
            
            r = item.sceneBoundingRect()
            iid = id(item)
            self._snap_item_rects[iid] = QRectF(r)  # 缓存边界矩形
            x_guides.append((r.left(), iid))
            x_guides.append((r.right(), iid))
            x_guides.append((r.center().x(), iid))
            y_guides.append((r.top(), iid))
            y_guides.append((r.bottom(), iid))
            y_guides.append((r.center().y(), iid))
        
        # 排序以便二分查找 / Sort for binary search
        x_guides.sort(key=lambda g: g[0])
        y_guides.sort(key=lambda g: g[0])
        self._snap_x_guides = x_guides
        self._snap_y_guides = y_guides

    def _findNearestGuide(self, guides, value, threshold):
        """
        二分查找最近的参考线，返回 (guide_value, distance) 或 None
        Binary search for the nearest guide within threshold.
        """
        if not guides:
            return None
        
        values = [g[0] for g in guides]
        idx = bisect.bisect_left(values, value)
        
        best = None
        best_dist = threshold + 1
        
        # 检查 idx-1, idx 两个候选 / Check candidates at idx-1 and idx
        for i in (idx - 1, idx):
            if 0 <= i < len(values):
                dist = abs(values[i] - value)
                if dist < best_dist:
                    best_dist = dist
                    best = values[i]
        
        if best is not None and best_dist <= threshold:
            return (best, best_dist)
        return None

    def _performSnap(self, dragged_item):
        """
        对所有选中项执行吸附检测和位移修正 / Perform snap detection for all selected items.
        """
        # 计算吸附阈值（屏幕像素 → 世界坐标）/ Threshold: screen px -> world coords
        view_scale = self.transform().m11()
        if view_scale < 0.001:
            view_scale = 1.0
        threshold = self._snap_threshold / view_scale
        
        # 计算所有选中项的联合边界 / Compute union bounds of all selected items
        selected = [it for it in self.scene().selectedItems() if isinstance(it, RefItem)]
        if not selected:
            return
        
        union = QRectF()
        for it in selected:
            union = union.united(it.sceneBoundingRect())
        
        # 被拖拽物体的 5 条关键线 / 5 key lines of dragged bounding box
        drag_x_vals = [union.left(), union.center().x(), union.right()]
        drag_y_vals = [union.top(), union.center().y(), union.bottom()]
        
        # 寻找 X 方向最近吸附 / Find nearest X snap
        best_snap_x = None  # (snap_to_value, drag_value, distance)
        for dv in drag_x_vals:
            result = self._findNearestGuide(self._snap_x_guides, dv, threshold)
            if result:
                guide_val, dist = result
                if best_snap_x is None or dist < best_snap_x[2]:
                    best_snap_x = (guide_val, dv, dist)
        
        # 寻找 Y 方向最近吸附 / Find nearest Y snap
        best_snap_y = None
        for dv in drag_y_vals:
            result = self._findNearestGuide(self._snap_y_guides, dv, threshold)
            if result:
                guide_val, dist = result
                if best_snap_y is None or dist < best_snap_y[2]:
                    best_snap_y = (guide_val, dv, dist)
        
        # 计算修正偏移 / Calculate correction offset
        dx = 0.0
        dy = 0.0
        new_snap_lines = []
        
        if best_snap_x:
            dx = best_snap_x[0] - best_snap_x[1]  # guide_value - drag_value
            # 辅助线纵向范围 / Vertical extent of guide line
            line_top = min(union.top(), self._getGuideExtentMin('y', best_snap_x[0])) - 20 / view_scale
            line_bottom = max(union.bottom(), self._getGuideExtentMax('y', best_snap_x[0])) + 20 / view_scale
            new_snap_lines.append(('x', best_snap_x[0], line_top, line_bottom))
        
        if best_snap_y:
            dy = best_snap_y[0] - best_snap_y[1]
            line_left = min(union.left(), self._getGuideExtentMin('x', best_snap_y[0])) - 20 / view_scale
            line_right = max(union.right(), self._getGuideExtentMax('x', best_snap_y[0])) + 20 / view_scale
            new_snap_lines.append(('y', best_snap_y[0], line_left, line_right))
        
        # 应用修正偏移到所有选中项 / Apply correction to all selected items
        if abs(dx) > 0.001 or abs(dy) > 0.001:
            for it in selected:
                it.moveBy(dx, dy)
        
        # 更新活跃辅助线并触发重绘（使用去抖调度，避免每帧直接 update）
        # Update active lines and trigger repaint (use debounced schedule to avoid per-frame direct update)
        self._active_snap_lines = new_snap_lines
        self.scheduleViewportUpdate()

    def _performResizeSnap(self, ratio, anchor, start_rect, corner):
        """
        缩放时的参考线吸附检测：根据正在移动的边缘检测吸附，修正 ratio 并显示辅助线。
        Resize snap: detect snap on the moving edges, correct ratio, and show guide lines.
        
        Args:
            ratio: 当前缩放比
            anchor: 缩放锚点 (QPointF)
            start_rect: 缩放开始时的联合边界 (QRectF)
            corner: 正在拖拽的角 ("tl"/"tr"/"bl"/"br")
        Returns:
            修正后的 ratio
        """
        view_scale = self.transform().m11()
        if view_scale < 0.001:
            view_scale = 1.0
        threshold = self._snap_threshold / view_scale

        # 根据当前 ratio 计算缩放后的边界
        # 缩放后的点 = anchor + (原始点 - anchor) * ratio
        def scaled_val(original):
            """将原始坐标通过 anchor 和 ratio 映射到缩放后的坐标"""
            return anchor.x() + (original - anchor.x()) * ratio if True else 0

        # 计算缩放后边界 / Compute scaled bounds
        s_left = anchor.x() + (start_rect.left() - anchor.x()) * ratio
        s_right = anchor.x() + (start_rect.right() - anchor.x()) * ratio
        s_top = anchor.y() + (start_rect.top() - anchor.y()) * ratio
        s_bottom = anchor.y() + (start_rect.bottom() - anchor.y()) * ratio

        # 根据 corner 确定哪些边在移动 / Determine which edges are moving
        # tl: 左上角拖拽 → left 和 top 在移动
        # tr: 右上角拖拽 → right 和 top 在移动
        # bl: 左下角拖拽 → left 和 bottom 在移动
        # br: 右下角拖拽 → right 和 bottom 在移动
        moving_x_edges = []  # [(scaled_value, original_value)]
        moving_y_edges = []
        
        if corner in ("tl", "bl"):
            moving_x_edges.append((s_left, start_rect.left()))
        if corner in ("tr", "br"):
            moving_x_edges.append((s_right, start_rect.right()))
        if corner in ("tl", "tr"):
            moving_y_edges.append((s_top, start_rect.top()))
        if corner in ("bl", "br"):
            moving_y_edges.append((s_bottom, start_rect.bottom()))

        # 寻找最近的 X 方向吸附 / Find nearest X snap for moving edges
        best_snap_x = None  # (guide_value, scaled_edge_value, original_edge_value, distance)
        for s_val, orig_val in moving_x_edges:
            result = self._findNearestGuide(self._snap_x_guides, s_val, threshold)
            if result:
                guide_val, dist = result
                if best_snap_x is None or dist < best_snap_x[3]:
                    best_snap_x = (guide_val, s_val, orig_val, dist)

        # 寻找最近的 Y 方向吸附 / Find nearest Y snap
        best_snap_y = None
        for s_val, orig_val in moving_y_edges:
            result = self._findNearestGuide(self._snap_y_guides, s_val, threshold)
            if result:
                guide_val, dist = result
                if best_snap_y is None or dist < best_snap_y[3]:
                    best_snap_y = (guide_val, s_val, orig_val, dist)

        # 通过吸附修正 ratio / Correct ratio via snap
        # 如果边缘吸附到参考线, 需要反算新的 ratio:
        #   guide_val = anchor + (original_edge - anchor) * new_ratio
        #   new_ratio = (guide_val - anchor) / (original_edge - anchor)
        corrected_ratios = []

        if best_snap_x:
            guide_val, _, orig_val, _ = best_snap_x
            denom = orig_val - anchor.x()
            if abs(denom) > 1e-3:
                corrected_ratios.append((guide_val - anchor.x()) / denom)

        if best_snap_y:
            guide_val, _, orig_val, _ = best_snap_y
            denom = orig_val - anchor.y()
            if abs(denom) > 1e-3:
                corrected_ratios.append((guide_val - anchor.y()) / denom)

        # 选择距离原始 ratio 最近的修正值（优先吸附最接近的边）
        if corrected_ratios:
            # 取离原始 ratio 偏差最小的修正 / Pick the correction closest to original ratio
            best_ratio = min(corrected_ratios, key=lambda r: abs(r - ratio))
            ratio = best_ratio

        # 重新计算缩放后边界用于辅助线绘制 / Recalculate scaled bounds with corrected ratio
        s_left = anchor.x() + (start_rect.left() - anchor.x()) * ratio
        s_right = anchor.x() + (start_rect.right() - anchor.x()) * ratio
        s_top = anchor.y() + (start_rect.top() - anchor.y()) * ratio
        s_bottom = anchor.y() + (start_rect.bottom() - anchor.y()) * ratio

        # 构建辅助线 / Build snap guide lines for display
        new_snap_lines = []

        if best_snap_x:
            guide_x = best_snap_x[0]
            # 用修正后的 ratio 重新检查是否仍在吸附范围
            line_top = min(s_top, self._getGuideExtentMin('y', guide_x)) - 20 / view_scale
            line_bottom = max(s_bottom, self._getGuideExtentMax('y', guide_x)) + 20 / view_scale
            new_snap_lines.append(('x', guide_x, line_top, line_bottom))

        if best_snap_y:
            guide_y = best_snap_y[0]
            line_left = min(s_left, self._getGuideExtentMin('x', guide_y)) - 20 / view_scale
            line_right = max(s_right, self._getGuideExtentMax('x', guide_y)) + 20 / view_scale
            new_snap_lines.append(('y', guide_y, line_left, line_right))

        self._active_snap_lines = new_snap_lines
        self.scheduleViewportUpdate()

        return ratio

    def _getGuideExtentMin(self, axis, snap_value):
        """
        获取对齐到指定值的所有参考物体在另一轴的最小值（使用缓存）
        Get min extent of all reference items aligned to snap_value on the other axis (cached).
        """
        min_val = float('inf')
        cached_rects = getattr(self, '_snap_item_rects', {})
        guides = self._snap_x_guides if axis == 'y' else self._snap_y_guides
        
        for guide_val, iid in guides:
            if abs(guide_val - snap_value) < 1:
                r = cached_rects.get(iid)
                if r is None:
                    continue
                if axis == 'y':  # snap_value 是 X，找 Y 的范围
                    min_val = min(min_val, r.top())
                else:  # snap_value 是 Y，找 X 的范围
                    min_val = min(min_val, r.left())
        return min_val if min_val != float('inf') else 0

    def _getGuideExtentMax(self, axis, snap_value):
        """
        获取对齐到指定值的所有参考物体在另一轴的最大值（使用缓存）
        Get max extent of all reference items aligned to snap_value on the other axis (cached).
        """
        max_val = float('-inf')
        cached_rects = getattr(self, '_snap_item_rects', {})
        guides = self._snap_x_guides if axis == 'y' else self._snap_y_guides
        
        for guide_val, iid in guides:
            if abs(guide_val - snap_value) < 1:
                r = cached_rects.get(iid)
                if r is None:
                    continue
                if axis == 'y':  # snap_value 是 X，找 Y 的范围
                    max_val = max(max_val, r.bottom())
                else:  # snap_value 是 Y，找 X 的范围
                    max_val = max(max_val, r.right())
        return max_val if max_val != float('-inf') else 0

    def drawForeground(self, painter, rect):
        """
        绘制智能对齐辅助线 / Draw smart alignment guide lines
        """
        if not self._active_snap_lines:
            return
        
        pen = QPen(QColor(0, 187, 255, 200))  # 亮蓝色辅助线 / Bright cyan guide line
        pen.setWidthF(1.0)
        pen.setCosmetic(True)  # 恒定屏幕像素宽度 / Constant screen pixel width
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        
        for snap_line in self._active_snap_lines:
            axis, value, start, end = snap_line
            if axis == 'x':  # 垂直线 / Vertical line
                painter.drawLine(QPointF(value, start), QPointF(value, end))
            else:  # 水平线 / Horizontal line
                painter.drawLine(QPointF(start, value), QPointF(end, value))

    def _doViewportUpdate(self):
        """
        手动触发视口刷新（由定时器去抖后调用）/ Manual viewport refresh (called after timer debounce)
        """
        self.viewport().update()
    
    def scheduleViewportUpdate(self):
        """
        调度一次视口刷新（去抖：16ms 内多次调用只触发一次）/ Schedule a viewport refresh (debounced)
        """
        if not self._viewport_update_timer.isActive():
            self._viewport_update_timer.start()
    
    def markBoardBoundsDirty(self):
        """
        标记画板边界需要重新计算 / Mark board bounds as needing recalculation
        """
        self._board_bounds_dirty = True
    
    def drawBackground(self, painter, rect):
        """
        绘制背景和网格 / Draw background and grid
        优化：画板有固定边界，只在画板内绘制网格，图片移出画板时画板扩展
        使用 _display_board_bounds（插值动画边界）进行绘制
        
        修复黑边累积问题：在亚克力模式下，OpenGL 帧缓冲区不会在帧之间自动清除，
        导致之前帧的残留内容累积，形成越来越粗的黑边。
        解决方案：每次 drawBackground 调用时，先清除整个 rect 区域，
        然后再分层绘制画板背景和边框。
        """
        # 仅在脏标记时更新画板边界 / Only update board bounds when dirty
        if self._board_bounds_dirty:
            old_bounds = QRectF(self._board_bounds)
            self._updateBoardBounds()
            self._board_bounds_dirty = False
            
            # 检测是否发生了扩展，如有则启动动画 / Detect expansion and start animation
            if self._board_bounds != old_bounds:
                self._startBoardBoundsAnimation()
        
        # 使用显示边界（动画插值中的边界）进行绘制 / Use display bounds (animated) for drawing
        display_bounds = self._display_board_bounds
        
        # 填充非活动区域 / Fill inactive area
        if Config.acrylic_enabled:
            # 亚克力模式：先用 CompositionMode_Source 清除整个 rect 区域，
            # 防止 OpenGL 帧缓冲区中之前帧的残留内容累积导致黑边越来越粗
            # Acrylic mode: clear entire rect first with CompositionMode_Source,
            # preventing OpenGL framebuffer residue from accumulating across frames
            painter.save()
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(rect, QColor(0, 0, 0, 0))
            painter.restore()
        else:
            painter.fillRect(rect, Config.inactive_bg_color)
        
        # 计算可见区域与画板的交集 / Calculate intersection of visible area and board
        visible_board_rect = rect.intersected(display_bounds)
        
        if visible_board_rect.isEmpty():
            # 画板不在可见范围内 / Board not visible
            return
        
        # 填充画板背景 / Fill board background
        painter.fillRect(visible_board_rect, Config.bg_color)
        
        # 绘制画板边框（帮助用户识别画板边界） / Draw board border
        border_pen = QPen(QColor(80, 80, 80), 1)
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        painter.drawRect(display_bounds)
        
        if Config.grid_enabled:
            # 根据画板主题绘制不同风格的网格 / Draw grid based on canvas theme
            if Config.canvas_theme == "ue5_blueprint":
                self._drawUE5BlueprintGrid(painter, visible_board_rect)
            else:
                # 默认点阵网格 / Default dot grid
                self._drawGridInRect(painter, visible_board_rect)
    
    def _updateBoardBounds(self):
        """
        更新画板边界，只扩展不收缩 / Update board bounds, expand only never shrink
        当图片移出画板边界时，扩展画板以包含该图片
        """
        items = [item for item in self.scene().items() if isinstance(item, RefItem)]
        
        if not items:
            return  # 没有图片时保持当前画板大小
        
        # 计算所有图片的边界框 / Calculate bounding box of all images
        padding = Config.active_area_padding
        
        for item in items:
            item_rect = item.sceneBoundingRect()
            # 添加边距 / Add padding
            item_rect.adjust(-padding, -padding, padding, padding)
            
            # 扩展画板边界以包含此图片（只扩展不收缩）
            # Expand board bounds to include this image (expand only)
            if item_rect.left() < self._board_bounds.left():
                # 左边扩展
                new_left = item_rect.left()
                new_width = self._board_bounds.right() - new_left
                self._board_bounds.setLeft(new_left)
                self._board_bounds.setWidth(new_width)
            
            if item_rect.right() > self._board_bounds.right():
                # 右边扩展
                self._board_bounds.setRight(item_rect.right())
            
            if item_rect.top() < self._board_bounds.top():
                # 上边扩展
                new_top = item_rect.top()
                new_height = self._board_bounds.bottom() - new_top
                self._board_bounds.setTop(new_top)
                self._board_bounds.setHeight(new_height)
            
            if item_rect.bottom() > self._board_bounds.bottom():
                # 下边扩展
                self._board_bounds.setBottom(item_rect.bottom())
    
    def _startBoardBoundsAnimation(self):
        """
        启动画板边界扩展动画 / Start board bounds expansion animation
        当逻辑边界 _board_bounds 变化时调用，_display_board_bounds 平滑过渡到目标
        """
        if not self._board_anim_timer.isActive():
            self._board_anim_timer.start()
    
    def _animateBoardBounds(self):
        """
        画板边界动画帧回调（由 _board_anim_timer 驱动，~60fps）
        Board bounds animation frame callback (driven by _board_anim_timer, ~60fps)
        对 _display_board_bounds 的四条边分别做 lerp 插值趋近 _board_bounds
        """
        t = self._board_anim_lerp_speed
        target = self._board_bounds
        current = self._display_board_bounds
        
        # 四条边分别插值 / Lerp each edge independently
        new_left = current.left() + (target.left() - current.left()) * t
        new_top = current.top() + (target.top() - current.top()) * t
        new_right = current.right() + (target.right() - current.right()) * t
        new_bottom = current.bottom() + (target.bottom() - current.bottom()) * t
        
        self._display_board_bounds = QRectF(
            QPointF(new_left, new_top),
            QPointF(new_right, new_bottom)
        )
        
        # 检查是否已收敛（所有边的差值 < 0.5 像素）/ Check convergence
        epsilon = 0.5
        if (abs(new_left - target.left()) < epsilon and
            abs(new_top - target.top()) < epsilon and
            abs(new_right - target.right()) < epsilon and
            abs(new_bottom - target.bottom()) < epsilon):
            # 动画完成，直接对齐到目标 / Animation done, snap to target
            self._display_board_bounds = QRectF(target)
            self._board_anim_timer.stop()
        
        # 触发重绘 / Trigger repaint
        self.scheduleViewportUpdate()
    
    def resetBoardBounds(self):
        """
        重置画板边界为初始大小 / Reset board bounds to initial size
        """
        half_w = Config.initial_board_width / 2
        half_h = Config.initial_board_height / 2
        self._board_bounds = QRectF(-half_w, -half_h, Config.initial_board_width, Config.initial_board_height)
        # 重置时也启动动画过渡 / Also animate when resetting
        self._startBoardBoundsAnimation()
    
    def resetBoardToFitImages(self):
        """
        根据实际图片分布重置画板大小 / Reset board size based on actual image distribution
        如果没有图片，则重置为默认大小
        """
        items = [item for item in self.scene().items() if isinstance(item, RefItem)]
        
        if not items:
            # 没有图片时重置为默认大小
            self.resetBoardBounds()
            self.viewport().update()
            return
        
        # 计算所有图片的边界框 / Calculate bounding box of all images
        union_rect = QRectF()
        for item in items:
            union_rect = union_rect.united(item.sceneBoundingRect())
        
        # 添加边距 / Add padding
        padding = Config.active_area_padding
        union_rect.adjust(-padding, -padding, padding, padding)
        
        # 确保最小尺寸不小于初始大小 / Ensure minimum size is not smaller than initial size
        min_width = Config.initial_board_width
        min_height = Config.initial_board_height
        
        # 计算中心点
        center = union_rect.center()
        
        # 如果计算出的尺寸小于最小尺寸，则扩展到最小尺寸
        final_width = max(union_rect.width(), min_width)
        final_height = max(union_rect.height(), min_height)
        
        # 以图片区域中心为中心创建新的画板边界
        self._board_bounds = QRectF(
            center.x() - final_width / 2,
            center.y() - final_height / 2,
            final_width,
            final_height
        )
        
        # 重置适配时启动动画过渡 / Animate when fitting to images
        self._startBoardBoundsAnimation()
        self.scheduleViewportUpdate()
    
    def _drawUE5BlueprintGrid(self, painter, rect):
        """
        绘制 UE5.4 蓝图编辑器风格的网格背景（使用 Config 可配置参数）
        Draw UE5.4 Blueprint editor style grid background (using Config settings)
        特征：深蓝黑底色 + 细线小网格 + 粗线大网格，配色贴合真实 UE5.4
        修复：缩放自适应线宽与透明度，防止缩小时线条变粗/溢出
        """
        view_scale = self.transform().m11()
        if view_scale < 0.001:
            view_scale = 0.001

        # --- 从 Config 读取 UE5 蓝图主题参数 ---
        painter.fillRect(rect, Config.ue5_bg_color)

        small_grid_base = Config.grid_size
        large_grid_multiplier = Config.ue5_large_grid_multiplier

        # --- LOD 策略（提高阈值，缩小时更积极合并）---
        # 小网格：屏幕间距 < 12px 时翻倍合并
        effective_small = small_grid_base
        while (effective_small * view_scale) < 12:
            effective_small *= 2

        large_grid_size = small_grid_base * large_grid_multiplier
        effective_large = large_grid_size
        # 大网格：屏幕间距 < 50px 时翻倍合并
        while (effective_large * view_scale) < 50:
            effective_large *= 2

        # --- 缩放自适应线宽 ---
        # 当缩放 < 1.0 时，线宽按比例衰减（最小 0.5px），防止线条视觉堆叠
        scale_factor = min(1.0, max(view_scale, 0.1))
        # 平滑衰减：在 0.1~1.0 范围内线性插值
        width_factor = 0.5 + 0.5 * ((scale_factor - 0.1) / 0.9) if scale_factor < 1.0 else 1.0

        small_line_w = max(0.5, Config.ue5_small_line_width * width_factor)
        large_line_w = max(0.5, Config.ue5_large_line_width * width_factor)

        # --- 缩放自适应透明度 ---
        # 当缩放 < 0.3 时，透明度开始衰减，极端缩放下线条渐隐
        alpha_factor = min(1.0, max(0.0, (view_scale - 0.05) / 0.25)) if view_scale < 0.3 else 1.0

        small_grid_color = QColor(Config.ue5_small_grid_color)
        small_grid_color.setAlpha(int(Config.ue5_small_line_alpha * alpha_factor))

        large_grid_color = QColor(Config.ue5_large_grid_color)
        large_grid_color.setAlpha(int(Config.ue5_large_line_alpha * alpha_factor))

        # --- 绘制小网格线 ---
        left = int(rect.left()) - (int(rect.left()) % effective_small)
        if left < rect.left():
            left += effective_small
        top_val = int(rect.top()) - (int(rect.top()) % effective_small)
        if top_val < rect.top():
            top_val += effective_small
        right = int(rect.right())
        bottom = int(rect.bottom())

        # 安全上限 / Safety cap
        h_lines = max(1, (bottom - top_val) // effective_small + 1)
        v_lines = max(1, (right - left) // effective_small + 1)
        if h_lines + v_lines < 3000 and small_grid_color.alpha() > 5:
            small_pen = QPen(small_grid_color, small_line_w)
            small_pen.setCosmetic(True)
            painter.setPen(small_pen)
            # 垂直线 / Vertical lines
            x = left
            while x <= right:
                if x % effective_large != 0:
                    painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
                x += effective_small
            # 水平线 / Horizontal lines
            y = top_val
            while y <= bottom:
                if y % effective_large != 0:
                    painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
                y += effective_small

        # --- 绘制大网格线 ---
        left_l = int(rect.left()) - (int(rect.left()) % effective_large)
        if left_l < rect.left():
            left_l += effective_large
        top_l = int(rect.top()) - (int(rect.top()) % effective_large)
        if top_l < rect.top():
            top_l += effective_large

        if large_grid_color.alpha() > 5:
            large_pen = QPen(large_grid_color, large_line_w)
            large_pen.setCosmetic(True)
            painter.setPen(large_pen)
            # 垂直粗线 / Vertical thick lines
            x = left_l
            while x <= right:
                painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
                x += effective_large
            # 水平粗线 / Horizontal thick lines
            y = top_l
            while y <= bottom:
                painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
                y += effective_large

    def _drawGridInRect(self, painter, rect):
        """
        在指定区域内绘制网格点（LOD 翻倍策略 + 无逐点检查）
        Draw grid dots within specified rect (LOD doubling strategy + no per-point check)
        借鉴 macOS 版本的 LOD 机制：当屏幕上的点间距 < 15px 时翻倍间距
        """
        # 获取当前缩放级别 / Get current zoom level
        view_scale = self.transform().m11()
        if view_scale < 0.001:
            view_scale = 0.001
        
        # LOD 翻倍策略（借鉴 macOS）：保证屏幕上的点间距 >= 15px
        # LOD doubling (from macOS): ensure screen dot spacing >= 15px
        effective_spacing = Config.grid_size
        while (effective_spacing * view_scale) < 15:
            effective_spacing *= 2
        grid_size = effective_spacing
        
        # 精确计算网格对齐的起止范围（避免逐点 rect.contains 检查）
        # Precisely compute grid-aligned start/end (avoid per-point rect.contains)
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        if left < rect.left():
            left += grid_size
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        if top < rect.top():
            top += grid_size
        right = int(rect.right())
        bottom = int(rect.bottom())
        
        # 安全上限：如果点数仍然过多则进一步翻倍间距
        # Safety cap: further double spacing if too many points
        cols = max(1, (right - left) // grid_size + 1)
        rows = max(1, (bottom - top) // grid_size + 1)
        while cols * rows > 5000:
            grid_size *= 2
            left = int(rect.left()) - (int(rect.left()) % grid_size)
            if left < rect.left():
                left += grid_size
            top = int(rect.top()) - (int(rect.top()) % grid_size)
            if top < rect.top():
                top += grid_size
            cols = max(1, (right - left) // grid_size + 1)
            rows = max(1, (bottom - top) // grid_size + 1)
        
        # 直接生成所有点（无需逐点检查 rect.contains）
        # Generate all points directly (no per-point rect.contains needed)
        points = []
        x = left
        while x <= right:
            y = top
            while y <= bottom:
                points.append(QPointF(x, y))
                y += grid_size
            x += grid_size
        
        if points:
            painter.setPen(QPen(Config.grid_color, Config.dot_size))
            painter.drawPoints(points)

    def wheelEvent(self, event):
        """
        处理滚轮事件，用于缩放画布 / Handle wheel event for zooming canvas
        """
        # Wheel -> Zoom Canvas
        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale(zoom_factor, zoom_factor)
        self.scheduleViewportUpdate()

    def mouseDoubleClickEvent(self, event):
        """
        处理双击事件：优先检查是否双击到了组名称标签 / Handle double click: check group name label first
        因为 GroupItem 的 zValue 为 -100（在图片下方），且 RubberBandDrag 模式会拦截空白区域的事件，
        所以必须在 View 层主动检查并分发事件到 GroupItem
        """
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            # 获取当前缩放级别 / Get current zoom level (lod)
            lod = self.transform().m11()  # 水平缩放因子即为 lod
            if lod < 0.00001:
                lod = 1
            # 遍历所有 GroupItem，检查是否双击到了名称标签区域
            for item in self.scene().items():
                if isinstance(item, GroupItem) and item.group_name:
                    # 将场景坐标转换为 GroupItem 的 item 局部坐标
                    local_pos = item.mapFromScene(scene_pos)
                    if item._name_label_local_rect(lod).contains(local_pos):
                        item._edit_name()
                        event.accept()
                        return
        super().mouseDoubleClickEvent(event)

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
        
        # Shift+Click -> Multi-select (Manual Logic)
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier):
            item = self.itemAt(event.position().toPoint())
            if item and (item.flags() & QGraphicsItem.ItemIsSelectable):
                # Save current selection
                previous_selection = self.scene().selectedItems()
                was_selected = item.isSelected()
                
                # Call super to handle drag initiation and standard click behavior
                # (which usually clears selection and selects the clicked item)
                super().mousePressEvent(event)
                
                # Restore previous selection
                for prev_item in previous_selection:
                    prev_item.setSelected(True)
                
                # Toggle the clicked item
                # If it was selected, we want it deselected.
                # If it was not selected, we want it selected.
                item.setSelected(not was_selected)
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
            self.scheduleViewportUpdate()
            event.accept()
            return
            
        super().mouseMoveEvent(event)
        # 注：super().mouseMoveEvent() 内部已通过 ItemSendsGeometryChanges 触发场景更新，
        # Smart Guides 的 _performSnap 也会调用 scheduleViewportUpdate()，
        # 此处不再无条件调用，避免双重重绘。
        # Note: super().mouseMoveEvent() already triggers scene updates via ItemSendsGeometryChanges,
        # and Smart Guides' _performSnap also calls scheduleViewportUpdate(),
        # so we no longer unconditionally call it here to avoid double redraws.
        # 但在 NoViewportUpdate 模式下，仍需确保至少有一次调度
        # However, in NoViewportUpdate mode, we still need to ensure at least one scheduled update
        if not self._viewport_update_timer.isActive():
            self.scheduleViewportUpdate()

    def mouseReleaseEvent(self, event):
        """
        处理鼠标释放事件 / Handle mouse release
        """
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            self.scheduleViewportUpdate()
            event.accept()
            return
            
        super().mouseReleaseEvent(event)
        self.scheduleViewportUpdate()

    def keyPressEvent(self, event):
        """
        处理按键按下事件 (空格键平移, G键打组) / Handle key press (Space for panning, G for grouping)
        """
        if event.key() == Qt.Key_Space:
            self._space_pressed = True
            if not self._is_panning:
                self.setCursor(Qt.OpenHandCursor)
        elif event.key() == Qt.Key_G:
            # G键打组 / G key to group
            if hasattr(self, 'parent') and self.parent():
                main_window = self.parent()
                if hasattr(main_window, 'group_selected_items'):
                    main_window.group_selected_items()
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
