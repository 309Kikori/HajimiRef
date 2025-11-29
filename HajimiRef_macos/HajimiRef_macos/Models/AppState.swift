import SwiftUI
import Observation
import UniformTypeIdentifiers
import Vision
import CoreImage
import CoreImage.CIFilterBuiltins

@Observable
class AppState {
    var images: [ImageEntity] = []
    var canvasOffset: CGSize = .zero
    var canvasScale: CGFloat = 1.0
    var selectedImageIds: Set<UUID> = []
    
    var isAlwaysOnTop: Bool = false {
        didSet {
            updateWindowLevel()
        }
    }
    
    init() {}
    
    // MARK: - Image Management
    
    func addImage(from url: URL, at position: CGPoint = .zero) {
        do {
            let data = try Data(contentsOf: url)
            let base64 = data.base64EncodedString()
            let newImage = ImageEntity(x: position.x, y: position.y, scale: 1.0, rotation: 0, data: base64)
            images.append(newImage)
        } catch {
            print("Failed to load image: \(error)")
        }
    }
    
    func addImage(data: Data, at position: CGPoint = .zero) {
        let base64 = data.base64EncodedString()
        let newImage = ImageEntity(x: position.x, y: position.y, scale: 1.0, rotation: 0, data: base64)
        images.append(newImage)
    }
    
    func removeImage(id: UUID) {
        images.removeAll { $0.id == id }
        selectedImageIds.remove(id)
    }
    
    func clearBoard() {
        images.removeAll()
        selectedImageIds.removeAll()
        canvasOffset = .zero
        canvasScale = 1.0
    }
    
    func centerContent() {
        guard !images.isEmpty else {
            canvasOffset = .zero
            canvasScale = 1.0
            return
        }
        
        // Calculate bounding box of all images
        var minX: CGFloat = .greatestFiniteMagnitude
        var minY: CGFloat = .greatestFiniteMagnitude
        var maxX: CGFloat = -.greatestFiniteMagnitude
        var maxY: CGFloat = -.greatestFiniteMagnitude
        
        for img in images {
            let w = (img.nsImage?.size.width ?? 100) * img.scale
            let h = (img.nsImage?.size.height ?? 100) * img.scale
            
            // Simple bounding box approximation (ignoring rotation for simplicity)
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
        
        // Reset offset to center the content
        canvasOffset = CGSize(width: -centerX, height: -centerY)
        
        // Adjust scale to fit
        let targetScaleX = 1000.0 / (contentWidth + 100)
        let targetScaleY = 800.0 / (contentHeight + 100)
        let fitScale = min(targetScaleX, targetScaleY)
        
        // Clamp scale
        canvasScale = min(max(fitScale, 0.1), 2.0)
    }
    
    func compactMemory() {
        // Placeholder
    }
    
    // MARK: - Layer Management (层级管理)
    
    func bringToFront(id: UUID) {
        if let index = images.firstIndex(where: { $0.id == id }) {
            let item = images.remove(at: index)
            images.append(item)
        }
    }
    
    func sendToBack(id: UUID) {
        if let index = images.firstIndex(where: { $0.id == id }) {
            let item = images.remove(at: index)
            images.insert(item, at: 0)
        }
    }
    
    func bringForward(id: UUID) {
        if let index = images.firstIndex(where: { $0.id == id }), index < images.count - 1 {
            images.swapAt(index, index + 1)
        }
    }
    
    func sendBackward(id: UUID) {
        if let index = images.firstIndex(where: { $0.id == id }), index > 0 {
            images.swapAt(index, index - 1)
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
            let boardData = BoardData(images: images)
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
                
                self.images = boardData.images
                self.canvasOffset = .zero
                self.canvasScale = 1.0
            } catch {
                print("Failed to load board: \(error)")
            }
        }
    }
    
    // MARK: - Window Management
    
    private func updateWindowLevel() {
        for window in NSApplication.shared.windows {
            if window.isKeyWindow || window.isMainWindow {
                window.level = isAlwaysOnTop ? .floating : .normal
            }
        }
    }
    
    // MARK: - NPU / Vision Features
    
    func removeBackground(for imageId: UUID) {
        guard let index = images.firstIndex(where: { $0.id == imageId }),
              let nsImage = images[index].nsImage,
              let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return }
        
        let request = VNGenerateForegroundInstanceMaskRequest()
        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                try handler.perform([request])
                if let result = request.results?.first {
                    let mask = try result.generateMask(forInstances: result.allInstances)
                    
                    let originalCI = CIImage(cgImage: cgImage)
                    let maskCI = CIImage(cvPixelBuffer: mask)
                    
                    let scaleX = originalCI.extent.width / maskCI.extent.width
                    let scaleY = originalCI.extent.height / maskCI.extent.height
                    let scaledMask = maskCI.transformed(by: CGAffineTransform(scaleX: scaleX, y: scaleY))
                    
                    let filter = CIFilter.blendWithMask()
                    filter.inputImage = originalCI
                    filter.maskImage = scaledMask
                    filter.backgroundImage = CIImage.empty()
                    
                    if let output = filter.outputImage {
                        let context = CIContext()
                        if let newCGImage = context.createCGImage(output, from: output.extent) {
                            let newNSImage = NSImage(cgImage: newCGImage, size: nsImage.size)
                            if let tiff = newNSImage.tiffRepresentation,
                               let bitmap = NSBitmapImageRep(data: tiff),
                               let pngData = bitmap.representation(using: .png, properties: [:]) {
                                
                                let base64 = pngData.base64EncodedString()
                                
                                DispatchQueue.main.async {
                                    self.images[index].data = base64
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
