import SwiftUI

struct HelpView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text(LocalizedStringKey("Help & Guide"))
                    .font(.largeTitle)
                    .bold()
                    .padding(.bottom, 10)
                
                Group {
                    Text(LocalizedStringKey("Basic Operations"))
                        .font(.title2)
                        .bold()
                    
                    VStack(alignment: .leading, spacing: 10) {
                        HelpItem(icon: "hand.draw", title: "Pan Canvas", description: "Hold Middle Mouse Button or Spacebar + Drag to pan the canvas.")
                        HelpItem(icon: "plus.magnifyingglass", title: "Zoom", description: "Scroll Wheel to zoom in/out. Or use Pinch gesture on trackpad.")
                        HelpItem(icon: "square.dashed", title: "Box Select", description: "Click and drag on empty space to box select multiple images.")
                        HelpItem(icon: "cursorarrow.click", title: "Multi-Select", description: "Hold Shift and click images to add/remove from selection.")
                    }
                }
                
                Divider()
                
                Group {
                    Text(LocalizedStringKey("Image Manipulation"))
                        .font(.title2)
                        .bold()
                    
                    VStack(alignment: .leading, spacing: 10) {
                        HelpItem(icon: "arrow.up.and.down.and.arrow.left.and.right", title: "Move", description: "Drag selected images to move them. Multi-selection is supported.")
                        HelpItem(icon: "arrow.up.left.and.arrow.down.right", title: "Resize", description: "Drag the corner handles of a selected image. Hold Shift to maintain aspect ratio (default).")
                        HelpItem(icon: "rotate.left", title: "Rotate", description: "Use two-finger rotate gesture on trackpad.")
                        HelpItem(icon: "wand.and.stars", title: "Remove Background", description: "Right-click an image and select 'Remove Background (NPU)' to use AI segmentation.")
                        HelpItem(icon: "square.grid.2x2", title: "Smart Sort", description: "Right-click and select 'Smart Sort' to automatically arrange selected images in a grid.")
                    }
                }
                
                Divider()
                
                Group {
                    Text(LocalizedStringKey("Shortcuts"))
                        .font(.title2)
                        .bold()
                    
                    VStack(alignment: .leading, spacing: 10) {
                        HelpItem(icon: "keyboard", title: "F", description: "Focus / Center Content")
                        HelpItem(icon: "keyboard", title: "Cmd + [", description: "Send Backward")
                        HelpItem(icon: "keyboard", title: "Cmd + ]", description: "Bring Forward")
                        HelpItem(icon: "keyboard", title: "Delete", description: "Delete selected images")
                    }
                }
            }
            .padding()
            .frame(maxWidth: 800, alignment: .leading)
        }
    }
}

struct HelpItem: View {
    var icon: String
    var title: LocalizedStringKey
    var description: LocalizedStringKey
    
    var body: some View {
        HStack(alignment: .top, spacing: 15) {
            Image(systemName: icon)
                .font(.title2)
                .frame(width: 30)
                .foregroundColor(.blue)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.headline)
                Text(description)
                    .font(.body)
                    .foregroundColor(.secondary)
            }
        }
    }
}

#Preview {
    HelpView()
}
