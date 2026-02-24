import SwiftUI
import Observation
import UniformTypeIdentifiers
import Vision
import CoreImage
import CoreImage.CIFilterBuiltins
import Combine

@Observable
class AppState {
    var images: [ImageEntity] = []
    var groups: [GroupEntity] = []  // 组数据
    var canvasOffset: CGSize = .zero
    var canvasScale: CGFloat = 1.0
    var selectedImageIds: Set<UUID> = []
    var selectedGroupId: UUID? = nil  // 当前选中的组
    
    // [撤销/重做] 撤销管理器
    var undoManager = CanvasUndoManager()
    
    // [画板状态] 画板边界（固定初始范围，只扩展不收缩）
    // 初始画板大小：以原点为中心，宽高各1200
    var boardBounds: CGRect = CGRect(x: -600, y: -600, width: 1200, height: 1200)
    
    // [自动重置画板] 定时器相关
    private var autoResetTimer: Timer?
    private var cancellables = Set<AnyCancellable>()
    
    // [交互状态] 临时拖拽偏移
    // 用于在拖拽过程中实时更新所有选中图片的位置，而不需要频繁提交到 images 数组。
    var currentDragOffset: CGSize = .zero
    
    // [交互状态] 多选缩放因子
    // 用于在调整大小时实时预览所有选中图片的缩放效果。
    var multiSelectScaleFactor: CGFloat = 1.0
    
    // [交互状态] 多选缩放锚点
    // 用于在调整大小时确定缩放中心。
    var multiSelectAnchor: CGPoint = .zero
    
    // [组功能] 组设置弹窗控制
    var showGroupSettings: Bool = false
    var editingGroupId: UUID? = nil
    
    var isAlwaysOnTop: Bool = false {
        didSet {
            updateWindowLevel()
        }
    }
    
    init() {
        // 启动时检查是否需要开启自动重置定时器
        setupAutoResetTimer()
    }
    
    deinit {
        autoResetTimer?.invalidate()
    }
    
    // MARK: - Auto Reset Board Timer (自动重置画板定时器)
    
    /// 设置自动重置画板定时器
    func setupAutoResetTimer() {
        // 取消现有定时器
        autoResetTimer?.invalidate()
        autoResetTimer = nil
        
        // 检查是否启用自动重置
        let enabled = UserDefaults.standard.bool(forKey: "autoResetBoardEnabled")
        guard enabled else { return }
        
        // 获取间隔时间（分钟），默认10分钟
        let intervalMinutes = UserDefaults.standard.integer(forKey: "autoResetBoardInterval")
        let interval = intervalMinutes > 0 ? TimeInterval(intervalMinutes * 60) : 600 // 默认600秒 = 10分钟
        
        // 创建定时器
        autoResetTimer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { [weak self] _ in
            DispatchQueue.main.async {
                self?.resetBoardBounds()
            }
        }
    }
    
    /// 更新自动重置设置（当用户修改设置时调用）
    func updateAutoResetSettings(enabled: Bool, intervalMinutes: Int) {
        UserDefaults.standard.set(enabled, forKey: "autoResetBoardEnabled")
        UserDefaults.standard.set(intervalMinutes, forKey: "autoResetBoardInterval")
        setupAutoResetTimer()
    }
    
    // MARK: - Group Management (组管理)
    
    /// 将选中的图片打组 / Group selected images
    func groupSelectedImages() {
        guard selectedImageIds.count >= 2 else { return }
        
        // 创建新组 / Create new group
        var newGroup = GroupEntity(name: NSLocalizedString("Group", comment: ""))
        newGroup.memberIds = Array(selectedImageIds)
        
        // 更新图片的组ID / Update group ID of images
        for id in selectedImageIds {
            if let index = images.firstIndex(where: { $0.id == id }) {
                images[index].groupId = newGroup.id
            }
        }
        
        // 更新组边界 / Update group bounds
        updateGroupBounds(group: &newGroup)
        
        groups.append(newGroup)
        
        // 记录撤销 / Record undo
        undoManager.recordAction(.createGroup(group: newGroup, memberIds: Array(selectedImageIds)))
    }
    
    /// 更新组的边界 / Update group bounds
    func updateGroupBounds(group: inout GroupEntity) {
        let members = images.filter { group.memberIds.contains($0.id) }
        guard !members.isEmpty else { return }
        
        var minX: CGFloat = .greatestFiniteMagnitude
        var minY: CGFloat = .greatestFiniteMagnitude
        var maxX: CGFloat = -.greatestFiniteMagnitude
        var maxY: CGFloat = -.greatestFiniteMagnitude
        
        for img in members {
            let w = (img.nsImage?.size.width ?? 100) * img.scale
            let h = (img.nsImage?.size.height ?? 100) * img.scale
            
            let left = img.x - w/2
            let right = img.x + w/2
            let top = img.y - h/2
            let bottom = img.y + h/2
            
            if left < minX { minX = left }
            if right > maxX { maxX = right }
            if top < minY { minY = top }
            if bottom > maxY { maxY = bottom }
        }
        
        let padding: CGFloat = 20
        group.x = minX - padding
        group.y = minY - padding
        group.width = (maxX - minX) + padding * 2
        group.height = (maxY - minY) + padding * 2
    }
    
    /// 更新所有组的边界 / Update all group bounds
    func updateAllGroupBounds() {
        for i in 0..<groups.count {
            updateGroupBounds(group: &groups[i])
        }
    }
    
    /// 解散组 / Ungroup
    func ungroupGroup(groupId: UUID) {
        guard let index = groups.firstIndex(where: { $0.id == groupId }) else { return }
        let group = groups[index]
        
        // 记录撤销 / Record undo
        undoManager.recordAction(.deleteGroup(group: group))
        
        // 移除图片的组ID / Remove group ID from images
        for memberId in group.memberIds {
            if let imgIndex = images.firstIndex(where: { $0.id == memberId }) {
                images[imgIndex].groupId = nil
            }
        }
        
        groups.remove(at: index)
        selectedGroupId = nil
    }
    
