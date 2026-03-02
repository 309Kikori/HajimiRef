import SwiftUI
import UniformTypeIdentifiers

// MARK: - Window Accessor & Event Monitor

struct WindowAccessor: NSViewRepresentable {
    @Environment(AppState.self) var appState
    
    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async {
            if let window = view.window {
                context.coordinator.setupMonitor(for: window)
            }
        }
        return view
    }
    
    func updateNSView(_ nsView: NSView, context: Context) {
        context.coordinator.appState = appState
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(appState: appState)
    }
    
    class Coordinator {
        var appState: AppState
        private var monitor: Any?
        private weak var window: NSWindow?
        
        // Pan State
        private var isPanning = false
        private var lastPanLocation: NSPoint = .zero
        
        init(appState: AppState) {
            self.appState = appState
        }
        
        deinit {
            removeMonitor()
        }
        
        func setupMonitor(for window: NSWindow) {
            self.window = window
            removeMonitor()
            
            // Monitor events globally in the window (Local Monitor)
            // This captures events before they are dispatched to views, allowing us to intercept Scroll/Pan
            monitor = NSEvent.addLocalMonitorForEvents(matching: [.scrollWheel, .magnify, .otherMouseDown, .otherMouseDragged, .otherMouseUp, .keyDown]) { [weak self] event in
                return self?.handleEvent(event) ?? event
            }
        }
        
        private func removeMonitor() {
            if let monitor = monitor {
                NSEvent.removeMonitor(monitor)
                self.monitor = nil
            }
        }
        
        private func handleEvent(_ event: NSEvent) -> NSEvent? {
            // Only handle if window is active
            guard let window = window, window.isKeyWindow else { return event }
            
            switch event.type {
            case .scrollWheel:
                handleScrollWheel(event)
                return nil // Consume event to prevent default behavior (like scrolling the document view if any)
                
            case .magnify:
                handleMagnify(event)
                return nil
                
            case .otherMouseDown:
                if event.buttonNumber == 2 { // Middle Button
                    isPanning = true
                    lastPanLocation = event.locationInWindow
                    NSCursor.closedHand.push()
                    return nil
                }
                
            case .otherMouseDragged:
                if isPanning {
                    let currentLocation = event.locationInWindow
                    let deltaX = currentLocation.x - lastPanLocation.x
                    let deltaY = currentLocation.y - lastPanLocation.y
                    
                    // [交互优化] 修正缩放后的拖拽灵敏度
                    // 当画布缩放比例很小（缩小）时，屏幕上的 1px 对应画布世界坐标中的 1/scale px。
                    // 如果不除以 scale，在缩小状态下拖拽会感觉非常“滑”或移动极其缓慢（不跟手）。
                    // 除以 scale 后，鼠标移动 1px，画布内容在视觉上也准确移动 1px。
                    appState.canvasOffset.width += deltaX / appState.canvasScale
                    appState.canvasOffset.height -= deltaY / appState.canvasScale
                    
                    lastPanLocation = currentLocation
                    return nil
                }
                
            case .otherMouseUp:
                if event.buttonNumber == 2 {
                    isPanning = false
                    NSCursor.pop()
                    return nil
                }
                
            case .keyDown:
                if handleKeyDown(event) {
                    return nil
                }
                
            default:
                break
            }
            
            return event
        }
        
        // MARK: - Key Events
        private func handleKeyDown(_ event: NSEvent) -> Bool {
            // [撤销/重做] Cmd+Z 撤销, Cmd+Shift+Z 重做
            if event.modifierFlags.contains(.command) && event.charactersIgnoringModifiers == "z" {
                if event.modifierFlags.contains(.shift) {
                    // Cmd+Shift+Z: 重做
                    appState.redo()
                } else {
                    // Cmd+Z: 撤销
                    appState.undo()
                }
                return true
            }
            
            // [复制/粘贴] Cmd+C 复制, Cmd+V 粘贴
            if event.modifierFlags.contains(.command) && event.charactersIgnoringModifiers == "c" {
                // 排除 Cmd+Shift+C（已用于复制画板到剪贴板）
                if !event.modifierFlags.contains(.shift) {
                    appState.copySelectedImages()
                    return true
                }
            }
            
            if event.modifierFlags.contains(.command) && event.charactersIgnoringModifiers == "v" {
                appState.pasteImages()
                return true
            }
            
            // G 键打组 / G key to group
            if event.charactersIgnoringModifiers == "g" {
                appState.groupSelectedImages()
                return true
            }
            
            if event.charactersIgnoringModifiers == "f" {
                appState.centerContent()
                return true
            } else if event.modifierFlags.contains(.command) && event.characters == "[" {
                if let id = appState.selectedImageIds.first {
                    appState.sendBackward(id: id)
                    return true
                }
            } else if event.modifierFlags.contains(.command) && event.characters == "]" {
                if let id = appState.selectedImageIds.first {
                    appState.bringForward(id: id)
                    return true
                }
            }
            return false
        }
        
        // MARK: - Scroll Wheel (Zoom)
        private func handleScrollWheel(_ event: NSEvent) {
            if event.modifierFlags.contains(.control) {
                // Ctrl + Wheel -> Scale Selected Images
                let scaleFactor: CGFloat = event.deltaY > 0 ? 1.05 : 0.95
                for id in appState.selectedImageIds {
                    if let index = appState.images.firstIndex(where: { $0.id == id }) {
                        appState.images[index].scale *= scaleFactor
                    }
                }
            } else {
                // Wheel -> Zoom Canvas
                let zoomDelta = event.deltaY * 0.005
                let zoomFactor = 1.0 + zoomDelta
                let newScale = appState.canvasScale * zoomFactor
                // [缩放范围] 放宽限制，与 win11 行为对齐（Qt 无显式限制）
                // 但保留安全范围防止极端值导致渲染问题
                appState.canvasScale = min(max(newScale, 0.02), 50.0)
            }
        }
        
        // MARK: - Magnify
        private func handleMagnify(_ event: NSEvent) {
            let zoomFactor = 1.0 + event.magnification
            let newScale = appState.canvasScale * zoomFactor
            appState.canvasScale = min(max(newScale, 0.02), 50.0)
        }
    }
}

// MARK: - Canvas View

struct CanvasView: View {
    @Environment(AppState.self) var appState
    
    // [个性化设置] 读取用户偏好
    @AppStorage("showGrid") private var showGrid: Bool = true
    @AppStorage("canvasBgColorHex") private var canvasBgColorHex: String = "#1E1E1E"
    @AppStorage("inactiveBgColorHex") private var inactiveBgColorHex: String = "#141414"  // 非活动区域更深色
    @AppStorage("gridColorHex") private var gridColorHex: String = "#404040"
    
    // [交互设计] 框选状态
    @State private var selectionRect: CGRect? = nil
    @State private var selectionStart: CGPoint? = nil
    
    init() {}
    
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // 0. Visual Background Layer - 非活动区域背景（更深色）
                // [视觉设计] 非活动区域用更深的颜色
                Color(hex: inactiveBgColorHex)
                    .ignoresSafeArea()
                
                // 0.3 Active Area Background Layer - 活动区域背景（较浅色）
                // [性能优化] 只在有图片的区域显示较浅背景
                ActiveAreaBackground(
                    appState: appState,
                    activeColor: Color(hex: canvasBgColorHex),
                    canvasOffset: appState.canvasOffset,
                    canvasScale: appState.canvasScale,
                    frameSize: geometry.size
                )
                
                // 0.5 Grid Layer
                // [视觉设计] 点阵网格，只在活动区域渲染
                if showGrid {
                    OptimizedGridBackground(
                        appState: appState,
                        offset: appState.canvasOffset,
                        scale: appState.canvasScale,
                        color: Color(hex: gridColorHex),
                        frameSize: geometry.size
                    )
                }
                
