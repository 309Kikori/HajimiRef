import base64
from PySide6.QtWidgets import (QGraphicsView, QGraphicsPixmapItem, QGraphicsItem, QStyleOptionGraphicsItem)
from PySide6.QtCore import Qt, QByteArray, QBuffer, QPointF, QRectF, QMimeData, QLineF
from PySide6.QtGui import QPixmap, QImage, QPainter, QCursor, QColor, QPen, QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from Config import Config, tr

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
            
            # Store start scale and pos for all selected items
            for item in selected_items:
                if isinstance(item, RefItem):
                    item._start_scale = item.scale()
                    item._start_pos = item.scenePos()
            
            event.accept()
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
            # Clean up temp attributes
            for item in self.scene().selectedItems():
                if isinstance(item, RefItem):
                    if hasattr(item, '_start_scale'): del item._start_scale
                    if hasattr(item, '_start_pos'): del item._start_pos
            event.accept()
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
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)
        
        # Background
        # self.setBackgroundBrush(Qt.darkGray) # Handled in drawBackground
        
        # State
        self._is_panning = False
        self._pan_start = QPointF()
        self._space_pressed = False

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
        """
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
