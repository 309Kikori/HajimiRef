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
                    
                    appState.canvasOffset.width += deltaX
                    appState.canvasOffset.height -= deltaY
                    
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

struct CanvasView: View {
    @Environment(AppState.self) var appState
    
    init() {}
    
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // 1. Background Layer (Click to clear selection)
                // [视觉设计] 使用几乎透明的黑色来捕获点击事件。
                // 这允许用户点击画布空白处来取消选择图片，模仿了标准设计软件（如 Photoshop, Figma）的交互行为。
                Color.black.opacity(0.001)
                    .onTapGesture {
                        appState.selectedImageIds.removeAll()
                    }
                
                // 2. Images Layer
                // [视觉设计] 这个 ZStack 容纳所有图片实体。
                // ForEach 中的顺序决定了 Z-index（渲染顺序）。数组后方的图片会被绘制在上方。
                ZStack {
                    ForEach(appState.images) { image in
                        ImageView(imageEntity: image)
                    }
                }
                // [视觉设计] 整个画布作为一个整体进行变换（偏移 & 缩放）。
                // 这创造了 2D 无限画布摄像机平移/缩放的视觉错觉。
                .offset(appState.canvasOffset)
                .scaleEffect(appState.canvasScale)
            }
            .clipped() // [视觉设计] 确保内容不会溢出窗口边界。
            .background(Color(nsColor: .darkGray)) // [视觉设计] 中性深灰背景减少眼部疲劳，并为参考图提供良好的对比度。
            // Attach Window Accessor to background to capture window events
            .background(WindowAccessor())
            .onDrop(of: [.image, .fileURL], isTargeted: nil) { providers in
                loadImages(from: providers)
                return true
            }
        }
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

struct ImageView: View {
    @Environment(AppState.self) var appState
    var imageEntity: ImageEntity
    
    // Local state for gestures
    @State private var dragOffset: CGSize = .zero
    @State private var zoomScale: CGFloat = 1.0
    @State private var rotationAngle: Angle = .zero
    
    var isSelected: Bool {
        appState.selectedImageIds.contains(imageEntity.id)
    }
    
    var body: some View {
        if let nsImage = imageEntity.nsImage {
            // [视觉设计] 恒定屏幕空间边框宽度
            // 我们动态计算边框宽度，使其在屏幕上看起来保持恒定的厚度（例如 3 点），
            // 无论用户放大或缩小了多少。
            // 公式：期望宽度 / (图片缩放 * 画布缩放)
            // 我们限制除数以避免除以零或在极度缩小时产生过大的边框。
            let totalScale = max(imageEntity.scale * zoomScale * appState.canvasScale, 0.01)
            let borderWidth = 3.0 / totalScale
            
            Image(nsImage: nsImage)
                .resizable()
                .antialiased(true) // [视觉设计] 对于旋转的图像至关重要，可避免边缘锯齿（aliasing）。
                .aspectRatio(contentMode: .fit) // [视觉设计] 保持参考图的原始纵横比。
                .frame(width: nsImage.size.width, height: nsImage.size.height)
                // [视觉设计] 选中指示器
                // 使用标准的系统蓝色来指示选中状态。
                // 边框作为覆盖层绘制，位于图像内容的“上方”。
                .overlay(
                    Rectangle()
                        .stroke(Color.blue, lineWidth: isSelected ? borderWidth : 0)
                )
                .scaleEffect(imageEntity.scale * zoomScale)
                .rotationEffect(Angle(degrees: imageEntity.rotation) + rotationAngle)
                .position(x: imageEntity.x + dragOffset.width, y: imageEntity.y + dragOffset.height)
                // Gestures
                .gesture(
                    SimultaneousGesture(
                        // Drag to Move
                        DragGesture()
                            .onChanged { value in
                                dragOffset = value.translation
                                if !isSelected {
                                    appState.selectedImageIds = [imageEntity.id]
                                }
                            }
                            .onEnded { value in
                                if let index = appState.images.firstIndex(where: { $0.id == imageEntity.id }) {
                                    appState.images[index].x += value.translation.width
                                    appState.images[index].y += value.translation.height
                                }
                                dragOffset = .zero
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
                    appState.selectedImageIds = [imageEntity.id]
                }
                .contextMenu {
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
}
