// Run with the destination 1024px PNG path as its only argument.
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let size = 1024
let space = CGColorSpace(name: CGColorSpace.sRGB)!
let drawing = CGContext(data: nil, width: size, height: size, bitsPerComponent: 8,
                        bytesPerRow: size * 4, space: space, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
let colors = [CGColor(srgbRed: 0.12, green: 0.35, blue: 0.30, alpha: 1),
              CGColor(srgbRed: 0.035, green: 0.15, blue: 0.14, alpha: 1)] as CFArray
let background = CGGradient(colorsSpace: space, colors: colors, locations: [0, 1])!
drawing.drawLinearGradient(background, start: CGPoint(x: 0, y: 1024), end: CGPoint(x: 1024, y: 0), options: [])
drawing.setLineCap(.round)
func arc(radius: CGFloat, width: CGFloat, from: CGFloat, to: CGFloat, color: CGColor) {
    drawing.setStrokeColor(color)
    drawing.setLineWidth(width)
    drawing.addArc(center: CGPoint(x: 512, y: 512), radius: radius,
                   startAngle: from * .pi / 180, endAngle: to * .pi / 180, clockwise: false)
    drawing.strokePath()
}
arc(radius: 292, width: 52, from: 52, to: 313, color: CGColor(srgbRed: 0.86, green: 0.96, blue: 0.87, alpha: 1))
arc(radius: 201, width: 46, from: 230, to: 487, color: CGColor(srgbRed: 0.51, green: 0.80, blue: 0.68, alpha: 1))
let url = URL(fileURLWithPath: CommandLine.arguments[1]) as CFURL
let file = CGImageDestinationCreateWithURL(url, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(file, drawing.makeImage()!, nil)
guard CGImageDestinationFinalize(file) else { exit(1) }