    /// 更新组设置 / Update group settings
    func updateGroupSettings(groupId: UUID, name: String, colorHex: String, opacity: CGFloat, fontSize: CGFloat) {
        guard let index = groups.firstIndex(where: { $0.id == groupId }) else { return }
        
        let oldGroup = groups[index]
        
        groups[index].name = name
        groups[index].colorHex = colorHex
        groups[index].opacity = opacity
        groups[index].fontSize = fontSize
        
        // 记录撤销 / Record undo
        undoManager.recordAction(.updateGroup(oldGroup: oldGroup, newGroup: groups[index]))
    }
    
    /// 移动组（包括所有成员）/ Move group (including all members)
    func moveGroup(groupId: UUID, by delta: CGSize) {
        guard let index = groups.firstIndex(where: { $0.id == groupId }) else { return }
        
        // 移动所有成员 / Move all members
        for memberId in groups[index].memberIds {
            if let imgIndex = images.firstIndex(where: { $0.id == memberId }) {
                images[imgIndex].x += delta.width
                images[imgIndex].y += delta.height
            }
        }
        
        // 更新组边界 / Update group bounds
        groups[index].x += delta.width
        groups[index].y += delta.height
    }
    
    /// 获取指定位置的组 / Get group at position
    func groupAt(position: CGPoint) -> GroupEntity? {
        for group in groups.reversed() {
            if group.bounds.contains(position) {
                return group
            }
        }
        return nil
    }
    
    /// 检测并拉入组边界内的图片 / Check and pull images inside group bounds into the group
    /// 当调整组边界大小时调用
    func checkImagesInGroupBounds(groupId: UUID) {
        guard let groupIndex = groups.firstIndex(where: { $0.id == groupId }) else { return }
        let group = groups[groupIndex]
        let groupRect = group.bounds
        
        for i in 0..<images.count {
            // 跳过已经在此组中的图片 / Skip images already in this group
            if images[i].groupId == groupId {
                continue
            }
            
            // 获取图片的中心点 / Get image center point
            let imageCenter = CGPoint(x: images[i].x, y: images[i].y)
            
            // 如果图片中心在组边界内，则将其加入组 / If image center is inside group bounds, add it to group
            if groupRect.contains(imageCenter) {
                // 如果图片之前在其他组中，先从那个组移除 / If image was in another group, remove from that group first
                if let oldGroupId = images[i].groupId,
                   let oldGroupIndex = groups.firstIndex(where: { $0.id == oldGroupId }) {
                    groups[oldGroupIndex].memberIds.removeAll { $0 == images[i].id }
                    // 如果旧组只剩一个或零个成员，自动解散 / Auto ungroup if old group has 1 or 0 members left
                    if groups[oldGroupIndex].memberIds.count < 2 {
                        ungroupGroup(groupId: oldGroupId)
                    }
                }
                
                // 将图片加入新组 / Add image to new group
                images[i].groupId = groupId
                if let groupIndex = groups.firstIndex(where: { $0.id == groupId }) {
                    groups[groupIndex].memberIds.append(images[i].id)
                }
            }
        }
    }
    
    /// 检测图片是否完全移出了组边界 / Check if image is completely outside group bounds
    /// 如果是，则自动将其从组中移除
    func checkImageOutOfGroup(imageId: UUID) {
        guard let imageIndex = images.firstIndex(where: { $0.id == imageId }),
              let groupId = images[imageIndex].groupId,
              let groupIndex = groups.firstIndex(where: { $0.id == groupId }) else { return }
        
        let group = groups[groupIndex]
        let groupRect = group.bounds
        
        // 获取图片的边界矩形 / Get image bounding rect
        let img = images[imageIndex]
        let w = (img.nsImage?.size.width ?? 100) * img.scale
        let h = (img.nsImage?.size.height ?? 100) * img.scale
        let imageRect = CGRect(x: img.x - w/2, y: img.y - h/2, width: w, height: h)
        
        // 如果图片边界与组边界完全不相交，则移出组 / If image bounds don't intersect with group bounds at all, remove from group
        if !groupRect.intersects(imageRect) {
            // 从组中移除图片 / Remove image from group
            images[imageIndex].groupId = nil
            groups[groupIndex].memberIds.removeAll { $0 == imageId }
            
            // 如果组只剩一个或零个成员，自动解散 / Auto ungroup if group has 1 or 0 members left
            if groups[groupIndex].memberIds.count < 2 {
                ungroupGroup(groupId: groupId)
            }
        }
    }
    
    // MARK: - Image Management
    // 处理应用程序内图片的生命周期。
    
    func addImage(from url: URL, at position: CGPoint = .zero) {
        do {
            let data = try Data(contentsOf: url)
            let base64 = data.base64EncodedString()
            // 初始化新图片实体，默认缩放 (1.0) 和旋转 (0)。
            let newImage = ImageEntity(x: position.x, y: position.y, scale: 1.0, rotation: 0, data: base64)
            images.append(newImage)
            
            // [撤销/重做] 记录添加图片操作
            undoManager.recordAction(.addImage(image: newImage))
            
            // [画布扩展] 添加图片后检查并扩展画板边界
            updateBoardBoundsIfNeeded()
        } catch {
            print("Failed to load image: \(error)")
        }
    }
    
    func addImage(data: Data, at position: CGPoint = .zero) {
        let base64 = data.base64EncodedString()
        let newImage = ImageEntity(x: position.x, y: position.y, scale: 1.0, rotation: 0, data: base64)
        images.append(newImage)
        
        // [撤销/重做] 记录添加图片操作
        undoManager.recordAction(.addImage(image: newImage))
        
        // [画布扩展] 添加图片后检查并扩展画板边界
        updateBoardBoundsIfNeeded()
    }
    
    // MARK: - Copy / Paste (复制/粘贴)
    
