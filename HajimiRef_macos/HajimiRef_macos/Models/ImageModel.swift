import SwiftUI
import CoreGraphics

struct BoardData: Codable {
    var version: Int = 2
    var images: [ImageEntity]
    
    init(images: [ImageEntity]) {
        self.images = images
    }
}

struct ImageEntity: Identifiable, Codable {
    var id: UUID = UUID()
    var x: CGFloat
    var y: CGFloat
    var scale: CGFloat
    var rotation: CGFloat
    var data: String // Base64 encoded string
    
    // Transient properties
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
        // Pre-cache immediately
        if let d = Data(base64Encoded: data) {
            self._cachedImage = NSImage(data: d)
        }
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        x = try container.decode(CGFloat.self, forKey: .x)
        y = try container.decode(CGFloat.self, forKey: .y)
        scale = try container.decode(CGFloat.self, forKey: .scale)
        rotation = try container.decode(CGFloat.self, forKey: .rotation)
        data = try container.decode(String.self, forKey: .data)
        // Pre-cache immediately
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
    var nsImage: NSImage? {
        if let cached = _cachedImage { return cached }
        if let data = Data(base64Encoded: self.data) {
            return NSImage(data: data)
        }
        return nil
    }
}