                // 1. Interaction Layer (Click to clear, Drag to Box Select)
                // [视觉设计] 使用几乎透明的黑色来捕获点击和拖拽事件。
                Color.black.opacity(0.001)
                    .gesture(
                        DragGesture(minimumDistance: 1, coordinateSpace: .local)
                            .onChanged { value in
                                if selectionStart == nil {
                                    selectionStart = value.startLocation
                                }
                                let start = selectionStart!
                                let current = value.location
                                selectionRect = CGRect(x: min(start.x, current.x),
                                                       y: min(start.y, current.y),
                                                       width: abs(current.x - start.x),
                                                       height: abs(current.y - start.y))
                            }
                            .onEnded { value in
                                if let rect = selectionRect {
                                    selectImages(in: rect, geometry: geometry)
                                }
                                selectionRect = nil
                                selectionStart = nil
                            }
                    )
                    .onTapGesture {
                        appState.selectedImageIds.removeAll()
                    }
                
                // 1.5 Groups Layer
                // [视觉设计] 组渲染层，在图片下方
                ZStack {
                    ForEach(appState.groups) { group in
                        GroupView(group: group)
                    }
                }
                .offset(appState.canvasOffset)
                .scaleEffect(appState.canvasScale)
                
                // 2. Images Layer
                // [视觉设计] 这个 ZStack 容纳所有图片实体。
                ZStack {
                    ForEach(appState.images) { image in
                        ImageView(imageEntity: image)
                    }
                }
                // [视觉设计] 整个画布作为一个整体进行变换（偏移 & 缩放）。
                .offset(appState.canvasOffset)
                .scaleEffect(appState.canvasScale)
                
                // 3. Selection Rect Overlay (Screen Space)
                // [视觉设计] 绘制框选矩形
                if let rect = selectionRect {
                    Rectangle()
                        .stroke(Color.blue, lineWidth: 1)
                        .background(Color.blue.opacity(0.1))
                        .frame(width: rect.width, height: rect.height)
                        .position(x: rect.midX, y: rect.midY)
                        .allowsHitTesting(false)
                }
                
                // 4. Smart Guides Overlay (画布空间)
                // [智能对齐] 绘制辅助线，跟随画布变换
                // 始终挂载，通过 SwiftUI 原生 transition + animation 实现逐条淡入淡出
                SmartGuidesOverlay(
                    snapLines: appState.activeSnapLines,
                    canvasOffset: appState.canvasOffset,
                    canvasScale: appState.canvasScale
                )
                .allowsHitTesting(false)
                .animation(.easeInOut(duration: 0.15), value: appState.activeSnapLines)
            }
            .clipped() // [视觉设计] 确保内容不会溢出窗口边界。
            // .background(Color(nsColor: .darkGray)) // Removed: Replaced by custom background layer
            // Attach Window Accessor to background to capture window events
            .background(WindowAccessor())
            .onDrop(of: [.image, .fileURL], isTargeted: nil) { providers, location in
                // [坐标转换] 将屏幕 Drop 位置转换为世界坐标
                // 逆变换公式（与 selectImages 保持一致）：
                // Screen = Center + (World + Offset - Center) * Scale
                // World  = (Screen - Center) / Scale - Offset + Center
                let center = CGPoint(x: geometry.size.width / 2, y: geometry.size.height / 2)
                let scale = appState.canvasScale
                let offset = appState.canvasOffset
                let worldX = (location.x - center.x) / scale - offset.width + center.x
                let worldY = (location.y - center.y) / scale - offset.height + center.y
                loadImages(from: providers, at: CGPoint(x: worldX, y: worldY))
                return true
            }
            // [交互优化] 定义全局坐标空间
            // 为子视图提供一个稳定的参考系，避免在缩放/移动时产生反馈循环导致的闪烁。
            .coordinateSpace(name: "Canvas")
        }
    }
    
    // [交互逻辑] 计算框选
    // 将屏幕空间的矩形转换为画布空间，并查找相交的图像。
    private func selectImages(in rect: CGRect, geometry: GeometryProxy) {
        // 1. 将屏幕矩形转换为画布空间
        // 屏幕坐标 = (画布坐标 * scale) + offset
        // 画布坐标 = (屏幕坐标 - offset) / scale
        
        // 由于 SwiftUI 的坐标系变换，我们需要小心处理。
        // 这里的 rect 是相对于 CanvasView (GeometryReader) 的。
        // 图片的 position 是相对于 ZStack 中心的吗？不，ZStack 默认是中心对齐，但我们通过 .position 放置图片。
        // 实际上，ZStack 内部的坐标系原点通常是左上角（如果使用了 GeometryReader），或者中心。
        // 让我们简化逻辑：我们将把每个图片的中心点投影到屏幕空间，看它是否在 rect 内。
        
        // 画布变换参数
        let offset = appState.canvasOffset
        let scale = appState.canvasScale
        _ = CGPoint(x: geometry.size.width / 2, y: geometry.size.height / 2)
        
        var newSelection = Set<UUID>()
        
        for image in appState.images {
            // 计算图片在屏幕上的位置
            // 注意：ZStack 的 .offset 和 .scaleEffect 是应用在整个层上的。
            // 假设 ZStack 填满 GeometryReader，其中心是 (w/2, h/2)。
            // 图片的 (x, y) 是相对于 ZStack 内部坐标系的（未变换前）。
            // 变换后的屏幕坐标 P_screen = (P_world * scale) + offset + center_correction?
            
            // 让我们反过来：把屏幕 rect 转换到世界空间 (World Space)
            // 假设 ZStack 的中心在屏幕中心 (geometry.size.width/2, height/2)
            // 实际上，ZStack 默认布局下，(0,0) 也是中心。
            // 但是我们在 ImageView 中使用了 .position(x: y:)，这通常意味着坐标系是左上角 (0,0)。
            
            // 修正：ZStack 默认是 Center alignment。
            // 但是 .position 修饰符会将视图放置在父视图坐标系的特定点。
            // 在 GeometryReader 中，(0,0) 是左上角。
            
            // World Coordinate of Image = (image.x, image.y)
            // Screen Coordinate = (World * scale) + offset
            // Wait, offset is applied to the ZStack.
            // So Screen X = (Image X * scale) + offset.width
            // Screen Y = (Image Y * scale) + offset.height
            // 这里的 Image X/Y 是相对于 GeometryReader 左上角的（因为 ZStack 填满了它）。
            
            // 让我们验证一下：
            // 如果 scale=1, offset=0，图片在 (100, 100)，屏幕上就在 (100, 100)。
            // 如果 offset=(10, 0)，屏幕上在 (110, 100)。
            // 如果 scale=2，屏幕上在 (200, 200) + offset?
            // 不，.scaleEffect 默认是以中心为锚点缩放的。
            // .offset 是平移。
            
            // 这是一个复杂的变换链。
            // 简单的方法：
            // 屏幕点 P_s
            // 对应的世界点 P_w = (P_s - Center) / scale - Offset/scale + Center
            // 让我们试着把 rect 转换到 "Image Layer Space"
            
            let frameWidth = geometry.size.width
            let frameHeight = geometry.size.height
            
            // 变换矩阵：
            // 1. Translate(-Center)
            // 2. Scale(s)
            // 3. Translate(Offset)
            // 4. Translate(Center)
            
            // 逆变换：
            // 1. Translate(-Center)
            // 2. Translate(-Offset)
            // 3. Scale(1/s)
            // 4. Translate(Center)
            
            let r = rect
            
            // 将 Rect 的四个角转换到世界空间
            let corners = [
                CGPoint(x: r.minX, y: r.minY),
                CGPoint(x: r.maxX, y: r.minY),
                CGPoint(x: r.maxX, y: r.maxY),
                CGPoint(x: r.minX, y: r.maxY)
            ]
            
            let worldCorners = corners.map { p -> CGPoint in
                let x1 = p.x - frameWidth / 2
                let y1 = p.y - frameHeight / 2
                
                // Inverse Transform:
                // Screen = Center + (World + Offset - Center) * Scale
                // World = (Screen - Center) / Scale - Offset + Center
                
                let x2 = x1 / scale
                let y2 = y1 / scale
                
                let x3 = x2 - offset.width
                let y3 = y2 - offset.height
                
                let x4 = x3 + frameWidth / 2
                let y4 = y3 + frameHeight / 2
                
                return CGPoint(x: x4, y: y4)
            }
            
            let minWx = worldCorners.map { $0.x }.min()!
            let maxWx = worldCorners.map { $0.x }.max()!
            let minWy = worldCorners.map { $0.y }.min()!
            let maxWy = worldCorners.map { $0.y }.max()!
            
            let worldRect = CGRect(x: minWx, y: minWy, width: maxWx - minWx, height: maxWy - minWy)
            
            // 检查图片中心是否在 worldRect 内
            if worldRect.contains(CGPoint(x: image.x, y: image.y)) {
                newSelection.insert(image.id)
            }
        }
        
        // 如果按住 Shift/Cmd，可以追加选择（这里简化为替换）
        appState.selectedImageIds = newSelection
    }
    
    private func loadImages(from providers: [NSItemProvider], at worldPosition: CGPoint = .zero) {
        for provider in providers {
            if provider.canLoadObject(ofClass: URL.self) {
                _ = provider.loadObject(ofClass: URL.self) { url, _ in
                    if let url = url {
                        DispatchQueue.main.async {
                            appState.addImage(from: url, at: worldPosition)
                        }
                    }
                }
            } else if provider.canLoadObject(ofClass: NSImage.self) {
                _ = provider.loadObject(ofClass: NSImage.self) { image, _ in
                    if let image = image as? NSImage,
                       let tiff = image.tiffRepresentation,
                       let bitmap = NSBitmapImageRep(data: tiff),
                       let data = bitmap.representation(using: .png, properties: [:]) {
                        DispatchQueue.main.async {
                            appState.addImage(data: data, at: worldPosition)
                        }
                    }
                }
            }
        }
    }
}