    /// 复制选中的图片到剪贴板 / Copy selected images to pasteboard
    func copySelectedImages() {
        let selected = images.filter { selectedImageIds.contains($0.id) }
        guard !selected.isEmpty else { return }
        
        // 将选中图片的 base64 数据写入剪贴板
        // 如果只有一张图片，直接将图片写入剪贴板（兼容外部粘贴）
        // 同时在自定义 pasteboard type 中存储完整的图片实体信息（保留 scale/rotation 等）
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        
        // 1. 写入自定义数据（用于应用内粘贴，保留所有属性）
        if let jsonData = try? JSONEncoder().encode(selected) {
            pasteboard.setData(jsonData, forType: NSPasteboard.PasteboardType("com.hajimi.ref.images"))
        }
        
        // 2. 同时写入标准图片格式（用于外部粘贴）
        if selected.count == 1, let nsImage = selected.first?.nsImage {
            pasteboard.writeObjects([nsImage])
        }
    }
    
    /// 从剪贴板粘贴图片 / Paste images from pasteboard
    func pasteImages() {
        let pasteboard = NSPasteboard.general
        
        // 1. 优先尝试从自定义类型粘贴（应用内复制的图片，保留所有属性）
        if let data = pasteboard.data(forType: NSPasteboard.PasteboardType("com.hajimi.ref.images")),
           let copiedImages = try? JSONDecoder().decode([ImageEntity].self, from: data) {
            
            // 计算偏移量（避免与原图完全重叠）
            let offset: CGFloat = 30
            var newIds = Set<UUID>()
            
            for var img in copiedImages {
                // 生成新 ID，偏移位置
                img.id = UUID()
                img.x += offset
                img.y += offset
                img.groupId = nil // 粘贴的图片不属于任何组
                images.append(img)
                undoManager.recordAction(.addImage(image: img))
                newIds.insert(img.id)
            }
            
            // 选中新粘贴的图片
            selectedImageIds = newIds
            updateBoardBoundsIfNeeded()
            return
        }
        
        // 2. 尝试从标准图片格式粘贴（从外部复制的图片）
        if let nsImage = NSImage(pasteboard: pasteboard),
           let tiffData = nsImage.tiffRepresentation,
           let bitmapRep = NSBitmapImageRep(data: tiffData),
           let pngData = bitmapRep.representation(using: .png, properties: [:]) {
            addImage(data: pngData)
            return
        }
        
        // 3. 尝试从文件 URL 粘贴
        if let urls = pasteboard.readObjects(forClasses: [NSURL.self], options: [
            .urlReadingFileURLsOnly: true,
            .urlReadingContentsConformToTypes: ["public.image"]
        ]) as? [URL] {
            for url in urls {
                addImage(from: url)
            }
        }
    }
    
    func removeImage(id: UUID) {
        // [撤销/重做] 记录删除图片操作
        if let index = images.firstIndex(where: { $0.id == id }) {
            let image = images[index]
            undoManager.recordAction(.removeImage(image: image, index: index))
            
            // 如果图片属于某个组，从组中移除 / If image belongs to a group, remove from group
            if let groupId = image.groupId, let groupIndex = groups.firstIndex(where: { $0.id == groupId }) {
                groups[groupIndex].memberIds.removeAll { $0 == id }
                // 如果组只剩一个或零个成员，自动解散组
                if groups[groupIndex].memberIds.count < 2 {
                    ungroupGroup(groupId: groupId)
                }
            }
        }
        
        images.removeAll { $0.id == id }
        selectedImageIds.remove(id)
    }
    
    func clearBoard() {
        // [撤销/重做] 记录清空画板操作
        if !images.isEmpty || !groups.isEmpty {
            undoManager.recordAction(.clearBoard(images: images, groups: groups))
        }
        
        images.removeAll()
        groups.removeAll()
        selectedImageIds.removeAll()
        selectedGroupId = nil
        // Reset canvas view to default state
        canvasOffset = .zero
        canvasScale = 1.0
        // 重置画板边界为初始大小
        boardBounds = CGRect(x: -600, y: -600, width: 1200, height: 1200)
    }
    
    // MARK: - Undo/Redo (撤销/重做)
    
    /// 撤销上一步操作
    func undo() {
        undoManager.undo(appState: self)
        // [画布扩展] 撤销后检查并扩展画板边界
        updateBoardBoundsIfNeeded()
    }
    
    /// 重做上一步撤销的操作
    func redo() {
        undoManager.redo(appState: self)
        // [画布扩展] 重做后检查并扩展画板边界
        updateBoardBoundsIfNeeded()
    }
    
    // MARK: - Board Bounds Management (画板边界管理)
    
    /// 扩展画板边界以包含指定的矩形区域（只扩展不收缩）
    func expandBoardBounds(toInclude rect: CGRect) {
        let newMinX = min(boardBounds.minX, rect.minX)
        let newMinY = min(boardBounds.minY, rect.minY)
        let newMaxX = max(boardBounds.maxX, rect.maxX)
        let newMaxY = max(boardBounds.maxY, rect.maxY)
        
        boardBounds = CGRect(
            x: newMinX,
            y: newMinY,
            width: newMaxX - newMinX,
            height: newMaxY - newMinY
        )
    }
    
    /// 检查并扩展画板边界以包含所有图片
    func updateBoardBoundsIfNeeded() {
        for img in images {
            let w = (img.nsImage?.size.width ?? 100) * img.scale
            let h = (img.nsImage?.size.height ?? 100) * img.scale
            
            // 计算图片边界（带边距）
            let padding: CGFloat = 100
            let imgRect = CGRect(
                x: img.x - w/2 - padding,
                y: img.y - h/2 - padding,
                width: w + padding * 2,
                height: h + padding * 2
            )
            
            // 只有当图片超出画板边界时才扩展
            if imgRect.minX < boardBounds.minX ||
               imgRect.minY < boardBounds.minY ||
               imgRect.maxX > boardBounds.maxX ||
               imgRect.maxY > boardBounds.maxY {
                expandBoardBounds(toInclude: imgRect)
            }
        }
    }
    
