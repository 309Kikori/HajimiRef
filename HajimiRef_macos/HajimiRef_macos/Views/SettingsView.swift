import SwiftUI

// [视觉设计] 设置页面枚举
// 定义设置面板的导航结构
enum SettingsPage: String, CaseIterable, Identifiable {
    case general = "General"
    case other = "Other"
    
    var id: String { self.rawValue }
    
    var icon: String {
        switch self {
        case .general: return "gear"
        case .other: return "ellipsis.circle"
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
            // [视觉设计] 侧边栏宽度
            // 确保侧边栏有足够的宽度显示文字，但不要太宽。
            .frame(minWidth: 180, idealWidth: 200)
        } detail: {
            // [视觉设计] 详情页内容
            switch selectedPage {
            case .general:
                GeneralSettingsView()
            case .other:
                OtherSettingsView()
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
    @AppStorage("showGrid") private var showGrid: Bool = true
    @AppStorage("canvasBgColorHex") private var canvasBgColorHex: String = "#1E1E1E"
    @AppStorage("gridColorHex") private var gridColorHex: String = "#404040"
    @AppStorage("appLanguage") private var appLanguage: String = "system"
    
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
                
                // 1. 画布背景颜色
                // [交互设计] 实时反馈
                // 用户调整颜色时，画布背景会立即更新（通过 AppStorage 绑定），提供即时的视觉反馈。
                ColorPicker(LocalizedStringKey("Canvas Background"), selection: bgColorBinding)
                    .help(LocalizedStringKey("Customize the background color of the infinite canvas."))
                
                // 2. 点阵开关
                Toggle(LocalizedStringKey("Show Dot Grid"), isOn: $showGrid)
                    .help(LocalizedStringKey("Display a dot grid pattern similar to Apple Freeform."))
                
                // 3. 点阵颜色
                // [视觉设计] 条件展示
                // 只有当点阵开启时，才允许调整颜色。虽然这里没有隐藏控件，但逻辑上它们是绑定的。
                // 允许用户自定义点阵颜色可以适应不同的背景色（例如浅色背景配深色点，深色背景配浅色点）。
                if showGrid {
                    ColorPicker(LocalizedStringKey("Dot Grid Color"), selection: gridColorBinding)
                        .help(LocalizedStringKey("Customize the color of the grid dots."))
                    // [视觉设计] 移除缩进
                    // 在 Form 布局中，缩进会导致标签对齐不一致，显得杂乱。
                    // 既然它是紧跟在开关下面的，上下文关系已经很明确了。
                }
            }
            
            // [优化] 移除显式的 Divider，Section 之间默认会有间距
            
            Section {
                HStack {
                    Spacer()
                    // 3. 重置按钮
                    // [交互设计] 破坏性操作的布局
                    // 将重置按钮放在右下角，并与常规选项分开，防止误触。
                    Button(LocalizedStringKey("Reset to Defaults")) {
                        resetSettings()
                    }
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
    
    func toHex() -> String? {
        guard let components = cgColor?.components, components.count >= 3 else {
            return nil
        }
        
        let r = Float(components[0])
        let g = Float(components[1])
        let b = Float(components[2])
        var a = Float(1.0)
        
        if components.count >= 4 {
            a = Float(components[3])
        }
        
        if a != 1.0 {
            return String(format: "#%02lX%02lX%02lX%02lX", lroundf(r * 255), lroundf(g * 255), lroundf(b * 255), lroundf(a * 255))
        } else {
            return String(format: "#%02lX%02lX%02lX", lroundf(r * 255), lroundf(g * 255), lroundf(b * 255))
        }
    }
}

// MARK: - Other Settings View
struct OtherSettingsView: View {
    var body: some View {
        // [临时调整] 用户要求暂时留空
        // 暂时隐藏快捷键列表，显示“敬请期待”占位符。
        VStack {
            Text(LocalizedStringKey("Coming Soon..."))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

#Preview {
    SettingsView()
}