// MARK: - Image View

struct ImageView: View {
    @Environment(AppState.self) var appState
    var imageEntity: ImageEntity
    
    // Local state for gestures
    // 注意：dragOffset 现在只用于 resizeGesture。
    // 移动图片的 dragOffset 已经移至 AppState.currentDragOffset 以支持多选移动。
    @State private var zoomScale: CGFloat = 1.0
    @State private var rotationAngle: Angle = .zero
    
    // [交互状态] 初始边界缓存
    // 用于在拖拽开始时记录整个选择集的边界，以便计算缩放锚点。
    @State private var initialSelectionBounds: CGRect? = nil
    
    // [撤销/重做] 记录操作前的状态
    @State private var dragStartPositions: [UUID: CGPoint] = [:]  // 拖拽开始时的位置
    @State private var scaleStartValue: CGFloat = 1.0  // 缩放开始时的值
    @State private var rotationStartValue: CGFloat = 0  // 旋转开始时的值
    @State private var resizeStartStates: [(id: UUID, scale: CGFloat, position: CGPoint)] = []  // resize开始时的状态
    
    var isSelected: Bool {
        appState.selectedImageIds.contains(imageEntity.id)
    }
    
    // [交互逻辑] 计算显示位置
    // 将多选缩放和拖拽的临时状态应用到位置计算中。
    private var displayPosition: CGPoint {
        let currentOffset = isSelected ? appState.currentDragOffset : .zero
        
        // 默认位置 (应用拖拽偏移)
        var x = imageEntity.x + currentOffset.width
        var y = imageEntity.y + currentOffset.height
        
        // 应用多选缩放 (相对于锚点)
        if isSelected && appState.multiSelectScaleFactor != 1.0 {
            let anchor = appState.multiSelectAnchor
            // NewPos = Anchor + (OldPos - Anchor) * Factor
            // 注意：这里的 OldPos 应该是原始位置 (imageEntity.x/y)，因为缩放是基于原始状态计算的。
            // 拖拽偏移 (currentOffset) 在缩放时通常为 0，除非同时进行（这在当前交互中是不可能的）。
            x = anchor.x + (imageEntity.x - anchor.x) * appState.multiSelectScaleFactor
            y = anchor.y + (imageEntity.y - anchor.y) * appState.multiSelectScaleFactor
        }
        
        return CGPoint(x: x, y: y)
    }
    
