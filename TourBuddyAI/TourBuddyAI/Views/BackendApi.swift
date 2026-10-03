import Foundation

struct AgentConfig: Decodable {
    let appId: String, token: String, uid: String, channelName: String, agentUid: String
    enum CodingKeys: String, CodingKey {
        case appId = "app_id", token, uid, channelName = "channel_name", agentUid = "agent_uid"
    }
}
private struct Envelope<T: Decodable>: Decodable { let code: Int; let data: T; let msg: String? }
private struct StartData: Decodable { let agentId: String; enum CodingKeys: String, CodingKey { case agentId = "agent_id" } }

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
    private func post(_ path: String, _ body: [String: Any]) async throws -> Data {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = "POST"; req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, _) = try await session.data(for: req)
        return data
    }
}
