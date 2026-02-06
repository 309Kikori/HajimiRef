"""
撤销/重做管理器 / Undo/Redo Manager
使用命令模式记录和恢复操作 / Use Command Pattern to record and restore operations
"""

from abc import ABC, abstractmethod
from PySide6.QtCore import QPointF
from typing import List, Dict, Any, Optional
import copy


class Command(ABC):
    """
    命令基类 / Base command class
    """
    @abstractmethod
    def undo(self):
        """撤销操作 / Undo operation"""
        pass
    
    @abstractmethod
    def redo(self):
        """重做操作 / Redo operation"""
        pass
    
    @abstractmethod
    def description(self) -> str:
        """操作描述 / Operation description"""
        pass


class MoveCommand(Command):
    """
    移动图片命令 / Move image command
    """
    def __init__(self, items_positions: List[tuple]):
        """
        items_positions: [(item, old_pos, new_pos), ...]
        """
        self._items_positions = items_positions
    
    def undo(self):
        for item, old_pos, new_pos in self._items_positions:
            if item.scene():  # 确保 item 仍在场景中
                item.setPos(old_pos)
    
    def redo(self):
        for item, old_pos, new_pos in self._items_positions:
            if item.scene():
                item.setPos(new_pos)
    
    def description(self) -> str:
        return f"移动 {len(self._items_positions)} 个图片"


class ScaleCommand(Command):
    """
    缩放图片命令 / Scale image command
    """
    def __init__(self, items_scales: List[tuple]):
        """
        items_scales: [(item, old_scale, new_scale, old_pos, new_pos), ...]
        注意：缩放时位置也可能改变（锚点缩放）
        """
        self._items_scales = items_scales
    
    def undo(self):
        for item, old_scale, new_scale, old_pos, new_pos in self._items_scales:
            if item.scene():
                item.setScale(old_scale)
                item.setPos(old_pos)
    
    def redo(self):
        for item, old_scale, new_scale, old_pos, new_pos in self._items_scales:
            if item.scene():
                item.setScale(new_scale)
                item.setPos(new_pos)
    
    def description(self) -> str:
        return f"缩放 {len(self._items_scales)} 个图片"


class AddItemCommand(Command):
    """
    添加图片命令 / Add image command
    """
    def __init__(self, scene, item):
        self._scene = scene
        self._item = item
        self._pos = item.pos()
        self._scale = item.scale()
        self._rotation = item.rotation()
    
    def undo(self):
        if self._item.scene():
            self._scene.removeItem(self._item)
    
    def redo(self):
        if not self._item.scene():
            self._scene.addItem(self._item)
            self._item.setPos(self._pos)
            self._item.setScale(self._scale)
            self._item.setRotation(self._rotation)
    
    def description(self) -> str:
        return "添加图片"


class DeleteItemsCommand(Command):
    """
    删除图片命令 / Delete images command
    """
    def __init__(self, scene, items: List):
        self._scene = scene
        # 保存每个 item 的状态
        self._items_data = []
        for item in items:
            self._items_data.append({
                'item': item,
                'pos': item.pos(),
                'scale': item.scale(),
                'rotation': item.rotation()
            })
    
    def undo(self):
        # 恢复所有删除的图片
        for data in self._items_data:
            item = data['item']
            if not item.scene():
                self._scene.addItem(item)
                item.setPos(data['pos'])
                item.setScale(data['scale'])
                item.setRotation(data['rotation'])
    
    def redo(self):
        # 重新删除所有图片
        for data in self._items_data:
            item = data['item']
            if item.scene():
                self._scene.removeItem(item)
    
    def description(self) -> str:
        return f"删除 {len(self._items_data)} 个图片"


class ClearBoardCommand(Command):
    """
    清空画布命令 / Clear board command
    """
    def __init__(self, scene, items: List):
        self._scene = scene
        # 保存所有 item 的状态
        self._items_data = []
        for item in items:
            self._items_data.append({
                'item': item,
                'pos': item.pos(),
                'scale': item.scale(),
                'rotation': item.rotation()
            })
    
    def undo(self):
        # 恢复所有图片
        for data in self._items_data:
            item = data['item']
            if not item.scene():
                self._scene.addItem(item)
                item.setPos(data['pos'])
                item.setScale(data['scale'])
                item.setRotation(data['rotation'])
    
    def redo(self):
        # 重新清空
        for data in self._items_data:
            item = data['item']
            if item.scene():
                self._scene.removeItem(item)
    
    def description(self) -> str:
        return f"清空画布 ({len(self._items_data)} 个图片)"


class OrganizeItemsCommand(Command):
    """
    整理图片命令 / Organize items command
    """
    def __init__(self, items_positions: List[tuple]):
        """
        items_positions: [(item, old_pos, new_pos), ...]
        """
        self._items_positions = items_positions
    
    def undo(self):
        for item, old_pos, new_pos in self._items_positions:
            if item.scene():
                item.setPos(old_pos)
    
    def redo(self):
        for item, old_pos, new_pos in self._items_positions:
            if item.scene():
                item.setPos(new_pos)
    
    def description(self) -> str:
        return f"整理 {len(self._items_positions)} 个图片"