    var body: some View {
        if let nsImage = imageEntity.nsImage {
            // [视觉设计] 恒定屏幕空间边框宽度
            let totalScale = max(imageEntity.scale * zoomScale * appState.canvasScale, 0.01)
            let borderWidth = 3.0 / totalScale
            let handleSize = 12.0 / totalScale // 恒定大小的手柄
            
            Image(nsImage: nsImage)
                .resizable()
                .antialiased(true)
                .aspectRatio(contentMode: .fit)
                .frame(width: nsImage.size.width, height: nsImage.size.height)
                // [视觉设计] 选中指示器 & 调整手柄
                .overlay(
                    ZStack {
                        if isSelected {
                            Rectangle()
                                .stroke(Color.blue, lineWidth: borderWidth)
                            
                            // Resize Handles (Corners)
                            // Top-Left
                            ResizeHandle(size: handleSize)
                                .position(x: 0, y: 0)
                                .gesture(resizeGesture(handle: .topLeading, originalSize: nsImage.size))
                            
                            // Top-Right
                            ResizeHandle(size: handleSize)
                                .position(x: nsImage.size.width, y: 0)
                                .gesture(resizeGesture(handle: .topTrailing, originalSize: nsImage.size))
                            
                            // Bottom-Left
                            ResizeHandle(size: handleSize)
                                .position(x: 0, y: nsImage.size.height)
                                .gesture(resizeGesture(handle: .bottomLeading, originalSize: nsImage.size))
                            
                            // Bottom-Right
                            ResizeHandle(size: handleSize)
                                .position(x: nsImage.size.width, y: nsImage.size.height)
                                .gesture(resizeGesture(handle: .bottomTrailing, originalSize: nsImage.size))
                        }
                    }
                )
                .scaleEffect(imageEntity.scale * zoomScale * (isSelected ? appState.multiSelectScaleFactor : 1.0))
                .rotationEffect(Angle(degrees: imageEntity.rotation) + rotationAngle)
                .position(displayPosition)
                // Gestures
                .gesture(
                    SimultaneousGesture(
                        // Drag to Move
                        // [交互优化] 使用全局坐标系 (Canvas)
                        // 避免使用 .local，因为手势过程中视图本身的位置会发生变化，导致坐标系不稳定（闪烁/不跟手）。
                        DragGesture(coordinateSpace: .named("Canvas"))
                            .onChanged { value in
                                // [交互逻辑] 多选移动支持
                                // 1. 如果拖拽的是未选中的图片，且没有按 Shift，则单选它。
                                if !isSelected {
                                    if !NSEvent.modifierFlags.contains(.shift) {
                                        appState.selectedImageIds = [imageEntity.id]
                                    } else {
                                        appState.selectedImageIds.insert(imageEntity.id)
                                    }
                                }
                                
                                // [撤销/重做] 记录拖拽开始时的位置（仅在第一次 onChanged 时记录）
                                if dragStartPositions.isEmpty {
                                    for id in appState.selectedImageIds {
                                        if let img = appState.images.first(where: { $0.id == id }) {
                                            dragStartPositions[id] = CGPoint(x: img.x, y: img.y)
                                        }
                                    }
                                    
                                    // [Smart Guides] 拖拽开始时构建参考线缓存
                                    if appState.snapEnabled {
                                        let guides = appState.buildSnapGuides(draggedIds: appState.selectedImageIds)
                                        appState.snapXGuides = guides.xGuides
                                        appState.snapYGuides = guides.yGuides
                                    }
                                }
                                
                                // 2. 更新全局拖拽偏移 (除以 canvasScale 以适应缩放)
                                // 注意：value.translation 是屏幕像素 (Canvas Space)，需要转换为世界坐标增量。
                                let rawOffset = CGSize(
                                    width: value.translation.width / appState.canvasScale,
                                    height: value.translation.height / appState.canvasScale
                                )
                                
                                // [Smart Guides] 应用吸附修正 / Apply snap correction
                                if appState.snapEnabled && !appState.snapXGuides.isEmpty {
                                    let snapResult = appState.performSnap(
                                        draggedIds: appState.selectedImageIds,
                                        currentOffset: rawOffset,
                                        xGuides: appState.snapXGuides,
                                        yGuides: appState.snapYGuides,
                                        canvasScale: appState.canvasScale
                                    )
                                    appState.currentDragOffset = snapResult.correctedOffset
                                    // [动画] 辅助线出现/切换使用原生 SwiftUI 快速淡入
                                    withAnimation(.easeIn(duration: 0.08)) {
                                        appState.activeSnapLines = snapResult.snapLines
                                    }
                                } else {
                                    appState.currentDragOffset = rawOffset
                                    withAnimation(.easeOut(duration: 0.12)) {
                                        appState.activeSnapLines = []
                                    }
                                }

                                // [画布扩展] 拖拽过程中实时扩展画板边界
                                // 与 win11 行为对齐：win11 的 drawBackground 每帧调用 _updateBoardBounds
                                appState.updateBoardBoundsIfNeeded()
                            }
                            .onEnded { value in
                                // 3. 提交移动
                                // 将偏移量应用到所有选中的图片
                                // [Smart Guides] 使用带吸附修正的偏移量 / Use snap-corrected offset
                                let finalOffset = appState.currentDragOffset
                                
                                // [撤销/重做] 构建批量移动记录
                                var moveChanges: [(imageId: UUID, oldPosition: CGPoint, newPosition: CGPoint)] = []
                                
                                for id in appState.selectedImageIds {
                                    if let index = appState.images.firstIndex(where: { $0.id == id }) {
                                        let oldPos = dragStartPositions[id] ?? CGPoint(x: appState.images[index].x, y: appState.images[index].y)
                                        let newPos = CGPoint(
                                            x: appState.images[index].x + finalOffset.width,
                                            y: appState.images[index].y + finalOffset.height
                                        )
                                        
                                        appState.images[index].x = newPos.x
                                        appState.images[index].y = newPos.y
                                        
                                        moveChanges.append((imageId: id, oldPosition: oldPos, newPosition: newPos))
                                    }
                                }
                                
                                // [撤销/重做] 记录批量移动操作（只有实际移动了才记录）
                                if !moveChanges.isEmpty && (abs(finalOffset.width) > 0.1 || abs(finalOffset.height) > 0.1) {
                                    appState.undoManager.recordAction(.batchMove(changes: moveChanges))
                                    
                                    // 检查移动的图片是否移出了组 / Check if moved images are out of their groups
                                    for change in moveChanges {
                                        appState.checkImageOutOfGroup(imageId: change.imageId)
                                    }
                                }
                                
                                // 4. 重置状态
                                appState.currentDragOffset = .zero
                                dragStartPositions.removeAll()
                                
                                // [Smart Guides] 清除辅助线（原生淡出动画）和缓存
                                withAnimation(.easeOut(duration: 0.2)) {
                                    appState.activeSnapLines = []
                                }
                                appState.snapXGuides = []
                                appState.snapYGuides = []
                                
                                // [画布扩展] 拖拽结束后检查是否需要扩展画板边界
                                appState.updateBoardBoundsIfNeeded()
                            }
                        ,
                        SimultaneousGesture(
                            // Pinch to Scale (Trackpad)
                            MagnificationGesture()
                                .onChanged { value in
                                    // [撤销/重做] 记录缩放开始时的值（仅在第一次 onChanged 时记录）
                                    if zoomScale == 1.0 {
                                        scaleStartValue = imageEntity.scale
                                    }
                                    zoomScale = value
                                }
                                .onEnded { value in
                                    if let index = appState.images.firstIndex(where: { $0.id == imageEntity.id }) {
                                        let oldScale = scaleStartValue
                                        let newScale = appState.images[index].scale * value
                                        appState.images[index].scale = newScale
                                        
                                        // [撤销/重做] 记录缩放操作
                                        appState.undoManager.recordAction(.scale(
                                            imageId: imageEntity.id,
                                            oldScale: oldScale,
                                            newScale: newScale
                                        ))
                                    }
                                    zoomScale = 1.0
                                    scaleStartValue = 1.0
                                    
                                    // [画布扩展] 缩放结束后检查是否需要扩展画板边界
                                    appState.updateBoardBoundsIfNeeded()
                                }
                            ,
                            // Rotate (Trackpad)
                            RotationGesture()
                                .onChanged { value in
                                    // [撤销/重做] 记录旋转开始时的值（仅在第一次 onChanged 时记录）
                                    if rotationAngle == .zero {
                                        rotationStartValue = imageEntity.rotation
                                    }
                                    rotationAngle = value
                                }
                                .onEnded { value in
                                    if let index = appState.images.firstIndex(where: { $0.id == imageEntity.id }) {
                                        let oldRotation = rotationStartValue
                                        let newRotation = appState.images[index].rotation + value.degrees
                                        appState.images[index].rotation = newRotation
                                        
                                        // [撤销/重做] 记录旋转操作
                                        appState.undoManager.recordAction(.rotate(
                                            imageId: imageEntity.id,
                                            oldRotation: oldRotation,
                                            newRotation: newRotation
                                        ))
                                    }
                                    rotationAngle = .zero
                                    rotationStartValue = 0
                                }
                        )
                    )
                )
                .onTapGesture {
                    // [交互逻辑] Shift 多选 / 反选
                    if NSEvent.modifierFlags.contains(.shift) {
                        if isSelected {
                            appState.selectedImageIds.remove(imageEntity.id)
                        } else {
                            appState.selectedImageIds.insert(imageEntity.id)
                        }
                    } else {
                        appState.selectedImageIds = [imageEntity.id]
                    }
                }
                .contextMenu {
                    // [打组] 当选中≥2张图片时显示打组选项
                    if appState.selectedImageIds.count >= 2 {
                        Button(LocalizedStringKey("Group Selected (G)")) {
                            appState.groupSelectedImages()
                        }
                        
                        Divider()
                    }
                    
                    Button(LocalizedStringKey("Smart Sort")) {
                        appState.smartSortSelected()
                    }
                    
                    Divider()
                    
                    Button(LocalizedStringKey("Remove Background (NPU)")) {
                        appState.removeBackground(for: imageEntity.id)
                    }
                    
                    Button(LocalizedStringKey("Delete")) {
                        appState.removeImage(id: imageEntity.id)
                    }
                    
                    Button(LocalizedStringKey("Reset Scale")) {
                        if let index = appState.images.firstIndex(where: { $0.id == imageEntity.id }) {
                            appState.images[index].scale = 1.0
                        }
                    }
                    
                    Divider()
                    
                    // [图层管理] 层级子菜单
                    Menu(LocalizedStringKey("Layer")) {
                        Button(LocalizedStringKey("Bring Forward")) {
                            appState.bringForward(id: imageEntity.id)
                        }
                        
                        Button(LocalizedStringKey("Send Backward")) {
                            appState.sendBackward(id: imageEntity.id)
                        }
                        
                        Divider()
                        
                        Button(LocalizedStringKey("Bring to Front")) {
                            appState.bringToFront(id: imageEntity.id)
                        }
                        
                        Button(LocalizedStringKey("Send to Back")) {
                            appState.sendToBack(id: imageEntity.id)
                        }
                    }
                    
                    Divider()
                    
                    Button(LocalizedStringKey("Reset Board Size")) {
                        appState.resetBoardBounds()
                    }
                    
                    Divider()
                    
                    Button(LocalizedStringKey("Export Board as Image")) {
                        appState.exportBoardAsImage()
                    }
                    
                    Button(LocalizedStringKey("Copy Board to Clipboard")) {
                        appState.copyBoardToClipboard()
                    }
                    
                    Divider()
                    
                    // [Smart Guides] 智能对齐开关
                    Button(appState.snapEnabled
                           ? LocalizedStringKey("✓ Smart Guides (On)")
                           : LocalizedStringKey("Smart Guides (Off)")) {
                        appState.snapEnabled.toggle()
                    }
                }
        }
    }
    
