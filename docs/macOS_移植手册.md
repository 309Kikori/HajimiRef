<!--
 * @Author: Xhinonome
 * @Date: 2025-11-29 21:30:02
 * @LastEditors: Quantize 161130485+309Kikori@users.noreply.github.com
 * @LastEditTime: 2025-11-29 22:07:31
 * @FilePath: /fantastic-fortnight/Users/shinonome/Documents/Hajimi_ref/docs/macOS_移植手册.md
 * @Description: 头部注释配置模板
 * Copyright ©2020- 2025 by Xhinonome, All Rights Reserved. 
-->
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
*   **混合渲染**: 
    *   底层使用 `NSViewRepresentable` 封装的 `InputHandlerView` 处理原生鼠标事件（中键平移、滚轮缩放、快捷键监听）。
    *   上层使用 SwiftUI `Image` 组件渲染图片，利用系统级优化保证高性能。
*   **交互优化**:
    *   **选中边框**: 动态计算边框宽度 (`3.0 / totalScale`)，确保在任何缩放级别下边框视觉宽度恒定。
    *   **平滑缩放**: 针对 macOS 触控板和鼠标滚轮分别调优了缩放系数。

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
