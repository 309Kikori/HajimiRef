import SwiftUI
import UniformTypeIdentifiers

// MARK: - Toolbar Hamburger Menu (触发 Liquid Glass + 展开/收起控制)

struct HamburgerToolbarMenu: View {
    @Bindable var appState: AppState
    @State private var isExpanded = false
    @State private var autoCollapseTask: Task<Void, Never>?

    var body: some View {
        GlassEffectContainer(spacing: 10) {
            HStack(spacing: 6) {
                // ☰ 汉堡按钮
                Button {
                    withAnimation(.spring(response: 0.42, dampingFraction: 0.70)) {
                        isExpanded.toggle()
                    }
                    isExpanded ? scheduleAutoCollapse() : cancelAutoCollapse()
                } label: {
                    Image(systemName: isExpanded ? "xmark" : "line.3.horizontal")
                        .font(.system(size: 13, weight: .semibold))
                        .contentTransition(.symbolEffect(.replace))
                }
                .buttonStyle(.glass)

                // 展开的功能按钮
                if isExpanded {
                    ToolbarActionButton(icon: "photo.on.rectangle.angled", label: "Open Images...", index: 0) {
                        appState.importImages(); scheduleAutoCollapse()
                    }
                    ToolbarActionButton(icon: "square.and.arrow.down", label: "Save Board...", index: 1) {
                        appState.saveBoard(); scheduleAutoCollapse()
                    }
                    ToolbarActionButton(icon: "folder", label: "Load Board...", index: 2) {
                        appState.loadBoard(); scheduleAutoCollapse()
                    }
                    ToolbarActionButton(icon: "square.and.arrow.up", label: "Export as Image...", index: 3) {
                        appState.exportBoardAsImage(); scheduleAutoCollapse()
                    }
                    ToolbarActionButton(icon: "doc.on.clipboard", label: "Copy to Clipboard", index: 4) {
                        appState.copyBoardToClipboard(); scheduleAutoCollapse()
                    }
                    ToolbarActionButton(
                        icon: appState.isAlwaysOnTop ? "pin.fill" : "pin",
                        label: "Always on Top",
                        index: 5,
                        isActive: appState.isAlwaysOnTop
                    ) {
                        appState.isAlwaysOnTop.toggle(); scheduleAutoCollapse()
                    }
                }
            }
        }
    }

    private func scheduleAutoCollapse() {
        cancelAutoCollapse()
        autoCollapseTask = Task {
            try? await Task.sleep(for: .seconds(5))
            guard !Task.isCancelled else { return }
            await MainActor.run {
                withAnimation(.spring(response: 0.35, dampingFraction: 0.72)) {
                    isExpanded = false
                }
            }
        }
    }

    private func cancelAutoCollapse() {
        autoCollapseTask?.cancel()
        autoCollapseTask = nil
    }
}

// MARK: - Toolbar Action Button (独立视图，避免编译器超时)

private struct ToolbarActionButton: View {
    let icon: String
    let label: LocalizedStringKey
    let index: Int
    var isActive: Bool = false
    let action: () -> Void

    var body: some View {
        let glassStyle: Glass = isActive
            ? Glass.regular.tint(.accentColor).interactive(true)
            : Glass.regular.interactive(true)

        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 13, weight: isActive ? .bold : .regular))
                .foregroundStyle(isActive ? Color.accentColor : Color.primary)
        }
        .buttonStyle(.plain)
        .glassEffect(glassStyle, in: Capsule())
        .help(label)
        .transition(.asymmetric(
            insertion: .move(edge: .leading).combined(with: .opacity),
            removal: .opacity
        ))
        .animation(
            .spring(response: 0.40, dampingFraction: 0.64)
            .delay(Double(index) * 0.05),
            value: true
        )
    }
}

// MARK: - Content View

struct ContentView: View {
    @Environment(AppState.self) var appState

    init() {}

    var body: some View {
        CanvasView()
            .frame(minWidth: 800, minHeight: 600)
    }
}

#Preview {
    ContentView()
        .environment(AppState())
}