class GroupCommand(Command):
    """
    打组命令 / Group command
    """
    def __init__(self, scene, group_item, members: List, groups_dict: Dict):
        self._scene = scene
        self._group_item = group_item
        self._members = members
        self._groups_dict = groups_dict
        self._group_id = group_item.group_id
    
    def undo(self):
        # 移除成员的组ID / Remove group ID from members
        for item in self._members:
            if hasattr(item, 'group_id'):
                item.group_id = None
        
        # 从场景和字典中移除组 / Remove group from scene and dict
        if self._group_item.scene():
            self._scene.removeItem(self._group_item)
        if self._group_id in self._groups_dict:
            del self._groups_dict[self._group_id]
    
    def redo(self):
        # 恢复成员的组ID / Restore group ID to members
        for item in self._members:
            if hasattr(item, 'group_id'):
                item.group_id = self._group_id
        
        # 重新添加组到场景和字典 / Re-add group to scene and dict
        if not self._group_item.scene():
            self._scene.addItem(self._group_item)
        self._groups_dict[self._group_id] = self._group_item
        
        # 更新组边界 / Update group bounds
        self._group_item.update_bounds(self._members)
    
    def description(self) -> str:
        return f"打组 {len(self._members)} 个图片"


class UngroupCommand(Command):
    """
    解散组命令 / Ungroup command
    """
    def __init__(self, scene, group_item, members: List, groups_dict: Dict):
        self._scene = scene
        self._group_item = group_item
        self._members = members
        self._groups_dict = groups_dict
        self._group_id = group_item.group_id
        
        # 保存组的状态 / Save group state
        self._group_name = group_item.group_name
        self._group_color = group_item.group_color
        self._group_opacity = group_item.group_opacity
        self._font_size = group_item.font_size
        self._rect = group_item.rect()
    
    def undo(self):
        # 恢复成员的组ID / Restore group ID to members
        for item in self._members:
            if hasattr(item, 'group_id'):
                item.group_id = self._group_id
        
        # 重新添加组到场景和字典 / Re-add group to scene and dict
        if not self._group_item.scene():
            self._scene.addItem(self._group_item)
        self._groups_dict[self._group_id] = self._group_item
    
    def redo(self):
        # 移除成员的组ID / Remove group ID from members
        for item in self._members:
            if hasattr(item, 'group_id'):
                item.group_id = None
        
        # 从场景和字典中移除组 / Remove group from scene and dict
        if self._group_item.scene():
            self._scene.removeItem(self._group_item)
        if self._group_id in self._groups_dict:
            del self._groups_dict[self._group_id]
    
    def description(self) -> str:
        return f"解散组 ({len(self._members)} 个图片)"


class GroupMoveCommand(Command):
    """
    移动组命令 / Group move command
    """
    def __init__(self, group_item, old_pos: QPointF, new_pos: QPointF, members_data: List[tuple]):
        """
        members_data: [(item, old_pos, new_pos), ...]
        """
        self._group_item = group_item
        self._old_pos = old_pos
        self._new_pos = new_pos
        self._members_data = members_data
    
    def undo(self):
        # 恢复组位置 / Restore group position
        delta = self._old_pos - self._new_pos
        rect = self._group_item.rect()
        rect.translate(delta)
        self._group_item.setRect(rect)
        
        # 恢复所有成员位置 / Restore all member positions
        for item, old_pos, new_pos in self._members_data:
            if item.scene():
                item.setPos(old_pos)
    
    def redo(self):
        # 应用组位置 / Apply group position
        delta = self._new_pos - self._old_pos
        rect = self._group_item.rect()
        rect.translate(delta)
        self._group_item.setRect(rect)
        
        # 应用所有成员位置 / Apply all member positions
        for item, old_pos, new_pos in self._members_data:
            if item.scene():
                item.setPos(new_pos)
    
    def description(self) -> str:
        return f"移动组 ({len(self._members_data)} 个图片)"


class UndoManager:
    """
    撤销/重做管理器 / Undo/Redo manager
    """
    def __init__(self, max_history: int = 100):
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_history = max_history
    
    def execute(self, command: Command):
        """
        执行命令并记录到历史 / Execute command and record to history
        """
        command.redo()  # 执行操作
        self._undo_stack.append(command)
        self._redo_stack.clear()  # 新操作清空重做栈
        
        # 限制历史记录数量
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
    
    def push(self, command: Command):
        """
        仅记录命令到历史（不执行）/ Only record command to history (don't execute)
        用于记录已经执行过的操作
        """
        self._undo_stack.append(command)
        self._redo_stack.clear()
        
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
    
    def undo(self) -> bool:
        """
        撤销操作 / Undo operation
        返回是否成功
        """
        if not self._undo_stack:
            return False
        
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        return True
    
    def redo(self) -> bool:
        """
        重做操作 / Redo operation
        返回是否成功
        """
        if not self._redo_stack:
            return False
        
        command = self._redo_stack.pop()
        command.redo()
        self._undo_stack.append(command)
        return True
    
    def can_undo(self) -> bool:
        """是否可以撤销 / Can undo"""
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """是否可以重做 / Can redo"""
        return len(self._redo_stack) > 0
    
    def clear(self):
        """清空历史 / Clear history"""
        self._undo_stack.clear()
        self._redo_stack.clear()
    
    def undo_description(self) -> Optional[str]:
        """获取撤销操作描述 / Get undo operation description"""
        if self._undo_stack:
            return self._undo_stack[-1].description()
        return None
    
    def redo_description(self) -> Optional[str]:
        """获取重做操作描述 / Get redo operation description"""
        if self._redo_stack:
            return self._redo_stack[-1].description()
        return None
