import SwiftUI
import UniformTypeIdentifiers

// MARK: - Input Handler (NSView)
struct InputHandlerView: NSViewRepresentable {
    @Environment(AppState.self) var appState
    
    func makeNSView(context: Context) -> InputView {
        let view = InputView()
        view.appState = appState
        return view
    }
    
    func updateNSView(_ nsView: InputView, context: Context) {
        nsView.appState = appState
    }
    
    class InputView: NSView {
        weak var appState: AppState?
        
        override var acceptsFirstResponder: Bool { true }
        
        // Middle Mouse Pan State
        private var isPanning = false
        private var lastPanLocation: NSPoint = .zero
        
        override func viewDidMoveToWindow() {
            super.viewDidMoveToWindow()
            // Ensure we can become first responder to receive key events
            window?.makeFirstResponder(self)
        }
        
        // MARK: - Key Events (键盘事件)
        override func keyDown(with event: NSEvent) {
            // 'F' to center content (F键聚焦)
            if event.charactersIgnoringModifiers == "f" {
                appState?.centerContent()
            } 
            // Cmd + [ : Send Backward (后移一层)
            else if event.modifierFlags.contains(.command) && event.characters == "[" {
                if let id = appState?.selectedImageIds.first {
                    appState?.sendBackward(id: id)
                }
            }
            // Cmd + ] : Bring Forward (前移一层)
            else if event.modifierFlags.contains(.command) && event.characters == "]" {
                if let id = appState?.selectedImageIds.first {
                    appState?.bringForward(id: id)
                }
            }
            else {
                super.keyDown(with: event)
            }
        }
        
        // MARK: - Scroll Wheel (Zoom)
        override func scrollWheel(with event: NSEvent) {
            guard let appState = appState else { return }
            
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
                // Use deltaY for zoom. 
                let zoomDelta = event.deltaY * 0.005 // Reduced sensitivity for smoother control
                let zoomFactor = 1.0 + zoomDelta
                
                // Apply zoom
                let newScale = appState.canvasScale * zoomFactor
                // Clamp scale to reasonable limits (e.g., 0.1x to 10x)
                appState.canvasScale = min(max(newScale, 0.1), 10.0)
            }
        }
        
        // MARK: - Magnify (Trackpad Pinch)
        override func magnify(with event: NSEvent) {
            guard let appState = appState else { return }
            let zoomFactor = 1.0 + event.magnification
            let newScale = appState.canvasScale * zoomFactor
            appState.canvasScale = min(max(newScale, 0.1), 10.0)
        }
        
        // MARK: - Middle Mouse (Pan)
        override func otherMouseDown(with event: NSEvent) {
            if event.buttonNumber == 2 { // Middle Button
                isPanning = true
                lastPanLocation = event.locationInWindow
                NSCursor.closedHand.push()
            } else {
                super.otherMouseDown(with: event)
            }
        }
        
        override func otherMouseDragged(with event: NSEvent) {
            if isPanning, let appState = appState {
                let currentLocation = event.locationInWindow
                let deltaX = currentLocation.x - lastPanLocation.x
                let deltaY = currentLocation.y - lastPanLocation.y 
                
                appState.canvasOffset.width += deltaX
                appState.canvasOffset.height -= deltaY 
                
                lastPanLocation = currentLocation
            } else {
                super.otherMouseDragged(with: event)
            }
        }
        
        override func otherMouseUp(with event: NSEvent) {
            if event.buttonNumber == 2 {
                isPanning = false
                NSCursor.pop()
            } else {
                super.otherMouseUp(with: event)
            }
        }
        
        // MARK: - Left Mouse
        override func mouseDown(with event: NSEvent) {
            // Click on background clears selection
            appState?.selectedImageIds.removeAll()
            window?.makeFirstResponder(self) // Ensure focus
            super.mouseDown(with: event)
        }
    }
}

struct CanvasView: View {
    @Environment(AppState.self) var appState
    
    init() {}
    
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // 1. Input Handler Layer (Background)
                Color.black.opacity(0.001)
                    .overlay(InputHandlerView())
                    .onDrop(of: [.image, .fileURL], isTargeted: nil) { providers in
                        loadImages(from: providers)
                        return true
                    }
                
                // 2. Images Layer
                ZStack {
                    ForEach(appState.images) { image in
                        ImageView(imageEntity: image)
                    }
                }
                .offset(appState.canvasOffset)
                .scaleEffect(appState.canvasScale)
            }
            .clipped()
            .background(Color(nsColor: .darkGray))
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
            // Calculate border width to be constant in screen space (e.g. 3 points)
            // Total scale = image scale * canvas scale
            // We clamp the divisor to avoid division by zero or extremely large borders
            let totalScale = max(imageEntity.scale * zoomScale * appState.canvasScale, 0.01)
            let borderWidth = 3.0 / totalScale
            
            Image(nsImage: nsImage)
                .resizable()
                .antialiased(true)
                .aspectRatio(contentMode: .fit)
                .frame(width: nsImage.size.width, height: nsImage.size.height)
                // Selection Border
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
