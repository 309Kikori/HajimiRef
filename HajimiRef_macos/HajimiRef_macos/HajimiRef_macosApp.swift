import SwiftUI
import AppKit

// MARK: - App Delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

// MARK: - App Entry Point

@main
struct HajimiRef_macosApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @State private var appState = AppState()
    @Environment(\.openWindow) private var openWindow
    
    // [国际化] 语言设置
    // 默认使用系统语言 (nil)，用户可以在设置中覆盖。
    @AppStorage("appLanguage") private var appLanguage: String = "system"

    // MARK: - Scene

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(appState)
                // [国际化] 动态语言切换
                .environment(\.locale, appLanguage == "system" ? .current : Locale(identifier: appLanguage))
                // [Liquid Glass] 工具栏
                // macOS 26 的 Liquid Glass 窗口 chrome（大圆角、毛玻璃标题栏）
                // 要求窗口拥有 .toolbar 内容才能激活。
                // 汉堡菜单视图放在 toolbar 里，确保 Liquid Glass 生效。
                .toolbar {
                    ToolbarItem(placement: .primaryAction) {
                        HamburgerToolbarMenu(appState: appState)
                    }
                }
        }
        // [视觉与交互设计] 菜单栏命令
        // 我们自定义 macOS 菜单栏以提供对基本功能的快速访问。
        // 这遵循 macOS 人机界面指南 (HIG)，通过菜单栏公开关键操作，
        // 使其易于发现并支持快捷键。
        .commands {
            // 自定义关于窗口
            // 用我们自定义设计的 AboutView 替换标准的"关于"对话框。
            CommandGroup(replacing: .appInfo) {
                Button("About Hajimi Ref") {
                    openWindow(id: "about")
                }
            }
            
            // 编辑菜单：撤销/重做
            // 添加撤销和重做命令
            // 快捷键：Cmd + Z, Cmd + Shift + Z
            CommandGroup(replacing: .undoRedo) {
                Button(LocalizedStringKey("Undo")) {
                    appState.undo()
                }
                .keyboardShortcut("z", modifiers: .command)
                .disabled(!appState.undoManager.canUndo)
                
                Button(LocalizedStringKey("Redo")) {
                    appState.redo()
                }
                .keyboardShortcut("z", modifiers: [.command, .shift])
                .disabled(!appState.undoManager.canRedo)
            }
            
            // 编辑菜单：复制/粘贴
            // 添加复制和粘贴命令，用于复制选中的图片
            // 快捷键：Cmd + C, Cmd + V
            CommandGroup(replacing: .pasteboard) {
                Button(LocalizedStringKey("Copy")) {
                    appState.copySelectedImages()
                }
                .keyboardShortcut("c", modifiers: .command)
                .disabled(appState.selectedImageIds.isEmpty)
                
                Button(LocalizedStringKey("Paste")) {
                    appState.pasteImages()
                }
                .keyboardShortcut("v", modifiers: .command)
            }
            
            // 文件菜单：导入
            // 在"文件"菜单中添加"打开图片..."命令。
            // 快捷键：Cmd + O
            CommandGroup(replacing: .newItem) {
                Button(LocalizedStringKey("Open Images...")) {
                    appState.importImages()
                }
                .keyboardShortcut("o", modifiers: .command)
            }            
            // 文件菜单：保存/加载
            // 添加"保存看板"和"加载看板"命令以进行项目管理。
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
                
                Divider()
                
                Button(LocalizedStringKey("Export as Image...")) {
                    appState.exportBoardAsImage()
                }
                .keyboardShortcut("e", modifiers: [.command, .shift])
                
                Button(LocalizedStringKey("Copy to Clipboard")) {
                    appState.copyBoardToClipboard()
                }
                .keyboardShortcut("c", modifiers: [.command, .shift])
            }
            // 视图菜单：窗口行为
            // 添加一个切换开关以保持窗口"始终置顶"。
            // 这是参考软件的一项关键功能，允许艺术家在另一个应用程序
            // （例如 Photoshop, Blender）中工作时保持参考图可见。
            CommandMenu(LocalizedStringKey("View")) {
                Toggle(LocalizedStringKey("Always on Top"), isOn: $appState.isAlwaysOnTop)
                    .keyboardShortcut("t", modifiers: [.command, .shift])
            }
        }
        
        // [Liquid Glass] About 窗口 — 使用 SwiftUI 原生 Window Scene
        // 替代旧的 NSHostingController 手动创建方式，
        // macOS 26 的 Window Scene 自动获得液态玻璃窗口效果。
        Window(LocalizedStringKey("About Hajimi Ref"), id: "about") {
            AboutView()
                .environment(\.locale, appLanguage == "system" ? .current : Locale(identifier: appLanguage))
        }
        .windowResizability(.contentSize)
        .defaultSize(width: 350, height: 500)
        
        // Settings Window
        // Standard macOS Settings/Preferences window.
        // Accessible via "Hajimi Ref > Settings..." or Cmd+,
        Settings {
            SettingsView()
                .environment(appState)
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
