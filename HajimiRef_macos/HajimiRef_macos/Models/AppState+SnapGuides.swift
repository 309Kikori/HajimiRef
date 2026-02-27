import SwiftUI

// MARK: - Smart Guides 辅助线数据
// 表示一条活跃的智能对齐辅助线
struct SnapLine: Equatable, Identifiable {
    enum Axis: Equatable {
        case x  // 垂直辅助线（X坐标固定）
        case y  // 水平辅助线（Y坐标固定）
    }
    // 使用 axis+value 生成稳定 ID，使 SwiftUI 能正确追踪同一条线的出现/消失
    var id: String { "\(axis == .x ? "x" : "y")_\(String(format: "%.1f", value))" }
    let axis: Axis
    let value: CGFloat    // 辅助线的坐标值
    let start: CGFloat    // 辅助线绘制起点（另一轴的坐标）
    let end: CGFloat      // 辅助线绘制终点（另一轴的坐标）
}

// MARK: - Snap Guide 缓存条目
struct SnapGuideEntry: Comparable {
    let value: CGFloat
    let itemId: UUID
    
    static func < (lhs: SnapGuideEntry, rhs: SnapGuideEntry) -> Bool {
        lhs.value < rhs.value
    }
}

// MARK: - AppState Smart Guides Extension

extension AppState {
    
    // MARK: - 构建参考线缓存 (拖拽开始时调用一次)
    // Build snap guide cache from all non-dragged items (called once at drag start).
    
    func buildSnapGuides(draggedIds: Set<UUID>) -> (xGuides: [SnapGuideEntry], yGuides: [SnapGuideEntry]) {
        var xGuides: [SnapGuideEntry] = []
        var yGuides: [SnapGuideEntry] = []
        
        for img in images {
            if draggedIds.contains(img.id) { continue }
            
            let w = (img.nsImage?.size.width ?? 100) * img.scale
            let h = (img.nsImage?.size.height ?? 100) * img.scale
            
            let left = img.x - w / 2
            let right = img.x + w / 2
            let top = img.y - h / 2
            let bottom = img.y + h / 2
            let centerX = img.x
            let centerY = img.y
            
            // 每个物体提取6条参考线: left, right, centerX, top, bottom, centerY
            xGuides.append(SnapGuideEntry(value: left, itemId: img.id))
            xGuides.append(SnapGuideEntry(value: right, itemId: img.id))
            xGuides.append(SnapGuideEntry(value: centerX, itemId: img.id))
            yGuides.append(SnapGuideEntry(value: top, itemId: img.id))
            yGuides.append(SnapGuideEntry(value: bottom, itemId: img.id))
            yGuides.append(SnapGuideEntry(value: centerY, itemId: img.id))
        }
        
        // 排序以便二分查找 / Sort for binary search
        xGuides.sort()
        yGuides.sort()
        
        return (xGuides, yGuides)
    }
    
    // MARK: - 二分查找最近参考线
    // Binary search for nearest guide within threshold.
    
    func findNearestGuide(in guides: [SnapGuideEntry], value: CGFloat, threshold: CGFloat) -> (guideValue: CGFloat, distance: CGFloat)? {
        if guides.isEmpty { return nil }
        
        // 二分查找插入位置 / Binary search for insertion point
        var lo = 0
        var hi = guides.count
        while lo < hi {
            let mid = (lo + hi) / 2
            if guides[mid].value < value {
                lo = mid + 1
            } else {
                hi = mid
            }
        }
        
        var best: CGFloat? = nil
        var bestDist: CGFloat = threshold + 1
        
        // 检查 lo-1 和 lo 两个候选 / Check candidates at lo-1 and lo
        for i in [lo - 1, lo] {
            if i >= 0 && i < guides.count {
                let dist = abs(guides[i].value - value)
                if dist < bestDist {
                    bestDist = dist
                    best = guides[i].value
                }
            }
        }
        
        if let bestVal = best, bestDist <= threshold {
            return (bestVal, bestDist)
        }
        return nil
    }
    
    // MARK: - 执行吸附检测
    // Perform snap detection and return correction offset + active snap lines.
    