    /// 重置画板边界为包含所有图片的最小范围
    func resetBoardBounds() {
        // 先重置为初始大小
        boardBounds = CGRect(x: -600, y: -600, width: 1200, height: 1200)
        // 然后扩展以包含所有图片
        updateBoardBoundsIfNeeded()
    }
    
    // [视觉设计] 内容居中
    // 自动调整画布偏移和缩放以适应视图中的所有图像。
    // 这类似于设计工具中的“缩放到合适大小 (Zoom to Fit)”功能。
    func centerContent() {
        guard !images.isEmpty else {
            canvasOffset = .zero
            canvasScale = 1.0
            return
        }
        
        // 计算所有图像的边界框
        var minX: CGFloat = .greatestFiniteMagnitude
        var minY: CGFloat = .greatestFiniteMagnitude
        var maxX: CGFloat = -.greatestFiniteMagnitude
        var maxY: CGFloat = -.greatestFiniteMagnitude
        
        for img in images {
            let w = (img.nsImage?.size.width ?? 100) * img.scale
            let h = (img.nsImage?.size.height ?? 100) * img.scale
            
            // 简单的边界框近似（为简单起见忽略旋转）
            let left = img.x - w/2
            let right = img.x + w/2
            let top = img.y - h/2
            let bottom = img.y + h/2
            
            if left < minX { minX = left }
            if right > maxX { maxX = right }
            if top < minY { minY = top }
            if bottom > maxY { maxY = bottom }
        }
        
        let contentWidth = maxX - minX
        let contentHeight = maxY - minY
        let centerX = (minX + maxX) / 2
        let centerY = (minY + maxY) / 2
        
        // 重置偏移以居中内容
        canvasOffset = CGSize(width: -centerX, height: -centerY)
        
        // 调整缩放以适应
        // 我们添加一些填充 (100pt)，这样图像就不会接触到窗口边缘。
        let targetScaleX = 1000.0 / (contentWidth + 100)
        let targetScaleY = 800.0 / (contentHeight + 100)
        let fitScale = min(targetScaleX, targetScaleY)
        
        // 将缩放限制在合理范围内 (0.1x 到 2.0x) 以防止过度缩放。
        canvasScale = min(max(fitScale, 0.1), 2.0)
    }
    
    func compactMemory() {
        // Placeholder for memory optimization logic
    }
    
    // MARK: - Layer Management (Z-Index)
    // 管理图像的渲染顺序。
    // 在 SwiftUI 的 ZStack 中，数组中的顺序决定了 Z-index。
    // 最后一个元素 = 最顶层。
    
    func bringToFront(id: UUID) {
        if let index = images.firstIndex(where: { $0.id == id }) {
            let oldIndex = index
            let item = images.remove(at: index)
            images.append(item) // Move to end of array
            let newIndex = images.count - 1
            
            // [撤销/重做] 记录图层顺序变更
            undoManager.recordAction(.reorder(imageId: id, oldIndex: oldIndex, newIndex: newIndex))
        }
    }
    
    func sendToBack(id: UUID) {
        if let index = images.firstIndex(where: { $0.id == id }) {
            let oldIndex = index
            let item = images.remove(at: index)
            images.insert(item, at: 0) // Move to start of array
            
            // [撤销/重做] 记录图层顺序变更
            undoManager.recordAction(.reorder(imageId: id, oldIndex: oldIndex, newIndex: 0))
        }
    }
    
    func bringForward(id: UUID) {
        if let index = images.firstIndex(where: { $0.id == id }), index < images.count - 1 {
            let oldIndex = index
            let newIndex = index + 1
            images.swapAt(index, index + 1) // Swap with the element above
            
            // [撤销/重做] 记录图层顺序变更
            undoManager.recordAction(.reorder(imageId: id, oldIndex: oldIndex, newIndex: newIndex))
        }
    }
    
    func sendBackward(id: UUID) {
        if let index = images.firstIndex(where: { $0.id == id }), index > 0 {
            let oldIndex = index
            let newIndex = index - 1
            images.swapAt(index, index - 1) // Swap with the element below
            
            // [撤销/重做] 记录图层顺序变更
            undoManager.recordAction(.reorder(imageId: id, oldIndex: oldIndex, newIndex: newIndex))
        }
    }
    
    // MARK: - File I/O (文件读写)
    
    func importImages() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        panel.allowedContentTypes = [.image]
        
