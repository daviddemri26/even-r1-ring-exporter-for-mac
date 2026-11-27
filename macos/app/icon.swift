import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

private func fail(_ message: String) -> Never {
    fputs("\(message)\n", stderr)
    exit(1)
}

private func writeIcon(mark: CGImage, pixels: Int, to url: URL) {
    guard let colorSpace = CGColorSpace(name: CGColorSpace.sRGB),
          let canvas = CGContext(data: nil, width: pixels, height: pixels, bitsPerComponent: 8,
                                 bytesPerRow: 0, space: colorSpace,
                                 bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
        fail("Could not create the \(pixels)-pixel icon canvas.")
    }

    // The 24-pixel Even Hub listing mark is transparent. Keep its original pixel
    // grid centered on a dark tile so it remains visible on light backgrounds.
    let scale = CGFloat(pixels) / 32
    canvas.scaleBy(x: scale, y: scale)
    canvas.addPath(CGPath(roundedRect: CGRect(x: 0, y: 0, width: 32, height: 32),
                          cornerWidth: 7, cornerHeight: 7, transform: nil))
    canvas.setFillColor(red: 24 / 255.0, green: 33 / 255.0, blue: 32 / 255.0, alpha: 1)
    canvas.fillPath()
    // The source doubles each logical pixel. Nearest-neighbor sampling also
    // preserves the complete 12-pixel mark in the smallest Finder slot.
    canvas.interpolationQuality = .none
    canvas.draw(mark, in: CGRect(x: 4, y: 4, width: 24, height: 24))

    guard let image = canvas.makeImage(),
          let output = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil) else {
        fail("Could not create \(url.lastPathComponent).")
    }
    CGImageDestinationAddImage(output, image, nil)
    guard CGImageDestinationFinalize(output) else { fail("Could not write \(url.lastPathComponent).") }
}

let args = CommandLine.arguments
guard args.count == 3 || args.count == 4 else {
    fail("Usage: icon.swift SOURCE.png OUTPUT.iconset | SOURCE.png OUTPUT.png PIXELS")
}
let sourceURL = URL(fileURLWithPath: args[1])
guard let source = CGImageSourceCreateWithURL(sourceURL as CFURL, nil),
      let mark = CGImageSourceCreateImageAtIndex(source, 0, nil),
      mark.width == 24 && mark.height == 24 else { fail("Expected the 24 × 24 Even Hub listing PNG.") }

let destination = URL(fileURLWithPath: args[2])
if args.count == 4 {
    guard let pixels = Int(args[3]), (1...1024).contains(pixels) else { fail("Expected a size between 1 and 1024 pixels.") }
    writeIcon(mark: mark, pixels: pixels, to: destination)
} else {
    for points in [16, 32, 128, 256, 512] {
        for scale in 1...2 {
            let suffix = scale == 2 ? "@2x" : ""
            let name = "icon_\(points)x\(points)\(suffix).png"
            writeIcon(mark: mark, pixels: points * scale, to: destination.appendingPathComponent(name))
        }
    }
}