    // [交互逻辑] 调整大小手势 (锚点缩放)
    // 根据拖拽的手柄位置，计算缩放比例和中心点偏移，以实现"对角线锚点"的视觉效果。
    private func resizeGesture(handle: Alignment, originalSize: CGSize) -> some Gesture {
        // [交互优化] 使用全局坐标系 (Canvas)
        // 避免使用 .local，因为手势过程中视图本身的大小和位置会发生变化，导致坐标系不稳定（闪烁）。
        DragGesture(minimumDistance: 1, coordinateSpace: .named("Canvas"))
            .onChanged { value in
                // 1. 初始化：计算初始边界和锚点
                if initialSelectionBounds == nil {
                    if let bounds = appState.calculateSelectionBounds() {
                        initialSelectionBounds = bounds
                        
                        // [撤销/重做] 记录resize开始时所有选中图片的状态
                        resizeStartStates.removeAll()
                        for id in appState.selectedImageIds {
                            if let img = appState.images.first(where: { $0.id == id }) {
                                resizeStartStates.append((id: id, scale: img.scale, position: CGPoint(x: img.x, y: img.y)))
                            }
                        }
                        
                        // 根据手柄位置确定锚点 (Anchor)
                        // 锚点是手柄的对角点
                        switch handle {
                        case .bottomTrailing: // Dragging Bottom-Right -> Anchor is Top-Left
                            appState.multiSelectAnchor = CGPoint(x: bounds.minX, y: bounds.minY)
                        case .topLeading: // Dragging Top-Left -> Anchor is Bottom-Right
                            appState.multiSelectAnchor = CGPoint(x: bounds.maxX, y: bounds.maxY)
                        case .topTrailing: // Dragging Top-Right -> Anchor is Bottom-Left
                            appState.multiSelectAnchor = CGPoint(x: bounds.minX, y: bounds.maxY)
                        case .bottomLeading: // Dragging Bottom-Left -> Anchor is Top-Right
                            appState.multiSelectAnchor = CGPoint(x: bounds.maxX, y: bounds.minY)
                        default:
                            appState.multiSelectAnchor = CGPoint(x: bounds.midX, y: bounds.midY)
                        }
                    }
                }
                
                guard let bounds = initialSelectionBounds else { return }
                let anchor = appState.multiSelectAnchor
                
                // 2. 计算缩放倍率 (k)
                // 我们需要计算手柄相对于锚点的当前距离与初始距离的比率。
                
                // 初始手柄位置 (Handle Start Position)
                // 注意：这里我们使用 bounds 的角点作为手柄的逻辑位置，这比使用单个图片的角点更准确，
                // 因为我们是在缩放整个 Selection Box。
                var startHandlePoint: CGPoint = .zero
                switch handle {
                case .bottomTrailing: startHandlePoint = CGPoint(x: bounds.maxX, y: bounds.maxY)
                case .topLeading:     startHandlePoint = CGPoint(x: bounds.minX, y: bounds.minY)
                case .topTrailing:    startHandlePoint = CGPoint(x: bounds.maxX, y: bounds.minY)
                case .bottomLeading:  startHandlePoint = CGPoint(x: bounds.minX, y: bounds.maxY)
                default: break
                }
                
                // 当前手柄位置 (Current Handle Position)
                // value.translation 是累积的拖拽距离 (Canvas Space)
                // 注意：value.translation 需要除以 canvasScale 才是世界坐标增量
                let deltaX = value.translation.width / appState.canvasScale
                let deltaY = value.translation.height / appState.canvasScale
                
                let currentHandlePoint = CGPoint(x: startHandlePoint.x + deltaX,
                                                 y: startHandlePoint.y + deltaY)
                
                // 计算距离 (投影到 X 轴或 Y 轴，取较大的变化量以保持比例，或者简单地使用 X 轴)
                // 为了简单且稳定，我们使用 X 轴距离比率，除非 X 轴距离太小。
                let startDistX = abs(startHandlePoint.x - anchor.x)
                let currentDistX = abs(currentHandlePoint.x - anchor.x)
                
                let startDistY = abs(startHandlePoint.y - anchor.y)
                let currentDistY = abs(currentHandlePoint.y - anchor.y)
                
                var k: CGFloat = 1.0
                
                if startDistX > 10 {
                    k = currentDistX / startDistX
                } else if startDistY > 10 {
                    k = currentDistY / startDistY
                }
                
                // 限制最小缩放
                k = max(0.1, k)
                
                // [交互逻辑] 多选缩放支持
                // 更新全局缩放因子，让所有选中的图片都能实时预览缩放效果。
                appState.multiSelectScaleFactor = k
            }
            .onEnded { value in
                // 5. 提交更改
                // 将临时的 zoomScale 和 dragOffset 应用到实体属性中。
                // [交互逻辑] 多选缩放提交
                // 遍历所有选中的图片，应用缩放因子。
                let anchor = appState.multiSelectAnchor
                let k = appState.multiSelectScaleFactor
                
                // [撤销/重做] 构建批量缩放记录
                var scaleChanges: [(imageId: UUID, oldScale: CGFloat, newScale: CGFloat, oldPosition: CGPoint, newPosition: CGPoint)] = []
                
                for id in appState.selectedImageIds {
                    if let index = appState.images.firstIndex(where: { $0.id == id }) {
                        // 获取原始状态
                        let startState = resizeStartStates.first(where: { $0.id == id })
                        let oldScale = startState?.scale ?? appState.images[index].scale
                        let oldPosition = startState?.position ?? CGPoint(x: appState.images[index].x, y: appState.images[index].y)
                        
                        // 1. 更新缩放
                        let newScale = oldScale * k
                        appState.images[index].scale = newScale
                        
                        // 2. 更新位置 (相对于锚点缩放)
                        // NewPos = Anchor + (OldPos - Anchor) * k
                        let newX = anchor.x + (oldPosition.x - anchor.x) * k
                        let newY = anchor.y + (oldPosition.y - anchor.y) * k
                        
                        appState.images[index].x = newX
                        appState.images[index].y = newY
                        
                        scaleChanges.append((
                            imageId: id,
                            oldScale: oldScale,
                            newScale: newScale,
                            oldPosition: oldPosition,
                            newPosition: CGPoint(x: newX, y: newY)
                        ))
                    }
                }
                
                // [撤销/重做] 记录批量缩放操作（只有实际缩放了才记录）
                if !scaleChanges.isEmpty && abs(k - 1.0) > 0.01 {
                    appState.undoManager.recordAction(.batchScale(changes: scaleChanges))
                }
                
                // 重置临时状态
                zoomScale = 1.0
                appState.multiSelectScaleFactor = 1.0
                initialSelectionBounds = nil
                resizeStartStates.removeAll()
                
                // [画布扩展] 多选缩放结束后检查是否需要扩展画板边界
                appState.updateBoardBoundsIfNeeded()
            }
    }
}
// MARK: - Resize Handle

