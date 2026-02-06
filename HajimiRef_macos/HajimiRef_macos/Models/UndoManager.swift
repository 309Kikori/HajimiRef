import SwiftUI
import Combine

// MARK: - Action Types (操作类型)

/// 可撤销的操作类型
enum UndoableAction {
    /// 移动图片
    case move(imageId: UUID, oldPosition: CGPoint, newPosition: CGPoint)
    
    /// 缩放图片
    case scale(imageId: UUID, oldScale: CGFloat, newScale: CGFloat)
    
    /// 旋转图片
    case rotate(imageId: UUID, oldRotation: CGFloat, newRotation: CGFloat)
    
    /// 添加图片
    case addImage(image: ImageEntity)
    
    /// 删除图片
    case removeImage(image: ImageEntity, index: Int)
    
    /// 批量移动（多选移动）
    case batchMove(changes: [(imageId: UUID, oldPosition: CGPoint, newPosition: CGPoint)])
    
    /// 批量缩放（多选缩放）
    case batchScale(changes: [(imageId: UUID, oldScale: CGFloat, newScale: CGFloat, oldPosition: CGPoint, newPosition: CGPoint)])
    
    /// 图层顺序变更
    case reorder(imageId: UUID, oldIndex: Int, newIndex: Int)
    
    /// 清空画板
    case clearBoard(images: [ImageEntity], groups: [GroupEntity])
    
    /// 创建组
    case createGroup(group: GroupEntity, memberIds: [UUID])
    
    /// 删除组
    case deleteGroup(group: GroupEntity)
    
    /// 更新组设置
    case updateGroup(oldGroup: GroupEntity, newGroup: GroupEntity)
    
    /// 移动组
    case moveGroup(groupId: UUID, oldPosition: CGPoint, newPosition: CGPoint, memberMoves: [(imageId: UUID, oldPosition: CGPoint, newPosition: CGPoint)])
}

// MARK: - Undo Manager (撤销管理器)

/// 撤销/重做管理器
@Observable
class CanvasUndoManager {
    /// 撤销栈
    private var undoStack: [UndoableAction] = []
    
    /// 重做栈
    private var redoStack: [UndoableAction] = []
    
    /// 最大历史记录数
    private let maxHistoryCount = 50
    
    /// 是否可以撤销
    var canUndo: Bool {
        !undoStack.isEmpty
    }
    
    /// 是否可以重做
    var canRedo: Bool {
        !redoStack.isEmpty
    }
    
    /// 撤销栈数量
    var undoCount: Int {
        undoStack.count
    }
    
    /// 重做栈数量
    var redoCount: Int {
        redoStack.count
    }
    
    // MARK: - Public Methods
    
    /// 记录一个可撤销的操作
    func recordAction(_ action: UndoableAction) {
        undoStack.append(action)
        
        // 限制历史记录数量
        if undoStack.count > maxHistoryCount {
            undoStack.removeFirst()
        }
        
        // 新操作会清空重做栈
        redoStack.removeAll()
    }
    
    /// 执行撤销
    func undo(appState: AppState) {
        guard let action = undoStack.popLast() else { return }
        
        // 执行撤销操作
        performUndo(action: action, appState: appState)
        
        // 将操作加入重做栈
        redoStack.append(action)
    }
    
    /// 执行重做
    func redo(appState: AppState) {
        guard let action = redoStack.popLast() else { return }
        
        // 执行重做操作
        performRedo(action: action, appState: appState)
        
        // 将操作加入撤销栈
        undoStack.append(action)
    }
    
    /// 清空历史记录
    func clearHistory() {
        undoStack.removeAll()
        redoStack.removeAll()
    }
    
    // MARK: - Private Methods
    
    /// 执行撤销操作
    private func performUndo(action: UndoableAction, appState: AppState) {
        switch action {
        case .move(let imageId, let oldPosition, _):
            // 撤销移动：恢复到旧位置
            if let index = appState.images.firstIndex(where: { $0.id == imageId }) {
                appState.images[index].x = oldPosition.x
                appState.images[index].y = oldPosition.y
            }
            
        case .scale(let imageId, let oldScale, _):
            // 撤销缩放：恢复到旧缩放值
            if let index = appState.images.firstIndex(where: { $0.id == imageId }) {
                appState.images[index].scale = oldScale
            }
            
        case .rotate(let imageId, let oldRotation, _):
            // 撤销旋转：恢复到旧角度
            if let index = appState.images.firstIndex(where: { $0.id == imageId }) {
                appState.images[index].rotation = oldRotation
            }
            
        case .addImage(let image):
            // 撤销添加：删除图片
            appState.images.removeAll { $0.id == image.id }
            appState.selectedImageIds.remove(image.id)
            
        case .removeImage(let image, let index):
            // 撤销删除：恢复图片
            let safeIndex = min(index, appState.images.count)
            appState.images.insert(image, at: safeIndex)
            
        case .batchMove(let changes):
            // 撤销批量移动：恢复所有图片到旧位置
            for change in changes {
                if let index = appState.images.firstIndex(where: { $0.id == change.imageId }) {
                    appState.images[index].x = change.oldPosition.x
                    appState.images[index].y = change.oldPosition.y
                }
            }
            
        case .batchScale(let changes):
            // 撤销批量缩放：恢复所有图片到旧缩放值和位置
            for change in changes {
                if let index = appState.images.firstIndex(where: { $0.id == change.imageId }) {
                    appState.images[index].scale = change.oldScale
                    appState.images[index].x = change.oldPosition.x
                    appState.images[index].y = change.oldPosition.y
                }
            }
            
        case .reorder(let imageId, let oldIndex, _):
            // 撤销图层顺序变更：恢复到旧位置
            if let currentIndex = appState.images.firstIndex(where: { $0.id == imageId }) {
                let image = appState.images.remove(at: currentIndex)
                let safeIndex = min(oldIndex, appState.images.count)
                appState.images.insert(image, at: safeIndex)
            }
            
        case .clearBoard(let images, let groups):
            // 撤销清空画板：恢复所有图片和组
            appState.images = images
            appState.groups = groups
            
        case .createGroup(let group, _):
            // 撤销创建组：删除组并移除成员的组ID
            for memberId in group.memberIds {
                if let imgIndex = appState.images.firstIndex(where: { $0.id == memberId }) {
                    appState.images[imgIndex].groupId = nil
                }
            }
            appState.groups.removeAll { $0.id == group.id }
            
        case .deleteGroup(let group):
            // 撤销删除组：恢复组并恢复成员的组ID
            appState.groups.append(group)
            for memberId in group.memberIds {
                if let imgIndex = appState.images.firstIndex(where: { $0.id == memberId }) {
                    appState.images[imgIndex].groupId = group.id
                }
            }
            
        case .updateGroup(let oldGroup, _):
            // 撤销更新组：恢复到旧设置
            if let index = appState.groups.firstIndex(where: { $0.id == oldGroup.id }) {
                appState.groups[index] = oldGroup
            }
            
        case .moveGroup(let groupId, let oldPosition, _, let memberMoves):
            // 撤销移动组：恢复组和成员位置
            if let index = appState.groups.firstIndex(where: { $0.id == groupId }) {
                appState.groups[index].x = oldPosition.x
                appState.groups[index].y = oldPosition.y
            }
            for move in memberMoves {
                if let imgIndex = appState.images.firstIndex(where: { $0.id == move.imageId }) {
                    appState.images[imgIndex].x = move.oldPosition.x
                    appState.images[imgIndex].y = move.oldPosition.y
                }
            }
        }
    }
    
