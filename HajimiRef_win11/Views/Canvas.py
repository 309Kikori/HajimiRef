import base64
import uuid
from PySide6.QtWidgets import (QGraphicsView, QGraphicsPixmapItem, QGraphicsItem, QStyleOptionGraphicsItem, 
                               QGraphicsRectItem, QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QSpinBox, QSlider, QPushButton, QColorDialog, QInputDialog)
from PySide6.QtCore import Qt, QByteArray, QBuffer, QPointF, QRectF, QMimeData, QLineF, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QCursor, QColor, QPen, QDragEnterEvent, QDropEvent, QMouseEvent, QBrush, QFont, QPainterPath
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
        
        # 成员图片ID列表 / Member image IDs
        self.member_ids = []
        
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
    
    def _name_label_local_rect(self):
        """返回名称标签在 item 局部坐标中的区域（不依赖 lod）/ Return name label rect in item local coords (lod-independent)"""
        rect = self.rect()
        label_height = self.font_size + 20  # 足够容纳标签
        return QRectF(rect.left(), rect.top() - label_height, max(rect.width(), 200), label_height)
    
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
    
    def add_member(self, item):
        """添加成员到组 / Add member to group"""
        if hasattr(item, 'group_id'):
            item.group_id = self.group_id
            if item not in self.member_ids:
                self.member_ids.append(id(item))
    
    def remove_member(self, item):
        """从组中移除成员 / Remove member from group"""
        if hasattr(item, 'group_id') and item.group_id == self.group_id:
            item.group_id = None
            if id(item) in self.member_ids:
                self.member_ids.remove(id(item))
    
    def update_bounds(self, items):
        """根据成员项目更新组边界 / Update group bounds based on member items"""
        if not items:
            return
        
        # 计算所有成员的边界 / Calculate bounds of all members
        padding = 20
        union_rect = QRectF()
        for item in items:
            if isinstance(item, RefItem) and hasattr(item, 'group_id') and item.group_id == self.group_id:
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
            
            # 同时记录所有成员的起始位置 / Record start positions of all members
            self._members_start_pos = {}
            scene = self.scene()
            if scene:
                for item in scene.items():
                    if isinstance(item, RefItem) and hasattr(item, 'group_id') and item.group_id == self.group_id:
                        self._members_start_pos[id(item)] = QPointF(item.pos())
        
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """处理双击事件，双击名称标签快速编辑 / Handle double click, edit name label"""
        if event.button() == Qt.LeftButton and self.group_name:
            click_pos = event.pos()  # item 局部坐标 / Item local coordinates
            if self._name_label_local_rect().contains(click_pos):
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
            # 计算移动量（基于 pos() 的变化）/ Calculate movement delta (based on pos() change)
            delta = self.pos() - self._undo_start_pos
            
            # 移动所有成员 / Move all members
            scene = self.scene()
            if scene:
                for item in scene.items():
                    if isinstance(item, RefItem) and hasattr(item, 'group_id') and item.group_id == self.group_id:
                        if id(item) in self._members_start_pos:
                            item.setPos(self._members_start_pos[id(item)] + delta)
        
        super().mouseMoveEvent(event)
    
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
            
            self._undo_start_pos = None
            self._members_start_pos = {}
        
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
            for item in selected_items:
                if isinstance(item, RefItem):
                    item._start_scale = item.scale()
                    item._start_pos = item.scenePos()
                    # 记录撤销状态 / Record undo state
                    item._undo_start_pos = QPointF(item.pos())
                    item._undo_start_scale = item.scale()
            
            event.accept()
        elif event.button() == Qt.LeftButton:
            # 记录拖动开始状态（用于撤销）/ Record drag start state (for undo)
            self._is_dragging = True
            selected_items = self.scene().selectedItems()
            for item in selected_items:
                if isinstance(item, RefItem):
                    item._undo_start_pos = QPointF(item.pos())
                    item._undo_start_scale = item.scale()
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
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        处理鼠标释放事件，结束调整大小 / Handle mouse release, finish resizing
        """
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
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)
        
        # Background
        # self.setBackgroundBrush(Qt.darkGray) # Handled in drawBackground
        
        # State
        self._is_panning = False
        self._pan_start = QPointF()
        self._space_pressed = False
        
        # 画板边界状态（只扩展不收缩）/ Board bounds state (expand only, never shrink)
        # 初始画板边界以原点为中心 / Initial board bounds centered at origin
        half_w = Config.initial_board_width / 2
        half_h = Config.initial_board_height / 2
        self._board_bounds = QRectF(-half_w, -half_h, Config.initial_board_width, Config.initial_board_height)
        
        # 组管理 / Group management
        self._groups = {}  # group_id -> GroupItem

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
            event.acceptProposedAction()

    def drawBackground(self, painter, rect):
        """
        绘制背景和网格 / Draw background and grid
        优化：画板有固定边界，只在画板内绘制网格，图片移出画板时画板扩展
        """
        # 更新画板边界（只扩展不收缩）/ Update board bounds (expand only)
        self._updateBoardBounds()
        
        # 先填充整个可见区域为非活动区域颜色 / Fill entire visible area with inactive color first
        painter.fillRect(rect, Config.inactive_bg_color)
        
        # 计算可见区域与画板的交集 / Calculate intersection of visible area and board
        visible_board_rect = rect.intersected(self._board_bounds)
        
        if visible_board_rect.isEmpty():
            # 画板不在可见范围内 / Board not visible
            return
        
        # 填充画板背景 / Fill board background
        painter.fillRect(visible_board_rect, Config.bg_color)
        
        # 绘制画板边框（帮助用户识别画板边界） / Draw board border
        border_pen = QPen(QColor(80, 80, 80), 1)
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        painter.drawRect(self._board_bounds)
        
        if Config.grid_enabled:
            # 只在画板内绘制网格 / Only draw grid within board
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
    
    def resetBoardBounds(self):
        """
        重置画板边界为初始大小 / Reset board bounds to initial size
        """
        half_w = Config.initial_board_width / 2
        half_h = Config.initial_board_height / 2
        self._board_bounds = QRectF(-half_w, -half_h, Config.initial_board_width, Config.initial_board_height)
    
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
        
        self.viewport().update()
    
    def _drawGridInRect(self, painter, rect):
        """
        在指定区域内绘制网格点 / Draw grid dots within specified rect
        """
        # 获取当前缩放级别 / Get current zoom level
        view_scale = self.transform().m11()
        
        # 根据缩放级别动态调整网格间隔 / Dynamically adjust grid spacing based on zoom level
        base_grid_size = Config.grid_size
        
        # 当缩放很小时，增大间隔以减少点数
        if view_scale < 1.0:
            multiplier = max(1, int(1.0 / view_scale))
            grid_size = base_grid_size * multiplier
        else:
            grid_size = base_grid_size
        
        # 限制最大绘制点数 / Limit max points
        max_points = 5000
        width = rect.width()
        height = rect.height()
        estimated_points = (width / grid_size) * (height / grid_size)
        
        if estimated_points > max_points:
            scale_factor = (estimated_points / max_points) ** 0.5
            grid_size = int(grid_size * scale_factor)
        
        # Calculate start points to align with the grid
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        
        points = []
        # Draw dots only within rect bounds
        for x in range(left, int(rect.right()) + grid_size, grid_size):
            for y in range(top, int(rect.bottom()) + grid_size, grid_size):
                if rect.contains(QPointF(x, y)):
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
