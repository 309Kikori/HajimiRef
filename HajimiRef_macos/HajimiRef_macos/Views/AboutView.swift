import SwiftUI
import AppKit

struct AboutView: View {
    init() {}
    
    var body: some View {
        // 最外层容器：垂直堆叠布局 (VStack)
        // spacing: 20 -> 内部各主要区块（Logo、文本区、分割线、版权）之间的垂直间距为 20pt
        VStack(spacing: 20) {
            // 1. Logo 图片区域
            // 获取当前应用程序的图标 (NSApplication.shared.applicationIconImage)
            Image(nsImage: NSApplication.shared.applicationIconImage)
                .resizable() // 允许图片调整大小
                .aspectRatio(contentMode: .fit) // 保持宽高比适配
                .frame(width: 128, height: 128) // 强制指定显示尺寸为 128x128
                .shadow(radius: 5) // 添加半径为 5 的阴影，增加立体感
            
            // 2. 文本信息区域容器
            // 使用嵌套的 VStack 将应用名、版本号、描述组合在一起
            // spacing: 8 -> 文本行之间的垂直间距较小，显得更紧凑
            VStack(spacing: 8) {
                // 应用中文名称
                Text("哈基米 参考")
                    .font(.system(size: 24, weight: .bold)) // 大号粗体字，作为主标题
                // 应用英文名称
                Text("Hajimi Ref")
                    .font(.system(size: 16, weight: .bold)) // 中号粗体字，作为副标题
                
                // 版本号信息
                Text("Version 2.0.0 (macOS Native)")
                    .font(.subheadline) // 使用系统副标题样式
                    .foregroundColor(.secondary) // 使用次级文本颜色（通常是灰色），降低视觉权重
                
                // 软件描述文案
                Text("传奇神人与圆头耄耋的设计图像参考软件")
                    .font(.body) // 正文字体
                    .multilineTextAlignment(.center) // 多行文本居中对齐
                    .padding(.horizontal) // 在水平方向添加默认内边距，防止文字贴边
                
                // [教学] 插入 Meme 图片示例
                // 步骤：
                // 1. 在 Assets.xcassets 中拖入图片，命名为 "Meme"
                // 2. 取消下面代码的注释

                Image("Meme")
                    .resizable()                    // 允许缩放
                    .aspectRatio(contentMode: .fit) // 保持比例
                    .frame(height: 150)             // 限制高度
                    .cornerRadius(8)                // 圆角
                    .padding(.vertical, 5)          // 垂直间距

                
                // 技术栈标识区域 (Badge)
                // 使用 HStack 水平排列图标和文字
                HStack {
                    Image(systemName: "swift") // SF Symbols 图标
                        .foregroundColor(.orange) // 设置图标颜色为橙色
                    Text("Built with Swift & Metal")
                        .font(.caption) // 说明性文字使用小号字体
                        .foregroundColor(.secondary)
                }
                .padding(.top, 5) // 顶部额外增加 5pt 间距，与上方描述区分开
            }
            
            // 分割线：一条横跨的细线，用于视觉分隔
            Divider()
            
            // 3. 底部版权信息
            Text("Copyright © 2025 Xhinonome. All rights reserved.")
                .font(.caption) // 最小号字体
                .foregroundColor(.secondary) // 灰色显示
        }
        .padding(30) // 整个 About 窗口内容的四周内边距为 30pt，避免内容紧贴窗口边缘
        .frame(width: 350) // 固定窗口内容宽度为 350pt，高度自适应
    }
}

func openAboutWindow() {
    if let window = NSApp.windows.first(where: { $0.title == "About Hajimi Ref" }) {
        window.makeKeyAndOrderFront(nil)
        return
    }
    
    let aboutView = AboutView()
    let controller = NSHostingController(rootView: aboutView)
    let window = NSWindow(contentViewController: controller)
    window.title = "About Hajimi Ref"
    window.styleMask = [.titled, .closable]
    window.center()
    window.isReleasedWhenClosed = false
    window.makeKeyAndOrderFront(nil)
}

#Preview {
    AboutView()
}
