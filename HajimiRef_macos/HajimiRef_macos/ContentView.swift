import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @Environment(AppState.self) var appState
    
    init() {}
    
    var body: some View {
        // [视觉设计] 主应用程序容器
        // 此视图充当整个应用程序窗口的根容器。
        // 它托管无限画布并处理全局拖放交互。
        CanvasView()
            // [视觉设计] 窗口约束
            // 我们强制执行 800x600 的最小窗口大小，以确保用户始终有
            // 足够的屏幕空间来舒适地查看和操作参考图像。
            // 这可以防止 UI 变得拥挤或无法使用。
            .frame(minWidth: 800, minHeight: 600)
            
            // [视觉设计] 背景一致性
            // 我们在这里也应用深灰色背景，以确保如果画布
            // 某种原因没有填满窗口（例如，在调整大小动画期间），用户
            // 看到的是一致的中性背景，而不是系统默认的窗口颜色。
            .background(Color(nsColor: .darkGray))
            
            // [交互设计] 全局拖放区域
            // 整个窗口都接受拖放的图片或文件 URL。
            // 这提供了无摩擦的“拖放”体验，允许用户
            // 快速从 Finder 或 Web 浏览器导入资源，而无需导航菜单。
            .onDrop(of: [.image, .fileURL], isTargeted: nil) { providers in
                loadImages(from: providers)
                return true
            }
    }
    
    private func loadImages(from providers: [NSItemProvider]) {
        for provider in providers {
            if provider.canLoadObject(ofClass: URL.self) {
                _ = provider.loadObject(ofClass: URL.self) { url, _ in
                    if let url = url {
                        DispatchQueue.main.async {
                            appState.addImage(from: url)
                        }
                    }
                }
            } else if provider.canLoadObject(ofClass: NSImage.self) {
                _ = provider.loadObject(ofClass: NSImage.self) { image, _ in
                    if let image = image as? NSImage,
                       let tiff = image.tiffRepresentation,
                       let bitmap = NSBitmapImageRep(data: tiff),
                       let data = bitmap.representation(using: .png, properties: [:]) {
                        DispatchQueue.main.async {
                            appState.addImage(data: data)
                        }
                    }
                }
            }
        }
    }
}

#Preview {
    ContentView()
        .environment(AppState())
}
