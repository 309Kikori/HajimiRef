import SwiftUI

// [视觉设计] 设置页面枚举
// 定义设置面板的导航结构
enum SettingsPage: String, CaseIterable, Identifiable {
    case general = "General"
    case other = "Other"
    case help = "Help"
    
    var id: String { self.rawValue }
    
    var icon: String {
        switch self {
        case .general: return "gear"
        case .other: return "ellipsis.circle"
        case .help: return "questionmark.circle"
        }
    }
}

struct SettingsView: View {
    // [交互设计] 侧边栏选择状态
    // 默认选中 "General"
    @State private var selectedPage: SettingsPage? = .general

    var body: some View {
        // [视觉设计] 现代 macOS 设置布局 (Sidebar Style)
        // 使用 NavigationSplitView 实现类似 macOS System Settings 的侧边栏布局。
        // 这种布局扩展性更好，看起来更现代。
        NavigationSplitView {
            List(SettingsPage.allCases, selection: $selectedPage) { page in
                NavigationLink(value: page) {
                    Label(LocalizedStringKey(page.rawValue), systemImage: page.icon)
                }
            }
            .navigationTitle(LocalizedStringKey("Settings"))
            // [Liquid Glass] 侧边栏在 macOS 26 中自动获得浮动液态玻璃效果
            // 确保侧边栏有足够的宽度显示文字，但不要太宽。
            .frame(minWidth: 180, idealWidth: 200)
        } detail: {
            // [视觉设计] 详情页内容
            switch selectedPage {
            case .general:
                GeneralSettingsView()
            case .other:
                OtherSettingsView()
            case .help:
                HelpView()
            case .none:
                Text("Select an option")
            }
        }
        // [视觉设计] 设置窗口尺寸
        // 现代布局通常需要更宽的窗口来容纳侧边栏和内容。
        .frame(minWidth: 600, maxWidth: .infinity, minHeight: 400, maxHeight: .infinity)
    }
}

struct GeneralSettingsView: View {
    @Environment(AppState.self) var appState
    
    @AppStorage("showGrid") private var showGrid: Bool = true
    @AppStorage("canvasBgColorHex") private var canvasBgColorHex: String = "#1E1E1E"
    @AppStorage("gridColorHex") private var gridColorHex: String = "#404040"
    @AppStorage("appLanguage") private var appLanguage: String = "system"
    @AppStorage("canvasTheme") private var canvasTheme: String = "dot_grid"
    
    // UE5 蓝图主题专属配置 / UE5 Blueprint theme specific settings
    @AppStorage("ue5BgColorHex") private var ue5BgColorHex: String = "#3B3B3B"
    @AppStorage("ue5SmallGridColorHex") private var ue5SmallGridColorHex: String = "#4D4D4D"
    @AppStorage("ue5LargeGridColorHex") private var ue5LargeGridColorHex: String = "#575757"
    @AppStorage("ue5LargeGridMultiplier") private var ue5LargeGridMultiplier: Int = 8
    @AppStorage("ue5SmallLineWidth") private var ue5SmallLineWidth: Double = 1.5
    @AppStorage("ue5LargeLineWidth") private var ue5LargeLineWidth: Double = 3.0
    @AppStorage("ue5SmallLineAlpha") private var ue5SmallLineAlpha: Double = 0.31
    @AppStorage("ue5LargeLineAlpha") private var ue5LargeLineAlpha: Double = 0.63
    @AppStorage("dotSize") private var dotSize: Double = 2.0
    
    // 色深模式 / Color Depth Mode
    @AppStorage("colorDepthMode") private var colorDepthMode: String = "auto"
    
    // [自动重置画板] 设置项
    @AppStorage("autoResetBoardEnabled") private var autoResetBoardEnabled: Bool = false
    @AppStorage("autoResetBoardInterval") private var autoResetBoardInterval: Int = 10
    
    // 绑定 ColorPicker 到 Hex 字符串
    var bgColorBinding: Binding<Color> {
        Binding(
            get: { Color(hex: canvasBgColorHex) },
            set: { canvasBgColorHex = $0.toHex() ?? "#1E1E1E" }
        )
    }
    
    var gridColorBinding: Binding<Color> {
        Binding(
            get: { Color(hex: gridColorHex) },
            set: { gridColorHex = $0.toHex() ?? "#404040" }
        )
    }
    
