import SwiftUI
import AppKit

struct CaptionScrollTextView: NSViewRepresentable {
    let lines: [SubtitleDisplayLine]
    let settings: AppSettings

    func makeNSView(context: Context) -> NSScrollView {
        let scrollView = NSScrollView()
        scrollView.drawsBackground = false
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder
        scrollView.scrollerStyle = .overlay
        scrollView.verticalScroller?.controlSize = .small

        let textView = NSTextView()
        textView.drawsBackground = false
        textView.isEditable = false
        textView.isSelectable = false
        textView.textContainerInset = NSSize(width: 0, height: 8)
        textView.textContainer?.widthTracksTextView = true
        textView.isVerticallyResizable = true
        textView.isHorizontallyResizable = false
        textView.autoresizingMask = [.width]
        textView.layoutManager?.allowsNonContiguousLayout = false

        scrollView.documentView = textView
        return scrollView
    }

    func updateNSView(_ scrollView: NSScrollView, context: Context) {
        guard let textView = scrollView.documentView as? NSTextView else { return }

        let needsUpdate = context.coordinator.lastLines != lines
            || context.coordinator.lastSettings != settings

        if needsUpdate {
            let isNearBottom = isNearBottom(scrollView)

            if let textStorage = textView.textStorage {
                textStorage.beginEditing()
                textStorage.setAttributedString(attributedText(lines))
                textStorage.endEditing()
            }

            context.coordinator.lastLines = lines
            context.coordinator.lastSettings = settings

            if isNearBottom || lines.isEmpty {
                DispatchQueue.main.async {
                    scrollSmoothlyToBottom(in: scrollView)
                }
            }
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    private func attributedText(_ lines: [SubtitleDisplayLine]) -> NSAttributedString {
        let result = NSMutableAttributedString()
        for (index, line) in lines.enumerated() {
            if index > 0 {
                result.append(NSAttributedString(string: "\n"))
            }
            result.append(NSAttributedString(string: line.text, attributes: attributes(for: line.role)))
        }
        return result
    }

    private func attributes(for role: SubtitleDisplayRole) -> [NSAttributedString.Key: Any] {
        let paragraph = NSMutableParagraphStyle()
        paragraph.lineSpacing = role == .spacer ? 2 : 4
        paragraph.alignment = .left

        let scale: Double = role == .original ? 0.78 : 1.0
        let font = settings.subtitleFontName.nsFont(
            size: CGFloat(settings.subtitleFontSize * scale),
            bold: role == .translated && settings.subtitleIsBold,
            italic: settings.subtitleIsItalic
        )

        let color: NSColor
        switch role {
        case .original:
            color = settings.subtitleColor.nsColor.withAlphaComponent(0.74)
        case .translated:
            color = settings.subtitleColor.nsColor
        case .spacer:
            color = .clear
        }

        var attributes: [NSAttributedString.Key: Any] = [
            .font: font,
            .foregroundColor: color,
            .paragraphStyle: paragraph
        ]

        if settings.subtitleIsUnderline, role == .translated {
            attributes[.underlineStyle] = NSUnderlineStyle.single.rawValue
        }

        return attributes
    }

    private func scrollSmoothlyToBottom(in scrollView: NSScrollView) {
        guard let documentView = scrollView.documentView else { return }

        let documentHeight = documentView.bounds.height
        let clipHeight = scrollView.contentView.bounds.height
        let maxY = max(0, documentHeight - clipHeight)
        let targetPoint = NSPoint(x: 0, y: maxY)

        NSAnimationContext.runAnimationGroup { context in
            context.duration = 0.25
            context.timingFunction = CAMediaTimingFunction(name: .easeOut)
            scrollView.contentView.animator().setBoundsOrigin(targetPoint)
        }
        scrollView.reflectScrolledClipView(scrollView.contentView)
    }

    private func isNearBottom(_ scrollView: NSScrollView) -> Bool {
        guard let documentView = scrollView.documentView else { return true }
        let maxY = max(0, documentView.bounds.height - scrollView.contentSize.height)
        let currentY = scrollView.contentView.bounds.origin.y
        return maxY - currentY < 50
    }

    final class Coordinator {
        var lastLines: [SubtitleDisplayLine] = []
        var lastSettings: AppSettings?
    }
}
