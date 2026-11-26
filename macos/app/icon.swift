import AppKit
import Foundation

let sizes = [(16,1),(16,2),(32,1),(32,2),(128,1),(128,2),(256,1),(256,2),(512,1),(512,2)]
guard CommandLine.arguments.count == 2 else { exit(1) }
let destination = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
for (points, scale) in sizes {
    let pixels = points * scale
    let side = CGFloat(pixels)
    let canvas = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: pixels, pixelsHigh: pixels,
                                  bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                                  colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: canvas)
    let transform = NSAffineTransform()
    transform.scale(by: side / 512)
    transform.concat()
    let tile = NSBezierPath(roundedRect: NSRect(x: 28, y: 28, width: 456, height: 456), xRadius: 106, yRadius: 106)
    NSColor(srgbRed: 0.075, green: 0.205, blue: 0.19, alpha: 1).setFill()
    tile.fill()
    NSColor(srgbRed: 0.71, green: 0.94, blue: 0.72, alpha: 1).setStroke()
    let mark = NSBezierPath(ovalIn: NSRect(x: 126, y: 121, width: 230, height: 230))
    mark.lineWidth = 37
    mark.stroke()
    let bridge = NSBezierPath()
    bridge.move(to: NSPoint(x: 275, y: 278))
    bridge.line(to: NSPoint(x: 365, y: 368))
    bridge.line(to: NSPoint(x: 365, y: 304))
    bridge.lineWidth = 27
    bridge.lineCapStyle = .round
    bridge.lineJoinStyle = .round
    NSColor.white.setStroke()
    bridge.stroke()
    NSGraphicsContext.restoreGraphicsState()
    let suffix = scale == 2 ? "@2x" : ""
    let url = destination.appendingPathComponent("icon_\(points)x\(points)\(suffix).png")
    try canvas.representation(using: .png, properties: [:])!.write(to: url)
}
