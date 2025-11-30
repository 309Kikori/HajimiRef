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
    // 处理应用程序内图片的生命周期。
    
    func addImage(from url: URL, at position: CGPoint = .zero) {
        do {
            let data = try Data(contentsOf: url)
            let base64 = data.base64EncodedString()
            // 初始化新图片实体，默认缩放 (1.0) 和旋转 (0)。
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
        // Reset canvas view to default state
        canvasOffset = .zero
        canvasScale = 1.0
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
            let item = images.remove(at: index)
            images.append(item) // Move to end of array
        }
    }
    
    func sendToBack(id: UUID) {
        if let index = images.firstIndex(where: { $0.id == id }) {
            let item = images.remove(at: index)
            images.insert(item, at: 0) // Move to start of array
        }
    }
    
    func bringForward(id: UUID) {
        if let index = images.firstIndex(where: { $0.id == id }), index < images.count - 1 {
            images.swapAt(index, index + 1) // Swap with the element above
        }
    }
    
    func sendBackward(id: UUID) {
        if let index = images.firstIndex(where: { $0.id == id }), index > 0 {
            images.swapAt(index, index - 1) // Swap with the element below
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
    
    // MARK: - Smart Arrangement (智能排序)
    
    func smartSortSelected() {
        guard !selectedImageIds.isEmpty else { return }
        
        // 1. 获取选中的图片实体
        let selectedImages = images.filter { selectedImageIds.contains($0.id) }
        guard !selectedImages.isEmpty else { return }
        
        // 2. 计算边界框以确定起始位置
        let minX = selectedImages.map { $0.x }.min() ?? 0
        let minY = selectedImages.map { $0.y }.min() ?? 0
        
        // 3. 简单的流式布局 (Flow Layout)
        // 我们尝试将图片排列成一个近似的正方形网格。
        let count = CGFloat(selectedImages.count)
        let columns = ceil(sqrt(count))
        
        var currentX: CGFloat = minX
        var currentY: CGFloat = minY
        var maxHeightInRow: CGFloat = 0
        var columnIndex: CGFloat = 0
        
        // 4. 应用布局
        // 我们需要更新原始数组中的位置
        for image in selectedImages {
            if let index = images.firstIndex(where: { $0.id == image.id }) {
                let img = images[index]
                let width = (img.nsImage?.size.width ?? 100) * img.scale
                let height = (img.nsImage?.size.height ?? 100) * img.scale
                
                // 移动图片
                // 注意：我们的坐标系是中心点，所以需要加上半宽/半高
                images[index].x = currentX + width / 2
                images[index].y = currentY + height / 2
                
                // 更新游标
                currentX += width + 20 // 20px 间距
                maxHeightInRow = max(maxHeightInRow, height)
                columnIndex += 1
                
                // 换行
                if columnIndex >= columns {
                    currentX = minX
                    currentY += maxHeightInRow + 20 // 20px 间距
                    maxHeightInRow = 0
                    columnIndex = 0
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
