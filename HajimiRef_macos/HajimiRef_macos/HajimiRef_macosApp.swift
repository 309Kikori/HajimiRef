import SwiftUI
import AppKit

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

@main
struct HajimiRef_macosApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @State private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(appState)
        }
        .commands {
            // Custom About Window
            CommandGroup(replacing: .appInfo) {
                Button("About Hajimi Ref") {
                    openAboutWindow()
                }
            }
            
            CommandGroup(replacing: .newItem) {
                Button(LocalizedStringKey("Open Images...")) {
                    appState.importImages()
                }
                .keyboardShortcut("o", modifiers: .command)
            }
            
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
            
            CommandMenu(LocalizedStringKey("View")) {
                Toggle(LocalizedStringKey("Always on Top"), isOn: $appState.isAlwaysOnTop)
                    .keyboardShortcut("t", modifiers: [.command, .shift])
            }
        }
    }
}