// [视觉设计] 调整大小手柄组件
struct ResizeHandle: View {
    var size: CGFloat
    
    var body: some View {
        Circle()
            .fill(Color.white)
            .frame(width: size, height: size)
            .overlay(
                Circle()
                    .stroke(Color.blue, lineWidth: 1)
            )
            .shadow(radius: 1)
    }
}

// MARK: - Grid Background
struct GridBackground: View {
    var offset: CGSize
    var scale: CGFloat
    var color: Color
    
    var body: some View {
        Canvas { context, size in
            let baseSpacing: CGFloat = 20.0
            var effectiveSpacing = baseSpacing
            
            // LOD (Level of Detail): Increase spacing when zoomed out to prevent moire patterns
            // and performance issues.
            while (effectiveSpacing * scale) < 15 {
                effectiveSpacing *= 2
            }
            
            let gridStep = effectiveSpacing * scale
            let dotRadius = 1.0 // Constant screen size for dots
            
            let offsetX = offset.width * scale
            let offsetY = offset.height * scale
            
            // Calculate start positions to align grid with world space
            var startX = offsetX.truncatingRemainder(dividingBy: gridStep)
            if startX < 0 { startX += gridStep }
            
            var startY = offsetY.truncatingRemainder(dividingBy: gridStep)
            if startY < 0 { startY += gridStep }
            
            // Draw dots
            for x in stride(from: startX, to: size.width, by: gridStep) {
                for y in stride(from: startY, to: size.height, by: gridStep) {
                    let rect = CGRect(x: x - dotRadius, y: y - dotRadius, width: dotRadius * 2, height: dotRadius * 2)
                    context.fill(Path(ellipseIn: rect), with: .color(color))
                }
            }
        }
        .allowsHitTesting(false) // Ensure clicks pass through to the background layer
    }
}

// MARK: - Active Area Background
/// [性能优化] 只在画板区域（boardBounds）绘制浅色背景
struct ActiveAreaBackground: View {
    var appState: AppState
    var activeColor: Color
    var canvasOffset: CGSize
    var canvasScale: CGFloat
    var frameSize: CGSize
    
    var body: some View {
        Canvas { context, size in
            // 使用画板边界（固定范围，只扩展不收缩）
            let worldBounds = appState.boardBounds

            // 将世界坐标转换为屏幕坐标
            // 图片层变换链: .offset(canvasOffset).scaleEffect(canvasScale)
            // 正向变换: Screen = Center + (World + Offset - Center) * Scale
            let centerX = size.width / 2
            let centerY = size.height / 2

            let screenX = centerX + (worldBounds.minX + canvasOffset.width - centerX) * canvasScale
            let screenY = centerY + (worldBounds.minY + canvasOffset.height - centerY) * canvasScale
            let screenWidth = worldBounds.width * canvasScale
            let screenHeight = worldBounds.height * canvasScale
            
            let screenRect = CGRect(x: screenX, y: screenY, width: screenWidth, height: screenHeight)
            
            // 绘制活动区域背景
            context.fill(Path(screenRect), with: .color(activeColor))
            
            // 绘制活动区域边框（帮助用户识别边界）
            context.stroke(Path(screenRect), with: .color(Color(white: 0.35)), lineWidth: 1)
        }
        .allowsHitTesting(false)
    }
}

// MARK: - Optimized Grid Background
/// [性能优化] 只在画板区域（boardBounds）绘制点阵网格
struct OptimizedGridBackground: View {
    var appState: AppState
    var offset: CGSize
    var scale: CGFloat
    var color: Color
    var frameSize: CGSize
    
    var body: some View {
        Canvas { context, size in
            // 使用画板边界（固定范围，只扩展不收缩）
            let worldBounds = appState.boardBounds

            // 将世界坐标转换为屏幕坐标
            // 正向变换: Screen = Center + (World + Offset - Center) * Scale
            let centerX = size.width / 2
            let centerY = size.height / 2

            let screenMinX = centerX + (worldBounds.minX + offset.width - centerX) * scale
            let screenMinY = centerY + (worldBounds.minY + offset.height - centerY) * scale
            let screenMaxX = centerX + (worldBounds.maxX + offset.width - centerX) * scale
            let screenMaxY = centerY + (worldBounds.maxY + offset.height - centerY) * scale

            // 裁剪到可见区域
            let visibleMinX = max(0, screenMinX)
            let visibleMinY = max(0, screenMinY)
            let visibleMaxX = min(size.width, screenMaxX)
            let visibleMaxY = min(size.height, screenMaxY)

            // 如果画板区域不在可见范围内，不绘制
            guard visibleMinX < visibleMaxX && visibleMinY < visibleMaxY else {
                return
            }

            let baseSpacing: CGFloat = 20.0
            var effectiveSpacing = baseSpacing

            // LOD (Level of Detail): Increase spacing when zoomed out
            while (effectiveSpacing * scale) < 15 {
                effectiveSpacing *= 2
            }

            let gridStep = effectiveSpacing * scale
            let dotRadius = 1.0

            // 网格点需要与世界坐标对齐：世界原点 (0,0) 经正向变换后的屏幕位置
            // Screen = Center + (World + Offset - Center) * Scale
            // 世界原点在屏幕上: originScreenX = centerX + (0 + offset.width - centerX) * scale
            let originScreenX = centerX + (offset.width - centerX) * scale
            let originScreenY = centerY + (offset.height - centerY) * scale

            // Calculate start positions to align grid with world space
            var startX = originScreenX.truncatingRemainder(dividingBy: gridStep)
            if startX < 0 { startX += gridStep }

            var startY = originScreenY.truncatingRemainder(dividingBy: gridStep)
            if startY < 0 { startY += gridStep }
            
            // 调整起始点到可见画板区域内
            var drawStartX = startX
            while drawStartX < visibleMinX {
                drawStartX += gridStep
            }
            
            var drawStartY = startY
            while drawStartY < visibleMinY {
                drawStartY += gridStep
            }
            
            // 限制最大点数（防止极端情况）
            let estimatedCols = (visibleMaxX - drawStartX) / gridStep
            let estimatedRows = (visibleMaxY - drawStartY) / gridStep
            let estimatedPoints = estimatedCols * estimatedRows
            
            var actualGridStep = gridStep
            if estimatedPoints > 5000 {
                let scaleFactor = sqrt(estimatedPoints / 5000)
                actualGridStep = gridStep * scaleFactor
                
                // 重新计算起始点
                drawStartX = startX
                while drawStartX < visibleMinX {
                    drawStartX += actualGridStep
                }
                drawStartY = startY
                while drawStartY < visibleMinY {
                    drawStartY += actualGridStep
                }
            }
            
            // Draw dots only within board area
            for x in stride(from: drawStartX, to: visibleMaxX, by: actualGridStep) {
                for y in stride(from: drawStartY, to: visibleMaxY, by: actualGridStep) {
                    let rect = CGRect(x: x - dotRadius, y: y - dotRadius, width: dotRadius * 2, height: dotRadius * 2)
                    context.fill(Path(ellipseIn: rect), with: .color(color))
                }
            }
        }
        .allowsHitTesting(false)
    }
}

