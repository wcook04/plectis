// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "zenith-macos",
    platforms: [
        .macOS(.v15),
    ],
    products: [
        .executable(name: "ZenithApp", targets: ["ZenithApp"]),
    ],
    targets: [
        .executableTarget(
            name: "ZenithApp",
            path: "Sources/ZenithApp"
        ),
        .testTarget(
            name: "ZenithAppTests",
            dependencies: ["ZenithApp"],
            path: "Tests/ZenithAppTests"
        ),
    ]
)
