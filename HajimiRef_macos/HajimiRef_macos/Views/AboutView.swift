import SwiftUI

struct AboutView: View {
    init() {}
    
    var body: some View {
        // [Liquid Glass] 用 GlassEffectContainer 包裹整个关于页面
        // 使图标阴影和技术栈徽章的玻璃效果产生联动感
        GlassEffectContainer {
            VStack(spacing: 20) {
                // 1. Logo 图片区域
                // [Liquid Glass] 应用图标使用阴影增强立体感，与液态玻璃风格呼应
                Image(nsImage: NSApplication.shared.applicationIconImage)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 128, height: 128)
                    .shadow(color: .primary.opacity(0.2), radius: 10, y: 4)
                
                // 2. 文本信息区域容器
                VStack(spacing: 8) {
                    // 应用中文名称
                    Text("哈基米 参考")
                        .font(.system(size: 24, weight: .bold))
                    // 应用英文名称
                    Text("Hajimi Ref")
                        .font(.system(size: 16, weight: .bold))
                    
                    // 版本号信息
                    Text("Version 0.0.2 (macOS Native)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    
                    // 软件描述文案
                    Text("传奇神人与圆头耄耋的设计图像参考软件")
                        .font(.body)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                    
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

                    
                    // [Liquid Glass] 技术栈标识 — 增强 tint 颜色使效果更明显
                    HStack {
                        Image(systemName: "swift")
                            .foregroundColor(.orange)
                        Text("Built with Swift & Metal")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .glassEffect(.regular.tint(.orange.opacity(0.2)), in: .capsule)
                    .padding(.top, 5)
                }
                
                // 分割线
                Divider()
                
                // 3. 底部版权信息
                Text("Copyright © 2025 Xhinonome. All rights reserved.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(30)
            .frame(width: 350)
        }
    }
}

// [Liquid Glass] openAboutWindow() 已移除
// About 窗口现在由 HajimiRef_macosApp.swift 中的
// Window(id: "about") Scene 声明式管理，
// 自动获得 macOS 26 液态玻璃窗口效果。

#Preview {
    AboutView()
}
