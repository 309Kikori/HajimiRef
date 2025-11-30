# Hajimi Ref (macOS) 移植开发手册

## 1. 项目概述
Hajimi Ref (macOS) 是原 Python 版 Hajimi Ref 的原生移植版本，专为 macOS 平台打造。它利用 Apple Silicon 的硬件优势（GPU/NPU），提供比原版更流畅、更高效的参考图查看体验。项目采用 Swift 5.9 + SwiftUI 开发，完全遵循 macOS 原生设计规范。

## 2. 技术架构

### 2.1 核心技术栈
*   **Language**: Swift 5.9
*   **UI Framework**: SwiftUI (声明式 UI) + AppKit (底层窗口与输入处理)
*   **Rendering**: Metal (通过 SwiftUI 渲染管线)
*   **AI/ML**: Vision Framework (利用 NPU 进行背景移除)
*   **Build System**: Shell Script (`build_app.sh`) + `swift build` + `iconutil`

### 2.2 核心模块设计

#### `AppState` (Global State)
基于 Swift `Observation` 框架 (`@Observable`) 的全局状态管理类。
*   **数据源**: 管理 `images` 数组和画布状态 (`canvasOffset`, `canvasScale`)。
*   **逻辑中心**: 处理图片的增删改查、文件 I/O、NPU 请求调度。
*   **内存管理**: 包含 `compactMemory()` 预留接口，利用 ARC 自动管理内存。

#### `CanvasView` (Rendering Layer)
*   **混合渲染与事件拦截**: 
    *   **WindowAccessor**: 引入了 `WindowAccessor` 机制，通过 `NSViewRepresentable` 获取底层 `NSWindow` 实例。
    *   **全局事件监听**: 使用 `NSEvent.addLocalMonitorForEvents` 在窗口级别拦截鼠标和键盘事件。这有效解决了 SwiftUI `DragGesture` 吞噬鼠标中键和滚轮事件的问题，实现了无缝的画布平移与缩放。
*   **交互优化**:
    *   **恒定视觉边框**: 动态计算边框宽度 (`3.0 / totalScale`)，确保在任何缩放级别下选中框在屏幕上保持恒定的像素宽度（如 3px），提供专业设计软件级的视觉体验。
    *   **无限画布**: 通过 `ZStack` 配合全局 `offset` 和 `scaleEffect` 模拟 2D 摄像机运动。

#### `ImageModel` (Data Model)
*   **数据结构**: `ImageEntity` 结构体，遵循 `Codable` 协议。
*   **懒加载**: 图片数据以 Base64 字符串存储，仅在渲染时转换为 `NSImage`。

### 2.3 关键技术特性

#### NPU 加速背景移除
*   **原理**: 利用 Apple Vision 框架的 `VNGenerateForegroundInstanceMaskRequest`。
*   **流程**: 
    1.  用户点击“Remove Background”。
    2.  后台线程发起 Vision 请求，调用 Neural Engine (NPU) 生成前景蒙版。
    3.  使用 CoreImage (`CIFilter.blendWithMask`) 在 GPU 上合成透明背景图片。
    4.  主线程更新 UI。
*   **优势**: 毫秒级处理，不占用 CPU，不卡顿界面。

#### 性能优化
*   **原生渲染**: 摒弃了 Python 版的“视口裁剪”算法，转而依赖 macOS 强大的图形子系统（Quartz/Metal），直接渲染完整视图树，由系统自动处理裁剪和离屏渲染。
*   **预缓存**: 图片加载时预先解码为位图，避免滚动时的解码卡顿。

## 3. 构建与发布
项目不依赖 Xcode 工程文件，而是使用轻量级的 Shell 脚本进行构建：
```bash
./build_app.sh
```
该脚本自动执行：
1.  `swift build -c release` 编译二进制。
2.  创建 `.app` 包结构。
3.  使用 `iconutil` 编译 `.icns` 图标。
4.  生成 `Info.plist` 并签名。

## 4. 数据存储
*   **格式**: 兼容原版 `.sref` (JSON)。
*   **互通性**: 可直接读取 Python 版生成的 `.sref` 文件。

## 5. 近期更新日志 (2025-11-30)

### 5.1 核心架构修复
*   **事件系统重构**: 废弃了早期的 `InputHandlerView` 方案，改用 **Window-Level Event Monitoring**。
    *   *问题*: 当鼠标悬停在图片上时，SwiftUI 的手势识别器会拦截所有事件，导致无法使用中键平移画布。
    *   *解决*: 通过 `WindowAccessor` 挂载 `LocalMonitor`，在事件分发给视图之前进行拦截和处理。
*   **路径修正**: 修正了项目文件结构中的路径错误，确保所有修改正确应用到 `Hajimi_ref` 仓库。

### 5.2 文档与规范
*   **全代码库注释**: 完成了 `Views`, `Models`, `App` 等核心模块的详细中文注释。
*   **设计决策文档化**: 在代码注释中显式标注了 **[视觉设计]** 和 **[交互设计]** 标签，解释了如“点击空白取消选择”、“深色背景减少眼疲劳”、“NPU 蒙版合成”等设计决策背后的 UX 考量。

### 5.3 功能完善
*   **视觉微调**: 优化了选中态的边框渲染逻辑，使其在缩放时保持视觉一致性。
*   **菜单栏集成**: 完善了 macOS 菜单栏命令（打开、保存、置顶），符合 macOS HIG 规范。
