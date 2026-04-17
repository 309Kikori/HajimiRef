import SwiftUI
import AppKit
import CoreGraphics

// MARK: - 色深模式枚举 / Color Depth Mode Enumeration
/// 与 Win11 端 ColorDepthMode 对应，保持双端一致
enum ColorDepthMode: String, CaseIterable, Identifiable {
    case auto = "auto"          // 自适应：根据图像源自动选择最佳色深
    case force8bit = "8bit"     // 强制 8bit：所有图像以 8bit/通道 渲染（省内存）
    case force10bit = "10bit"   // 强制 10bit：所有图像以 10bit/通道 渲染（需硬件支持）
    case force16bit = "16bit"   // 强制 16bit：所有图像以 16bit/通道 渲染（最高精度）
    
    var id: String { self.rawValue }
    
    /// 人类可读的显示名称
    var displayName: LocalizedStringKey {
        switch self {
        case .auto: return LocalizedStringKey("Auto (Adaptive)")
        case .force8bit: return LocalizedStringKey("8bit (Standard)")
        case .force10bit: return LocalizedStringKey("10bit (High Color)")
        case .force16bit: return LocalizedStringKey("16bit (Maximum)")
        }
    }
}

// MARK: - 图像色深信息 / Image Color Depth Info
/// 存储单张图像的位深检测结果
struct ImageColorDepthInfo {
    let bitsPerChannel: Int       // 每通道位深 (8, 10, 16)
    let hasAlpha: Bool            // 是否包含 alpha 通道
    let colorSpaceName: String    // 色彩空间名称
    
    /// 是否为高位深图像（>8bit）
    var isHighBitDepth: Bool {
        return bitsPerChannel > 8
    }
    
    /// 默认 8bit 信息
    static let standard = ImageColorDepthInfo(bitsPerChannel: 8, hasAlpha: false, colorSpaceName: "sRGB")
}

// MARK: - 色深管理器 / Color Depth Manager
/// macOS 端自适应色深管理器
/// 核心职责：
/// 1. 检测图像的原始位深（通过 NSBitmapImageRep）
/// 2. 根据当前模式决定最佳渲染色彩空间
/// 3. 提供图像格式转换工具方法
/// 4. 与 Win11 端 ColorDepthManager 保持 API 对称
class ColorDepthManagerMac: ObservableObject {
    
    @Published var mode: ColorDepthMode {
        didSet {
            if oldValue != mode {
                print("[ColorDepthManager] 色深模式已切换为: \(mode.rawValue)")
            }
        }
    }
    
    init(mode: ColorDepthMode = .auto) {
        self.mode = mode
    }
    
    // ────────────────────────────────────────────
    // 1. 图像位深检测 / Image bit-depth detection
    // ────────────────────────────────────────────
    
    /// 从 NSImage 检测色深信息
    static func detectImageDepth(_ image: NSImage) -> ImageColorDepthInfo {
        guard let tiffData = image.tiffRepresentation,
              let bitmap = NSBitmapImageRep(data: tiffData) else {
            return .standard
        }
        return detectBitmapDepth(bitmap)
    }
    
    /// 从 NSBitmapImageRep 检测色深信息
    static func detectBitmapDepth(_ bitmap: NSBitmapImageRep) -> ImageColorDepthInfo {
        let bitsPerSample = bitmap.bitsPerSample  // 每通道位深
        let hasAlpha = bitmap.hasAlpha
        let colorSpaceName = bitmap.colorSpace.localizedName ?? "Unknown"
        
        return ImageColorDepthInfo(
            bitsPerChannel: bitsPerSample,
            hasAlpha: hasAlpha,
            colorSpaceName: colorSpaceName
        )
    }
    
    /// 从 Data 检测色深信息（不完全解码，仅加载头部信息）
    static func detectDepthFromData(_ data: Data) -> ImageColorDepthInfo {
        guard let bitmap = NSBitmapImageRep(data: data) else {
            return .standard
        }
        return detectBitmapDepth(bitmap)
    }
    