    func performSnap(
        draggedIds: Set<UUID>,
        currentOffset: CGSize,
        xGuides: [SnapGuideEntry],
        yGuides: [SnapGuideEntry],
        canvasScale: CGFloat
    ) -> (correctedOffset: CGSize, snapLines: [SnapLine]) {
        
        // 吸附阈值：5屏幕像素 → 世界坐标 / Threshold: 5 screen px -> world coords
        let screenThreshold: CGFloat = 5.0
        let threshold = screenThreshold / max(canvasScale, 0.01)
        
        // 计算拖拽中选中项的联合边界 / Compute union bounds of dragged items with current offset
        let selected = images.filter { draggedIds.contains($0.id) }
        guard !selected.isEmpty else {
            return (currentOffset, [])
        }
        
        var minX: CGFloat = .greatestFiniteMagnitude
        var minY: CGFloat = .greatestFiniteMagnitude
        var maxX: CGFloat = -.greatestFiniteMagnitude
        var maxY: CGFloat = -.greatestFiniteMagnitude
        
        for img in selected {
            let w = (img.nsImage?.size.width ?? 100) * img.scale
            let h = (img.nsImage?.size.height ?? 100) * img.scale
            
            let cx = img.x + currentOffset.width
            let cy = img.y + currentOffset.height
            
            let left = cx - w / 2
            let right = cx + w / 2
            let top = cy - h / 2
            let bottom = cy + h / 2
            
            if left < minX { minX = left }
            if right > maxX { maxX = right }
            if top < minY { minY = top }
            if bottom > maxY { maxY = bottom }
        }
        
        let unionCenterX = (minX + maxX) / 2
        let unionCenterY = (minY + maxY) / 2
        
        // 被拖拽物体的5条关键线 / 5 key lines of dragged bounding box
        let dragXVals = [minX, unionCenterX, maxX]
        let dragYVals = [minY, unionCenterY, maxY]
        
        // 寻找X方向最近吸附 / Find nearest X snap
        var bestSnapX: (guideValue: CGFloat, dragValue: CGFloat, distance: CGFloat)? = nil
        for dv in dragXVals {
            if let result = findNearestGuide(in: xGuides, value: dv, threshold: threshold) {
                if bestSnapX == nil || result.distance < bestSnapX!.distance {
                    bestSnapX = (result.guideValue, dv, result.distance)
                }
            }
        }
        
        // 寻找Y方向最近吸附 / Find nearest Y snap
        var bestSnapY: (guideValue: CGFloat, dragValue: CGFloat, distance: CGFloat)? = nil
        for dv in dragYVals {
            if let result = findNearestGuide(in: yGuides, value: dv, threshold: threshold) {
                if bestSnapY == nil || result.distance < bestSnapY!.distance {
                    bestSnapY = (result.guideValue, dv, result.distance)
                }
            }
        }
        
        // 计算修正偏移 / Calculate correction offset
        var dx: CGFloat = 0
        var dy: CGFloat = 0
        var snapLines: [SnapLine] = []
        
        let lineExtension: CGFloat = 20 / max(canvasScale, 0.01)
        
        if let snapX = bestSnapX {
            dx = snapX.guideValue - snapX.dragValue
            // 辅助线纵向范围 / Vertical extent of guide line
            let lineTop = min(minY + dy, getGuideExtentMin(axis: .y, snapValue: snapX.guideValue, draggedIds: draggedIds)) - lineExtension
            let lineBottom = max(maxY + dy, getGuideExtentMax(axis: .y, snapValue: snapX.guideValue, draggedIds: draggedIds)) + lineExtension
            snapLines.append(SnapLine(axis: .x, value: snapX.guideValue, start: lineTop, end: lineBottom))
        }
        
        if let snapY = bestSnapY {
            dy = snapY.guideValue - snapY.dragValue
            let lineLeft = min(minX + dx, getGuideExtentMin(axis: .x, snapValue: snapY.guideValue, draggedIds: draggedIds)) - lineExtension
            let lineRight = max(maxX + dx, getGuideExtentMax(axis: .x, snapValue: snapY.guideValue, draggedIds: draggedIds)) + lineExtension
            snapLines.append(SnapLine(axis: .y, value: snapY.guideValue, start: lineLeft, end: lineRight))
        }
        
        let correctedOffset = CGSize(
            width: currentOffset.width + dx,
            height: currentOffset.height + dy
        )
        
        return (correctedOffset, snapLines)
    }
    
    // MARK: - 辅助线延伸范围计算
    
    /// 获取对齐到指定值的所有参考物体在另一轴的最小值
    private func getGuideExtentMin(axis: SnapLine.Axis, snapValue: CGFloat, draggedIds: Set<UUID>) -> CGFloat {
        var minVal: CGFloat = .greatestFiniteMagnitude
        
        for img in images {
            if draggedIds.contains(img.id) { continue }
            
            let w = (img.nsImage?.size.width ?? 100) * img.scale
            let h = (img.nsImage?.size.height ?? 100) * img.scale
            
            let left = img.x - w / 2
            let right = img.x + w / 2
            let top = img.y - h / 2
            let bottom = img.y + h / 2
            
            switch axis {
            case .y:  // snapValue是X坐标，找Y的范围
                if abs(left - snapValue) < 1 || abs(right - snapValue) < 1 || abs(img.x - snapValue) < 1 {
                    minVal = min(minVal, top)
                }
            case .x:  // snapValue是Y坐标，找X的范围
                if abs(top - snapValue) < 1 || abs(bottom - snapValue) < 1 || abs(img.y - snapValue) < 1 {
                    minVal = min(minVal, left)
                }
            }
        }
        
        return minVal == .greatestFiniteMagnitude ? 0 : minVal
    }
    
    /// 获取对齐到指定值的所有参考物体在另一轴的最大值
    private func getGuideExtentMax(axis: SnapLine.Axis, snapValue: CGFloat, draggedIds: Set<UUID>) -> CGFloat {
        var maxVal: CGFloat = -.greatestFiniteMagnitude
        
        for img in images {
            if draggedIds.contains(img.id) { continue }
            
            let w = (img.nsImage?.size.width ?? 100) * img.scale
            let h = (img.nsImage?.size.height ?? 100) * img.scale
            
            let left = img.x - w / 2
            let right = img.x + w / 2
            let top = img.y - h / 2
            let bottom = img.y + h / 2
            
            switch axis {
            case .y:
                if abs(left - snapValue) < 1 || abs(right - snapValue) < 1 || abs(img.x - snapValue) < 1 {
                    maxVal = max(maxVal, bottom)
                }
            case .x:
                if abs(top - snapValue) < 1 || abs(bottom - snapValue) < 1 || abs(img.y - snapValue) < 1 {
                    maxVal = max(maxVal, right)
                }
            }
        }
        
        return maxVal == -.greatestFiniteMagnitude ? 0 : maxVal
    }
}