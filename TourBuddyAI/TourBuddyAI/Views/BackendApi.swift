import Foundation

struct AgentConfig: Decodable {
    let appId: String, token: String, uid: String, channelName: String, agentUid: String
    enum CodingKeys: String, CodingKey {
        case appId = "app_id", token, uid, channelName = "channel_name", agentUid = "agent_uid"
    }
}
// Backend payload decoded by the poller; older destination-only events omit source.
struct NavigationEvent: Decodable {
    let type: String
    let channelName: String
    let source: String?
    let latitude: Double
    let longitude: Double
    let label: String

    enum CodingKeys: String, CodingKey {
        case type, channelName = "channel_name", source, latitude, longitude, label
    }
}
private struct Envelope<T: Decodable>: Decodable { let code: Int; let data: T; let msg: String? }
private struct StartData: Decodable { let agentId: String; enum CodingKeys: String, CodingKey { case agentId = "agent_id" } }

// Owns HTTP communication with FastAPI, including consuming queued navigation events.
struct BackendApi {
    let baseURL: URL
    var session: URLSession = .shared

    func getConfig() async throws -> AgentConfig {
        var c = URLComponents(url: baseURL.appendingPathComponent("get_config"), resolvingAgainstBaseURL: false)!
        c.queryItems = [URLQueryItem(name: "uid", value: "0")]
        let (data, _) = try await session.data(from: c.url!)
        return try JSONDecoder().decode(Envelope<AgentConfig>.self, from: data).data
    }
    func startAgent(channelName: String, rtcUid: Int, userUid: Int) async throws -> String {
        let body = ["channelName": channelName, "rtcUid": rtcUid, "userUid": userUid] as [String: Any]
        let data = try await post("startAgent", body)
        return try JSONDecoder().decode(Envelope<StartData>.self, from: data).data.agentId
    }
    func stopAgent(agentId: String) async throws {
        _ = try await post("stopAgent", ["agentId": agentId])
    }
    func getNavigationEvent(channelName: String) async throws -> NavigationEvent? {
        let pathCharacters = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
        guard let encodedChannelName = channelName.addingPercentEncoding(withAllowedCharacters: pathCharacters),
              var components = URLComponents(
                url: baseURL.appendingPathComponent("navigation-event"),
                resolvingAgainstBaseURL: false
              ) else {
            throw URLError(.badURL)
        }
        components.percentEncodedPath += "/\(encodedChannelName)"
        guard let url = components.url else { throw URLError(.badURL) }

        let (data, response) = try await session.data(from: url)
        guard let response = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }
        if response.statusCode == 404 { return nil }
        guard (200..<300).contains(response.statusCode) else { throw URLError(.badServerResponse) }

        return try JSONDecoder().decode(Envelope<NavigationEvent>.self, from: data).data
    }
    private func post(_ path: String, _ body: [String: Any]) async throws -> Data {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = "POST"; req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, _) = try await session.data(for: req)
        return data
    }
}