    /// 执行重做操作
    private func performRedo(action: UndoableAction, appState: AppState) {
        switch action {
        case .move(let imageId, _, let newPosition):
            // 重做移动：应用新位置
            if let index = appState.images.firstIndex(where: { $0.id == imageId }) {
                appState.images[index].x = newPosition.x
                appState.images[index].y = newPosition.y
            }
            
        case .scale(let imageId, _, let newScale):
            // 重做缩放：应用新缩放值
            if let index = appState.images.firstIndex(where: { $0.id == imageId }) {
                appState.images[index].scale = newScale
            }
            
        case .rotate(let imageId, _, let newRotation):
            // 重做旋转：应用新角度
            if let index = appState.images.firstIndex(where: { $0.id == imageId }) {
                appState.images[index].rotation = newRotation
            }
            
        case .addImage(let image):
            // 重做添加：重新添加图片
            appState.images.append(image)
            
        case .removeImage(let image, _):
            // 重做删除：重新删除图片
            appState.images.removeAll { $0.id == image.id }
            appState.selectedImageIds.remove(image.id)
            
        case .batchMove(let changes):
            // 重做批量移动：应用所有图片的新位置
            for change in changes {
                if let index = appState.images.firstIndex(where: { $0.id == change.imageId }) {
                    appState.images[index].x = change.newPosition.x
                    appState.images[index].y = change.newPosition.y
                }
            }
            
        case .batchScale(let changes):
            // 重做批量缩放：应用所有图片的新缩放值和位置
            for change in changes {
                if let index = appState.images.firstIndex(where: { $0.id == change.imageId }) {
                    appState.images[index].scale = change.newScale
                    appState.images[index].x = change.newPosition.x
                    appState.images[index].y = change.newPosition.y
                }
            }
            
        case .reorder(let imageId, _, let newIndex):
            // 重做图层顺序变更：应用新位置
            if let currentIndex = appState.images.firstIndex(where: { $0.id == imageId }) {
                let image = appState.images.remove(at: currentIndex)
                let safeIndex = min(newIndex, appState.images.count)
                appState.images.insert(image, at: safeIndex)
            }
            
        case .clearBoard(_, _):
            // 重做清空画板：清空所有图片和组
            appState.images.removeAll()
            appState.groups.removeAll()
            appState.selectedImageIds.removeAll()
            appState.selectedGroupId = nil
            
        case .createGroup(let group, let memberIds):
            // 重做创建组：恢复组并恢复成员的组ID
            appState.groups.append(group)
            for memberId in memberIds {
                if let imgIndex = appState.images.firstIndex(where: { $0.id == memberId }) {
                    appState.images[imgIndex].groupId = group.id
                }
            }
            
        case .deleteGroup(let group):
            // 重做删除组：删除组并移除成员的组ID
            for memberId in group.memberIds {
                if let imgIndex = appState.images.firstIndex(where: { $0.id == memberId }) {
                    appState.images[imgIndex].groupId = nil
                }
            }
            appState.groups.removeAll { $0.id == group.id }
            
        case .updateGroup(_, let newGroup):
            // 重做更新组：应用新设置
            if let index = appState.groups.firstIndex(where: { $0.id == newGroup.id }) {
                appState.groups[index] = newGroup
            }
            
        case .moveGroup(let groupId, _, let newPosition, let memberMoves):
            // 重做移动组：应用新位置
            if let index = appState.groups.firstIndex(where: { $0.id == groupId }) {
                appState.groups[index].x = newPosition.x
                appState.groups[index].y = newPosition.y
            }
            for move in memberMoves {
                if let imgIndex = appState.images.firstIndex(where: { $0.id == move.imageId }) {
                    appState.images[imgIndex].x = move.newPosition.x
                    appState.images[imgIndex].y = move.newPosition.y
                }
            }
        }
    }
}