// MARK: - Group View
/// 组视图，用于渲染图片组 / Group view for rendering image groups
struct GroupView: View {
    @Environment(AppState.self) var appState
    var group: GroupEntity
    
    // [交互状态]
    @State private var isDragging = false
    @State private var dragStartPosition: CGPoint? = nil
    @State private var memberStartPositions: [UUID: CGPoint] = [:]
    
    // [调整大小状态] / Resize state
    @State private var isResizing = false
    @State private var resizeCorner: String? = nil
    @State private var resizeStartRect: CGRect? = nil
    @State private var resizeStartMouse: CGPoint? = nil
    
    // [双击编辑状态] / Double click edit state
    @State private var showNameEditor = false
    @State private var editingName = ""
    
    var isSelected: Bool {
        appState.selectedGroupId == group.id
    }
    
    var body: some View {
        ZStack {
            // 组背景 / Group background
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(hex: String(group.colorHex.prefix(7))).opacity(group.opacity))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(
                            isSelected ? Color.blue : Color(hex: String(group.colorHex.prefix(7))).opacity(min(group.opacity + 0.3, 1.0)),
                            lineWidth: isSelected ? 3 : 2
                        )
                )
            
            // 调整大小手柄 / Resize handles (when selected)
            if isSelected {
                // 四个角的调整手柄 / Four corner resize handles
                ForEach(["tl", "tr", "bl", "br"], id: \.self) { corner in
                    ResizeHandleView(corner: corner, groupWidth: group.width, groupHeight: group.height)
                        .gesture(
                            resizeGesture(corner: corner)
                        )
                }
            }
            
            // 组名称标签（左上角外侧）/ Group name label (outside top-left)
            // 注意：不使用 .offset()，因为 .offset 只是视觉偏移，不会改变 hit testing 区域
            // 改用 overlay + GeometryReader 实现正确的点击区域定位
            // (名称标签在 .frame/.position 之外单独处理，见下方 overlay)
        }
        .frame(width: group.width, height: group.height)
        // 组名称标签 overlay（使用 allowsHitTesting + 独立手势，避免被 DragGesture 抢占）
        .overlay(alignment: .topLeading) {
            if !group.name.isEmpty {
                Text(group.name)
                    .font(.system(size: group.fontSize))
                    .foregroundColor(Color(hex: String(group.colorHex.prefix(7))))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color(white: 0.15, opacity: 0.85))
                    .cornerRadius(4)
                    .fixedSize()  // 防止文本被截断
                    .alignmentGuide(.top) { d in d[.bottom] + 4 }  // 将标签推到组框上方
                    .onTapGesture(count: 2) {
                        // 双击编辑名称 / Double click to edit name
                        editingName = group.name
                        showNameEditor = true
                    }
                    .onTapGesture(count: 1) {
                        // 单击选中组（防止单击穿透到下层）
                        appState.selectedGroupId = group.id
                        appState.selectedImageIds.removeAll()
                    }
            }
        }
        .position(x: group.x + group.width / 2, y: group.y + group.height / 2)
        .gesture(
            DragGesture(coordinateSpace: .named("Canvas"))
                .onChanged { value in
                    if !isDragging {
                        isDragging = true
                        dragStartPosition = CGPoint(x: group.x, y: group.y)
                        
                        // 记录所有成员的起始位置 / Record start positions of all members
                        memberStartPositions.removeAll()
                        for memberId in group.memberIds {
                            if let img = appState.images.first(where: { $0.id == memberId }) {
                                memberStartPositions[memberId] = CGPoint(x: img.x, y: img.y)
                            }
                        }
                    }
                    
                    // 计算拖拽偏移 / Calculate drag offset
                    let delta = CGSize(
                        width: value.translation.width / appState.canvasScale,
                        height: value.translation.height / appState.canvasScale
                    )
                    
                    // 移动所有成员 / Move all members
                    for memberId in group.memberIds {
                        if let imgIndex = appState.images.firstIndex(where: { $0.id == memberId }),
                           let startPos = memberStartPositions[memberId] {
                            appState.images[imgIndex].x = startPos.x + delta.width
                            appState.images[imgIndex].y = startPos.y + delta.height
                        }
                    }
                    
                    // 更新组位置 / Update group position
                    if let groupIndex = appState.groups.firstIndex(where: { $0.id == group.id }),
                       let startPos = dragStartPosition {
                        appState.groups[groupIndex].x = startPos.x + delta.width
                        appState.groups[groupIndex].y = startPos.y + delta.height
                    }
                }
                .onEnded { value in
                    isDragging = false
                    
                    // 记录撤销 / Record undo
                    if let startPos = dragStartPosition,
                       let groupIndex = appState.groups.firstIndex(where: { $0.id == group.id }) {
                        let endPos = CGPoint(x: appState.groups[groupIndex].x, y: appState.groups[groupIndex].y)
                        let delta = CGSize(width: endPos.x - startPos.x, height: endPos.y - startPos.y)
                        
                        if abs(delta.width) > 1 || abs(delta.height) > 1 {
                            var memberMoves: [(imageId: UUID, oldPosition: CGPoint, newPosition: CGPoint)] = []
                            for (memberId, startMemberPos) in memberStartPositions {
                                if let img = appState.images.first(where: { $0.id == memberId }) {
                                    memberMoves.append((memberId, startMemberPos, CGPoint(x: img.x, y: img.y)))
                                }
                            }
                            appState.undoManager.recordAction(.moveGroup(
                                groupId: group.id,
                                oldPosition: startPos,
                                newPosition: endPos,
                                memberMoves: memberMoves
                            ))
                        }
                    }
                    
                    // [画布扩展] 组拖拽结束后检查是否需要扩展画板边界
                    appState.updateBoardBoundsIfNeeded()
                    
                    dragStartPosition = nil
                    memberStartPositions.removeAll()
                }
        )
        .onTapGesture {
            appState.selectedGroupId = group.id
            appState.selectedImageIds.removeAll()
        }
        .contextMenu {
            Button(LocalizedStringKey("Group Settings")) {
                appState.editingGroupId = group.id
                appState.showGroupSettings = true
            }
            
            Divider()
            
            Button(LocalizedStringKey("Ungroup")) {
                appState.ungroupGroup(groupId: group.id)
            }
        }
        .sheet(isPresented: $showNameEditor) {
            // 名称编辑弹窗 / Name edit sheet
            VStack(spacing: 16) {
                Text(LocalizedStringKey("Group Name"))
                    .font(.headline)
                
                TextField("", text: $editingName)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 200)
                
                HStack {
                    Button(LocalizedStringKey("Cancel")) {
                        showNameEditor = false
                    }
                    .keyboardShortcut(.cancelAction)
                    
                    Button(LocalizedStringKey("OK")) {
                        if let index = appState.groups.firstIndex(where: { $0.id == group.id }) {
                            appState.groups[index].name = editingName
                        }
                        showNameEditor = false
                    }
                    .keyboardShortcut(.defaultAction)
                }
            }
            .padding(20)
            .frame(width: 280)
        }
    }
    
    // 调整大小手势 / Resize gesture
    private func resizeGesture(corner: String) -> some Gesture {
        DragGesture(coordinateSpace: .named("Canvas"))
            .onChanged { value in
                if !isResizing {
                    isResizing = true
                    resizeCorner = corner
                    resizeStartRect = CGRect(x: group.x, y: group.y, width: group.width, height: group.height)
                    resizeStartMouse = value.startLocation
                }
                
                guard let startRect = resizeStartRect else { return }
                
                let delta = CGSize(
                    width: value.translation.width / appState.canvasScale,
                    height: value.translation.height / appState.canvasScale
                )
                
                let minSize: CGFloat = 50
                
                if let index = appState.groups.firstIndex(where: { $0.id == group.id }) {
                    var newX = startRect.minX
                    var newY = startRect.minY
                    var newWidth = startRect.width
                    var newHeight = startRect.height
                    
                    switch corner {
                    case "br":
                        newWidth = max(minSize, startRect.width + delta.width)
                        newHeight = max(minSize, startRect.height + delta.height)
                    case "bl":
                        let newW = max(minSize, startRect.width - delta.width)
                        newX = startRect.minX + (startRect.width - newW)
                        newWidth = newW
                        newHeight = max(minSize, startRect.height + delta.height)
                    case "tr":
                        newWidth = max(minSize, startRect.width + delta.width)
                        let newH = max(minSize, startRect.height - delta.height)
                        newY = startRect.minY + (startRect.height - newH)
                        newHeight = newH
                    case "tl":
                        let newW = max(minSize, startRect.width - delta.width)
                        newX = startRect.minX + (startRect.width - newW)
                        newWidth = newW
                        let newH = max(minSize, startRect.height - delta.height)
                        newY = startRect.minY + (startRect.height - newH)
                        newHeight = newH
                    default:
                        break
                    }
                    
                    appState.groups[index].x = newX
                    appState.groups[index].y = newY
                    appState.groups[index].width = newWidth
                    appState.groups[index].height = newHeight
                }
            }
            .onEnded { _ in
                isResizing = false
                
                // 调整组边界后检测拉入图片 / Check for images to pull into group after resize
                appState.checkImagesInGroupBounds(groupId: group.id)
                
                resizeCorner = nil
                resizeStartRect = nil
                resizeStartMouse = nil
            }
    }
}

