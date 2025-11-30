import SwiftUI
import CoreGraphics

// MARK: - Data Persistence Model
// 代表用于保存/加载到磁盘的整个看板状态。
struct BoardData: Codable {
    var version: Int = 2 // 架构版本，用于未来的迁移
    var images: [ImageEntity]
    
    init(images: [ImageEntity]) {
        self.images = images
    }
}

// MARK: - Image Entity
// 画布上单个图像的核心数据模型。
// 遵循 Identifiable 以用于 SwiftUI 列表，遵循 Codable 以用于 JSON 序列化。
struct ImageEntity: Identifiable, Codable {
    var id: UUID = UUID()
    
    // 空间属性
    var x: CGFloat
    var y: CGFloat
    var scale: CGFloat
    var rotation: CGFloat // 以度为单位
    
    // 图像数据存储为 Base64 字符串，以确保 JSON 文件的可移植性。
    // 这允许 .sref 文件是自包含的，没有外部依赖。
    var data: String 
    
    // 瞬态属性 (被 Codable 忽略)
    // 缓存解码后的 NSImage 以避免在每个渲染帧上进行昂贵的 Base64 解码。
    var _cachedImage: NSImage?
    
    enum CodingKeys: String, CodingKey {
        case x, y, scale, rotation, data
    }
    
    init(x: CGFloat, y: CGFloat, scale: CGFloat, rotation: CGFloat, data: String) {
        self.x = x
        self.y = y
        self.scale = scale
        self.rotation = rotation
        self.data = data
        // 创建时立即预缓存
        if let d = Data(base64Encoded: data) {
            self._cachedImage = NSImage(data: d)
        }
    }
    
    // 自定义解码以处理缓存逻辑
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        x = try container.decode(CGFloat.self, forKey: .x)
        y = try container.decode(CGFloat.self, forKey: .y)
        scale = try container.decode(CGFloat.self, forKey: .scale)
        rotation = try container.decode(CGFloat.self, forKey: .rotation)
        data = try container.decode(String.self, forKey: .data)
        // 解码时立即预缓存
        if let d = Data(base64Encoded: data) {
            self._cachedImage = NSImage(data: d)
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(x, forKey: .x)
        try container.encode(y, forKey: .y)
        try container.encode(scale, forKey: .scale)
        try container.encode(rotation, forKey: .rotation)
        try container.encode(data, forKey: .data)
    }
}

extension ImageEntity {
    // 辅助访问器以获取 NSImage，如果可用则使用缓存。
    var nsImage: NSImage? {
        if let cached = _cachedImage { return cached }
        if let data = Data(base64Encoded: self.data) {
            return NSImage(data: data)
        }
        return nil
    }
}
