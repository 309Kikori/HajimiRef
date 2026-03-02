import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    // MARK: - Properties
    
    @Environment(AppState.self) var appState
    
    init() {}
    
    // MARK: - Body
    
    var body: some View {
        // [视觉设计] 主应用程序容器
        // 此视图充当整个应用程序窗口的根容器。
        // 它托管无限画布，所有拖放交互由内层 CanvasView 处理（含精确世界坐标转换）。
        CanvasView()
            // [视觉设计] 窗口约束
            .frame(minWidth: 800, minHeight: 600)

            // [视觉设计] 背景一致性
            .background(Color(nsColor: .darkGray))
    }
}
#Preview {
    ContentView()
        .environment(AppState())
}
