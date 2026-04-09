using System.Text.Json.Serialization;

namespace DesktopApp.Models;

/// <summary>
/// A named connection to a getMediaPlayerInfo server instance.
/// </summary>
public record ServerConnection
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public string Name { get; init; } = "My Server";
    public string Host { get; init; } = "localhost";
    public int Port { get; init; } = 8765;

    [JsonIgnore]
    public string BaseUrl => $"http://{Host}:{Port}";

    [JsonIgnore]
    public string WsUrl => $"ws://{Host}:{Port}/ws";

    [JsonIgnore]
    public string NowPlayingUrl => $"{BaseUrl}/now-playing";

    public override string ToString() => $"{Name} ({Host}:{Port})";
}

/// <summary>
/// Application configuration serialised to/from JSON.
/// </summary>
public class AppConfig
{
    public List<ServerConnection> Connections { get; set; } = [new ServerConnection()];

    public int ActiveConnectionIndex { get; set; } = 0;

    /// <summary>Polling interval in milliseconds when WebSocket is not available.</summary>
    public int PollingIntervalMs { get; set; } = 2000;

    /// <summary>Prefer WebSocket over HTTP polling.</summary>
    public bool UseWebSocket { get; set; } = true;

    public bool NotificationsEnabled { get; set; } = true;

    /// <summary>"Default", "Light", or "Dark".</summary>
    public string Theme { get; set; } = "Default";

    public bool MinimizeToTray { get; set; } = true;

    public bool StartMinimized { get; set; } = false;

    public bool DiscordPresenceEnabled { get; set; } = false;

    public bool RegisterStartup { get; set; } = false;
}
