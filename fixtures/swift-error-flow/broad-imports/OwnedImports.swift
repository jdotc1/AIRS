import Foundation
struct Item: Decodable { let id: Int }
@inline(never) func loadData(_ url: URL) throws -> Data { try Data(contentsOf: url) }
@inline(never) func decodeItem(_ data: Data) throws -> Item { try JSONDecoder().decode(Item.self, from: data) }
@inline(never) func writeText(_ text: String, _ url: URL) throws { try text.write(to: url, atomically: true, encoding: .utf8) }
let url = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "x")
do { let d = try loadData(url); print(try decodeItem(d).id); try writeText("ok", url) } catch { print(error) }
