import Darwin
import Foundation

/// Decides whether two local file locations are the same, or one lies below the
/// other, independently of how either path is spelled.
///
/// Foundation's standardizing calls remove a leading `/private` only when the
/// resulting path exists. A destination that does not exist yet and an existing
/// folder beside it can therefore come back with different prefixes, and a
/// string-prefix comparison of the two lets a nested destination through.
/// These functions resolve the deepest existing ancestor through the file
/// system and compare file identity (device and inode) where files exist.
///
/// This is a preflight on names, not a guarantee against a concurrent writer.
/// Nothing is opened, read or created.
public enum PathContainment {
    /// Physical path of the deepest existing ancestor, followed by the
    /// remaining components resolved lexically. `nil` for a URL that is not an
    /// absolute local file URL.
    public static func comparisonKey(_ url: URL) -> String? {
        guard url.isFileURL else { return nil }
        let path = url.path
        guard path.hasPrefix("/"), !path.utf8.contains(0) else { return nil }
        var physical = "/"
        var missing: [Substring] = []
        for component in path.split(separator: "/", omittingEmptySubsequences: true) {
            if component == "." { continue }
            if component == ".." {
                if missing.isEmpty { physical = parent(physical) } else { missing.removeLast() }
                continue
            }
            if missing.isEmpty, let resolved = real(join(physical, component)) {
                physical = resolved
            } else {
                missing.append(component)
            }
        }
        return missing.reduce(physical) { join($0, $1) }
    }

    /// True when both URLs name the same location: equal comparison keys, or
    /// two existing entries with the same device and inode.
    public static func sameLocation(_ first: URL, _ second: URL) -> Bool {
        guard let a = comparisonKey(first), let b = comparisonKey(second) else { return false }
        if a.utf8.elementsEqual(b.utf8) { return true }
        guard let x = identity(a), let y = identity(b) else { return false }
        return x == y
    }

    /// True when `candidate` lies strictly below `root`. `candidate` need not exist.
    public static func isInside(_ candidate: URL, _ root: URL) -> Bool {
        guard let candidateKey = comparisonKey(candidate), let rootKey = comparisonKey(root),
              !candidateKey.utf8.elementsEqual(rootKey.utf8) else { return false }
        let prefix = rootKey == "/" ? "/" : rootKey + "/"
        if candidateKey.utf8.starts(with: prefix.utf8) { return true }
        // Identity also covers spellings that differ only by case or Unicode
        // form on a file system that treats them as one name.
        guard let rootIdentity = identity(rootKey) else { return false }
        var ancestor = parent(candidateKey)
        while true {
            if let current = identity(ancestor), current == rootIdentity { return true }
            if ancestor == "/" { return false }
            ancestor = parent(ancestor)
        }
    }

    public static func isSameOrInside(_ candidate: URL, _ root: URL) -> Bool {
        sameLocation(candidate, root) || isInside(candidate, root)
    }

    private struct Identity: Equatable { let device: dev_t; let inode: ino_t }

    private static func identity(_ path: String) -> Identity? {
        var info = stat()
        guard lstat(path, &info) == 0 else { return nil }
        return Identity(device: info.st_dev, inode: info.st_ino)
    }

    private static func real(_ path: String) -> String? {
        guard let pointer = realpath(path, nil) else { return nil }
        defer { free(pointer) }
        return FileManager.default.string(withFileSystemRepresentation: pointer, length: strlen(pointer))
    }

    private static func join(_ directory: String, _ component: Substring) -> String {
        directory == "/" ? "/" + component : directory + "/" + component
    }

    private static func parent(_ path: String) -> String {
        guard let slash = path.lastIndex(of: "/"), slash != path.startIndex else { return "/" }
        return String(path[..<slash])
    }
}