    /// 从 Base64 字符串检测色深信息
    static func detectDepthFromBase64(_ base64String: String) -> ImageColorDepthInfo {
        guard let data = Data(base64Encoded: base64String) else {
            return .standard
        }
        return detectDepthFromData(data)
    }
    
    // ────────────────────────────────────────────
    // 2. 渲染色彩空间选择 / Rendering color space selection
    // ────────────────────────────────────────────
    
    /// 根据当前色深模式和图像信息，返回最佳渲染色彩空间
    /// - AUTO: 高位深图像 → Display P3 / Extended sRGB，低位深图像 → sRGB
    /// - FORCE_8BIT: 始终 sRGB
    /// - FORCE_10BIT/16BIT: 始终 Display P3 / Extended sRGB
    func getOptimalColorSpace(for depthInfo: ImageColorDepthInfo) -> NSColorSpace {
        switch mode {
        case .force8bit:
            return .sRGB
        case .force10bit, .force16bit:
            return .displayP3
        case .auto:
            return depthInfo.isHighBitDepth ? .displayP3 : .sRGB
        }
    }
    
    /// 获取最佳的 CGColorSpace（用于 Core Graphics 操作）
    func getOptimalCGColorSpace(for depthInfo: ImageColorDepthInfo) -> CGColorSpace {
        switch mode {
        case .force8bit:
            return CGColorSpace(name: CGColorSpace.sRGB)!
        case .force10bit, .force16bit:
            return CGColorSpace(name: CGColorSpace.displayP3)!
        case .auto:
            if depthInfo.isHighBitDepth {
                return CGColorSpace(name: CGColorSpace.displayP3)!
            }
            return CGColorSpace(name: CGColorSpace.sRGB)!
        }
    }
    
    // ────────────────────────────────────────────
    // 3. 图像转换工具 / Image conversion utilities
    // ────────────────────────────────────────────
    
    /// 根据当前色深模式转换 NSImage
    /// 如果图像已经是目标格式，直接返回（零拷贝）
    func convertImage(_ image: NSImage) -> NSImage {
        let depthInfo = Self.detectImageDepth(image)
        
        // 如果是 8bit 模式且图像是高位深，需要降级
        if mode == .force8bit && depthInfo.isHighBitDepth {
            return downscaleTo8bit(image)
        }
        
        // AUTO 模式或高位深模式：保持原始精度
        return image
    }
    
    /// 将高位深图像降级到 8bit
    private func downscaleTo8bit(_ image: NSImage) -> NSImage {
        guard let tiffData = image.tiffRepresentation,
              let bitmap = NSBitmapImageRep(data: tiffData) else {
            return image
        }
        
        // 转换到 sRGB 8bit
        guard let converted = bitmap.converting(to: .sRGB, renderingIntent: .perceptual) else {
            return image
        }
        
        let newImage = NSImage(size: image.size)
        newImage.addRepresentation(converted)
        return newImage
    }
    
    /// 获取导出时的最佳 bitsPerSample
    func getExportBitsPerSample(for depthInfo: ImageColorDepthInfo, fileFormat: String) -> Int {
        let fmt = fileFormat.lowercased()
        
        // JPEG/BMP 不支持 16bit，强制降级
        if fmt == "jpg" || fmt == "jpeg" || fmt == "bmp" {
            return 8
        }
        
        // PNG/TIFF 支持 16bit
        switch mode {
        case .force8bit:
            return 8
        case .force16bit:
            return 16
        case .force10bit:
            return depthInfo.isHighBitDepth ? 16 : 8  // 10bit 用 16bit 容器
        case .auto:
            return depthInfo.isHighBitDepth ? 16 : 8
        }
    }
    
    // ────────────────────────────────────────────
    // 4. 工具方法 / Utility methods
    // ────────────────────────────────────────────
    
    /// 从字符串解析色深模式
    static func modeFromString(_ str: String) -> ColorDepthMode {
        return ColorDepthMode(rawValue: str) ?? .auto
    }
}
