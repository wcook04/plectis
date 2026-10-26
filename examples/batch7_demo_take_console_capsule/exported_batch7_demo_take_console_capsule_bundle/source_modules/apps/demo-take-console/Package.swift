// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "demo-take-console",
    platforms: [
        .macOS(.v15),
    ],
    products: [
        .executable(name: "DemoTakeConsoleApp", targets: ["DemoTakeConsoleApp"]),
        .executable(name: "demo-take-transcribe", targets: ["DemoTakeTranscribe"]),
    ],
    dependencies: [
        .package(url: "https://github.com/argmaxinc/WhisperKit", from: "1.0.0"),
    ],
    targets: [
        .executableTarget(
            name: "DemoTakeConsoleApp",
            path: "Sources/DemoTakeConsoleApp"
        ),
        .executableTarget(
            name: "DemoTakeTranscribe",
            dependencies: [
                .product(name: "WhisperKit", package: "WhisperKit"),
            ],
            path: "Sources/DemoTakeTranscribe"
        ),
        .testTarget(
            name: "DemoTakeConsoleAppTests",
            dependencies: ["DemoTakeConsoleApp"],
            path: "Tests/DemoTakeConsoleAppTests"
        ),
    ]
)
