// 누끼 1단계 = 사진에서 가림(mask) 뽑기 — macOS Vision(기기 안에서만 처리 · 모델 내려받기 0 · 바깥 전송 0).
// 필요: macOS 14 이상(VNGenerateForegroundInstanceMaskRequest · VNGeneratePersonInstanceMaskRequest 도입 판)
// 사용: swift vision_mask.swift <그림.png> <가림.png> [person|foreground]
//   person     = VNGeneratePersonInstanceMaskRequest(사람만 · 기본 — 사람 옆 물건이 섞이지 않는다 · 가림 해상도가 낮다)
//   foreground = VNGenerateForegroundInstanceMaskRequest(앞에 놓인 것 전부 · portrait_cutout.py 가 쓰는 쪽)
// 출력 = 그림과 같은 크기의 8비트 회색 PNG(255 = 앞 물체 · 부드러운 가장자리 그대로). 합성·가장자리 다듬기·자르기 = portrait_cutout.py.
import Foundation
import Vision
import CoreImage
import ImageIO
import UniformTypeIdentifiers

let a = CommandLine.arguments
guard a.count >= 3 else { FileHandle.standardError.write("사용: swift vision_mask.swift <그림.png> <가림.png> [person|foreground]\n".data(using: .utf8)!); exit(2) }
let mode = a.count > 3 ? a[3] : "person"
guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: a[1]) as CFURL, nil), let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { print("그림을 못 읽음"); exit(1) }
let handler = VNImageRequestHandler(cgImage: img, options: [:])
var mask: CVPixelBuffer
var count = 0
do {
  if mode == "foreground" {
    let req = VNGenerateForegroundInstanceMaskRequest()
    try handler.perform([req])
    guard let obs = req.results?.first else { print("앞 물체 0"); exit(1) }
    count = obs.allInstances.count
    mask = try obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: handler)
  } else {
    let req = VNGeneratePersonInstanceMaskRequest()
    try handler.perform([req])
    guard let obs = req.results?.first else { print("사람 0"); exit(1) }
    count = obs.allInstances.count
    mask = try obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: handler)
  }
} catch { print("Vision 실패: \(error)"); exit(1) }
// 가림(float32 0~1 한 채널) → 8비트 회색 PNG
let ci = CIImage(cvPixelBuffer: mask)
let ctx = CIContext()
guard let cg = ctx.createCGImage(ci, from: ci.extent, format: .L8, colorSpace: CGColorSpaceCreateDeviceGray()) else { print("가림 변환 실패"); exit(1) }
guard let dst = CGImageDestinationCreateWithURL(URL(fileURLWithPath: a[2]) as CFURL, UTType.png.identifier as CFString, 1, nil) else { exit(1) }
CGImageDestinationAddImage(dst, cg, nil)
guard CGImageDestinationFinalize(dst) else { print("쓰기 실패"); exit(1) }
print("{\"mode\":\"\(mode)\",\"instances\":\(count),\"width\":\(cg.width),\"height\":\(cg.height),\"out\":\"\(a[2])\"}")
