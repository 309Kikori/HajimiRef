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
                appState.canvasScale = min(max(newScale, 0.1), 10.0)
            }
        }
        
        // MARK: - Magnify
        private func handleMagnify(_ event: NSEvent) {
            let zoomFactor = 1.0 + event.magnification
            let newScale = appState.canvasScale * zoomFactor
            appState.canvasScale = min(max(newScale, 0.1), 10.0)
        }
    }
}

// MARK: - Canvas View

struct CanvasView: View {
    @Environment(AppState.self) var appState
    
    // [个性化设置] 读取用户偏好
    @AppStorage("showGrid") private var showGrid: Bool = true
    @AppStorage("canvasBgColorHex") private var canvasBgColorHex: String = "#1E1E1E"
    @AppStorage("gridColorHex") private var gridColorHex: String = "#404040"
    
    // [交互设计] 框选状态
    @State private var selectionRect: CGRect? = nil
    @State private var selectionStart: CGPoint? = nil
    
    init() {}
    
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // 0. Visual Background Layer
                // [视觉设计] 用户自定义背景颜色
                Color(hex: canvasBgColorHex)
                    .ignoresSafeArea()
                
                // 0.5 Grid Layer
                // [视觉设计] 点阵网格，模仿 Freeform/手帐应用
                if showGrid {
                    GridBackground(offset: appState.canvasOffset, scale: appState.canvasScale, color: Color(hex: gridColorHex))
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
            }
            .clipped() // [视觉设计] 确保内容不会溢出窗口边界。
            // .background(Color(nsColor: .darkGray)) // Removed: Replaced by custom background layer
            // Attach Window Accessor to background to capture window events
            .background(WindowAccessor())
            .onDrop(of: [.image, .fileURL], isTargeted: nil) { providers in
                loadImages(from: providers)
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
    
    private func loadImages(from providers: [NSItemProvider]) {
        for provider in providers {
            if provider.canLoadObject(ofClass: URL.self) {
                _ = provider.loadObject(ofClass: URL.self) { url, _ in
                    if let url = url {
                        DispatchQueue.main.async {
                            appState.addImage(from: url)
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
                            appState.addImage(data: data)
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
                                
                                // 2. 更新全局拖拽偏移 (除以 canvasScale 以适应缩放)
                                // 注意：value.translation 是屏幕像素 (Canvas Space)，需要转换为世界坐标增量。
                                appState.currentDragOffset = CGSize(
                                    width: value.translation.width / appState.canvasScale,
                                    height: value.translation.height / appState.canvasScale
                                )
                            }
                            .onEnded { value in
                                // 3. 提交移动
                                // 将偏移量应用到所有选中的图片
                                let finalOffset = CGSize(
                                    width: value.translation.width / appState.canvasScale,
                                    height: value.translation.height / appState.canvasScale
                                )
                                
                                for id in appState.selectedImageIds {
                                    if let index = appState.images.firstIndex(where: { $0.id == id }) {
                                        appState.images[index].x += finalOffset.width
                                        appState.images[index].y += finalOffset.height
                                    }
                                }
                                
                                // 4. 重置全局偏移
                                appState.currentDragOffset = .zero
                            }
                        ,
                        SimultaneousGesture(
                            // Pinch to Scale (Trackpad)
                            MagnificationGesture()
                                .onChanged { value in
                                    zoomScale = value
                                }
                                .onEnded { value in
                                    if let index = appState.images.firstIndex(where: { $0.id == imageEntity.id }) {
                                        appState.images[index].scale *= value
                                    }
                                    zoomScale = 1.0
                                }
                            ,
                            // Rotate (Trackpad)
                            RotationGesture()
                                .onChanged { value in
                                    rotationAngle = value
                                }
                                .onEnded { value in
                                    if let index = appState.images.firstIndex(where: { $0.id == imageEntity.id }) {
                                        appState.images[index].rotation += value.degrees
                                    }
                                    rotationAngle = .zero
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
                    
                    Button(LocalizedStringKey("Bring to Front")) {
                        appState.bringToFront(id: imageEntity.id)
                    }
                    
                    Button(LocalizedStringKey("Send to Back")) {
                        appState.sendToBack(id: imageEntity.id)
                    }
                }
        }
    }
    
    // [交互逻辑] 调整大小手势 (锚点缩放)
    // 根据拖拽的手柄位置，计算缩放比例和中心点偏移，以实现“对角线锚点”的视觉效果。
    private func resizeGesture(handle: Alignment, originalSize: CGSize) -> some Gesture {
        // [交互优化] 使用全局坐标系 (Canvas)
        // 避免使用 .local，因为手势过程中视图本身的大小和位置会发生变化，导致坐标系不稳定（闪烁）。
        DragGesture(minimumDistance: 1, coordinateSpace: .named("Canvas"))
            .onChanged { value in
                // 1. 初始化：计算初始边界和锚点
                if initialSelectionBounds == nil {
                    if let bounds = appState.calculateSelectionBounds() {
                        initialSelectionBounds = bounds
                        
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
                
                for id in appState.selectedImageIds {
                    if let index = appState.images.firstIndex(where: { $0.id == id }) {
                        // 1. 更新缩放
                        appState.images[index].scale *= k
                        
                        // 2. 更新位置 (相对于锚点缩放)
                        // NewPos = Anchor + (OldPos - Anchor) * k
                        let oldX = appState.images[index].x
                        let oldY = appState.images[index].y
                        
                        appState.images[index].x = anchor.x + (oldX - anchor.x) * k
                        appState.images[index].y = anchor.y + (oldY - anchor.y) * k
                    }
                }
                
                // 重置临时状态
                zoomScale = 1.0
                appState.multiSelectScaleFactor = 1.0
                initialSelectionBounds = nil
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

