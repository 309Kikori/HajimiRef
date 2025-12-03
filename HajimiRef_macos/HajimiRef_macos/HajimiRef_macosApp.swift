import SwiftUI
import AppKit

// MARK: - App Delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Ensure the app is a regular app (appears in Dock, has menu bar)
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
        
        // Bring window to front
        if let window = NSApp.windows.first {
            window.makeKeyAndOrderFront(nil)
        }
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

// MARK: - App Entry Point

@main
struct HajimiRef_macosApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @State private var appState = AppState()
    
    // [国际化] 语言设置
    // 默认使用系统语言 (nil)，用户可以在设置中覆盖。
    @AppStorage("appLanguage") private var appLanguage: String = "system"

    // MARK: - Scene

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(appState)
                // [国际化] 动态语言切换
                // 如果用户选择了特定语言，我们覆盖环境的 locale。
                // 注意：这可能不会立即更新所有系统提供的组件，但对 SwiftUI 视图有效。
                .environment(\.locale, appLanguage == "system" ? .current : Locale(identifier: appLanguage))
        }
        // [视觉与交互设计] 菜单栏命令
        // 我们自定义 macOS 菜单栏以提供对基本功能的快速访问。
        // 这遵循 macOS 人机界面指南 (HIG)，通过菜单栏公开关键操作，
        // 使其易于发现并支持快捷键。
        .commands {
            // 自定义关于窗口
            // 用我们自定义设计的 AboutView 替换标准的“关于”对话框。
            CommandGroup(replacing: .appInfo) {
                Button("About Hajimi Ref") {
                    openAboutWindow()
                }
            }
            
            // 文件菜单：导入
            // 在“文件”菜单中添加“打开图片...”命令。
            // 快捷键：Cmd + O
            CommandGroup(replacing: .newItem) {
                Button(LocalizedStringKey("Open Images...")) {
                    appState.importImages()
                }
                .keyboardShortcut("o", modifiers: .command)
            }
            
            // 文件菜单：保存/加载
            // 添加“保存看板”和“加载看板”命令以进行项目管理。
            // 快捷键：Cmd + S, Cmd + L
            CommandGroup(after: .saveItem) {
                Button(LocalizedStringKey("Save Board...")) {
                    appState.saveBoard()
                }
                .keyboardShortcut("s", modifiers: .command)
                
                Button(LocalizedStringKey("Load Board...")) {
                    appState.loadBoard()
                }
                .keyboardShortcut("l", modifiers: .command)
            }
            
            // 视图菜单：窗口行为
            // 添加一个切换开关以保持窗口“始终置顶”。
            // 这是参考软件的一项关键功能，允许艺术家在另一个应用程序
            // （例如 Photoshop, Blender）中工作时保持参考图可见。
            CommandMenu(LocalizedStringKey("View")) {
                Toggle(LocalizedStringKey("Always on Top"), isOn: $appState.isAlwaysOnTop)
                    .keyboardShortcut("t", modifiers: [.command, .shift])
            }
        }
        
        // Settings Window
        // Standard macOS Settings/Preferences window.
        // Accessible via "Hajimi Ref > Settings..." or Cmd+,
        Settings {
            SettingsView()
                // [国际化] 修复设置窗口语言不跟随的问题
                // Settings 场景是独立的，需要单独注入环境变数。
                .environment(\.locale, appLanguage == "system" ? .current : Locale(identifier: appLanguage))
        }
        // [交互设计] 允许设置窗口调整大小
        // 使用 .contentSize 允许窗口在内容定义的最小和最大尺寸之间调整。
        // 配合 SettingsView 中的 frame(minWidth: ..., maxWidth: ...)，实现完全可调整的窗口。
        .windowResizability(.contentSize)
    }
}
