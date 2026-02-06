import SwiftUI
import CoreGraphics

// MARK: - Group Entity
// 画布上图片组的核心数据模型。
// 遵循 Identifiable 以用于 SwiftUI 列表，遵循 Codable 以用于 JSON 序列化。

struct GroupEntity: Identifiable, Codable {
    var id: UUID = UUID()
    
    // 空间属性
    var x: CGFloat
    var y: CGFloat
    var width: CGFloat
    var height: CGFloat
    
    // 样式属性
    var name: String
    var colorHex: String  // 颜色的十六进制表示
    var opacity: CGFloat
    var fontSize: CGFloat
    
    // 成员图片ID列表
    var memberIds: [UUID]
    
    enum CodingKeys: String, CodingKey {
        case id, x, y, width, height, name, colorHex, opacity, fontSize, memberIds
    }
    
    // 预设的好看颜色 / Preset nice colors
    static let presetColors: [String] = [
        "#6495ED80",  // 矢车菊蓝
        "#90EE9080",  // 浅绿色
        "#FFB6C180",  // 浅粉色
        "#FFDAB980",  // 桃色
        "#DDA0DD80",  // 梅红色
        "#B0E0E680",  // 淡蓝色
        "#FAFAD280",  // 柠檬绸色
        "#E6E6FA80",  // 薰衣草色
    ]
    private static var colorIndex = 0
    
    init(x: CGFloat = 0, y: CGFloat = 0, width: CGFloat = 100, height: CGFloat = 100,
         name: String = "Group", colorHex: String? = nil, opacity: CGFloat = 0.3,
         fontSize: CGFloat = 14, memberIds: [UUID] = []) {
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.name = name
        
        // 自动分配颜色 / Auto assign color
        if let hex = colorHex {
            self.colorHex = hex
        } else {
            self.colorHex = GroupEntity.presetColors[GroupEntity.colorIndex % GroupEntity.presetColors.count]
            GroupEntity.colorIndex += 1
        }
        
        self.opacity = opacity
        self.fontSize = fontSize
        self.memberIds = memberIds
    }
    
    // 自定义解码以处理旧版本兼容
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = (try? container.decode(UUID.self, forKey: .id)) ?? UUID()
        x = try container.decode(CGFloat.self, forKey: .x)
        y = try container.decode(CGFloat.self, forKey: .y)
        width = try container.decode(CGFloat.self, forKey: .width)
        height = try container.decode(CGFloat.self, forKey: .height)
        name = (try? container.decode(String.self, forKey: .name)) ?? "Group"
        colorHex = (try? container.decode(String.self, forKey: .colorHex)) ?? "#6495ED80"
        opacity = (try? container.decode(CGFloat.self, forKey: .opacity)) ?? 0.3
        fontSize = (try? container.decode(CGFloat.self, forKey: .fontSize)) ?? 14
        memberIds = (try? container.decode([UUID].self, forKey: .memberIds)) ?? []
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(x, forKey: .x)
        try container.encode(y, forKey: .y)
        try container.encode(width, forKey: .width)
        try container.encode(height, forKey: .height)
        try container.encode(name, forKey: .name)
        try container.encode(colorHex, forKey: .colorHex)
        try container.encode(opacity, forKey: .opacity)
        try container.encode(fontSize, forKey: .fontSize)
        try container.encode(memberIds, forKey: .memberIds)
    }
    
    /// 获取组的边界矩形
    var bounds: CGRect {
        CGRect(x: x, y: y, width: width, height: height)
    }
    
    /// 根据颜色十六进制值获取 SwiftUI Color
    var color: Color {
        Color(hex: String(colorHex.prefix(7)))  // 去掉透明度后缀
    }
}

// MARK: - Board Data Extension
// 扩展 BoardData 以支持组功能

extension BoardData {
    // BoardData 现在在 ImageModel.swift 中定义
    // 这里添加组相关的辅助属性和方法
}