        if panel.runModal() == .OK {
            for url in panel.urls {
                let count = CGFloat(images.count)
                addImage(from: url, at: CGPoint(x: count * 20, y: count * 20))
            }
        }
    }
    
    func saveBoard() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [UTType(filenameExtension: "sref") ?? .json]
        panel.nameFieldStringValue = "board.sref"
        
        if panel.runModal() == .OK, let url = panel.url {
            // 保存时根据数组索引设置 zIndex，确保图层顺序保存
            var imagesToSave = images
            for i in 0..<imagesToSave.count {
                imagesToSave[i].zIndex = CGFloat(i)
            }
            let boardData = BoardData(images: imagesToSave, groups: groups)
            do {
                let encoder = JSONEncoder()
                let data = try encoder.encode(boardData)
                try data.write(to: url)
            } catch {
                print("Failed to save board: \(error)")
            }
        }
    }
    
    func loadBoard() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [UTType(filenameExtension: "sref") ?? .json, .json]
        
        if panel.runModal() == .OK, let url = panel.url {
            do {
                let data = try Data(contentsOf: url)
                let decoder = JSONDecoder()
                let boardData = try decoder.decode(BoardData.self, from: data)
                
                // 加载时根据 zIndex 排序，确保图层顺序正确
                var loadedImages = boardData.images
                loadedImages.sort { $0.zIndex < $1.zIndex }
                
                self.images = loadedImages
                self.groups = boardData.groups
                self.selectedImageIds.removeAll()
                self.selectedGroupId = nil
                self.canvasOffset = .zero
                self.canvasScale = 1.0
            } catch {
                print("Failed to load board: \(error)")
            }
        }
    }
    
    // MARK: - Export Board as Image (导出画布为图片)
    
    /// 计算图片旋转后的边界框
    /// - Parameters:
    ///   - width: 图片宽度
    ///   - height: 图片高度
    ///   - rotation: 旋转角度（度）
    /// - Returns: 旋转后的边界框尺寸 (width, height)
    private func rotatedBoundingBox(width: CGFloat, height: CGFloat, rotation: CGFloat) -> (CGFloat, CGFloat) {
        let radians = rotation * .pi / 180.0
        let cos = abs(Darwin.cos(radians))
        let sin = abs(Darwin.sin(radians))
        
        let newWidth = width * cos + height * sin
        let newHeight = width * sin + height * cos
        
        return (newWidth, newHeight)
    }
    
    func exportBoardAsImage() {
        guard !images.isEmpty else {
            // 没有图片可导出
            let alert = NSAlert()
            alert.messageText = NSLocalizedString("No Images", comment: "")
            alert.informativeText = NSLocalizedString("There are no images on the canvas to export.", comment: "")
            alert.alertStyle = .warning
            alert.runModal()
            return
        }
        
        // 计算所有图片的边界框（考虑旋转）
        var minX: CGFloat = .greatestFiniteMagnitude
        var minY: CGFloat = .greatestFiniteMagnitude
        var maxX: CGFloat = -.greatestFiniteMagnitude
        var maxY: CGFloat = -.greatestFiniteMagnitude
        
        for img in images {
            let originalW = (img.nsImage?.size.width ?? 100) * img.scale
            let originalH = (img.nsImage?.size.height ?? 100) * img.scale
            
            // 计算旋转后的边界框尺寸
            let (rotatedW, rotatedH) = rotatedBoundingBox(width: originalW, height: originalH, rotation: img.rotation)
            
            let left = img.x - rotatedW/2
            let right = img.x + rotatedW/2
            let top = img.y - rotatedH/2
            let bottom = img.y + rotatedH/2
            
            if left < minX { minX = left }
            if right > maxX { maxX = right }
            if top < minY { minY = top }
            if bottom > maxY { maxY = bottom }
        }
        
        // 添加边距
        let margin: CGFloat = 20
        minX -= margin
        minY -= margin
        maxX += margin
        maxY += margin
        
        let width = maxX - minX
        let height = maxY - minY
        
        // 弹出保存对话框
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.png, .jpeg]
        panel.nameFieldStringValue = "board_export.png"
        
        if panel.runModal() == .OK, let url = panel.url {
            // 创建目标图片
            let size = NSSize(width: width, height: height)
            let image = NSImage(size: size)
            
            image.lockFocus()
            
            // 设置背景（PNG 为透明，其他格式为白色）
            if url.pathExtension.lowercased() == "png" {
                NSColor.clear.setFill()
            } else {
                NSColor.white.setFill()
            }
            NSRect(origin: .zero, size: size).fill()
            
            // 绘制每张图片
            for img in images {
                guard let nsImage = img.nsImage else { continue }
                
                let imgWidth = nsImage.size.width * img.scale
                let imgHeight = nsImage.size.height * img.scale
                
                // 计算图片中心相对于导出图片的位置
                let centerX = img.x - minX
                let centerY = img.y - minY
                
                // 保存当前图形状态
                NSGraphicsContext.saveGraphicsState()
                
                // 移动到图片中心点，应用旋转，然后绘制
                let transform = NSAffineTransform()
                transform.translateX(by: centerX, yBy: centerY)
                transform.rotate(byDegrees: img.rotation)
                transform.concat()
                
                // 绘制图片（以中心为原点）
                nsImage.draw(in: NSRect(x: -imgWidth/2, y: -imgHeight/2, width: imgWidth, height: imgHeight),
                            from: NSRect(origin: .zero, size: nsImage.size),
                            operation: .sourceOver,
                            fraction: 1.0)
                
                // 恢复图形状态
                NSGraphicsContext.restoreGraphicsState()
            }
            
            image.unlockFocus()
            
            // 保存图片到文件
            guard let tiffData = image.tiffRepresentation,
                  let bitmap = NSBitmapImageRep(data: tiffData) else {
                showExportError()
                return
            }
            
            var imageData: Data?
            if url.pathExtension.lowercased() == "png" {
                imageData = bitmap.representation(using: .png, properties: [:])
            } else {
                imageData = bitmap.representation(using: .jpeg, properties: [.compressionFactor: 0.9])
            }
            
            guard let data = imageData else {
                showExportError()
                return
            }
            
            do {
                try data.write(to: url)
                // 显示成功提示
                let alert = NSAlert()
                alert.messageText = NSLocalizedString("Export Successful", comment: "")
                alert.informativeText = String(format: NSLocalizedString("Board exported to:\n%@", comment: ""), url.path)
                alert.alertStyle = .informational
                alert.runModal()
            } catch {
                showExportError()
            }
        }
    }
    
    private func showExportError() {
        let alert = NSAlert()
        alert.messageText = NSLocalizedString("Export Failed", comment: "")
        alert.informativeText = NSLocalizedString("Failed to export the board as an image.", comment: "")
        alert.alertStyle = .critical
        alert.runModal()
    }
    
    // MARK: - Copy Board to Clipboard (复制画布到剪贴板)
    
    func copyBoardToClipboard() {
        guard !images.isEmpty else {
            // 没有图片可导出
            let alert = NSAlert()
            alert.messageText = NSLocalizedString("No Images", comment: "")
            alert.informativeText = NSLocalizedString("There are no images on the canvas to export.", comment: "")
            alert.alertStyle = .warning
            alert.runModal()
            return
        }
        
        // 计算所有图片的边界框（考虑旋转）
        var minX: CGFloat = .greatestFiniteMagnitude
        var minY: CGFloat = .greatestFiniteMagnitude
        var maxX: CGFloat = -.greatestFiniteMagnitude
        var maxY: CGFloat = -.greatestFiniteMagnitude
        
        for img in images {
            let originalW = (img.nsImage?.size.width ?? 100) * img.scale
            let originalH = (img.nsImage?.size.height ?? 100) * img.scale
            
            // 计算旋转后的边界框尺寸
            let (rotatedW, rotatedH) = rotatedBoundingBox(width: originalW, height: originalH, rotation: img.rotation)
            
            let left = img.x - rotatedW/2
            let right = img.x + rotatedW/2
            let top = img.y - rotatedH/2
            let bottom = img.y + rotatedH/2
            
            if left < minX { minX = left }
            if right > maxX { maxX = right }
            if top < minY { minY = top }
            if bottom > maxY { maxY = bottom }
        }
        
        // 添加边距
        let margin: CGFloat = 20
        minX -= margin
        minY -= margin
        maxX += margin
        maxY += margin
        
        let width = maxX - minX
        let height = maxY - minY
        
        // 创建目标图片
        let size = NSSize(width: width, height: height)
        let image = NSImage(size: size)
        
        image.lockFocus()
        
        // 透明背景
        NSColor.clear.setFill()
        NSRect(origin: .zero, size: size).fill()
        
        // 绘制每张图片
        for img in images {
            guard let nsImage = img.nsImage else { continue }
            
            let imgWidth = nsImage.size.width * img.scale
            let imgHeight = nsImage.size.height * img.scale
            
            // 计算图片中心相对于导出图片的位置
            let centerX = img.x - minX
            let centerY = img.y - minY
            
            // 保存当前图形状态
            NSGraphicsContext.saveGraphicsState()
            
            // 移动到图片中心点，应用旋转，然后绘制
            let transform = NSAffineTransform()
            transform.translateX(by: centerX, yBy: centerY)
            transform.rotate(byDegrees: img.rotation)
            transform.concat()
            
            // 绘制图片（以中心为原点）
            nsImage.draw(in: NSRect(x: -imgWidth/2, y: -imgHeight/2, width: imgWidth, height: imgHeight),
                        from: NSRect(origin: .zero, size: nsImage.size),
                        operation: .sourceOver,
                        fraction: 1.0)
            
            // 恢复图形状态
            NSGraphicsContext.restoreGraphicsState()
        }
        
        image.unlockFocus()
        
        // 复制到剪贴板
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.writeObjects([image])
    }
    
    // MARK: - Window Management
    
    private func updateWindowLevel() {
        for window in NSApplication.shared.windows {
            if window.isKeyWindow || window.isMainWindow {
                window.level = isAlwaysOnTop ? .floating : .normal
            }
        }
    }
    
    // MARK: - Smart Arrangement (智能排序)
    
    func smartSortSelected() {
        guard !selectedImageIds.isEmpty else { return }
        
        // 1. 获取选中的图片实体及其索引
        let selectedIndices = images.indices.filter { selectedImageIds.contains(images[$0].id) }
        guard !selectedIndices.isEmpty else { return }
        
        let n = selectedIndices.count
        
        // 2. 构建物理刚体数据 / Build physics body data
        struct Body {
            var index: Int      // 在 images 数组中的索引
            var x: CGFloat      // 中心 x
            var y: CGFloat      // 中心 y
            var w: CGFloat      // 宽
            var h: CGFloat      // 高
            var vx: CGFloat = 0 // 速度 x
            var vy: CGFloat = 0 // 速度 y
        }
        
        var bodies: [Body] = selectedIndices.map { idx in
            let img = images[idx]
            let w = (img.nsImage?.size.width ?? 100) * img.scale
            let h = (img.nsImage?.size.height ?? 100) * img.scale
            return Body(index: idx, x: img.x, y: img.y, w: w, h: h)
        }
        
        // 3. 记录原始质心用于偏移校正 / Record original centroid for offset correction
        let origCenterX = bodies.reduce(CGFloat(0)) { $0 + $1.x } / CGFloat(n)
        let origCenterY = bodies.reduce(CGFloat(0)) { $0 + $1.y } / CGFloat(n)
        
        // 4. 物理模拟参数 / Physics simulation parameters
        // ─────────────────────────────────────────────────────────────────────
        // spacing: 图片之间的最小期望间距（pt），值越大图片排列越稀疏
        // Minimum desired gap (pt) between images. Larger = more spread out.
        let spacing: CGFloat = 12.0
        
        // repulsionStrength: 斥力强度系数，控制重叠图片被推开的速度
        //   值范围建议 0.5~2.0，越大越快消除重叠，但过大可能导致抖动
        //   相比向心引力需要足够大以确保斥力占主导，避免收敛时残留重叠
        // Repulsion coefficient. Recommended range: 0.5~2.0. Must dominate over attraction.
        let repulsionStrength: CGFloat = 1.2
        
        // attractionStrength: 向心引力系数，将所有图片拉向共同质心以保持紧凑
        //   值范围建议 0.005~0.05，越大布局越紧凑，过大会与斥力冲突导致振荡
        //   必须远小于 repulsionStrength，否则会在收敛阶段将图片拉回重叠状态
        // Attraction coefficient. Recommended range: 0.005~0.05. Must be much smaller than repulsion.
        let attractionStrength: CGFloat = 0.01
        
        // damping: 速度阻尼系数（0~1），每帧速度乘以此值
        //   越接近 1 收敛越慢但更平滑，越接近 0 收敛越快但可能突变
        //   建议 0.75~0.90，过高会导致斥力产生的位移被快速吃掉从而推不开
        // Velocity damping (0~1). Recommended: 0.75~0.90. Too high dampens repulsion displacement.
        let damping: CGFloat = 0.80
        
        // maxIterations: 最大模拟迭代次数，防止极端情况下无限循环
        //   通常 80~200 足够收敛，图片数量越多可能需要更多迭代
        // Max simulation iterations. Usually 80~200 suffices. More images may need more.
        let maxIterations = 150
        
        // convergenceThreshold: 收敛速度阈值，当所有物体最大速度低于此值时提前终止
        //   值越小结果越精确，但耗时越长。建议 0.1~0.5
        // Convergence threshold. Smaller = more precise but longer computation. Recommended: 0.1~0.5.
        let convergenceThreshold: CGFloat = 0.1
        
        // maxForce: 单步最大力限制，防止极端重叠导致图片弹射过远
        // Max force per step. Safety cap to prevent catapulting from extreme overlap.
        let maxForce: CGFloat = 300.0
        
        // 5. 迭代物理模拟 / Iterative physics simulation
        for _ in 0..<maxIterations {
            // 计算质心 / Calculate centroid
            let cx = bodies.reduce(CGFloat(0)) { $0 + $1.x } / CGFloat(n)
            let cy = bodies.reduce(CGFloat(0)) { $0 + $1.y } / CGFloat(n)
            
            // 初始化力 / Initialize forces
            var forces = Array(repeating: (fx: CGFloat(0), fy: CGFloat(0)), count: n)
            
            // 检测是否还有重叠，用于后半段关闭引力 / Track if any overlap remains
            var hasOverlap = false
            
            // 5a) 斥力：防止重叠 / Repulsion: prevent overlap
            for i in 0..<n {
                for j in (i + 1)..<n {
                    let a = bodies[i]
                    let b = bodies[j]
                    
                    let halfWA = a.w / 2.0 + spacing / 2.0
                    let halfHA = a.h / 2.0 + spacing / 2.0
                    let halfWB = b.w / 2.0 + spacing / 2.0
                    let halfHB = b.h / 2.0 + spacing / 2.0
                    
                    let dx = b.x - a.x
                    let dy = b.y - a.y
                    
                    let overlapX = (halfWA + halfWB) - abs(dx)
                    let overlapY = (halfHA + halfHB) - abs(dy)
                    
                    if overlapX > 0 && overlapY > 0 {
                        hasOverlap = true
                        if overlapX < overlapY {
                            // 沿 X 轴推开
                            let force = min(overlapX * repulsionStrength, maxForce)
                            if dx >= 0 {
                                forces[i].fx -= force
                                forces[j].fx += force
                            } else {
                                forces[i].fx += force
                                forces[j].fx -= force
                            }
                        } else {
                            // 沿 Y 轴推开
                            let force = min(overlapY * repulsionStrength, maxForce)
                            if dy >= 0 {
                                forces[i].fy -= force
                                forces[j].fy += force
                            } else {
                                forces[i].fy += force
                                forces[j].fy -= force
                            }
                        }
                    }
                }
            }
            
            // 5b) 向心引力（仅在无重叠时施加，避免把已分离的图片拉回重叠）
            // Attraction toward centroid (only when no overlap, to avoid pulling separated images back)
            if !hasOverlap {
                for i in 0..<n {
                    forces[i].fx += (cx - bodies[i].x) * attractionStrength
                    forces[i].fy += (cy - bodies[i].y) * attractionStrength
                }
            }
            
            // 5c) 更新速度和位置 / Update velocity and position
            var maxVel: CGFloat = 0
            for i in 0..<n {
                bodies[i].vx = (bodies[i].vx + forces[i].fx) * damping
                bodies[i].vy = (bodies[i].vy + forces[i].fy) * damping
                bodies[i].x += bodies[i].vx
                bodies[i].y += bodies[i].vy
                
                let vel = sqrt(bodies[i].vx * bodies[i].vx + bodies[i].vy * bodies[i].vy)
                if vel > maxVel { maxVel = vel }
            }
            
            // 5d) 检查收敛（必须同时无重叠且速度低于阈值才终止）
            // Converge only when no overlap AND velocity is below threshold
            if maxVel < convergenceThreshold && !hasOverlap {
                break
            }
        }
        
        // 5e) 强制去重叠后处理：模拟结束后逐对检查，直接位移消除残留重叠
        //      确保 100% 无重叠，作为物理模拟的最终安全网
        // Post-processing: forcefully resolve any remaining overlaps after simulation.
        for _ in 0..<50 {
            var anyOverlap = false
            for i in 0..<n {
                for j in (i + 1)..<n {
                    let halfWA = bodies[i].w / 2.0 + spacing / 2.0
                    let halfHA = bodies[i].h / 2.0 + spacing / 2.0
                    let halfWB = bodies[j].w / 2.0 + spacing / 2.0
                    let halfHB = bodies[j].h / 2.0 + spacing / 2.0
                    
                    let dx = bodies[j].x - bodies[i].x
                    let dy = bodies[j].y - bodies[i].y
                    
                    let overlapX = (halfWA + halfWB) - abs(dx)
                    let overlapY = (halfHA + halfHB) - abs(dy)
                    
                    if overlapX > 0 && overlapY > 0 {
                        anyOverlap = true
                        // 沿最小重叠轴直接位移一半距离 / Displace each body by half the overlap along min axis
                        if overlapX < overlapY {
                            let shift = overlapX / 2.0 + 0.5  // +0.5 确保完全分离
                            if dx >= 0 {
                                bodies[i].x -= shift
                                bodies[j].x += shift
                            } else {
                                bodies[i].x += shift
                                bodies[j].x -= shift
                            }
                        } else {
                            let shift = overlapY / 2.0 + 0.5
                            if dy >= 0 {
                                bodies[i].y -= shift
                                bodies[j].y += shift
                            } else {
                                bodies[i].y += shift
                                bodies[j].y -= shift
                            }
                        }
                    }
                }
            }
            if !anyOverlap { break }
        }
        
        // 6. 紧凑化压缩：反复尝试将每张图片向质心方向移动以消除多余间隙
        //    只有在不产生新重叠的前提下才保留移动，确保布局尽可能紧凑
        // Compaction phase: iteratively move each image toward centroid to eliminate
        // excess gaps. A move is kept only if it doesn't create new overlaps.
        // ─────────────────────────────────────────────────────────────────────
        // compactStep: 每次向质心移动的步长（pt），值越大压缩越快但精度越低
        // Step size (pt) per compaction move. Larger = faster but less precise.
        let compactStep: CGFloat = 4.0
        // compactPasses: 紧凑化最大轮数 / Maximum compaction passes
        let compactPasses = 60
        
        func hasOverlapWithOthers(_ idx: Int, _ bods: [Body], _ sp: CGFloat) -> Bool {
            let a = bods[idx]
            for k in 0..<bods.count {
                if k == idx { continue }
                let b = bods[k]
                let hwA = a.w / 2.0 + sp / 2.0
                let hhA = a.h / 2.0 + sp / 2.0
                let hwB = b.w / 2.0 + sp / 2.0
                let hhB = b.h / 2.0 + sp / 2.0
                if (hwA + hwB) - abs(b.x - a.x) > 0 && (hhA + hhB) - abs(b.y - a.y) > 0 {
                    return true
                }
            }
            return false
        }
        
        for _ in 0..<compactPasses {
            var movedAny = false
            let ccx = bodies.reduce(CGFloat(0)) { $0 + $1.x } / CGFloat(n)
            let ccy = bodies.reduce(CGFloat(0)) { $0 + $1.y } / CGFloat(n)
            for i in 0..<n {
                let dxC = ccx - bodies[i].x
                let dyC = ccy - bodies[i].y
                let dist = sqrt(dxC * dxC + dyC * dyC)
                if dist < 1.0 { continue }
                // 归一化方向，移动 compactStep / Normalize direction, move by compactStep
                let step = min(compactStep, dist)
                let mx = dxC / dist * step
                let my = dyC / dist * step
                // 暂存旧位置，尝试移动 / Save old, try move
                let oldX = bodies[i].x
                let oldY = bodies[i].y
                bodies[i].x += mx
                bodies[i].y += my
                // 如果产生了新重叠，回退 / If new overlap, revert
                if hasOverlapWithOthers(i, bodies, spacing) {
                    bodies[i].x = oldX
                    bodies[i].y = oldY
                } else {
                    movedAny = true
                }
            }
            if !movedAny { break }
        }
        
        // 7. 偏移校正：对齐到原始质心 / Offset correction: align to original centroid
        let newCX = bodies.reduce(CGFloat(0)) { $0 + $1.x } / CGFloat(n)
        let newCY = bodies.reduce(CGFloat(0)) { $0 + $1.y } / CGFloat(n)
        let offsetX = origCenterX - newCX
        let offsetY = origCenterY - newCY
        
        // 8. 使用弹性动画过渡应用最终位置（图片 + 组边界同步动画）
        //    Apply final positions with spring animation transition (images + group bounds synced)
        //    SwiftUI 的 withAnimation(.spring()) 自动利用 Core Animation / Metal 实现流畅的 GPU 加速动画
        //    Leverages SwiftUI's withAnimation(.spring()) for smooth GPU-accelerated animation
        
        // 9. 收集受影响的组ID / Collect affected group IDs
        var affectedGroupIds = Set<UUID>()
        for body in bodies {
            if let gid = images[body.index].groupId {
                affectedGroupIds.insert(gid)
            }
        }
        
        withAnimation(.spring(response: 0.5, dampingFraction: 0.75)) {
            // 更新图片位置 / Update image positions
            for body in bodies {
                images[body.index].x = body.x + offsetX
                images[body.index].y = body.y + offsetY
            }
            
            // 同步更新组边界（在同一个动画块中，组大小变化与图片移动完全同步）
            // Synchronously update group bounds (in the same animation block, group resize syncs perfectly with image movement)
            for gid in affectedGroupIds {
                if let gi = groups.firstIndex(where: { $0.id == gid }) {
                    updateGroupBounds(group: &groups[gi])
                }
            }
        }
    }

    // MARK: - NPU / Vision Features
    // 利用 Apple 的 Vision 框架和神经引擎 (NPU) 进行高级图像处理。
    
    func removeBackground(for imageId: UUID) {
        guard let index = images.firstIndex(where: { $0.id == imageId }),
              let nsImage = images[index].nsImage,
              let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return }
        
        // 创建一个请求以生成前景主体的分割蒙版。
        // 这使用了针对 Apple Silicon 优化的机器学习模型。
        let request = VNGenerateForegroundInstanceMaskRequest()
        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                try handler.perform([request])
                if let result = request.results?.first {
                    // 从分析结果生成蒙版
                    let mask = try result.generateMask(forInstances: result.allInstances)
                    
                    let originalCI = CIImage(cgImage: cgImage)
                    let maskCI = CIImage(cvPixelBuffer: mask)
                    
                    // 缩放蒙版以匹配原始图像大小
                    let scaleX = originalCI.extent.width / maskCI.extent.width
                    let scaleY = originalCI.extent.height / maskCI.extent.height
                    let scaledMask = maskCI.transformed(by: CGAffineTransform(scaleX: scaleX, y: scaleY))
                    
                    // 使用 Core Image 混合应用蒙版
                    let filter = CIFilter.blendWithMask()
                    filter.inputImage = originalCI
                    filter.maskImage = scaledMask
                    filter.backgroundImage = CIImage.empty() // Transparent background
                    
                    if let output = filter.outputImage {
                        let context = CIContext()
                        if let newCGImage = context.createCGImage(output, from: output.extent) {
                            let newNSImage = NSImage(cgImage: newCGImage, size: nsImage.size)
                            // 转换回 PNG 数据进行存储
                            if let tiff = newNSImage.tiffRepresentation,
                               let bitmap = NSBitmapImageRep(data: tiff),
                               let pngData = bitmap.representation(using: .png, properties: [:]) {
                                
                                let base64 = pngData.base64EncodedString()
                                
                                DispatchQueue.main.async {
                                    // Update the image data in place
                                    self.images[index].data = base64
                                    // [Bug Fix] 必须同时更新缓存，否则视图会继续显示旧图片
                                    if let d = Data(base64Encoded: base64) {
                                        self.images[index]._cachedImage = NSImage(data: d)
                                    }
                                }
                            }
                        }
                    }
                }
            } catch {
                print("Vision request failed: \(error)")
            }
        }
    }
}

// Helper to access the underlying NSWindow for "Always on Top"
extension NSWindow {
    var isFloating: Bool {
        get { level == .floating }
        set { level = newValue ? .floating : .normal }
    }
}
