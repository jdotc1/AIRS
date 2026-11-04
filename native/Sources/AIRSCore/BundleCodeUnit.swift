import Foundation
public struct BundleCodeUnit: Sendable {
    public let codeURL: URL
    public let executableURL: URL
    public let infoPath: String
    public let infoBytes: Data
    public let resourcePath: String
}
public struct CodeUnitDeclarationLocations: Sendable {
    public let container: String
    public let infoPath: String
    public let resourcePath: String
    public let executablePrefix: String
}
public enum CodeUnitPreflight {
    public static func data(_ unit: BundleImageProvenance, relativePath: String) throws -> Data {
        try BundleDiscovery.validate(unit, input: unit.bundle.appendingPathComponent(unit.relativePath))
        let bytes = try BundleDiscovery.readMetadata(unit, relativePath: relativePath)
        try BundleDiscovery.validate(unit, input: unit.bundle.appendingPathComponent(unit.relativePath))
        return bytes
    }
    public static func inspect(_ unit: BundleImageProvenance) throws -> BundleCodeUnit {
        let input = unit.bundle.appendingPathComponent(unit.relativePath)
        try BundleDiscovery.validate(unit, input: input)
        let locations = try declarationLocations(relativePath: unit.relativePath)
        let container = locations.container
        let infoPath = locations.infoPath, resources = locations.resourcePath, expectedPrefix = locations.executablePrefix
        let bytes = try BundleDiscovery.readMetadata(unit, relativePath: infoPath)
        guard let plist = try PropertyListSerialization.propertyList(from: bytes, format: nil) as? [String: Any],
              let name = plist["CFBundleExecutable"] as? String,
              !name.isEmpty, name != ".", name != "..", name.utf8.count <= 255,
              !name.contains("/"), !name.contains("\\"), !name.contains("\0"),
              (expectedPrefix + name).utf8.elementsEqual(unit.relativePath.utf8) else {
            throw ReportError.invalidContents("Code unit is not at its exact safe declared executable path.")
        }
        try BundleDiscovery.validate(unit, input: input)
        return .init(codeURL: container.isEmpty ? unit.bundle : unit.bundle.appendingPathComponent(container), executableURL: input,
            infoPath: infoPath, infoBytes: bytes, resourcePath: resources)
    }

    /// Derive conventional paths without opening files or conferring authority.
    public static func declarationLocations(relativePath: String) throws -> CodeUnitDeclarationLocations {
        let parts = relativePath.split(separator: "/", omittingEmptySubsequences: false)
        guard parts.count >= 3, parts.first == "Contents", relativePath.utf8.count <= 4096,
              parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." && !$0.contains("\\") && !$0.contains("\0") }) else {
            throw ReportError.invalidContents("Invalid code unit path.")
        }
        let container = ComponentMetadataReader.container(for: relativePath)
        let ext = URL(fileURLWithPath: container).pathExtension.lowercased()
        guard container.isEmpty ? relativePath.hasPrefix("Contents/MacOS/") : ["app", "xpc", "appex", "framework"].contains(ext) else {
            throw ReportError.invalidContents("Naked helpers and nonconventional code units are unavailable for entitlement reads.")
        }
        let infoPath: String, resources: String, expectedPrefix: String
        if ext == "framework" {
            let suffix = String(relativePath.dropFirst(container.count + 1)).split(separator: "/").map(String.init)
            let version = suffix.count >= 3 && suffix[0] == "Versions" ? "/Versions/" + suffix[1] : ""
            expectedPrefix = container + version + "/"
            resources = expectedPrefix + "Resources"
            infoPath = resources + "/Info.plist"
        } else {
            let prefix = container.isEmpty ? "" : container + "/"
            infoPath = prefix + "Contents/Info.plist"; resources = prefix + "Contents/Resources"
            expectedPrefix = prefix + "Contents/MacOS/"
        }
        return .init(container: container, infoPath: infoPath, resourcePath: resources, executablePrefix: expectedPrefix)
    }
}

public extension BundleDiscoveryEntry {
    static func forCodeUnit(_ provenance: BundleImageProvenance) throws -> Self {
        try BundleDiscovery.validate(provenance, input: provenance.bundle.appendingPathComponent(provenance.relativePath))
        return .init(relativePath: provenance.relativePath, state: "candidate", message: "Explicit code unit", provenance: provenance)
    }
}