// MARK: - Resize Handle View for Group
struct ResizeHandleView: View {
    var corner: String
    var groupWidth: CGFloat
    var groupHeight: CGFloat
    
    var body: some View {
        Circle()
            .fill(Color.white)
            .frame(width: 12, height: 12)
            .overlay(
                Circle()
                    .stroke(Color.blue, lineWidth: 1)
            )
            .position(handlePosition)
    }
    
    private var handlePosition: CGPoint {
        switch corner {
        case "tl": return CGPoint(x: 0, y: 0)
        case "tr": return CGPoint(x: groupWidth, y: 0)
        case "bl": return CGPoint(x: 0, y: groupHeight)
        case "br": return CGPoint(x: groupWidth, y: groupHeight)
        default: return CGPoint(x: 0, y: 0)
        }
    }
}

// MARK: - Group Settings Sheet
/// 组设置弹窗 / Group settings sheet
struct GroupSettingsSheet: View {
    @Environment(AppState.self) var appState
    @Environment(\.dismiss) var dismiss
    var groupId: UUID
    
    @State private var name: String = ""
    @State private var colorHex: String = "#6495ED"
    @State private var opacity: Double = 0.3
    @State private var fontSize: Double = 14
    
    var body: some View {
        VStack(spacing: 20) {
            Text(LocalizedStringKey("Group Settings"))
                .font(.headline)
            
            // 组名称 / Group name
            HStack {
                Text(LocalizedStringKey("Name"))
                    .frame(width: 80, alignment: .leading)
                TextField("", text: $name)
                    .textFieldStyle(.roundedBorder)
            }
            
            // 颜色选择 / Color picker
            HStack {
                Text(LocalizedStringKey("Color"))
                    .frame(width: 80, alignment: .leading)
                ColorPicker("", selection: Binding(
                    get: { Color(hex: colorHex) },
                    set: { newColor in
                        if let hex = newColor.toHex() {
                            colorHex = hex
                        }
                    }
                ))
                .labelsHidden()
            }
            
            // 透明度 / Opacity
            HStack {
                Text(LocalizedStringKey("Opacity"))
                    .frame(width: 80, alignment: .leading)
                Slider(value: $opacity, in: 0.1...1.0)
                Text("\(Int(opacity * 100))%")
                    .frame(width: 40)
            }
            
            // 字体大小 / Font size
            HStack {
                Text(LocalizedStringKey("Font Size"))
                    .frame(width: 80, alignment: .leading)
                Slider(value: $fontSize, in: 8...72, step: 1)
                Text("\(Int(fontSize))")
                    .frame(width: 40)
            }
            
            // 按钮 / Buttons
            HStack {
                Button(LocalizedStringKey("Cancel")) {
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)
                
                Button(LocalizedStringKey("OK")) {
                    appState.updateGroupSettings(
                        groupId: groupId,
                        name: name,
                        colorHex: colorHex,
                        opacity: CGFloat(opacity),
                        fontSize: CGFloat(fontSize)
                    )
                    dismiss()
                }
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(width: 350)
        .onAppear {
            if let group = appState.groups.first(where: { $0.id == groupId }) {
                name = group.name
                colorHex = String(group.colorHex.prefix(7))
                opacity = Double(group.opacity)
                fontSize = Double(group.fontSize)
            }
        }
    }
}

// MARK: - Smart Guides Overlay
/// [智能对齐] 辅助线绘制覆盖层 - 使用原生 SwiftUI View + ForEach + transition 实现逐条动画
struct SmartGuidesOverlay: View {
    var snapLines: [SnapLine]
    var canvasOffset: CGSize
    var canvasScale: CGFloat
    
    var body: some View {
        GeometryReader { geometry in
            let centerX = geometry.size.width / 2
            let centerY = geometry.size.height / 2
            
            ZStack {
                ForEach(snapLines) { line in
                    SnapLineShape(
                        line: line,
                        canvasOffset: canvasOffset,
                        canvasScale: canvasScale,
                        centerX: centerX,
                        centerY: centerY
                    )
                    .stroke(
                        Color(red: 0, green: 0.73, blue: 1.0, opacity: 0.85),
                        style: StrokeStyle(lineWidth: 1, dash: [4, 3])
                    )
                    // [原生动画] 每条辅助线独立的淡入淡出 transition
                    .transition(.opacity)
                }
            }
        }
    }
}

// MARK: - SnapLineShape
/// 单条辅助线的 Shape，支持 SwiftUI 原生动画系统
struct SnapLineShape: Shape {
    let line: SnapLine
    let canvasOffset: CGSize
    let canvasScale: CGFloat
    let centerX: CGFloat
    let centerY: CGFloat
    
    func path(in rect: CGRect) -> Path {
        var path = Path()

        switch line.axis {
        case .x:
            // 垂直辅助线：世界坐标 → 屏幕坐标
            // 正向变换: Screen = Center + (World + Offset - Center) * Scale
            let screenX = centerX + (line.value + canvasOffset.width - centerX) * canvasScale
            let screenStartY = centerY + (line.start + canvasOffset.height - centerY) * canvasScale
            let screenEndY = centerY + (line.end + canvasOffset.height - centerY) * canvasScale
            path.move(to: CGPoint(x: screenX, y: screenStartY))
            path.addLine(to: CGPoint(x: screenX, y: screenEndY))

        case .y:
            // 水平辅助线：世界坐标 → 屏幕坐标
            // 正向变换: Screen = Center + (World + Offset - Center) * Scale
            let screenY = centerY + (line.value + canvasOffset.height - centerY) * canvasScale
            let screenStartX = centerX + (line.start + canvasOffset.width - centerX) * canvasScale
            let screenEndX = centerX + (line.end + canvasOffset.width - centerX) * canvasScale
            path.move(to: CGPoint(x: screenStartX, y: screenY))
            path.addLine(to: CGPoint(x: screenEndX, y: screenY))
        }

        return path
    }
}



