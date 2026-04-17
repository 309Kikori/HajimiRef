import SwiftUI
import CoreGraphics

// MARK: - Data Persistence Model
// 代表用于保存/加载到磁盘的整个看板状态。
struct BoardData: Codable {
    var version: Int = 4 // 架构版本，版本4添加了组功能支持
    var images: [ImageEntity]
    var groups: [GroupEntity]  // 组数据
    
    init(images: [ImageEntity], groups: [GroupEntity] = []) {
        self.images = images
        self.groups = groups
    }
    
    // 自定义解码以处理旧版本兼容
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        version = (try? container.decode(Int.self, forKey: .version)) ?? 3
        images = try container.decode([ImageEntity].self, forKey: .images)
        groups = (try? container.decode([GroupEntity].self, forKey: .groups)) ?? []
    }
    
    enum CodingKeys: String, CodingKey {
        case version, images, groups
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
    var zIndex: CGFloat = 0 // 图层顺序，用于双端兼容
    
    // 组ID / Group ID
    var groupId: UUID? = nil
    
    // 图像数据存储为 Base64 字符串，以确保 JSON 文件的可移植性。
    // 这允许 .sref 文件是自包含的，没有外部依赖。
    var data: String 
    
    // 瞬态属性 (被 Codable 忽略)
    // 缓存解码后的 NSImage 以避免在每个渲染帧上进行昂贵的 Base64 解码。
    var _cachedImage: NSImage?
    
    enum CodingKeys: String, CodingKey {
        case x, y, scale, rotation, zIndex, groupId, data
    }
    
    init(x: CGFloat, y: CGFloat, scale: CGFloat, rotation: CGFloat, zIndex: CGFloat = 0, groupId: UUID? = nil, data: String) {
        self.x = x
        self.y = y
        self.scale = scale
        self.rotation = rotation
        self.zIndex = zIndex
        self.groupId = groupId
        self.data = data
        // 创建时立即预缓存
        if let d = Data(base64Encoded: data) {
            self._cachedImage = NSImage(data: d)
        }
    }
    
    // 自定义解码以处理缓存逻辑和旧版本兼容
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        x = try container.decode(CGFloat.self, forKey: .x)
        y = try container.decode(CGFloat.self, forKey: .y)
        scale = try container.decode(CGFloat.self, forKey: .scale)
        rotation = try container.decode(CGFloat.self, forKey: .rotation)
        // zIndex 可选，兼容旧版本存档
        zIndex = (try? container.decode(CGFloat.self, forKey: .zIndex)) ?? 0
        // groupId 可选，兼容旧版本存档
        groupId = try? container.decode(UUID.self, forKey: .groupId)
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
        try container.encode(zIndex, forKey: .zIndex)
        try container.encodeIfPresent(groupId, forKey: .groupId)
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
    
    // ── 自适应色深：检测图像的原始位深信息 ──
    // Adaptive color depth: detect original bit depth of the image
    var colorDepthInfo: ImageColorDepthInfo {
        return ColorDepthManagerMac.detectDepthFromBase64(self.data)
    }
}
