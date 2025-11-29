import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @Environment(AppState.self) var appState
    
    init() {}
    
    var body: some View {
        CanvasView()
            .frame(minWidth: 800, minHeight: 600)
            .background(Color(nsColor: .darkGray))
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