    // UE5 蓝图主题颜色绑定 / UE5 Blueprint theme color bindings
    var ue5BgColorBinding: Binding<Color> {
        Binding(
            get: { Color(hex: ue5BgColorHex) },
            set: { ue5BgColorHex = $0.toHex() ?? "#3B3B3B" }
        )
    }
    var ue5SmallGridColorBinding: Binding<Color> {
        Binding(
            get: { Color(hex: ue5SmallGridColorHex) },
            set: { ue5SmallGridColorHex = $0.toHex() ?? "#4D4D4D" }
        )
    }
    var ue5LargeGridColorBinding: Binding<Color> {
        Binding(
            get: { Color(hex: ue5LargeGridColorHex) },
            set: { ue5LargeGridColorHex = $0.toHex() ?? "#575757" }
        )
    }
    
    var body: some View {
        // [视觉设计] 表单布局 (Form Layout)
        // 使用 macOS 标准的 Form 布局，它会自动处理标签对齐和控件间距。
        // 这确保了设置界面与系统原生应用（如 Finder, Safari）的一致性。
        Form {
            // [视觉设计] 分组 (Section)
            // 将相关的设置项分组在 "Personalization" 下，建立清晰的信息层级。
            Section(header: Text(LocalizedStringKey("Personalization"))) {
                // 0. 语言设置
                Picker(LocalizedStringKey("Language"), selection: $appLanguage) {
                    Text(LocalizedStringKey("System Default")).tag("system")
                    Text("English").tag("en")
                    Text("简体中文").tag("zh-Hans")
                }
                .help(LocalizedStringKey("Choose the display language for the app."))
                
                // 1. 画板主题选择（顶层）/ Canvas Theme Picker (Top Level)
                Picker(LocalizedStringKey("Canvas Theme"), selection: $canvasTheme) {
                    Text(LocalizedStringKey("Dot Grid")).tag("dot_grid")
                    Text(LocalizedStringKey("UE5 Blueprint")).tag("ue5_blueprint")
                }
                .help(LocalizedStringKey("Choose the visual style of the canvas grid."))
                
                // 2. 网格开关（通用）
                Toggle(LocalizedStringKey("Show Dot Grid"), isOn: $showGrid)
                    .help(LocalizedStringKey("Display a dot grid pattern similar to Apple Freeform."))
            }
            
            // === 点阵主题选项组 / Dot Grid Theme Options ===
            if canvasTheme == "dot_grid" {
                Section(header: Text(LocalizedStringKey("Dot Grid"))) {
                    ColorPicker(LocalizedStringKey("Canvas Background"), selection: bgColorBinding)
                        .help(LocalizedStringKey("Customize the background color of the infinite canvas."))
                    
                    if showGrid {
                        ColorPicker(LocalizedStringKey("Dot Grid Color"), selection: gridColorBinding)
                            .help(LocalizedStringKey("Customize the color of the grid dots."))
                        
                        // 点大小 / Dot Size
                        HStack {
                            Text(LocalizedStringKey("Dot Size"))
                            Slider(value: $dotSize, in: 0.5...5.0, step: 0.5)
                            Text(String(format: "%.1f", dotSize))
                                .frame(width: 30)
                        }
                        .help(LocalizedStringKey("Adjust the size of grid dots."))
                    }
                }
            }
            
            // === UE5 蓝图主题选项组 / UE5 Blueprint Theme Options ===
            if canvasTheme == "ue5_blueprint" {
                Section(header: Text(LocalizedStringKey("UE5 Blueprint"))) {
                    ColorPicker(LocalizedStringKey("Blueprint Background"), selection: ue5BgColorBinding)
                        .help(LocalizedStringKey("Customize the UE5 blueprint background color."))
                    
                    if showGrid {
                        ColorPicker(LocalizedStringKey("Small Grid Color"), selection: ue5SmallGridColorBinding)
                            .help(LocalizedStringKey("Customize the small grid line color."))
                        
                        ColorPicker(LocalizedStringKey("Large Grid Color"), selection: ue5LargeGridColorBinding)
                            .help(LocalizedStringKey("Customize the large grid line color."))
                        
                        Picker(LocalizedStringKey("Large Grid Interval"), selection: $ue5LargeGridMultiplier) {
                            ForEach([2, 4, 5, 8, 10, 16, 20], id: \.self) { val in
                                Text("\(val)").tag(val)
                            }
                        }
                        .help(LocalizedStringKey("Number of small grid cells per large grid line."))
                        
                        // 小网格线宽 / Small Grid Line Width
                        HStack {
                            Text(LocalizedStringKey("Small Grid Line Width"))
                            Slider(value: $ue5SmallLineWidth, in: 0.5...5.0, step: 0.5)
                            Text(String(format: "%.1f", ue5SmallLineWidth))
                                .frame(width: 30)
                        }
                        .help(LocalizedStringKey("Adjust the width of small grid lines."))
                        
                        // 大网格线宽 / Large Grid Line Width
                        HStack {
                            Text(LocalizedStringKey("Large Grid Line Width"))
                            Slider(value: $ue5LargeLineWidth, in: 0.5...8.0, step: 0.5)
                            Text(String(format: "%.1f", ue5LargeLineWidth))
                                .frame(width: 30)
                        }
                        .help(LocalizedStringKey("Adjust the width of large grid lines."))
                        
                        // 小网格透明度 / Small Grid Opacity
                        HStack {
                            Text(LocalizedStringKey("Small Grid Opacity"))
                            Slider(value: $ue5SmallLineAlpha, in: 0.0...1.0, step: 0.05)
                            Text(String(format: "%.0f%%", ue5SmallLineAlpha * 100))
                                .frame(width: 40)
                        }
                        .help(LocalizedStringKey("Adjust the opacity of small grid lines."))
                        
                        // 大网格透明度 / Large Grid Opacity
                        HStack {
                            Text(LocalizedStringKey("Large Grid Opacity"))
                            Slider(value: $ue5LargeLineAlpha, in: 0.0...1.0, step: 0.05)
                            Text(String(format: "%.0f%%", ue5LargeLineAlpha * 100))
                                .frame(width: 40)
                        }
                        .help(LocalizedStringKey("Adjust the opacity of large grid lines."))
                    }
                }
            }
            
            // [画板设置] 自动重置画板
            Section(header: Text(LocalizedStringKey("Board"))) {
                // 自动重置画板开关
                Toggle(LocalizedStringKey("Auto Reset Board"), isOn: $autoResetBoardEnabled)
                    .help(LocalizedStringKey("Automatically reset board size based on image distribution."))
                    .onChange(of: autoResetBoardEnabled) { _, newValue in
                        appState.updateAutoResetSettings(enabled: newValue, intervalMinutes: autoResetBoardInterval)
                    }
                
                // 间隔时间选择器
                if autoResetBoardEnabled {
                    Picker(LocalizedStringKey("Interval"), selection: $autoResetBoardInterval) {
                        Text(LocalizedStringKey("5 minutes")).tag(5)
                        Text(LocalizedStringKey("10 minutes")).tag(10)
                        Text(LocalizedStringKey("15 minutes")).tag(15)
                        Text(LocalizedStringKey("30 minutes")).tag(30)
                        Text(LocalizedStringKey("60 minutes")).tag(60)
                    }
                    .help(LocalizedStringKey("How often to automatically reset the board size."))
                    .onChange(of: autoResetBoardInterval) { _, newValue in
                        appState.updateAutoResetSettings(enabled: autoResetBoardEnabled, intervalMinutes: newValue)
                    }
                }
                
                // 手动重置按钮
                Button(LocalizedStringKey("Reset Board Now")) {
                    appState.resetBoardBounds()
                }
                .help(LocalizedStringKey("Reset board size to fit current image distribution."))
            }
            
            // === 色深模式设置 / Color Depth Mode Settings ===
            Section(header: Text(LocalizedStringKey("Color Depth"))) {
                Picker(LocalizedStringKey("Color Depth Mode"), selection: $colorDepthMode) {
                    Text(LocalizedStringKey("Auto (Adaptive)")).tag("auto")
                    Text(LocalizedStringKey("8bit (Standard)")).tag("8bit")
                    Text(LocalizedStringKey("10bit (High Color)")).tag("10bit")
                    Text(LocalizedStringKey("16bit (Maximum)")).tag("16bit")
                }
                .help(LocalizedStringKey("Auto mode: high-bit images render at high bit depth, low-bit images at 8bit."))
                .onChange(of: colorDepthMode) { _, newValue in
                    appState.colorDepthManager.mode = ColorDepthManagerMac.modeFromString(newValue)
                }
                
                Text(LocalizedStringKey("Auto mode adapts to each image's native bit depth for optimal quality and memory usage."))
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            // [优化] 移除显式的 Divider，Section 之间默认会有间距
            
            Section {
                HStack {
                    Spacer()
                    // [交互设计] 破坏性操作的布局
                    // 将重置按钮放在右下角，并与常规选项分开，防止误触。
                    // [Liquid Glass] 使用 .bordered 样式，在 macOS 26 中自动获得玻璃质感
                    Button(LocalizedStringKey("Reset to Defaults")) {
                        resetSettings()
                    }
                    .buttonStyle(.bordered)
                    .keyboardShortcut(.delete, modifiers: .command) // Cmd + Delete (Optional)
                }
            }
        }
        // [视觉设计] 样式优化
        // 使用 .grouped 样式，使 Form 在侧边栏布局中看起来更像系统原生设置。
        .formStyle(.grouped) 
    }
    
    private func resetSettings() {
        // [交互设计] 动画过渡
        // 使用 withAnimation 让重置过程平滑过渡，而不是突兀地跳变。
        withAnimation {
            showGrid = true
            canvasBgColorHex = "#1E1E1E" // Dark Gray
            gridColorHex = "#404040" // Light Gray
            canvasTheme = "dot_grid"
            // 重置 UE5 蓝图主题参数 / Reset UE5 blueprint theme settings
            ue5BgColorHex = "#3B3B3B"
            ue5SmallGridColorHex = "#4D4D4D"
            ue5LargeGridColorHex = "#575757"
            ue5LargeGridMultiplier = 8
            ue5SmallLineWidth = 1.5
            ue5LargeLineWidth = 3.0
            ue5SmallLineAlpha = 0.31
            ue5LargeLineAlpha = 0.63
            dotSize = 2.0
            colorDepthMode = "auto"
        }
    }
}

// MARK: - Color Hex Extensions
extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }

        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
    
    /// 将 Color 转换为 Hex 字符串（安全处理 Display P3 等宽色域颜色）
    /// 通过 NSColor.usingColorSpace(.sRGB) 进行原生色彩空间转换，
    /// 避免直接从 cgColor.components 取值导致的 16 位颜色越界问题。
    func toHex() -> String? {
        // 先转为 NSColor，再强制转换到 sRGB 色彩空间
        guard let sRGBColor = NSColor(self).usingColorSpace(.sRGB) else {
            return nil
        }
        
        // 从 sRGB 颜色中提取分量（保证值域 [0, 1]）
        let r = lroundf(Float(sRGBColor.redComponent) * 255)
        let g = lroundf(Float(sRGBColor.greenComponent) * 255)
        let b = lroundf(Float(sRGBColor.blueComponent) * 255)
        let a = lroundf(Float(sRGBColor.alphaComponent) * 255)
        
        // 防御性 clamp（处理浮点精度边界）
        let clamp = { (v: Int) in min(max(v, 0), 255) }
        
        if a < 255 {
            return String(format: "#%02lX%02lX%02lX%02lX",
                          clamp(r), clamp(g), clamp(b), clamp(a))
        } else {
            return String(format: "#%02lX%02lX%02lX",
                          clamp(r), clamp(g), clamp(b))
        }
    }
}

// MARK: - Other Settings View
struct OtherSettingsView: View {
    var body: some View {
        // [临时调整] 用户要求暂时留空
        // 暂时隐藏快捷键列表，显示"敬请期待"占位符。
        GlassEffectContainer {
            VStack(spacing: 12) {
                Image(systemName: "sparkles")
                    .font(.system(size: 40))
                    .foregroundStyle(.secondary)
                    .frame(width: 60, height: 60)
                    .glassEffect(.regular.tint(.purple.opacity(0.15)), in: .circle)
                Text(LocalizedStringKey("Coming Soon..."))
                    .foregroundColor(.secondary)
            }
            // [Liquid Glass] 使用更醒目的 tint 颜色以增强玻璃感知
            .padding(24)
            .glassEffect(.regular.tint(.purple.opacity(0.08)), in: .rect(cornerRadius: 16))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
#Preview {
    SettingsView()
}

