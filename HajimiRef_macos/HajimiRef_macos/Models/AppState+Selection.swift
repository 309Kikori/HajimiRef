import SwiftUI

extension AppState {
    // MARK: - Selection Helpers
    
    func calculateSelectionBounds() -> CGRect? {
        let selectedImages = images.filter { selectedImageIds.contains($0.id) }
        guard !selectedImages.isEmpty else { return nil }
        
        var minX: CGFloat = .greatestFiniteMagnitude
        var minY: CGFloat = .greatestFiniteMagnitude
        var maxX: CGFloat = -.greatestFiniteMagnitude
        var maxY: CGFloat = -.greatestFiniteMagnitude
        
        for img in selectedImages {
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
        
        return CGRect(x: minX, y: minY, width: maxX - minX, height: maxY - minY)
    }
    
    /// 计算所有图片的边界框（活动区域）/ Calculate bounding box of all images (active area)
    func calculateAllImagesBounds(padding: CGFloat = 200) -> CGRect? {
        guard !images.isEmpty else { return nil }
        
        var minX: CGFloat = .greatestFiniteMagnitude
        var minY: CGFloat = .greatestFiniteMagnitude
        var maxX: CGFloat = -.greatestFiniteMagnitude
        var maxY: CGFloat = -.greatestFiniteMagnitude
        
        for img in images {
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
        
        // 添加边距 / Add padding
        return CGRect(
            x: minX - padding,
            y: minY - padding,
            width: (maxX - minX) + padding * 2,
            height: (maxY - minY) + padding * 2
        )
    }
}